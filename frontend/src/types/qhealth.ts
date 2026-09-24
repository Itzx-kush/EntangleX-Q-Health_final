export type ModelKind = 'logistic_regression' | 'svm' | 'random_forest' | 'vqc' | 'qsvc' | 'qnn';
export type MetricName = 'accuracy' | 'precision' | 'recall' | 'sensitivity' | 'specificity' | 'f1' | 'roc_auc';

export interface PipelineConfig {
  imputer:'median'|'mean'|'most_frequent'; scaler:'standard'|'minmax'|'robust'|'none';
  outlier_strategy:'none'|'clip_quantiles'; lower_quantile:number; upper_quantile:number;
  log_features:string[]; ratios:{name:string;numerator:string;denominator:string}[];
  selection:'none'|'anova'|'mutual_info'|'variance'; k_features:number; variance_threshold:number;
  pca_components:number|null; pca_whiten:boolean; angle_scaling:boolean;
}
export interface QuantumConfig {
  backend:'statevector'|'aer'; qubits:number; feature_map_reps:number; ansatz_reps:number;
  entanglement:'linear'|'full'; optimizer:'COBYLA'|'SPSA'; maxiter:number; shots:number; noise_probability:number;
}
export interface TrainingConfig {
  dataset_id:string; features:string[]|null; models:ModelKind[]; pipeline:PipelineConfig; quantum:QuantumConfig;
  parameters:{logistic_c:number;svm_c:number;svm_kernel:'rbf'|'linear';forest_trees:number;forest_max_depth:number|null;class_weight:'balanced'|null};
  seed:number; test_size:number; cv_folds:number; max_samples:number|null; duplicate_policy:'reject'|'drop_exact';
  probability_threshold:number; calibration:'none'|'sigmoid'|'isotonic'; calibration_folds:number;
}
export interface Provenance {name:string;domain:string;source:string;source_url:string|null;version:string;target:string;positive_label:string;negative_label:string;features:string[];numeric_features:string[];categorical_features:string[];row_count:number;feature_count:number;class_distribution:Record<string,number>;target_classes:string[];is_demo:boolean;dataset_hash:string;license:string|null;[key:string]:unknown}
export interface Quality {scope:string;row_count:number;feature_count:number;class_distribution:Record<string,number>;minority_fraction:number;class_imbalance:boolean;missing_values:Record<string,number>;infinite_values:Record<string,number>;duplicate_rows:number;duplicate_feature_rows:number;constant_features:string[];low_variance_features:string[];suspiciously_predictive_features:string[];identifier_features:string[];highly_correlated_pairs:{feature_a:string;feature_b:string;absolute_correlation:number}[];warnings:string[];blockers:string[];distributions:Record<string,unknown>[];invalid_numeric_values:string}
export interface Dataset {id:string;name:string;sha256:string;provenance:Provenance;quality:Quality;created_at:string}
export interface DatasetLibraryItem {slug:string;name:string;domain:string;description:string;source:string;source_url:string;version:string;license:string;task:string;target:string;positive_label:string;negative_label:string;rows:number;features:number;numeric_feature_count:number;categorical_feature_count:number;filename:string;is_demo:boolean;dataset_hash:string;hash_algorithm:string;hash_scope:string}
export interface TargetCandidate {column:string;confidence:number;reasons:string[];class_count:number;class_distribution:Record<string,number>}
export interface SuggestedMetadata {name:string;name_source:string;target:string|null;target_confidence:number;target_source:string;target_classes:string[];target_classes_source:string;target_class_distribution:Record<string,number>;positive_label:string|null;positive_label_confidence:number;positive_label_source:string;negative_label:string|null;negative_label_source:string|null;version:string;version_source:string;domain:string;domain_source:string;source:string;source_source:string}
export interface CompatibilityCheck {code:string;status:'PASS'|'WARNING'|'BLOCKED';message:string}
export interface CompatibilityReport {status:'READY'|'WARNING'|'BLOCKED';checks:CompatibilityCheck[];blockers:string[];warnings:string[]}
export interface DatasetInspection {suggested_metadata:SuggestedMetadata;metadata_warnings:string[];row_count:number;column_count:number;column_names:string[];numeric_columns:string[];categorical_columns:string[];boolean_columns:string[];datetime_like_columns:string[];unsupported_columns:string[];missing_values:Record<string,number>;infinite_values:Record<string,number>;duplicate_rows:number;duplicate_feature_rows:number;constant_features:string[];low_variance_features:string[];high_cardinality_categorical_features:string[];identifier_like_columns:string[];empty_columns:string[];possible_target_columns:string[];target_candidates:TargetCandidate[];target:string|null;target_classes:string[];class_distribution:Record<string,number>;schema_consistent:boolean;suspicious_target_proxy_columns:string[];transformations_applied:string[];compatibility:CompatibilityReport;file_format:string;filename:string;file_size_bytes:number}
export interface Job {id:string;experiment_id:string;status:string;progress:number;state:string;errors:Record<string,unknown>[];created_at:string;updated_at:string}
export interface Experiment {id:string;dataset_id:string;parent_id:string|null;status:string;config:TrainingConfig;summary:Record<string,unknown>;created_at:string}
export interface Metrics {accuracy:number|null;precision:number|null;recall:number|null;sensitivity:number|null;specificity:number|null;f1:number|null;roc_auc:number|null;true_positive:number;true_negative:number;false_positive:number;false_negative:number;confusion_matrix:number[][];sample_count:number;roc_curve:{fpr:number[];tpr:number[];thresholds:(number|null)[]}|null;undefined_metrics:string[]}
export interface ModelMetrics {training:Metrics;test:Metrics;validation:{folds:Metrics[];summary:Record<MetricName,{mean:number|null;std:number|null;valid_folds:number}>;std_definition:string};timing:{final_training_seconds:number;cv_total_seconds:number;test_inference_seconds:number;test_inference_seconds_per_sample:number};calibration:Record<string,unknown>}
export interface ModelRecord {id:string;experiment_id:string;dataset_id:string;model_type:ModelKind;status:string;details:Record<string,unknown>;metrics:Partial<ModelMetrics>;created_at:string}
export interface ExperimentDetail {experiment:Experiment;models:ModelRecord[];jobs:Job[]}
export interface Preview {train_count:number;test_count:number;input_features:string[];selected_features:string[];output_features:string[];selection_scores:{feature:string;score:number|null;selected:boolean}[];pca_explained_variance:number[];pca_loadings:number[][];split_hash:string;stages:string[];warnings:string[]}
export interface Circuit {model_type:string;execution_kind:string;backend:string;qubits:number;logical_depth:number;parameter_count:number;gate_counts:Record<string,number>;text:string;gates:{name:string;qubits:number[];parameters:string[]}[];limitation:string}
export interface Influence {feature:string;magnitude:number;std?:number;delta_plus?:number;delta_minus?:number;perturbation?:string}
export interface Explanation {id:string;model_id:string;method:string;created_at:string;result:{title:string;scope:string;sample_count:number;units:string;influence:Influence[];elapsed_seconds:number;limitations:string[]}}
export interface Prediction {model_id:string;model_type:ModelKind;positive_label:string;negative_label:string;probability_status:string;decision_rule:string;risk_thresholds:[number,number];predictions:{sample:string;predicted_class:string;probability_positive:number|null;decision_score:number|null;research_risk_category:string|null}[];influence:Influence[]|null;limitations:string[];disclaimer:string}
export interface Comparison {experiment_id:string;models:ModelRecord[];pairs:{quantum_type:string;classical_type:string;conclusion:string;test_metric_delta_quantum_minus_classical:Record<MetricName,number|null>;final_training_seconds_delta:number}[];split:Record<string,unknown>;comparison_fingerprint:string;conclusion:string;limitations:string[]}
export interface Health {status:string;version:string;mode:string;authentication_required:boolean;quantum:{available:boolean;runtime_verified:boolean;execution:string};disclaimer:string}
export interface SystemStatus {status:string;version:string;mode:string;database_available:boolean;storage_available:boolean;quantum:Health['quantum'];supported_models:{classical:string[];quantum:string[]};jobs:{queued:number;running:number;active:number};}
