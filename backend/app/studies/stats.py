from __future__ import annotations

import hashlib
from typing import Any
import numpy as np

MULTI_SEED_LIMITATIONS = [
    "Repeating over seeds measures stability with respect to the chosen random initialization, partition splitting, and training stochasticity only.",
    "Seed variability is descriptive and is NOT equivalent to independent patient-level or population-level clinical evidence.",
    "Seed repetition does not establish clinical validity, diagnostic efficacy, or therapeutic utility.",
    "Observed seed-to-seed differences do not constitute proof of statistical superiority over baseline models.",
    "Seed repetition alone does not establish quantum advantage or computational speedup on physical quantum hardware.",
    "External validation on independent clinical cohorts remains necessary for reliable generalization assessment.",
]

AGGREGATE_METRIC_PATHS: list[tuple[str, tuple[str, ...]]] = [
    ("accuracy", ("test", "accuracy")),
    ("sensitivity", ("test", "sensitivity")),
    ("specificity", ("test", "specificity")),
    ("precision", ("test", "precision")),
    ("recall", ("test", "recall")),
    ("f1", ("test", "f1")),
    ("roc_auc", ("test", "roc_auc")),
    ("pr_auc", ("test", "pr_auc")),
    ("brier_score", ("calibration", "brier_score")),
    ("final_training_seconds", ("timing", "final_training_seconds")),
    ("cv_total_seconds", ("timing", "cv_total_seconds")),
    ("test_inference_seconds", ("timing", "test_inference_seconds")),
    ("test_inference_seconds_per_sample", ("timing", "test_inference_seconds_per_sample")),
]

PAIRED_METRICS: list[str] = [
    "accuracy",
    "sensitivity",
    "specificity",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "brier_score",
    "final_training_seconds",
    "test_inference_seconds",
]


def extract_metric(metrics: dict, path: tuple[str, ...]) -> float | None:
    current: Any = metrics or {}
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if current is None:
        return None
    try:
        val = float(current)
        return val if np.isfinite(val) else None
    except (ValueError, TypeError):
        return None


def derive_bootstrap_seed(study_id: str, label: str) -> int:
    raw = f"{study_id}:{label}:bootstrap"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2147483647


def compute_bootstrap_interval(
    values: list[float],
    *,
    seed: int,
    n_resamples: int = 2000,
    alpha: float = 0.05,
) -> dict:
    if not values:
        return {
            "lower": None,
            "upper": None,
            "method": "bootstrap_percentile",
            "interpretation": "descriptive seed-variability interval; not population-level clinical or statistical significance",
            "bootstrap_samples": n_resamples,
            "bootstrap_seed": seed,
            "limitations": ["No valid observations available for interval calculation."],
        }
    if len(values) == 1:
        single = round(float(values[0]), 6)
        return {
            "lower": single,
            "upper": single,
            "method": "bootstrap_percentile",
            "interpretation": "descriptive seed-variability interval; not population-level clinical or statistical significance",
            "bootstrap_samples": n_resamples,
            "bootstrap_seed": seed,
            "limitations": ["Single observation; bootstrap interval degenerates to point estimate."],
        }

    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=float)
    boot_means = [
        float(np.mean(rng.choice(arr, size=len(arr), replace=True)))
        for _ in range(n_resamples)
    ]
    lower = float(np.percentile(boot_means, 100 * (alpha / 2)))
    upper = float(np.percentile(boot_means, 100 * (1 - alpha / 2)))

    limitations = [
        "Descriptive bootstrap percentile interval of the mean across observed seeds.",
        "Reflects simulation/splitting instability; not population or clinical confidence.",
    ]
    if len(values) < 5:
        limitations.append(f"Small seed count (n={len(values)} < 5) produces coarse bootstrap percentile intervals.")

    return {
        "lower": round(lower, 6),
        "upper": round(upper, 6),
        "method": "bootstrap_percentile",
        "interpretation": "descriptive seed-variability interval; not population-level clinical or statistical significance",
        "bootstrap_samples": n_resamples,
        "bootstrap_seed": seed,
        "limitations": limitations,
    }


def compute_descriptive_stats(
    metric_name: str,
    values_by_seed: dict[int, float | None],
    all_seeds: list[int],
    *,
    bootstrap_seed: int,
) -> dict:
    n = len(all_seeds)
    valid_values = [values_by_seed[s] for s in all_seeds if values_by_seed.get(s) is not None]
    valid_count = len(valid_values)
    missing_seeds = [s for s in all_seeds if values_by_seed.get(s) is None]
    missing_count = len(missing_seeds)

    if valid_count == 0:
        return {
            "metric_name": metric_name,
            "n": n,
            "valid_count": 0,
            "missing_count": missing_count,
            "missing_seeds": missing_seeds,
            "mean": None,
            "median": None,
            "std": None,
            "min": None,
            "max": None,
            "interval_95": None,
        }

    mean_val = round(float(np.mean(valid_values)), 6)
    median_val = round(float(np.median(valid_values)), 6)
    std_val = round(float(np.std(valid_values, ddof=1)), 6) if valid_count > 1 else None
    min_val = round(float(np.min(valid_values)), 6)
    max_val = round(float(np.max(valid_values)), 6)
    interval = compute_bootstrap_interval(valid_values, seed=bootstrap_seed)

    return {
        "metric_name": metric_name,
        "n": n,
        "valid_count": valid_count,
        "missing_count": missing_count,
        "missing_seeds": missing_seeds,
        "mean": mean_val,
        "median": median_val,
        "std": std_val,
        "min": min_val,
        "max": max_val,
        "interval_95": interval,
    }


def compute_paired_comparison(
    model_a: str,
    model_b: str,
    metric_name: str,
    a_values: dict[int, float | None],
    b_values: dict[int, float | None],
    common_seeds: list[int],
    *,
    bootstrap_seed: int,
) -> dict:
    observations: list[dict] = []
    deltas: list[float] = []

    for seed in common_seeds:
        val_a = a_values.get(seed)
        val_b = b_values.get(seed)
        if val_a is not None and val_b is not None:
            delta = round(val_a - val_b, 6)
            observations.append({
                "seed": seed,
                "value_a": round(val_a, 6),
                "value_b": round(val_b, 6),
                "delta": delta,
            })
            deltas.append(delta)

    if not deltas:
        return {
            "metric_name": metric_name,
            "model_a": model_a,
            "model_b": model_b,
            "available": False,
            "reason": "No matching seed executions produced valid observations for both models.",
            "valid_pairs_count": 0,
            "mean_delta": None,
            "median_delta": None,
            "std_delta": None,
            "min_delta": None,
            "max_delta": None,
            "interval_95": None,
            "observations": [],
        }

    mean_delta = round(float(np.mean(deltas)), 6)
    median_delta = round(float(np.median(deltas)), 6)
    std_delta = round(float(np.std(deltas, ddof=1)), 6) if len(deltas) > 1 else None
    min_delta = round(float(np.min(deltas)), 6)
    max_delta = round(float(np.max(deltas)), 6)
    interval = compute_bootstrap_interval(deltas, seed=bootstrap_seed)

    return {
        "metric_name": metric_name,
        "model_a": model_a,
        "model_b": model_b,
        "available": True,
        "reason": None,
        "valid_pairs_count": len(deltas),
        "mean_delta": mean_delta,
        "median_delta": median_delta,
        "std_delta": std_delta,
        "min_delta": min_delta,
        "max_delta": max_delta,
        "interval_95": interval,
        "observations": observations,
    }


def aggregate_study_results(
    study_id: str,
    completed_seeds: list[int],
    models: list[str],
    seed_model_metrics: dict[int, dict[str, dict]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Compute per-model descriptive aggregates and cross-model paired seed deltas.

    seed_model_metrics is mapping: seed -> {model_type -> raw_metrics_dict}
    """
    model_aggregates: dict[str, Any] = {}
    model_metric_values: dict[str, dict[str, dict[int, float | None]]] = {}

    for model in models:
        model_aggregates[model] = {
            "model_type": model,
            "metrics": {},
            "evaluated_seeds": completed_seeds,
            "successful_seeds": [],
            "failed_seeds": [],
        }
        model_metric_values[model] = {}
        for metric_name, path in AGGREGATE_METRIC_PATHS:
            model_metric_values[model][metric_name] = {}

    for seed in completed_seeds:
        models_at_seed = seed_model_metrics.get(seed, {})
        for model in models:
            if model in models_at_seed:
                model_aggregates[model]["successful_seeds"].append(seed)
                raw = models_at_seed[model]
                for metric_name, path in AGGREGATE_METRIC_PATHS:
                    val = extract_metric(raw, path)
                    model_metric_values[model][metric_name][seed] = val
            else:
                model_aggregates[model]["failed_seeds"].append(seed)
                for metric_name, path in AGGREGATE_METRIC_PATHS:
                    model_metric_values[model][metric_name][seed] = None

    for model in models:
        for metric_name, _path in AGGREGATE_METRIC_PATHS:
            b_seed = derive_bootstrap_seed(study_id, f"{model}:{metric_name}")
            stats = compute_descriptive_stats(
                metric_name=metric_name,
                values_by_seed=model_metric_values[model][metric_name],
                all_seeds=completed_seeds,
                bootstrap_seed=b_seed,
            )
            model_aggregates[model]["metrics"][metric_name] = stats

    paired_comparisons: list[dict[str, Any]] = []
    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            model_a = models[i]
            model_b = models[j]
            for metric_name in PAIRED_METRICS:
                b_seed = derive_bootstrap_seed(study_id, f"{model_a}:{model_b}:{metric_name}:paired")
                comp = compute_paired_comparison(
                    model_a=model_a,
                    model_b=model_b,
                    metric_name=metric_name,
                    a_values=model_metric_values[model_a][metric_name],
                    b_values=model_metric_values[model_b][metric_name],
                    common_seeds=completed_seeds,
                    bootstrap_seed=b_seed,
                )
                paired_comparisons.append(comp)

    return model_aggregates, paired_comparisons
