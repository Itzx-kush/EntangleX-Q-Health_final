"""Constants, limitations, and scientific disclaimers for external validation."""

VALIDATION_LIMITATIONS = [
    "External validation evaluates the locked model on a separate dataset.",
    "External validation is stronger evidence about generalization than reusing the training/holdout population, but it does not by itself establish clinical validity.",
    "Dataset provenance and independence matter.",
    "Differences in acquisition, population, feature definitions, class balance, missingness, or preprocessing conventions can affect results.",
    "External validation does not establish causal validity.",
    "External validation does not establish treatment effectiveness.",
    "External validation does not establish quantum advantage.",
    "If the external dataset is small, the uncertainty of its metrics must be explicitly disclosed.",
]

SIGN_CONVENTION = (
    "delta = external_metric - internal_metric; "
    "negative delta indicates external metric is lower than internal held-out baseline"
)

EVALUATED_METRIC_NAMES = [
    "accuracy",
    "sensitivity",
    "specificity",
    "precision",
    "recall",
    "f1",
    "roc_auc",
]
