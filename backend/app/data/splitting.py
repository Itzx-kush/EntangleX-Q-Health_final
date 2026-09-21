from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split
from ..api.schemas import TrainingConfig
from ..config import get_settings
from ..utils.errors import AppError
from ..utils.serialization import fingerprint
from .service import load_frame
from .quality import quality_report

@dataclass
class PreparedData:
    dataset: object
    frame: pd.DataFrame
    X: pd.DataFrame
    y: np.ndarray
    train: np.ndarray
    test: np.ndarray
    cv: list[tuple[np.ndarray, np.ndarray]]
    features: list[str]
    numeric: list[str]
    quality: dict
    split_hash: str
    dropped_duplicates: int
    excluded_by_sampling: int

    def split_metadata(self) -> dict:
        return {"split_hash": self.split_hash, "train_count": len(self.train), "test_count": len(self.test), "evaluated_sample_count": len(self.train) + len(self.test), "source_sample_count": len(self.frame), "dropped_duplicate_count": self.dropped_duplicates, "excluded_by_sampling": self.excluded_by_sampling, "cv_folds": len(self.cv), "scheme": "stratified random holdout + stratified CV on training only", "independent_samples_assumed": True}

def prepare_data(config: TrainingConfig) -> PreparedData:
    dataset, frame = load_frame(str(config.dataset_id))
    target, positive = dataset.provenance["target"], dataset.provenance["positive_label"]
    features = config.features if config.features is not None else dataset.provenance["features"]
    quality = quality_report(frame, target, positive, features)
    if quality["blockers"]:
        raise AppError("quality_blocked", " ".join(quality["blockers"]))
    if target in config.pipeline.log_features or any(target in (r.name, r.numerator, r.denominator) for r in config.pipeline.ratios):
        raise AppError("target_leakage", "Feature engineering must not access or create the target column.")
    full_X = frame[features].copy()
    y = (frame[target].astype(str) == positive).astype(int).to_numpy()
    duplicates = frame[features + [target]].duplicated()
    drop_count = int(duplicates.sum())
    if drop_count and config.duplicate_policy == "reject":
        raise AppError("duplicate_leakage", "Duplicate records could cross partitions. Choose explicit drop_exact or correct the source.")
    indices = np.flatnonzero(~duplicates.to_numpy()) if config.duplicate_policy == "drop_exact" else np.arange(len(frame))
    if full_X.iloc[indices].duplicated().any():
        raise AppError("duplicate_features", "Identical selected input vectors would cross partitions. Review duplicates and feature selection.")
    excluded = 0
    if config.max_samples is not None and len(indices) > config.max_samples:
        try:
            chosen, _ = train_test_split(indices, train_size=config.max_samples, stratify=y[indices], random_state=config.seed)
        except ValueError as exc:
            raise AppError("sampling_not_feasible", "The requested common sample budget does not support stratified sampling for both classes.") from exc
        excluded = len(indices) - len(chosen)
        indices = np.sort(chosen)
    if {"vqc", "qsvc"}.intersection(config.models) and len(indices) > get_settings().quantum_max_samples:
        raise AppError("quantum_budget", "Selected benchmark exceeds the quantum sample budget. Set max_samples for ALL compared models.")
    try:
        train, test = train_test_split(indices, test_size=config.test_size, stratify=y[indices], random_state=config.seed)
        if len(np.unique(y[test])) != 2 or min(np.bincount(y[train], minlength=2)) < config.cv_folds:
            raise ValueError("insufficient class support")
        folds = list(StratifiedKFold(n_splits=config.cv_folds, shuffle=True, random_state=config.seed).split(full_X.iloc[train], y[train]))
        if config.calibration != "none":
            for tr, _ in folds:
                if min(np.bincount(y[train[tr]], minlength=2)) < config.calibration_folds:
                    raise ValueError("insufficient inner calibration support")
    except ValueError as exc:
        raise AppError("split_not_feasible", "Not enough class support for the requested holdout, CV, and optional calibration folds.") from exc
    split_hash = fingerprint({"dataset_hash": dataset.sha256, "train_indices": train.tolist(), "test_indices": test.tolist(), "cv": [(a.tolist(), b.tolist()) for a, b in folds]})
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(full_X[c])]
    return PreparedData(dataset, frame, full_X, y, train, test, folds, features, numeric, quality, split_hash, drop_count, excluded)
