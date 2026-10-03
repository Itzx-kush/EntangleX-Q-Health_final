from uuid import uuid4
from sqlalchemy import select
from datetime import datetime
import numpy as np

from ..database import session_scope
from ..storage.entities import CalibrationStudy
from ..data.splitting import prepare_data
from ..api.schemas import TrainingConfig
from .schemas import CalibrationRequest, CalibrationPreflightResponse
from ..utils.errors import AppError
from ..utils.serialization import fingerprint
from ..storage.files import load_model
from ..evaluation.calibration import base_pipeline
from .methods import fit_calibrator
from .metrics import calculate_calibration_metrics
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from ..evaluation.context import resolve_model_evaluation_context

CLASSICAL_MODELS = {"logistic_regression", "svm", "random_forest"}

def _get_evaluation_data(req: CalibrationRequest, base_config: TrainingConfig):
    # Determine the test evaluation subset
    config = base_config.model_copy(update={
        "dataset_id": req.dataset_id,
        "dataset_version_id": req.dataset_version_id,
        "sampling_unit": req.sampling_unit,
        "group_column": req.group_column,
        "test_size": req.test_size,
        "seed": req.split_seed,
    })
    return prepare_data(config)

def preflight(req: CalibrationRequest) -> CalibrationPreflightResponse:
    with session_scope() as session:
        context = resolve_model_evaluation_context(
            session, str(req.model_id), str(req.dataset_id),
            str(req.dataset_version_id) if req.dataset_version_id else None,
        )
        model = context.model
        base_config = context.training_config
    
    limitations = []
    feasible = True
    method_support = {
        "sigmoid": model.model_type in CLASSICAL_MODELS,
        "isotonic": model.model_type in CLASSICAL_MODELS,
        "temperature_scaling": model.model_type in CLASSICAL_MODELS,
        "none": model.model_type in CLASSICAL_MODELS,
    }
    if model.model_type not in CLASSICAL_MODELS:
        return CalibrationPreflightResponse(
            feasible=False,
            limitations=["Calibration is not applicable to quantum-family models under the current research protocol."],
            method_support=method_support,
            configuration_fingerprint=context.configuration_fingerprint,
            source_context_type=context.source_context_type,
            model_family="quantum",
        )
    
    try:
        data = _get_evaluation_data(req, base_config)
    except Exception as exc:
        limitations.append(f"Data preparation failed: {exc}")
        return CalibrationPreflightResponse(
            feasible=False, limitations=limitations, method_support=method_support,
            configuration_fingerprint=context.configuration_fingerprint,
            source_context_type=context.source_context_type, model_family="classical",
        )

    if len(data.test) < 10:
        limitations.append("Insufficient evaluation samples.")
        feasible = False

    if req.calibration_method == "isotonic" and len(data.test) < 50:
        limitations.append("Isotonic calibration requires at least 50 calibration samples.")
        method_support["isotonic"] = False
        if req.calibration_method == "isotonic":
            feasible = False
            
    return CalibrationPreflightResponse(
        feasible=feasible,
        limitations=limitations,
        method_support=method_support,
        configuration_fingerprint=context.configuration_fingerprint,
        source_context_type=context.source_context_type,
        model_family="classical",
    )

def execute_calibration_study(study_id: str):
    with session_scope() as session:
        study = session.get(CalibrationStudy, study_id)
        if not study: return
        study.status = "running"
        req = CalibrationRequest.model_validate(study.configuration)
        
        context = resolve_model_evaluation_context(
            session, study.model_id, study.dataset_id, study.dataset_version_id
        )
        model = context.model
        base_config = context.training_config
        study.provenance = context.source_context()
        data = _get_evaluation_data(req, base_config)
        
    try:
        bundle = load_model(study.model_id, model.artifact_sha256)
        estimator = base_pipeline(bundle["estimator"]) # get base model
        
        X_test = data.X.iloc[data.test]
        y_test = data.y[data.test]
        
        if req.calibration_method == "none":
            # No fitting needed
            X_calib, y_calib = None, None
            X_eval, y_eval = X_test, y_test
        else:
            if req.calibration_protocol == "dedicated_split":
                # Split the test set into calibration and final evaluation
                if req.sampling_unit == "grouped_samples":
                    splitter = GroupShuffleSplit(n_splits=1, test_size=1.0 - req.calibration_size, random_state=req.split_seed)
                    groups = data.frame.iloc[data.test][req.group_column]
                    calib_idx, eval_idx = next(splitter.split(X_test, y_test, groups=groups))
                else:
                    calib_idx, eval_idx = train_test_split(
                        np.arange(len(y_test)), 
                        test_size=1.0 - req.calibration_size, 
                        random_state=req.split_seed, 
                        stratify=y_test
                    )
                X_calib, y_calib = X_test.iloc[calib_idx], y_test[calib_idx]
                X_eval, y_eval = X_test.iloc[eval_idx], y_test[eval_idx]
            elif req.calibration_protocol == "out_of_fold":
                raise NotImplementedError("out_of_fold requires retraining the base estimator, use dedicated_split.")
            else:
                raise ValueError("Unsupported protocol.")
                
        calibrator = fit_calibrator(estimator, X_calib, y_calib, req.calibration_method)
        
        if hasattr(calibrator, "predict_proba"):
            y_prob = calibrator.predict_proba(X_eval)[:, 1]
        else:
            scores = calibrator.decision_function(X_eval)
            y_prob = 1 / (1 + np.exp(-np.clip(scores, -700, 700)))
            
        metrics, curve = calculate_calibration_metrics(y_eval, y_prob, n_bins=req.bins)
        
        with session_scope() as session:
            study = session.get(CalibrationStudy, study_id)
            study.status = "completed"
            study.metrics = metrics
            study.curves = {"reliability_curve": curve}
            study.completed_at = datetime.utcnow()
            study.summary = {
                "evaluated_samples": len(y_eval),
                "calibration_samples": len(y_calib) if y_calib is not None else 0,
                "positive_events": int(np.sum(y_eval)),
                "negative_events": int(len(y_eval) - np.sum(y_eval))
            }
            study.provenance = context.source_context()
            study.limitations = list(study.limitations or [])
            if context.source_context_type == "verified_demo_experiment":
                study.limitations.append(
                    "Derived from the immutable verified precomputed demo model context; no live training Run is claimed."
                )
            
    except Exception as exc:
        with session_scope() as session:
            study = session.get(CalibrationStudy, study_id)
            study.status = "failed"
            study.failure = {"code": "calibration_failed", "message": str(exc)}
            study.completed_at = datetime.utcnow()
