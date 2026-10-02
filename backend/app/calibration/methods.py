import numpy as np
from scipy.optimize import minimize
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

class TemperatureScaling(BaseEstimator, ClassifierMixin):
    """Temperature scaling calibrator for binary classification."""
    def __init__(self):
        self.temperature_ = 1.0
        self.classes_ = np.array([0, 1])

    def fit(self, scores, y):
        """Fit temperature to minimize log loss.
        Expects scores to be logits or unbounded decision scores.
        """
        def objective(t):
            t_val = t[0]
            # stable sigmoid
            logits = scores / t_val
            p = 1 / (1 + np.exp(-np.clip(logits, -700, 700)))
            p = np.clip(p, 1e-15, 1 - 1e-15)
            return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))

        # Optimize T > 0
        res = minimize(objective, [1.0], bounds=[(1e-3, 100.0)], method="L-BFGS-B")
        self.temperature_ = res.x[0]
        return self

    def predict_proba(self, scores):
        logits = scores / self.temperature_
        p1 = 1 / (1 + np.exp(-np.clip(logits, -700, 700)))
        return np.vstack([1 - p1, p1]).T

    def predict(self, scores):
        return (self.predict_proba(scores)[:, 1] >= 0.5).astype(int)

def fit_calibrator(base_estimator, X_calib, y_calib, method: str):
    if method == "none":
        return base_estimator

    if method in ["sigmoid", "isotonic"]:
        calibrator = CalibratedClassifierCV(
            estimator=base_estimator,
            method=method,
            cv="prefit"
        )
        calibrator.fit(X_calib, y_calib)
        return calibrator

    if method == "temperature_scaling":
        if hasattr(base_estimator, "decision_function"):
            scores = base_estimator.decision_function(X_calib)
        else:
            p = base_estimator.predict_proba(X_calib)[:, 1]
            p = np.clip(p, 1e-15, 1 - 1e-15)
            scores = np.log(p / (1 - p)) # logits
            
        ts = TemperatureScaling()
        ts.fit(scores, y_calib)
        
        # We need a wrapper to chain base_estimator and ts
        class TSWrap:
            def __init__(self, base, temp_scaler):
                self.base = base
                self.ts = temp_scaler
                self.classes_ = base.classes_
            def predict_proba(self, X):
                if hasattr(self.base, "decision_function"):
                    s = self.base.decision_function(X)
                else:
                    p = self.base.predict_proba(X)[:, 1]
                    p = np.clip(p, 1e-15, 1 - 1e-15)
                    s = np.log(p / (1 - p))
                return self.ts.predict_proba(s)
            def predict(self, X):
                return self.ts.predict(X)
        return TSWrap(base_estimator, ts)
        
    raise ValueError(f"Unsupported calibration method: {method}")

