"""Statistical test functions and multiple-testing corrections for distribution shift."""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import pandas as pd
from scipy import stats

from .constants import classify_smd_heuristic


def benjamini_hochberg_fdr(
    raw_p_values: dict[str, float | None],
) -> dict[str, float | None]:
    """Calculate Benjamini-Hochberg False Discovery Rate (FDR) adjusted p-values.

    Parameters
    ----------
    raw_p_values : dict[str, float | None]
        Mapping from feature name to raw two-sided p-value.
        Features with None or NaN p-values are preserved as None and excluded
        from the total hypothesis count.

    Returns
    -------
    dict[str, float | None]
        Mapping from feature name to FDR-adjusted p-value (q-value).
    """
    valid_items = [
        (k, float(v))
        for k, v in raw_p_values.items()
        if v is not None and not math.isnan(v)
    ]
    m = len(valid_items)
    if m == 0:
        return {k: None for k in raw_p_values}

    # Sort in ascending order of raw p-value
    valid_items.sort(key=lambda item: item[1])

    adjusted: dict[str, float] = {}
    # Step-up calculation: q_i = p_i * m / rank
    # Enforce monotonicity: q_i = min(q_i, q_{i+1})
    running_min = 1.0
    for rank in range(m, 0, -1):
        feature, p_val = valid_items[rank - 1]
        raw_q = (p_val * m) / rank
        running_min = min(running_min, raw_q)
        adjusted[feature] = float(np.clip(running_min, 0.0, 1.0))

    result: dict[str, float | None] = {}
    for k in raw_p_values:
        result[k] = adjusted.get(k, None)
    return result


def compute_numeric_shift(
    ref_series: pd.Series,
    comp_series: pd.Series,
    *,
    significance_threshold: float = 0.05,
    distance_threshold: float = 0.15,
) -> dict[str, Any]:
    """Compute descriptive statistics, KS-test, Wasserstein distance, and SMD for numeric feature."""
    ref_clean = pd.to_numeric(ref_series, errors="coerce").dropna().to_numpy(dtype=float)
    comp_clean = pd.to_numeric(comp_series, errors="coerce").dropna().to_numpy(dtype=float)

    # Filter infinities
    ref_clean = ref_clean[np.isfinite(ref_clean)]
    comp_clean = comp_clean[np.isfinite(comp_clean)]

    n_ref = len(ref_clean)
    n_comp = len(comp_clean)

    warnings: list[str] = []
    if n_ref < 5 or n_comp < 5:
        warnings.append("Sample count < 5 in one or both cohorts; distribution tests have limited power.")

    # Base descriptive metrics
    ref_mean = float(np.mean(ref_clean)) if n_ref > 0 else None
    comp_mean = float(np.mean(comp_clean)) if n_comp > 0 else None
    mean_diff = (comp_mean - ref_mean) if (ref_mean is not None and comp_mean is not None) else None

    ref_std = float(np.std(ref_clean, ddof=1)) if n_ref > 1 else (0.0 if n_ref == 1 else None)
    comp_std = float(np.std(comp_clean, ddof=1)) if n_comp > 1 else (0.0 if n_comp == 1 else None)
    std_diff = (comp_std - ref_std) if (ref_std is not None and comp_std is not None) else None

    ref_median = float(np.median(ref_clean)) if n_ref > 0 else None
    comp_median = float(np.median(comp_clean)) if n_comp > 0 else None
    median_diff = (comp_median - ref_median) if (ref_median is not None and comp_median is not None) else None

    ref_min = float(np.min(ref_clean)) if n_ref > 0 else None
    ref_max = float(np.max(ref_clean)) if n_ref > 0 else None
    comp_min = float(np.min(comp_clean)) if n_comp > 0 else None
    comp_max = float(np.max(comp_clean)) if n_comp > 0 else None

    # Standardized Mean Difference (Cohen's d with pooled std dev)
    smd: float | None = None
    smd_label: str | None = None
    if n_ref > 1 and n_comp > 1 and ref_std is not None and comp_std is not None and mean_diff is not None:
        pooled_var = (((n_ref - 1) * (ref_std ** 2)) + ((n_comp - 1) * (comp_std ** 2))) / (n_ref + n_comp - 2)
        if pooled_var > 1e-12:
            smd = float(mean_diff / math.sqrt(pooled_var))
            smd_label = classify_smd_heuristic(abs(smd))
        elif abs(mean_diff) < 1e-12:
            smd = 0.0
            smd_label = classify_smd_heuristic(0.0)

    # Kolmogorov-Smirnov test
    ks_stat: float | None = None
    ks_p_val: float | None = None
    wasserstein_dist: float | None = None

    if n_ref >= 2 and n_comp >= 2:
        try:
            ks_res = stats.ks_2samp(ref_clean, comp_clean)
            ks_stat = float(ks_res.statistic)
            ks_p_val = float(ks_res.pvalue)
        except Exception as exc:
            warnings.append(f"Kolmogorov-Smirnov test computation failed: {str(exc)}")

        try:
            w_dist = stats.wasserstein_distance(ref_clean, comp_clean)
            wasserstein_dist = float(w_dist)
        except Exception as exc:
            warnings.append(f"Wasserstein distance computation failed: {str(exc)}")
    else:
        warnings.append("Insufficient distinct numeric samples for 2-sample distribution tests.")

    return {
        "reference_count": n_ref,
        "comparison_count": n_comp,
        "reference_mean": ref_mean,
        "comparison_mean": comp_mean,
        "mean_difference": mean_diff,
        "reference_std": ref_std,
        "comparison_std": comp_std,
        "std_difference": std_diff,
        "reference_median": ref_median,
        "comparison_median": comp_median,
        "median_difference": median_diff,
        "reference_min": ref_min,
        "reference_max": ref_max,
        "comparison_min": comp_min,
        "comparison_max": comp_max,
        "standardized_mean_difference": smd,
        "effect_size_label": smd_label,
        "test_method": "kolmogorov_smirnov",
        "statistic": ks_stat,
        "raw_p_value": ks_p_val,
        "distance_metric": "wasserstein_distance",
        "distance_value": wasserstein_dist,
        "warnings": warnings,
    }


def compute_categorical_shift(
    ref_series: pd.Series,
    comp_series: pd.Series,
    *,
    significance_threshold: float = 0.05,
    distance_threshold: float = 0.15,
) -> dict[str, Any]:
    """Compute category proportions, Total Variation Distance, and Chi-square test for categorical feature."""
    ref_clean = ref_series.dropna().astype(str).str.strip()
    comp_clean = comp_series.dropna().astype(str).str.strip()

    n_ref = len(ref_clean)
    n_comp = len(comp_clean)

    warnings: list[str] = []
    if n_ref < 5 or n_comp < 5:
        warnings.append("Sample count < 5 in one or both cohorts; categorical tests have limited power.")

    ref_counts = ref_clean.value_counts().to_dict()
    comp_counts = comp_clean.value_counts().to_dict()

    all_categories = sorted(list(set(ref_counts.keys()) | set(comp_counts.keys())))

    ref_proportions: dict[str, float] = {}
    comp_proportions: dict[str, float] = {}
    proportion_deltas: dict[str, float] = {}
    total_abs_diff = 0.0

    for cat in all_categories:
        r_p = float(ref_counts.get(cat, 0) / n_ref) if n_ref > 0 else 0.0
        c_p = float(comp_counts.get(cat, 0) / n_comp) if n_comp > 0 else 0.0
        delta = c_p - r_p
        ref_proportions[cat] = r_p
        comp_proportions[cat] = c_p
        proportion_deltas[cat] = delta
        total_abs_diff += abs(delta)

    # Total Variation Distance: TVD = 0.5 * sum |p(x) - q(x)|
    tvd = float(0.5 * total_abs_diff) if all_categories else None

    # Chi-square test of independence
    chi2_stat: float | None = None
    chi2_p_val: float | None = None
    sparse_categories = False

    if n_ref >= 5 and n_comp >= 5 and len(all_categories) >= 2:
        try:
            contingency = np.array([
                [ref_counts.get(cat, 0) for cat in all_categories],
                [comp_counts.get(cat, 0) for cat in all_categories],
            ])
            res = stats.chi2_contingency(contingency)
            chi2_stat = float(res.statistic)
            chi2_p_val = float(res.pvalue)
            if np.any(res.expected_freq < 5.0):
                sparse_categories = True
                warnings.append("Sparse categories detected: some expected frequencies < 5; chi-square p-value may be unreliable.")
        except Exception as exc:
            warnings.append(f"Chi-square contingency test failed: {str(exc)}")
    else:
        if len(all_categories) < 2:
            warnings.append("Fewer than 2 distinct categories observed; statistical test not applicable.")
        else:
            warnings.append("Sample count insufficient for chi-square contingency test.")

    return {
        "reference_count": n_ref,
        "comparison_count": n_comp,
        "category_count": len(all_categories),
        "reference_proportions": ref_proportions,
        "comparison_proportions": comp_proportions,
        "proportion_deltas": proportion_deltas,
        "distance_metric": "total_variation_distance",
        "distance_value": tvd,
        "test_method": "chi_square_contingency",
        "statistic": chi2_stat,
        "raw_p_value": chi2_p_val,
        "sparse_categories": sparse_categories,
        "warnings": warnings,
    }


def compute_missingness_shift(
    ref_series: pd.Series,
    comp_series: pd.Series,
    *,
    threshold: float = 0.05,
) -> dict[str, Any]:
    """Compute missingness counts and fraction differences."""
    n_ref = len(ref_series)
    n_comp = len(comp_series)

    ref_missing = int(ref_series.isna().sum())
    comp_missing = int(comp_series.isna().sum())

    ref_frac = float(ref_missing / n_ref) if n_ref > 0 else 0.0
    comp_frac = float(comp_missing / n_comp) if n_comp > 0 else 0.0
    delta = comp_frac - ref_frac

    flagged = abs(delta) >= threshold

    return {
        "reference_missing_count": ref_missing,
        "reference_missing_fraction": ref_frac,
        "comparison_missing_count": comp_missing,
        "comparison_missing_fraction": comp_frac,
        "delta": delta,
        "threshold": threshold,
        "flagged": flagged,
    }
