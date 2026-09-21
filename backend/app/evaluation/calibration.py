from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

def with_calibration(pipeline, method: str, folds: int, seed: int):
    """Wrap the WHOLE unfitted pipeline so transforms refit inside inner CV.

    ensemble=False uses out-of-fold predictions for calibration and a final
    base pipeline fitted on all relevant training data. Outer test data is not used.
    """
    if method == "none":
        return pipeline
    return CalibratedClassifierCV(
        estimator=pipeline, method=method,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed),
        ensemble=False, n_jobs=1,
    )

def base_pipeline(fitted_estimator):
    if isinstance(fitted_estimator, CalibratedClassifierCV):
        return fitted_estimator.calibrated_classifiers_[0].estimator
    return fitted_estimator
