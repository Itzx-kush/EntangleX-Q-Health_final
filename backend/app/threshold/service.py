import numpy as np
from uuid import uuid4
from datetime import datetime

from ..database import session_scope
from ..storage.entities import ThresholdAnalysisStudy
from ..storage.files import load_model
from ..api.schemas import TrainingConfig
from ..data.splitting import prepare_data
from ..evaluation.calibration import base_pipeline
from ..utils.serialization import fingerprint, utcnow
from ..utils.errors import AppError
from .schemas import ThresholdAnalysisRequest, ThresholdPreflightResponse
from .metrics import calculate_threshold_metrics, select_threshold
from ..evaluation.context import resolve_model_evaluation_context

from sklearn.model_selection import GroupShuffleSplit, train_test_split, cross_val_predict


def get_predictions_for_threshold(req: ThresholdAnalysisRequest, data, estimator, run_config):
    if req.selection_protocol == "dedicated_split":
        X_test = data.X.iloc[data.test]
        y_test = data.y[data.test]
        
        if req.sampling_unit == "grouped_samples":
            from sklearn.model_selection import GroupShuffleSplit
            splitter = GroupShuffleSplit(n_splits=1, test_size=1.0 - req.selection_size, random_state=req.split_seed)
            groups = data.frame.iloc[data.test][req.group_column]
            calib_idx, eval_idx = next(splitter.split(X_test, y_test, groups=groups))
        else:
            from sklearn.model_selection import train_test_split
            import numpy as np
            calib_idx, eval_idx = train_test_split(
                np.arange(len(y_test)), 
                test_size=1.0 - req.selection_size, 
                random_state=req.split_seed, 
                stratify=y_test
            )
        
        X_sel, y_sel = X_test.iloc[calib_idx], y_test[calib_idx]
        X_eval, y_eval = X_test.iloc[eval_idx], y_test[eval_idx]
        
        import numpy as np
        if hasattr(estimator, "predict_proba"):
            y_prob_sel = estimator.predict_proba(X_sel)[:, 1]
            y_prob_eval = estimator.predict_proba(X_eval)[:, 1]
        else:
            scores_sel = estimator.decision_function(X_sel)
            y_prob_sel = 1 / (1 + np.exp(-np.clip(scores_sel, -700, 700)))
            scores_eval = estimator.decision_function(X_eval)
            y_prob_eval = 1 / (1 + np.exp(-np.clip(scores_eval, -700, 700)))
            
        return y_sel, y_prob_sel, y_eval, y_prob_eval

def preflight(req: ThresholdAnalysisRequest) -> ThresholdPreflightResponse:
    with session_scope() as session:
        context = resolve_model_evaluation_context(
            session, str(req.model_id), str(req.dataset_id),
            str(req.dataset_version_id) if req.dataset_version_id else None,
        )
        base_config = context.training_config
        
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
        return ThresholdPreflightResponse(
            feasible=False, limitations=limitations, method_support={},
            configuration_fingerprint=context.configuration_fingerprint,
            source_context_type=context.source_context_type,
        )
        
    if len(data.test) < 10:
        limitations.append("Insufficient evaluation samples.")
        feasible = False
        
    if req.target_value is not None and (req.target_value < 0 or req.target_value > 1):
        limitations.append("Invalid target value.")
        feasible = False
        
    return ThresholdPreflightResponse(
        feasible=feasible,
        limitations=limitations,
        method_support={"dedicated_split": True},
        configuration_fingerprint=context.configuration_fingerprint,
        source_context_type=context.source_context_type,
    )

def execute_threshold_study(study_id: str):
    with session_scope() as session:
        study = session.get(ThresholdAnalysisStudy, study_id)
        if not study: return
        study.status = "running"
        req = ThresholdAnalysisRequest.model_validate(study.configuration)
        
        context = resolve_model_evaluation_context(
            session, study.model_id, study.dataset_id, study.dataset_version_id
        )
        model = context.model
        base_config = context.training_config
        study.provenance = context.source_context()
        
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
            
        y_sel, y_prob_sel, y_eval, y_prob_eval = get_predictions_for_threshold(req, data, estimator, base_config)
        
        # 1. Sweep on selection set
        results, roc_points, pr_points = calculate_threshold_metrics(
            y_sel, y_prob_sel, 
            t_min=req.threshold_min, 
            t_max=req.threshold_max, 
            t_step=req.threshold_step, fp_cost=req.false_positive_cost, fn_cost=req.false_negative_cost
        )
        
        # 2. Choose threshold
        chosen, feasible, reason = select_threshold(
            results, 
            method=req.selection_method, 
            target=req.fixed_threshold if req.selection_method == "fixed_user_threshold" else req.target_value,
            tie_breaker=req.tie_breaking_policy
        )
        
        # 3. Final evaluation on evaluation set
        if feasible:
            eval_results, _, _ = calculate_threshold_metrics(
                y_eval, y_prob_eval,
                t_min=chosen["threshold"],
                t_max=chosen["threshold"],
                t_step=1.0, fp_cost=req.false_positive_cost, fn_cost=req.false_negative_cost
            )
            final_operating_point = eval_results[0]
            final_operating_point["threshold"] = chosen["threshold"]
            
            # 4. Local Robustness Analysis
            robustness_results = []
            for delta in [-0.05, -0.01, 0.01, 0.05]:
                t_neighbor = max(0.0, min(1.0, chosen["threshold"] + delta))
                n_metrics, _, _ = calculate_threshold_metrics(y_eval, y_prob_eval, t_min=t_neighbor, t_max=t_neighbor, t_step=1.0, fp_cost=req.false_positive_cost, fn_cost=req.false_negative_cost)
                n_metrics[0]["threshold"] = t_neighbor
                n_metrics[0]["delta"] = delta
                robustness_results.append(n_metrics[0])
            
        else:
            final_operating_point = None
            robustness_results = []
        
        with session_scope() as session:
            study = session.get(ThresholdAnalysisStudy, study_id)
            study.status = "completed"
            study.results = {
                "sweep": results, # selection sweep
                "selected_operating_point": final_operating_point, # final eval metrics at the locked threshold!
                "selection_operating_point": chosen, # original metrics on selection set for transparency
                "feasible": feasible,
                "robustness": robustness_results,
            }
            study.curves = {
                "roc": roc_points,
                "pr": pr_points
            }
            if not feasible:
                study.limitations = (study.limitations or []) + [reason]
            study.summary = {
                "selection_samples": len(y_sel),
                "evaluated_samples": len(y_eval),
                "positive_events": int(np.sum(y_eval)),
                "negative_events": int(len(y_eval) - np.sum(y_eval)),
                "prevalence": float(np.sum(y_eval) / len(y_eval)) if len(y_eval) > 0 else 0
            }
            study.provenance = context.source_context()
            study.provenance["threshold_protocol"] = {
                "selection_protocol": req.selection_protocol,
                "selection_method": req.selection_method,
                "selection_population": "dedicated selection subset",
                "evaluation_population": "separate frozen evaluation subset",
                "threshold_frozen_before_evaluation": True,
            }
            if context.source_context_type == "verified_demo_experiment":
                study.limitations = list(study.limitations or []) + [
                    "Derived from the immutable verified precomputed demo model context; no live training Run is claimed."
                ]
            study.completed_at = datetime.utcnow()
            
    except Exception as exc:
        with session_scope() as session:
            study = session.get(ThresholdAnalysisStudy, study_id)
            study.status = "failed"
            study.failure = {"code": "threshold_failed", "message": str(exc)}
            study.completed_at = datetime.utcnow()
