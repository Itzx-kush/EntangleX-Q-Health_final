from functools import partial
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif, mutual_info_classif
from sklearn.utils.validation import check_is_fitted

class BiomedicalFeatures(TransformerMixin, BaseEstimator):
    """Deterministic feature engineering. No target or learned test statistics."""
    def __init__(self, log_features=(), ratios=()):
        self.log_features = log_features
        self.ratios = ratios

    def fit(self, X, y=None):
        self.feature_names_in_ = np.array(X.columns, dtype=object)
        self.n_features_in_ = len(self.feature_names_in_)
        names = set(X.columns)
        for feature in self.log_features:
            if feature not in names or not pd.api.types.is_numeric_dtype(X[feature]):
                raise ValueError("Log transforms require selected numeric features.")
            if (X[feature].dropna() < 0).any():
                raise ValueError("log1p feature engineering requires nonnegative training values.")
        for ratio in self.ratios:
            if ratio["name"] in names or ratio["numerator"] not in X or ratio["denominator"] not in X:
                raise ValueError("Ratio names must be new and reference selected original columns.")
            if not all(pd.api.types.is_numeric_dtype(X[c]) for c in [ratio["numerator"], ratio["denominator"]]):
                raise ValueError("Ratios require numeric columns.")
            names.add(ratio["name"])
        return self

    def transform(self, X):
        check_is_fitted(self, "feature_names_in_")
        out = X.loc[:, self.feature_names_in_].copy()
        for ratio in self.ratios:
            # Denominator zeros become missing and follow training-fitted imputation.
            out[ratio["name"]] = X[ratio["numerator"]].divide(X[ratio["denominator"]].replace(0, np.nan))
        for feature in self.log_features:
            if (out[feature].dropna() < 0).any():
                raise ValueError("Negative values are outside the configured log1p domain.")
            out[feature] = np.log1p(out[feature])
        return out.replace([np.inf, -np.inf], np.nan)

    def get_feature_names_out(self, input_features=None):
        return np.array(list(self.feature_names_in_) + [r["name"] for r in self.ratios], dtype=object)

class QuantileClipper(TransformerMixin, BaseEstimator):
    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper
    def fit(self, X, y=None):
        self.low_ = np.quantile(np.asarray(X, dtype=float), self.lower, axis=0)
        self.high_ = np.quantile(np.asarray(X, dtype=float), self.upper, axis=0)
        self.n_features_in_ = len(self.low_)
        return self
    def transform(self, X):
        check_is_fitted(self, "low_")
        return np.clip(np.asarray(X, dtype=float), self.low_, self.high_)
    def get_feature_names_out(self, input_features=None):
        return np.asarray(input_features if input_features is not None else [f"x{i}" for i in range(self.n_features_in_)], dtype=object)

class FeatureSelector(TransformerMixin, BaseEstimator):
    def __init__(self, method="anova", k=12, threshold=0.0, seed=42):
        self.method, self.k, self.threshold, self.seed = method, k, threshold, seed
    def fit(self, X, y=None):
        self.n_features_in_ = np.asarray(X).shape[1]
        if self.n_features_in_ == 0:
            raise ValueError("No encoded input features remain.")
        if self.method == "none":
            self.selector_ = None
        elif self.method == "variance":
            self.selector_ = VarianceThreshold(self.threshold).fit(X, y)
        else:
            score = f_classif if self.method == "anova" else partial(mutual_info_classif, random_state=self.seed)
            self.selector_ = SelectKBest(score_func=score, k=min(self.k, self.n_features_in_)).fit(X, y)
        self.support_ = np.ones(self.n_features_in_, dtype=bool) if self.selector_ is None else self.selector_.get_support()
        self.scores_ = None if self.selector_ is None else getattr(self.selector_, "scores_", getattr(self.selector_, "variances_", None))
        return self
    def transform(self, X):
        check_is_fitted(self, "support_")
        return np.asarray(X)[:, self.support_]
    def get_feature_names_out(self, input_features=None):
        names = np.asarray(input_features if input_features is not None else [f"x{i}" for i in range(self.n_features_in_)], dtype=object)
        return names[self.support_]
