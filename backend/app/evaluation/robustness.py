"""Bounded, deterministic degradation evaluation for frozen model artifacts."""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy import select

from ..api.schemas import RobustnessRequest, RobustnessScenario
from ..data.service import load_frame
from ..database import session_scope
from ..evaluation.metrics import classification_metrics, score_outputs
from ..evaluation.thresholds import predictions_at_threshold
from ..models.prediction import get_bundle, resolve_operating_threshold
from ..storage.entities import Experiment, ModelRecord, RobustnessRecord
from ..storage.repository import require
from ..utils.errors import AppError
from ..utils.serialization import clean_json, fingerprint, software_versions


ROBUSTNESS_METRICS = ["accuracy", "sensitivity", "specificity", "precision", "recall", "f1", "roc_auc"]
METHOD_VERSION = "controlled-perturbation-v1"


def _numeric_statistics(background: pd.DataFrame, numeric: list[str]) -> dict[str, float]:
    result = {}
    for feature in numeric:
        sigma = float(pd.to_numeric(background[feature], errors="coerce").std())
        if np.isfinite(sigma) and sigma > 0:
            result[feature] = sigma
    return result


def perturb_frame(
    frame: pd.DataFrame,
    background: pd.DataFrame,
    numeric: list[str],
    scenario: RobustnessScenario,
    seed: int,
) -> dict:
    """Return one deterministic perturbed copy and non-sensitive metadata."""

    rng = np.random.default_rng(seed)
    output = frame.copy(deep=True)
    statistics = _numeric_statistics(background, numeric)
    numeric_valid = [name for name in numeric if name in frame and name in statistics]
    categorical = [name for name in frame.columns if name not in numeric]
    kind, level = scenario.perturbation_type, scenario.level

    if kind == "missingness":
        eligible = [(row, col) for row in range(len(output)) for col in output.columns]
        count = min(len(eligible), max(1, round(level * len(eligible))))
        chosen = rng.choice(len(eligible), size=count, replace=False)
        for index in chosen:
            row, col = eligible[int(index)]
            output.iat[row, output.columns.get_loc(col)] = np.nan
        return {"status": "evaluated", "frame": output, "metadata": {"eligible_cells": len(eligible), "changed_cells": count, "realized_fraction": count / len(eligible)}}

    if kind == "gaussian_noise":
        if not numeric_valid:
            return {"status": "not_applicable", "frame": None, "reason": "No numeric feature with nonzero training standard deviation is available."}
        changed = 0
        eligible = 0
        for feature in numeric_valid:
            values = pd.to_numeric(output[feature], errors="coerce")
            mask = values.notna().to_numpy()
            noise = rng.normal(0.0, level * statistics[feature], size=len(output))
            output.loc[mask, feature] = values.loc[mask] + noise[mask]
            changed += int(mask.sum())
            eligible += int(mask.sum())
        return {"status": "evaluated", "frame": output, "metadata": {"eligible_cells": eligible, "changed_cells": changed, "noise_scale_in_training_sd": level}}

    if kind == "outliers":
        if not numeric_valid:
            return {"status": "not_applicable", "frame": None, "reason": "No numeric feature with nonzero training standard deviation is available."}
        eligible = [(row, col) for row in range(len(output)) for col in numeric_valid if pd.notna(output.iloc[row][col])]
        count = min(len(eligible), max(1, round(0.05 * len(eligible))))
        chosen = rng.choice(len(eligible), size=count, replace=False)
        for index in chosen:
            row, feature = eligible[int(index)]
            sign = -1 if rng.integers(0, 2) == 0 else 1
            value = float(output.at[output.index[row], feature]) + sign * level * statistics[feature]
            if (pd.to_numeric(background[feature], errors="coerce").dropna() >= 0).all():
                value = max(0.0, value)
            output.at[output.index[row], feature] = value
        return {"status": "evaluated", "frame": output, "metadata": {"eligible_cells": len(eligible), "changed_cells": count, "injected_standard_deviations": level, "injected_fraction": count / len(eligible)}}

    if kind == "categorical":
        alternatives = {
            feature: background[feature].dropna().value_counts().index.tolist()
            for feature in categorical
            if background[feature].dropna().nunique() >= 2
        }
        eligible = [(row, feature) for row in range(len(output)) for feature in alternatives]
        if not eligible:
            return {"status": "not_applicable", "frame": None, "reason": "No categorical feature with at least two observed training categories is available."}
        count = min(len(eligible), max(1, round(level * len(eligible))))
        chosen = rng.choice(len(eligible), size=count, replace=False)
        for index in chosen:
            row, feature = eligible[int(index)]
            current = output.at[output.index[row], feature]
            choices = [value for value in alternatives[feature] if value != current]
            output.at[output.index[row], feature] = choices[int(rng.integers(0, len(choices)))]
        return {"status": "evaluated", "frame": output, "metadata": {"eligible_cells": len(eligible), "changed_cells": count, "realized_fraction": count / len(eligible)}}

    raise ValueError("Unsupported robustness perturbation.")


def _bounded_test_indices(all_indices: list[int], labels: np.ndarray, max_samples: int, seed: int) -> np.ndarray:
    values = np.asarray(all_indices, dtype=int)
    if len(values) <= max_samples:
        return values
    try:
        chosen, _ = train_test_split(values, train_size=max_samples, stratify=labels[values], random_state=seed)
    except ValueError:
        chosen = np.random.default_rng(seed).choice(values, size=max_samples, replace=False)
    return np.sort(chosen)


def _measure(estimator, frame: pd.DataFrame, labels: np.ndarray, threshold: float) -> tuple[dict, float]:
    started = perf_counter()
    _, scores, _ = score_outputs(estimator, frame, threshold)
    predicted = predictions_at_threshold(scores, threshold)
    elapsed = perf_counter() - started
    return classification_metrics(labels, predicted, scores), elapsed


def _changes(baseline: dict, perturbed: dict | None) -> tuple[dict, dict, dict]:
    delta, relative, undefined = {}, {}, {}
    for name in ROBUSTNESS_METRICS:
        before = baseline.get(name)
        after = perturbed.get(name) if perturbed else None
        delta[name] = after - before if before is not None and after is not None else None
        relative[name] = delta[name] / abs(before) if delta[name] is not None and before not in (None, 0) else None
        if before is None or after is None:
            undefined[name] = "Baseline or perturbed metric is undefined for the bounded evaluation sample."
        elif before == 0:
            undefined[f"relative_{name}"] = "Relative change is undefined because the baseline metric is zero."
    return delta, relative, undefined


def evaluate_robustness(experiment_id: str, request: RobustnessRequest) -> dict:
    with session_scope() as session:
        experiment = require(session, Experiment, experiment_id)
        available = list(session.scalars(select(ModelRecord).where(
            ModelRecord.experiment_id == experiment_id,
            ModelRecord.status == "ready",
        )))
    selected_ids = {str(value) for value in request.model_ids} if request.model_ids else {model.id for model in available}
    models = [model for model in available if model.id in selected_ids]
    if selected_ids - {model.id for model in models}:
        raise AppError("robustness_model_context", "Every selected model must be ready and belong to this experiment.", 409)
    if not models:
        raise AppError("robustness_models_missing", "No ready model is available for robustness evaluation.", 409)
    if len(models) * len(request.scenarios) > 24:
        raise AppError("robustness_budget", "The bounded robustness budget allows at most 24 model-scenario conditions.", 422)

    loaded = [(model, get_bundle(model.id)[1]) for model in models]
    first_bundle = loaded[0][1]
    if first_bundle["dataset_id"] != experiment.dataset_id:
        raise AppError("robustness_dataset_context", "The experiment and stored model artifact do not reference the same dataset.", 409)
    dataset, source = load_frame(first_bundle["dataset_id"])
    target = dataset.provenance["target"]
    positive = first_bundle["positive_label"]
    labels_all = (source[target].astype(str) == positive).astype(int).to_numpy()
    test_indices = _bounded_test_indices(first_bundle["test_indices"], labels_all, request.max_samples, request.random_seed)
    features = first_bundle["features"]
    numeric = first_bundle["numeric"]
    baseline_frame = source[features].iloc[test_indices].copy()
    background = source[features].iloc[first_bundle["train_indices"]].copy()
    labels = labels_all[test_indices]

    for model, bundle in loaded[1:]:
        if bundle["dataset_hash"] != first_bundle["dataset_hash"] or bundle["features"] != features or bundle["test_indices"] != first_bundle["test_indices"]:
            raise AppError("robustness_comparison_mismatch", "Selected models do not share an identical dataset, feature schema, and held-out split.", 409)

    scenarios = []
    for index, scenario in enumerate(request.scenarios):
        scenario_seed = request.random_seed + index
        scenarios.append((scenario, scenario_seed, perturb_frame(baseline_frame, background, numeric, scenario, scenario_seed)))

    results = []
    with session_scope() as session:
        for model, bundle in loaded:
            threshold, threshold_source = resolve_operating_threshold(model, bundle)
            baseline_metrics, baseline_seconds = _measure(bundle["estimator"], baseline_frame, labels, threshold)
            for scenario, scenario_seed, perturbation in scenarios:
                perturbed_metrics, perturbed_seconds, failure = None, None, None
                status = perturbation["status"]
                if status == "evaluated":
                    try:
                        perturbed_metrics, perturbed_seconds = _measure(bundle["estimator"], perturbation["frame"], labels, threshold)
                    except ValueError:
                        status = "failed"
                        failure = "The frozen model could not evaluate this perturbation within its configured transformation domain."
                delta, relative, undefined = _changes(baseline_metrics, perturbed_metrics)
                result = clean_json({
                    "status": status,
                    "reason": perturbation.get("reason") or failure,
                    "experiment_id": experiment_id,
                    "dataset_id": experiment.dataset_id,
                    "dataset_hash": dataset.sha256,
                    "split_hash": (experiment.summary or {}).get("split", {}).get("split_hash"),
                    "model_id": model.id,
                    "model_type": model.model_type,
                    "perturbation_type": scenario.perturbation_type,
                    "perturbation_level": scenario.level,
                    "random_seed": scenario_seed,
                    "sample_count": len(test_indices),
                    "baseline_metrics": baseline_metrics,
                    "perturbed_metrics": perturbed_metrics,
                    "degradation_delta": delta,
                    "relative_degradation": relative,
                    "undefined_metrics": undefined,
                    "threshold_used": threshold,
                    "threshold_source": threshold_source,
                    "preprocessing_context": (experiment.config or {}).get("pipeline"),
                    "perturbation_metadata": perturbation.get("metadata"),
                    "execution_timing": {
                        "baseline_inference_seconds": baseline_seconds,
                        "perturbed_inference_seconds": perturbed_seconds,
                    },
                    "limitations": [
                        "Observed degradation under a controlled synthetic benchmark perturbation; not clinical robustness.",
                        "The frozen model and locked research operating threshold are unchanged; no refitting or threshold reselection occurs.",
                        "Perturbations in original feature space may be off-manifold and do not represent a specific hospital or population shift.",
                    ],
                    "reproducibility_metadata": {
                        "method_version": METHOD_VERSION,
                        "perturbation_fingerprint": fingerprint({
                            "dataset_hash": dataset.sha256,
                            "test_indices": test_indices.tolist(),
                            "scenario": scenario.model_dump(mode="json"),
                            "seed": scenario_seed,
                        }),
                        "condition_fingerprint": fingerprint({
                            "dataset_hash": dataset.sha256,
                            "test_indices": test_indices.tolist(),
                            "scenario": scenario.model_dump(mode="json"),
                            "seed": scenario_seed,
                            "model_id": model.id,
                            "threshold": threshold,
                        }),
                        "test_indices_fingerprint": fingerprint(test_indices.tolist()),
                        "software": software_versions(),
                    },
                })
                record = RobustnessRecord(
                    id=str(uuid4()),
                    experiment_id=experiment_id,
                    model_id=model.id,
                    perturbation_type=scenario.perturbation_type,
                    perturbation_level=scenario.level,
                    random_seed=scenario_seed,
                    result=result,
                )
                session.add(record)
                session.flush()
                results.append({"id": record.id, **result, "created_at": record.created_at})

    return clean_json({
        "experiment_id": experiment_id,
        "dataset_id": experiment.dataset_id,
        "sample_count": len(test_indices),
        "model_count": len(models),
        "condition_count": len(results),
        "results": results,
        "limitations": [
            "Robustness evidence is a bounded research evaluation, not clinical validation or a model ranking.",
            "No quantum robustness advantage is claimed.",
        ],
    })


def list_robustness(experiment_id: str) -> list[RobustnessRecord]:
    with session_scope() as session:
        require(session, Experiment, experiment_id)
        return list(session.scalars(
            select(RobustnessRecord)
            .where(RobustnessRecord.experiment_id == experiment_id)
            .order_by(RobustnessRecord.created_at.desc())
        ))