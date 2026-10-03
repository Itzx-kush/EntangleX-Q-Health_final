"""Built-in reusable research protocol templates for EntangleX Q-Health."""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from ..utils.serialization import fingerprint


PROTOCOL_SCHEMA_VERSION = "protocol_definition_v1"


def _template_id(name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"qhealth:protocol-template:{name}"))


BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "Biomedical Binary Classification",
        "description": "Standardized biomedical binary risk classification benchmark with 5-fold cross-validation, locked operating threshold, and probability calibration.",
        "version": "v1",
        "task_type": "binary_classification",
        "parameters_schema": {
            "cv_folds": {"type": "integer", "default": 5, "description": "Cross-validation fold count (2-20)"},
            "test_size": {"type": "float", "default": 0.2, "description": "Holdout test fraction (0.05-0.5)"},
            "primary_metric": {"type": "string", "default": "roc_auc", "description": "Primary evaluation metric"},
            "threshold_strategy": {"type": "string", "default": "f1_optimal", "description": "Threshold selection strategy"},
            "calibration_required": {"type": "boolean", "default": True, "description": "Whether probability calibration is mandatory"},
            "dataset_id": {"type": "string", "default": None, "description": "Optional dataset lock"},
            "pipeline_version_id": {"type": "string", "default": None, "description": "Optional pipeline version lock"},
        },
        "definition": {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "study_metadata": {
                "study_purpose": "Biomedical binary classification benchmark with controlled held-out and CV evaluation.",
                "task_type": "binary_classification",
                "task_description": "Evaluation of clinical condition risk prediction models with rigorous evaluation metrics.",
                "experiment_scope": "biomedical_risk_prediction",
            },
            "dataset_policy": {
                "dataset_id": None,
                "dataset_version_id": None,
                "required_dataset_version": False,
                "target_column": None,
                "positive_label": None,
                "negative_label": None,
                "included_populations": [],
                "excluded_populations": [],
            },
            "split_policy": {
                "strategy": "stratified_kfold",
                "test_size": 0.2,
                "cv_folds": 5,
                "stratify": True,
                "group_column": None,
                "split_seed": 42,
            },
            "randomness_policy": {
                "primary_seed": 42,
                "seed_list": [42, 101, 202, 303, 404],
                "multi_seed_count": 5,
                "determinism_required": True,
            },
            "model_policy": {
                "allowed_model_types": ["logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"],
                "model_families": ["classical", "quantum", "hybrid"],
            },
            "pipeline_policy": {
                "pipeline_version_id": None,
                "pipeline_fingerprint": None,
                "requirement": "OPTIONAL",
            },
            "evaluation_policy": {
                "primary_metric": "roc_auc",
                "secondary_metrics": ["accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity", "pr_auc", "brier_score"],
                "confidence_intervals": False,
                "statistical_reporting": True,
            },
            "threshold_policy": {
                "requirement": "REQUIRED",
                "strategy": "f1_optimal",
                "target_sensitivity": None,
                "fixed_threshold": None,
                "lock_threshold": True,
            },
            "calibration_policy": {
                "requirement": "REQUIRED",
                "method": "isotonic",
                "calibration_split": "cv",
                "calibration_metrics": ["brier_score"],
            },
            "validation_extensions": {
                "multi_seed": {"requirement": "OPTIONAL", "min_seed_count": 5},
                "external_validation": {"requirement": "OPTIONAL", "external_dataset_id": None},
                "distribution_shift": {"requirement": "OPTIONAL", "significance_alpha": 0.05},
                "group_validation": {"requirement": "OPTIONAL", "required_group_column": None},
                "robustness": {"requirement": "OPTIONAL", "perturbation_types": ["missingness", "gaussian_noise"]},
                "ablation": {"requirement": "OPTIONAL", "target_components": []},
            },
            "quantum_controls": {
                "requirement": "OPTIONAL",
                "controlled_comparison_protocol_id": None,
                "dataset_parity": True,
                "sample_parity": True,
                "test_population_parity": True,
                "preprocessing_parity": True,
                "seed_policy_parity": True,
                "provider_provenance": True,
            },
            "constraints": {
                "required_cv_folds": 5,
                "calibration_required": True,
                "threshold_must_be_locked": True,
                "required_metrics": ["roc_auc", "f1", "sensitivity", "specificity"],
            },
        },
    },
    {
        "name": "External Validation Study",
        "description": "Validation protocol requiring testing on an independent cohort and explicit distribution-shift verification.",
        "version": "v1",
        "task_type": "binary_classification",
        "parameters_schema": {
            "external_dataset_id": {"type": "string", "default": None, "description": "Independent validation dataset ID (mandatory for application)"},
            "significance_alpha": {"type": "float", "default": 0.05, "description": "Significance alpha for distribution shift tests"},
            "primary_metric": {"type": "string", "default": "roc_auc", "description": "Primary evaluation metric"},
            "calibration_required": {"type": "boolean", "default": True, "description": "Whether calibration is required on baseline"},
        },
        "definition": {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "study_metadata": {
                "study_purpose": "External cohort validation protocol evaluating transportability across distinct biomedical populations.",
                "task_type": "binary_classification",
                "task_description": "Evaluation of model generalization on an independent external validation dataset.",
                "experiment_scope": "external_validation",
            },
            "dataset_policy": {
                "dataset_id": None,
                "dataset_version_id": None,
                "required_dataset_version": True,
                "target_column": None,
                "positive_label": None,
                "negative_label": None,
                "included_populations": [],
                "excluded_populations": [],
            },
            "split_policy": {
                "strategy": "train_test_split",
                "test_size": 0.2,
                "cv_folds": 5,
                "stratify": True,
                "group_column": None,
                "split_seed": 42,
            },
            "randomness_policy": {
                "primary_seed": 42,
                "seed_list": [42, 101, 202],
                "multi_seed_count": 3,
                "determinism_required": True,
            },
            "model_policy": {
                "allowed_model_types": ["logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"],
                "model_families": ["classical", "quantum", "hybrid"],
            },
            "pipeline_policy": {
                "pipeline_version_id": None,
                "pipeline_fingerprint": None,
                "requirement": "REQUIRED",
            },
            "evaluation_policy": {
                "primary_metric": "roc_auc",
                "secondary_metrics": ["accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity", "pr_auc", "brier_score"],
                "confidence_intervals": False,
                "statistical_reporting": True,
            },
            "threshold_policy": {
                "requirement": "REQUIRED",
                "strategy": "fixed",
                "target_sensitivity": None,
                "fixed_threshold": 0.5,
                "lock_threshold": True,
            },
            "calibration_policy": {
                "requirement": "REQUIRED",
                "method": "isotonic",
                "calibration_split": "cv",
                "calibration_metrics": ["brier_score"],
            },
            "validation_extensions": {
                "multi_seed": {"requirement": "OPTIONAL", "min_seed_count": 3},
                "external_validation": {"requirement": "REQUIRED", "external_dataset_id": None},
                "distribution_shift": {"requirement": "REQUIRED", "significance_alpha": 0.05},
                "group_validation": {"requirement": "OPTIONAL", "required_group_column": None},
                "robustness": {"requirement": "OPTIONAL", "perturbation_types": ["missingness"]},
                "ablation": {"requirement": "OPTIONAL", "target_components": []},
            },
            "quantum_controls": {
                "requirement": "OPTIONAL",
                "controlled_comparison_protocol_id": None,
                "dataset_parity": True,
                "sample_parity": True,
                "test_population_parity": True,
                "preprocessing_parity": True,
                "seed_policy_parity": True,
                "provider_provenance": True,
            },
            "constraints": {
                "external_validation_required": True,
                "distribution_shift_required": True,
                "required_dataset_version": True,
                "calibration_required": True,
            },
        },
    },
    {
        "name": "Quantum-vs-Classical Controlled Study",
        "description": "Rigorous benchmark requiring matched datasets, identical train/test splits, controlled random seeds, and verifiable parity checks between classical and quantum/hybrid models.",
        "version": "v1",
        "task_type": "binary_classification",
        "parameters_schema": {
            "controlled_comparison_required": {"type": "boolean", "default": True, "description": "Mandatory controlled comparison evidence protocol"},
            "primary_metric": {"type": "string", "default": "roc_auc", "description": "Primary benchmark metric"},
            "n_seeds": {"type": "integer", "default": 5, "description": "Random seed count for parity"},
            "calibration_required": {"type": "boolean", "default": False, "description": "Whether calibration is mandatory"},
        },
        "definition": {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "study_metadata": {
                "study_purpose": "Controlled head-to-head classical-vs-quantum comparison under strict parity constraints.",
                "task_type": "binary_classification",
                "task_description": "Controlled benchmark measuring classical baselines against quantum and hybrid PennyLane architectures.",
                "experiment_scope": "quantum_vs_classical",
            },
            "dataset_policy": {
                "dataset_id": None,
                "dataset_version_id": None,
                "required_dataset_version": True,
                "target_column": None,
                "positive_label": None,
                "negative_label": None,
                "included_populations": [],
                "excluded_populations": [],
            },
            "split_policy": {
                "strategy": "stratified_kfold",
                "test_size": 0.2,
                "cv_folds": 5,
                "stratify": True,
                "group_column": None,
                "split_seed": 42,
            },
            "randomness_policy": {
                "primary_seed": 42,
                "seed_list": [42, 101, 202, 303, 404],
                "multi_seed_count": 5,
                "determinism_required": True,
            },
            "model_policy": {
                "allowed_model_types": ["logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"],
                "model_families": ["classical", "quantum", "hybrid"],
            },
            "pipeline_policy": {
                "pipeline_version_id": None,
                "pipeline_fingerprint": None,
                "requirement": "REQUIRED",
            },
            "evaluation_policy": {
                "primary_metric": "roc_auc",
                "secondary_metrics": ["accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity", "pr_auc", "brier_score"],
                "confidence_intervals": False,
                "statistical_reporting": True,
            },
            "threshold_policy": {
                "requirement": "REQUIRED",
                "strategy": "target_sensitivity",
                "target_sensitivity": 0.85,
                "fixed_threshold": None,
                "lock_threshold": True,
            },
            "calibration_policy": {
                "requirement": "OPTIONAL",
                "method": "isotonic",
                "calibration_split": "cv",
                "calibration_metrics": ["brier_score"],
            },
            "validation_extensions": {
                "multi_seed": {"requirement": "OPTIONAL", "min_seed_count": 5},
                "external_validation": {"requirement": "OPTIONAL", "external_dataset_id": None},
                "distribution_shift": {"requirement": "OPTIONAL", "significance_alpha": 0.05},
                "group_validation": {"requirement": "OPTIONAL", "required_group_column": None},
                "robustness": {"requirement": "OPTIONAL", "perturbation_types": ["missingness", "gaussian_noise"]},
                "ablation": {"requirement": "OPTIONAL", "target_components": []},
            },
            "quantum_controls": {
                "requirement": "REQUIRED",
                "controlled_comparison_protocol_id": None,
                "dataset_parity": True,
                "sample_parity": True,
                "test_population_parity": True,
                "preprocessing_parity": True,
                "seed_policy_parity": True,
                "provider_provenance": True,
            },
            "constraints": {
                "controlled_comparison_required": True,
                "required_dataset_version": True,
                "dataset_parity_required": True,
                "preprocessing_parity_required": True,
            },
        },
    },
    {
        "name": "Multi-Seed Evaluation",
        "description": "Protocol mandating evaluation over at least 5 independent pseudo-random seeds to assess model stability and variance.",
        "version": "v1",
        "task_type": "binary_classification",
        "parameters_schema": {
            "n_seeds": {"type": "integer", "default": 5, "description": "Minimum seed count (>= 5)"},
            "cv_folds": {"type": "integer", "default": 5, "description": "Cross-validation fold count"},
            "primary_metric": {"type": "string", "default": "roc_auc", "description": "Primary evaluation metric"},
        },
        "definition": {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "study_metadata": {
                "study_purpose": "Multi-seed statistical evaluation assessing training stability and performance dispersion.",
                "task_type": "binary_classification",
                "task_description": "Stability evaluation across deterministic random seeds.",
                "experiment_scope": "multi_seed_stability",
            },
            "dataset_policy": {
                "dataset_id": None,
                "dataset_version_id": None,
                "required_dataset_version": False,
                "target_column": None,
                "positive_label": None,
                "negative_label": None,
                "included_populations": [],
                "excluded_populations": [],
            },
            "split_policy": {
                "strategy": "stratified_kfold",
                "test_size": 0.2,
                "cv_folds": 5,
                "stratify": True,
                "group_column": None,
                "split_seed": 42,
            },
            "randomness_policy": {
                "primary_seed": 42,
                "seed_list": [42, 101, 202, 303, 404],
                "multi_seed_count": 5,
                "determinism_required": True,
            },
            "model_policy": {
                "allowed_model_types": ["logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"],
                "model_families": ["classical", "quantum", "hybrid"],
            },
            "pipeline_policy": {
                "pipeline_version_id": None,
                "pipeline_fingerprint": None,
                "requirement": "OPTIONAL",
            },
            "evaluation_policy": {
                "primary_metric": "roc_auc",
                "secondary_metrics": ["accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity", "pr_auc"],
                "confidence_intervals": True,
                "statistical_reporting": True,
            },
            "threshold_policy": {
                "requirement": "OPTIONAL",
                "strategy": "f1_optimal",
                "target_sensitivity": None,
                "fixed_threshold": None,
                "lock_threshold": True,
            },
            "calibration_policy": {
                "requirement": "OPTIONAL",
                "method": "isotonic",
                "calibration_split": "cv",
                "calibration_metrics": ["brier_score"],
            },
            "validation_extensions": {
                "multi_seed": {"requirement": "REQUIRED", "min_seed_count": 5},
                "external_validation": {"requirement": "OPTIONAL", "external_dataset_id": None},
                "distribution_shift": {"requirement": "OPTIONAL", "significance_alpha": 0.05},
                "group_validation": {"requirement": "OPTIONAL", "required_group_column": None},
                "robustness": {"requirement": "OPTIONAL", "perturbation_types": []},
                "ablation": {"requirement": "OPTIONAL", "target_components": []},
            },
            "quantum_controls": {
                "requirement": "OPTIONAL",
                "controlled_comparison_protocol_id": None,
                "dataset_parity": True,
                "sample_parity": True,
                "test_population_parity": True,
                "preprocessing_parity": True,
                "seed_policy_parity": True,
                "provider_provenance": True,
            },
            "constraints": {
                "minimum_seed_count": 5,
                "multi_seed_required": True,
            },
        },
    },
    {
        "name": "Robustness Evaluation",
        "description": "Stress-test protocol measuring metric degradation under controlled synthetic missingness and noise perturbations.",
        "version": "v1",
        "task_type": "binary_classification",
        "parameters_schema": {
            "perturbation_types": {"type": "list", "default": ["missingness", "gaussian_noise"], "description": "Perturbation types to test"},
            "primary_metric": {"type": "string", "default": "roc_auc", "description": "Primary evaluation metric"},
        },
        "definition": {
            "schema_version": PROTOCOL_SCHEMA_VERSION,
            "study_metadata": {
                "study_purpose": "Stress testing model resistance to data corruption and missing values.",
                "task_type": "binary_classification",
                "task_description": "Robustness analysis under controlled data degradation scenarios.",
                "experiment_scope": "perturbation_robustness",
            },
            "dataset_policy": {
                "dataset_id": None,
                "dataset_version_id": None,
                "required_dataset_version": False,
                "target_column": None,
                "positive_label": None,
                "negative_label": None,
                "included_populations": [],
                "excluded_populations": [],
            },
            "split_policy": {
                "strategy": "stratified_kfold",
                "test_size": 0.2,
                "cv_folds": 5,
                "stratify": True,
                "group_column": None,
                "split_seed": 42,
            },
            "randomness_policy": {
                "primary_seed": 42,
                "seed_list": [42, 101, 202],
                "multi_seed_count": 3,
                "determinism_required": True,
            },
            "model_policy": {
                "allowed_model_types": ["logistic_regression", "random_forest", "svm", "vqc", "qnn", "hybrid_pennylane_torch"],
                "model_families": ["classical", "quantum", "hybrid"],
            },
            "pipeline_policy": {
                "pipeline_version_id": None,
                "pipeline_fingerprint": None,
                "requirement": "OPTIONAL",
            },
            "evaluation_policy": {
                "primary_metric": "roc_auc",
                "secondary_metrics": ["accuracy", "balanced_accuracy", "f1", "sensitivity", "specificity"],
                "confidence_intervals": False,
                "statistical_reporting": True,
            },
            "threshold_policy": {
                "requirement": "OPTIONAL",
                "strategy": "f1_optimal",
                "target_sensitivity": None,
                "fixed_threshold": None,
                "lock_threshold": True,
            },
            "calibration_policy": {
                "requirement": "OPTIONAL",
                "method": "isotonic",
                "calibration_split": "cv",
                "calibration_metrics": ["brier_score"],
            },
            "validation_extensions": {
                "multi_seed": {"requirement": "OPTIONAL", "min_seed_count": 3},
                "external_validation": {"requirement": "OPTIONAL", "external_dataset_id": None},
                "distribution_shift": {"requirement": "OPTIONAL", "significance_alpha": 0.05},
                "group_validation": {"requirement": "OPTIONAL", "required_group_column": None},
                "robustness": {"requirement": "REQUIRED", "perturbation_types": ["missingness", "gaussian_noise"]},
                "ablation": {"requirement": "OPTIONAL", "target_components": []},
            },
            "quantum_controls": {
                "requirement": "OPTIONAL",
                "controlled_comparison_protocol_id": None,
                "dataset_parity": True,
                "sample_parity": True,
                "test_population_parity": True,
                "preprocessing_parity": True,
                "seed_policy_parity": True,
                "provider_provenance": True,
            },
            "constraints": {
                "robustness_required": True,
            },
        },
    },
]


def get_builtin_template(name: str) -> dict[str, Any] | None:
    for template in BUILTIN_TEMPLATES:
        if template["name"] == name:
            return template
    return None
