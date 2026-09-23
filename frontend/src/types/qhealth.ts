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
