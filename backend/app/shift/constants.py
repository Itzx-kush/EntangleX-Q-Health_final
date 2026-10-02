"""Constants, versioned policy, and mandatory limitations for distribution-shift engine."""

DISTRIBUTION_SHIFT_POLICY_VERSION = "2026-10-03-v1"

SHIFT_DIRECTION_CONVENTION = "comparison - reference"

# Default configurable thresholds
DEFAULT_MISSINGNESS_DELTA_THRESHOLD = 0.05
DEFAULT_NUMERIC_DISTANCE_THRESHOLD = 0.15
DEFAULT_CATEGORICAL_DISTANCE_THRESHOLD = 0.15
DEFAULT_SIGNIFICANCE_THRESHOLD = 0.05
DEFAULT_MULTIPLE_TESTING_CORRECTION = "benjamini_hochberg"
DEFAULT_NUMERIC_TEST = "kolmogorov_smirnov"
DEFAULT_CATEGORICAL_TEST = "total_variation_distance"

# Threshold bounds
MIN_MISSINGNESS_DELTA_THRESHOLD = 0.001
MAX_MISSINGNESS_DELTA_THRESHOLD = 0.50
MIN_NUMERIC_DISTANCE_THRESHOLD = 0.01
MAX_NUMERIC_DISTANCE_THRESHOLD = 1.0
MIN_CATEGORICAL_DISTANCE_THRESHOLD = 0.01
MAX_CATEGORICAL_DISTANCE_THRESHOLD = 1.0
MIN_SIGNIFICANCE_THRESHOLD = 0.0001
MAX_SIGNIFICANCE_THRESHOLD = 0.20

# Standardized Mean Difference (Cohen's d) heuristic thresholds
SMD_HEURISTIC_THRESHOLDS = {
    "negligible": 0.2,
    "small": 0.5,
    "medium": 0.8,
}

SHIFT_LIMITATIONS = [
    "Dataset shift is an observed distributional difference between two cohorts or dataset snapshots.",
    "Distribution shift does not automatically imply that a trained model will fail or suffer performance degradation.",
    "The absence of detectable statistical shift does not prove that a model is clinically valid or safe.",
    "Statistical significance does not equal practical or clinical significance; large sample sizes can detect trivial differences.",
    "The chosen statistical tests (Kolmogorov-Smirnov, Chi-square, Benjamini-Hochberg) rely on specific mathematical assumptions.",
    "Unmeasured confounding, correlation between features, and latent variables complicate the interpretation of marginal distribution shifts.",
    "Differences in dataset composition, clinical protocols, patient demographics, and collection processes directly affect observed distributions.",
    "Target prevalence differences reflect cohort selection or operational contexts and do not establish underlying biological differences.",
    "This analysis is purely observational and descriptive; it does not establish causality between features and outcomes.",
    "The analysis does not evaluate or establish clinical effectiveness, diagnostic efficacy, or therapeutic utility.",
    "Distribution shift metrics do not imply or evaluate quantum advantage or disadvantage for classical vs. quantum models.",
]


def classify_smd_heuristic(smd_abs: float) -> str:
    """Classify standardized mean difference magnitude with explicit heuristic labeling."""
    if smd_abs < SMD_HEURISTIC_THRESHOLDS["negligible"]:
        return "negligible (heuristic)"
    elif smd_abs < SMD_HEURISTIC_THRESHOLDS["small"]:
        return "small (heuristic)"
    elif smd_abs < SMD_HEURISTIC_THRESHOLDS["medium"]:
        return "medium (heuristic)"
    return "large (heuristic)"
