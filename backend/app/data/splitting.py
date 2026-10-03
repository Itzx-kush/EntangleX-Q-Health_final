from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split, StratifiedGroupKFold, GroupShuffleSplit
from ..api.schemas import TrainingConfig
from ..config import get_settings
from ..utils.errors import AppError
from ..utils.serialization import fingerprint
from .service import load_versioned_frame
from .quality import quality_report

@dataclass
class PreparedData:
    dataset: object
    dataset_version: object | None
    provenance: dict
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
    group_metadata: dict | None = None

    def split_metadata(self) -> dict:
        sampled = sorted([*self.train.tolist(), *self.test.tolist()])
        meta = {
            "split_hash": self.split_hash,
            "sample_pool_hash": fingerprint({"dataset_hash": self.dataset_version.content_sha256 if self.dataset_version else self.dataset.sha256, "sampled_row_indices": sampled}),
            "sampled_row_indices": sampled,
            "train_indices": self.train.tolist(),
            "test_indices": self.test.tolist(),
            "train_count": len(self.train),
            "test_count": len(self.test),
            "evaluated_sample_count": len(self.train) + len(self.test),
            "source_sample_count": len(self.frame),
            "dropped_duplicate_count": self.dropped_duplicates,
            "excluded_by_sampling": self.excluded_by_sampling,
            "cv_folds": len(self.cv),
            "scheme": "grouped_samples" if self.group_metadata else "stratified random holdout + stratified CV on training only",
            "independent_samples_assumed": self.group_metadata is None,
        }
        if self.group_metadata:
            meta.update(self.group_metadata)
        return meta

def _validate_group_column(frame, config, target, features):
    if not config.group_column:
        raise AppError("group_column_missing", "Group column is required when sampling_unit='grouped_samples'.")
    if config.group_column not in frame.columns:
        raise AppError("group_column_not_found", f"Group column '{config.group_column}' was not found in dataset version.")
    if config.group_column == target:
        raise AppError("group_column_target_overlap", "Group column cannot be the target column.")
    if config.group_column in features:
        raise AppError("group_column_feature_overlap", "Group column overlaps with model feature set.")
    if frame[config.group_column].isnull().any() or (frame[config.group_column] == "").any():
        raise AppError("group_column_nulls", "Group identifiers cannot contain nulls or blanks.")
    if frame[config.group_column].nunique() < 2:
        raise AppError("group_column_constant", "Group column has fewer than 2 unique groups. Validation is infeasible.")

def _grouped_holdout_split(X_indices, y_subset, groups_subset, test_size, seed):
    n_splits = max(2, int(round(1.0 / test_size)))
    try:
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        train_idx_local, test_idx_local = next(sgkf.split(X_indices, y_subset, groups_subset))
        return X_indices[train_idx_local], X_indices[test_idx_local], "stratified_group_kfold"
    except ValueError:
        pass
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx_local, test_idx_local = next(gss.split(X_indices, y_subset, groups_subset))
    return X_indices[train_idx_local], X_indices[test_idx_local], "group_shuffle_split"

def prepare_data(config: TrainingConfig) -> PreparedData:
    dataset, dataset_version, frame = load_versioned_frame(str(config.dataset_id), str(config.dataset_version_id) if config.dataset_version_id else None)
    provenance = dataset_version.provenance if dataset_version else dataset.provenance
    target, positive = provenance["target"], provenance["positive_label"]
    features = config.features if config.features is not None else provenance["features"]
    
    if config.sampling_unit == "grouped_samples":
        _validate_group_column(frame, config, target, features)
        
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
        if config.sampling_unit == "grouped_samples":
            target_prop = config.max_samples / len(indices)
            try:
                gss = GroupShuffleSplit(n_splits=1, train_size=target_prop, random_state=config.seed)
                chosen_local, _ = next(gss.split(indices, y[indices], frame[config.group_column].iloc[indices]))
                chosen = indices[chosen_local]
            except ValueError as exc:
                raise AppError("sampling_not_feasible", "Could not downsample groups to meet budget.") from exc
            excluded = len(indices) - len(chosen)
            indices = np.sort(chosen)
        else:
            try:
                chosen, _ = train_test_split(indices, train_size=config.max_samples, stratify=y[indices], random_state=config.seed)
            except ValueError as exc:
                raise AppError("sampling_not_feasible", "The requested common sample budget does not support stratified sampling for both classes.") from exc
            excluded = len(indices) - len(chosen)
            indices = np.sort(chosen)
            
    if {"vqc", "qsvc", "qnn", "hybrid_pennylane_torch"}.intersection(config.models) and len(indices) > get_settings().quantum_max_samples:
        raise AppError("quantum_budget", "Selected benchmark exceeds the quantum sample budget. Set max_samples for ALL compared models.")
        
    group_metadata = None
    
    if config.sampling_unit == "grouped_samples":
        groups_subset = frame[config.group_column].iloc[indices].to_numpy()
        unique_groups, group_counts = np.unique(groups_subset, return_counts=True)
        group_metadata = {
            "group_column": config.group_column,
            "total_groups": int(len(unique_groups)),
            "rows_per_group": {
                "min": int(group_counts.min()),
                "max": int(group_counts.max()),
                "mean": float(group_counts.mean()),
                "median": float(np.median(group_counts))
            },
            "singleton_groups": int(np.sum(group_counts == 1))
        }
        
        # Verify enough groups
        if len(unique_groups) < config.cv_folds:
            raise AppError("split_not_feasible", "Requested number of folds greater than feasible group structure.")
        
        try:
            train, test, holdout_strat = _grouped_holdout_split(indices, y[indices], groups_subset, config.test_size, config.seed)
            if len(np.unique(y[test])) != 2 or min(np.bincount(y[train], minlength=2)) < config.cv_folds:
                raise ValueError("insufficient class support")
                
            group_metadata["holdout_strategy"] = holdout_strat
            
            # CV
            train_groups = frame[config.group_column].iloc[train].to_numpy()
            
            try:
                sgkf = StratifiedGroupKFold(n_splits=config.cv_folds, shuffle=True, random_state=config.seed)
                folds = list(sgkf.split(full_X.iloc[train], y[train], train_groups))
                group_metadata["cv_strategy"] = "stratified_group_kfold"
            except ValueError:
                # Fallback
                gss_cv = GroupShuffleSplit(n_splits=config.cv_folds, test_size=1.0/config.cv_folds, random_state=config.seed)
                folds = list(gss_cv.split(full_X.iloc[train], y[train], train_groups))
                group_metadata["cv_strategy"] = "group_shuffle_split_fallback"
                
            if config.calibration != "none":
                for tr, _ in folds:
                    if min(np.bincount(y[train[tr]], minlength=2)) < config.calibration_folds:
                        raise ValueError("insufficient inner calibration support")
                        
        except ValueError as exc:
            raise AppError("split_not_feasible", "Not enough class support or groups for the requested holdout and CV folds.") from exc

        # Assert disjoint
        train_g = set(frame[config.group_column].iloc[train])
        test_g = set(frame[config.group_column].iloc[test])
        assert train_g.isdisjoint(test_g), "Group leakage detected in holdout!"
        for tr_idx, val_idx in folds:
            tr_g = set(train_groups[tr_idx])
            val_g = set(train_groups[val_idx])
            assert tr_g.isdisjoint(val_g), "Group leakage detected in CV folds!"
            
        group_metadata["train_group_count"] = len(train_g)
        group_metadata["test_group_count"] = len(test_g)
        group_metadata["train_groups_fingerprint"] = fingerprint(sorted(str(value) for value in train_g))
        group_metadata["test_groups_fingerprint"] = fingerprint(sorted(str(value) for value in test_g))
        
        split_hash_components = {
            "dataset_hash": dataset_version.content_sha256 if dataset_version else dataset.sha256, 
            "sampling_unit": config.sampling_unit,
            "group_column": config.group_column,
            "train_indices": train.tolist(), 
            "test_indices": test.tolist(), 
            "cv": [(a.tolist(), b.tolist()) for a, b in folds],
            "train_groups": sorted(list(train_g)),
            "test_groups": sorted(list(test_g))
        }
        split_hash = fingerprint(split_hash_components)
        group_metadata["group_split_fingerprint"] = split_hash
        
    else:
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
        split_hash = fingerprint({"dataset_hash": dataset_version.content_sha256 if dataset_version else dataset.sha256, "train_indices": train.tolist(), "test_indices": test.tolist(), "cv": [(a.tolist(), b.tolist()) for a, b in folds]})

    numeric = [c for c in features if pd.api.types.is_numeric_dtype(full_X[c])]
    return PreparedData(dataset, dataset_version, provenance, frame, full_X, y, train, test, folds, features, numeric, quality, split_hash, drop_count, excluded, group_metadata)
