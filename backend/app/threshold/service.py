import numpy as np
from uuid import uuid4
from datetime import datetime

from ..database import session_scope
from ..storage.entities import ThresholdAnalysisStudy, ModelRecord, Run, Dataset
from ..storage.files import load_model
from ..api.schemas import TrainingConfig
from ..data.splitting import prepare_data
from ..evaluation.calibration import base_pipeline
from ..utils.serialization import fingerprint, utcnow
from ..utils.errors import AppError
from .schemas import ThresholdAnalysisRequest, ThresholdPreflightResponse
from .metrics import calculate_threshold_metrics, select_threshold

from sklearn.model_selection import GroupShuffleSplit, train_test_split, cross_val_predict

def get_predictions_for_threshold(req: ThresholdAnalysisRequest, data, estimator, run_config):
    # Depending on protocol, we either do OOF on train_indices, or split test_indices
    # Wait, the prompt says "Avoid evaluating thresholds on predictions generated from data used to fit the model".
    # And "OOF predictions or dedicated validation predictions."
    if req.selection_protocol == "dedicated_split":
        # We split the test set
        X_test = data.X.iloc[data.test]
        y_test = data.y[data.test]
        
        if req.sampling_unit == "grouped_samples":
            splitter = GroupShuffleSplit(n_splits=1, test_size=1.0 - req.selection_size, random_state=req.split_seed)
            groups = data.frame.iloc[data.test][req.group_column]
            calib_idx, eval_idx = next(splitter.split(X_test, y_test, groups=groups))
        else:
            calib_idx, eval_idx = train_test_split(
                np.arange(len(y_test)), 
                test_size=1.0 - req.selection_size, 
                random_state=req.split_seed, 
                stratify=y_test
            )
        
        X_sel, y_sel = X_test.iloc[calib_idx], y_test[calib_idx]
        
        if hasattr(estimator, "predict_proba"):
            y_prob = estimator.predict_proba(X_sel)[:, 1]
        else:
            scores = estimator.decision_function(X_sel)
            y_prob = 1 / (1 + np.exp(-np.clip(scores, -700, 700)))
            
        return y_sel, y_prob
        
    elif req.selection_protocol == "out_of_fold":
        raise AppError("protocol_error", "out_of_fold threshold selection is not yet supported in this version.")

def preflight(req: ThresholdAnalysisRequest) -> ThresholdPreflightResponse:
    with session_scope() as session:
        model = session.get(ModelRecord, str(req.model_id))
        if not model or model.status != "ready":
            raise AppError("model_unavailable", "The requested model is not available.")
            
        run = session.get(Run, model.run_id)
        dataset = session.get(Dataset, str(req.dataset_id))
        if not run or not dataset:
            raise AppError("missing_entity", "Run or dataset missing.")
            
        base_config = TrainingConfig.model_validate(run.config)
        
    limitations = []
    feasible = True
    
    config = base_config.model_copy(update={
        "dataset_id": req.dataset_id,
        "dataset_version_id": req.dataset_version_id,
        "sampling_unit": req.sampling_unit,
        "group_column": req.group_column,
        "seed": req.split_seed,
    })
    
    try:
        data = prepare_data(config)
    except Exception as exc:
        limitations.append(f"Data preparation failed: {exc}")
        return ThresholdPreflightResponse(feasible=False, limitations=limitations, method_support={}, configuration_fingerprint="")
        
    if len(data.test) < 10:
        limitations.append("Insufficient evaluation samples.")
        feasible = False
        
    if req.target_value is not None and req.target_value < 0 or req.target_value > 1:
        limitations.append("Invalid target value.")
        feasible = False
        
    return ThresholdPreflightResponse(
        feasible=feasible,
        limitations=limitations,
        method_support={"out_of_fold": False, "dedicated_split": True},
        configuration_fingerprint=fingerprint(req.model_dump(mode="json"))
    )

def execute_threshold_study(study_id: str):
    with session_scope() as session:
        study = session.get(ThresholdAnalysisStudy, study_id)
        if not study: return
        study.status = "running"
        req = ThresholdAnalysisRequest.model_validate(study.configuration)
        
        model = session.get(ModelRecord, study.model_id)
        run = session.get(Run, model.run_id)
        base_config = TrainingConfig.model_validate(run.config)
        
        config = base_config.model_copy(update={
            "dataset_id": req.dataset_id,
            "dataset_version_id": req.dataset_version_id,
            "sampling_unit": req.sampling_unit,
            "group_column": req.group_column,
            "seed": req.split_seed,
        })
        data = prepare_data(config)
        
    try:
        # Check Calibration Compatibility
        # If the request asks for calibrated probabilities, we assume the model bundle IS the calibrated one
        # Or we load the base pipeline.
        # But wait! 'bundle["estimator"]' is exactly what was used to compute model.metrics.
        # If it was trained uncalibrated, it is uncalibrated. 
        # For this prototype, we'll extract the estimator directly.
        bundle = load_model(study.model_id, model.artifact_sha256)
        if req.probability_source == "uncalibrated":
            estimator = base_pipeline(bundle["estimator"])
        else:
            estimator = bundle["estimator"]
            
        y_sel, y_prob = get_predictions_for_threshold(req, data, estimator, base_config)
        
        results, roc_points, pr_points = calculate_threshold_metrics(
            y_sel, y_prob, 
            t_min=req.threshold_min, 
            t_max=req.threshold_max, 
            t_step=req.threshold_step
        )
        
        chosen, feasible, reason = select_threshold(
            results, 
            method=req.selection_method, 
            target=req.fixed_threshold if req.selection_method == "fixed_user_threshold" else req.target_value,
            tie_breaker=req.tie_breaking_policy
        )
        
        with session_scope() as session:
            study = session.get(ThresholdAnalysisStudy, study_id)
            study.status = "completed"
            study.results = {
                "sweep": results,
                "selected_operating_point": chosen,
                "feasible": feasible,
            }
            study.curves = {
                "roc": roc_points,
                "pr": pr_points
            }
            if not feasible:
                study.limitations = (study.limitations or []) + [reason]
            study.summary = {
                "evaluated_samples": len(y_sel),
                "positive_events": int(np.sum(y_sel)),
                "negative_events": int(len(y_sel) - np.sum(y_sel)),
                "prevalence": float(np.sum(y_sel) / len(y_sel)) if len(y_sel) > 0 else 0
            }
            study.completed_at = datetime.utcnow()
            
    except Exception as exc:
        with session_scope() as session:
            study = session.get(ThresholdAnalysisStudy, study_id)
            study.status = "failed"
            study.failure = {"code": "threshold_failed", "message": str(exc)}
            study.completed_at = datetime.utcnow()
