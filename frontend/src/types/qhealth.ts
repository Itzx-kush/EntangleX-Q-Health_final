export type ModelKind = 'logistic_regression' | 'svm' | 'random_forest' | 'vqc' | 'qsvc' | 'qnn' | 'hybrid_pennylane_torch';
export type MetricName = 'accuracy' | 'precision' | 'recall' | 'sensitivity' | 'specificity' | 'f1' | 'roc_auc';

export interface PipelineConfig {
  imputer:'median'|'mean'|'most_frequent'; scaler:'standard'|'minmax'|'robust'|'none';
  outlier_strategy:'none'|'clip_quantiles'; lower_quantile:number; upper_quantile:number;
  log_features:string[]; ratios:{name:string;numerator:string;denominator:string}[];
  selection:'none'|'anova'|'mutual_info'|'variance'; k_features:number; variance_threshold:number;
  pca_components:number|null; pca_whiten:boolean; angle_scaling:boolean;
}
export interface QuantumConfig {
  provider_id?:'qiskit_local'; execution_mode?:'local_simulator';
  backend:'statevector'|'aer'; qubits:number; feature_map_reps:number; ansatz_reps:number;
  entanglement:'linear'|'full'; optimizer:'COBYLA'|'SPSA'; maxiter:number; shots:number; noise_probability:number;
}
export interface HybridModelConfig {model_type:'hybrid_pennylane_torch';provider_id?:'pennylane_local';execution_mode?:'local_simulator';qubits:number;feature_map:'angle';quantum_layers:number;classical_hidden_dimensions:number[];classical_activation:'relu'|'tanh';optimizer:'adam'|'sgd';learning_rate:number;epochs:number;batch_size:number;deterministic_seed:number;sample_cap:number;backend:'default.qubit'}
export interface QuantumBackendDescriptor {backend_id:string;display_name:string;provider_id:string;backend_type:string;available:boolean;capabilities:Record<string,string|number|null>}
export interface QuantumProviderDescriptor {provider_id:string;display_name:string;provider_type:'LOCAL_SIMULATOR'|'REMOTE_SIMULATOR'|'HARDWARE'|'CUSTOM';enabled:boolean;availability:string;backends:QuantumBackendDescriptor[]}
export interface TrainingConfig {
  dataset_id:string; features:string[]|null; models:ModelKind[]; pipeline:PipelineConfig; quantum:QuantumConfig; hybrid:HybridModelConfig;
  parameters:{logistic_c:number;svm_c:number;svm_kernel:'rbf'|'linear';forest_trees:number;forest_max_depth:number|null;class_weight:'balanced'|null};
  seed:number; test_size:number; cv_folds:number; max_samples:number|null; duplicate_policy:'reject'|'drop_exact';
  probability_threshold:number; threshold_strategy:'fixed'|'target_sensitivity'; target_sensitivity:number;
  calibration:'none'|'sigmoid'|'isotonic'; calibration_folds:number;
}
export interface Provenance {name:string;domain:string;source:string;source_url:string|null;version:string;target:string;positive_label:string;negative_label:string;features:string[];numeric_features:string[];categorical_features:string[];row_count:number;feature_count:number;class_distribution:Record<string,number>;target_classes:string[];is_demo:boolean;dataset_hash:string;license:string|null;origin?:'built_in'|'uploaded';dataset_status?:string;target_type?:string;recommended_duplicate_policy?:'reject'|'drop_exact';[key:string]:unknown}
export interface Quality {scope:string;row_count:number;feature_count:number;class_distribution:Record<string,number>;minority_fraction:number;class_imbalance:boolean;missing_values:Record<string,number>;infinite_values:Record<string,number>;duplicate_rows:number;duplicate_feature_rows:number;constant_features:string[];low_variance_features:string[];suspiciously_predictive_features:string[];identifier_features:string[];highly_correlated_pairs:{feature_a:string;feature_b:string;absolute_correlation:number}[];warnings:string[];blockers:string[];distributions:Record<string,unknown>[];invalid_numeric_values:string}
export interface Dataset {id:string;name:string;sha256:string;provenance:Provenance;quality:Quality;created_at:string}
export interface TargetCandidate {column:string;score:number;confidence:'low'|'medium'|'high';target_type:string;class_labels:string[];class_distribution:Record<string,number>;unique_values:number;missing_fraction:number;eligible_for_current_pipeline:boolean;reasons:string[];penalties:string[];position:number}
export interface DatasetInspection {filename:string;sha256:string;row_count:number;column_count:number;columns:string[];schema:{name:string;type:string;missing_count:number;unique_count:number}[];detected_target:string|null;target_type:string|null;confidence_score:number;confidence:'low'|'medium'|'high';selection_method:string;class_labels:string[];class_distribution:Record<string,number>;positive_label:string|null;positive_label_confidence:number;positive_label_reason:string;requires_manual_target:boolean;requires_positive_label:boolean;heuristic_notice:string;candidates:TargetCandidate[]}
export interface DemoReadiness {status:'ready'|'requires_processing';instant_demo_available:boolean;artifact_version:string|null;experiment_id:string|null;model_ids:string[];verified_dataset_hash:string|null;verified_artifact_manifest_hash:string|null;unavailable_reason?:string|null}
export interface DatasetLibraryItem {slug:string;name:string;domain:string;description:string;source:string;source_url:string;version:string;license:string;license_url:string;attribution:string;target:string;target_type:'binary_classification';positive_label:string;negative_label:string;row_count:number;feature_count:number;class_labels:string[];sha256:string;normalization:string[];recommended_duplicate_policy:'reject'|'drop_exact';origin:'built_in';dataset_status:'available';demo_readiness:DemoReadiness}
export interface Job {id:string;experiment_id:string;run_id?:string|null;job_type?:string;status:string;priority?:number;progress:number;total_units?:number|null;completed_units?:number;failed_units?:number;skipped_units?:number;active_unit?:string|null;current_phase?:string|null;state:string;errors:Record<string,unknown>[];attempt_count?:number;resume_count?:number;current_checkpoint_id?:string|null;failure_category?:string|null;error_code?:string|null;error_message?:string|null;requested_at?:string|null;started_at?:string|null;completed_at?:string|null;cancelled_at?:string|null;created_at:string;updated_at:string;experiment_name?:string|null;models?:ModelRecord[]}
export interface Experiment {id:string;name?:string|null;dataset_id:string;parent_id:string|null;status:string;config:TrainingConfig;summary:Record<string,unknown>;created_at:string}
export interface Metrics {accuracy:number|null;precision:number|null;recall:number|null;sensitivity:number|null;specificity:number|null;f1:number|null;roc_auc:number|null;true_positive:number;true_negative:number;false_positive:number;false_negative:number;confusion_matrix:number[][];sample_count:number;roc_curve:{fpr:number[];tpr:number[];thresholds:(number|null)[]}|null;undefined_metrics:string[]}
export interface ThresholdPoint {threshold:number;sensitivity:number|null;specificity:number|null;precision:number|null;recall:number|null;f1:number|null;accuracy:number|null;roc_auc:number|null}
export interface OperatingPoint {selection_strategy:'fixed'|'target_sensitivity';target_sensitivity:number|null;target_specificity:number|null;selected_threshold:number|null;threshold_units:string;threshold_feasible:boolean;threshold_source:string;validation_metrics:ThresholdPoint|null;holdout_metrics:Partial<Record<MetricName,number|null>>|null;number_of_oof_samples:number|null;cv_fold_count:number|null;curve:ThresholdPoint[];interpretation:string;infeasible_reason?:string|null}
export interface ModelMetrics {training:Metrics;test:Metrics;validation:{folds:Metrics[];summary:Record<MetricName,{mean:number|null;std:number|null;valid_folds:number}>;std_definition:string};timing:{final_training_seconds:number;cv_total_seconds:number;cv_fold_seconds:number[];test_inference_seconds:number;test_inference_seconds_per_sample:number};calibration:Record<string,unknown>;operating_point?:OperatingPoint}
export interface HybridMetadata {framework?:string;classical_framework?:string;backend?:string;execution_kind?:string;real_hardware?:boolean;qubits?:number;quantum_layers?:number;classical_parameter_count?:number;quantum_parameter_count?:number;configuration?:{hidden_dimensions?:number[]};[key:string]:unknown}
export interface ModelDetails extends Record<string,unknown> {quantum?:HybridMetadata;supports_probability?:boolean;probability_status?:string;operating_point?:OperatingPoint;experiment_kind?:string}
export interface ModelRecord {id:string;experiment_id:string;dataset_id:string;model_type:ModelKind;status:string;progress?:number|null;details:ModelDetails;metrics:Partial<ModelMetrics>;created_at:string}
export type ModelCardEvidenceStatus='available'|'not_available'|'not_applicable'|'limited'|'not_recorded'|'not_yet_evaluated';
export interface ModelCard {
  schema_version:'model_card_v1';card_id:string;generated_at:string;
  card_status:'COMPLETE'|'COMPLETE_WITH_LIMITATIONS'|'INCOMPLETE_EVIDENCE'|'UNAVAILABLE';
  intended_use:Record<string,unknown>;model_identity:Record<string,unknown>;task:Record<string,unknown>;
  data:Record<string,unknown>;training:Record<string,unknown>;model:Record<string,unknown>;
  evaluation:{status:ModelCardEvidenceStatus;evidence:Record<string,unknown>[]};
  multi_seed_evidence:{status:ModelCardEvidenceStatus;studies:Record<string,unknown>[]};
  calibration:{status:ModelCardEvidenceStatus;studies:Record<string,unknown>[]};
  threshold:{status:ModelCardEvidenceStatus;studies:Record<string,unknown>[]};
  robustness:{status:ModelCardEvidenceStatus;records:Record<string,unknown>[]};
  external_validation:{status:ModelCardEvidenceStatus;validations:Record<string,unknown>[]};
  distribution_shift:{status:ModelCardEvidenceStatus;analyses:Record<string,unknown>[]};
  group_validation:Record<string,unknown>&{status:ModelCardEvidenceStatus};
  quantum:Record<string,unknown>&{status:ModelCardEvidenceStatus};
  provenance:Record<string,unknown>;reproducibility:Record<string,unknown>;
  limitations:{category:string;description:string;source:string}[];
  evidence_gaps:{category:string;status:string;description:string}[];
  artifact:{artifact_id:string;integrity_hash:string;immutable:boolean};
}
export interface ExperimentDetail {experiment:Experiment;models:ModelRecord[];jobs:Job[]}
export type EvidenceAvailability='available'|'not_available'|'not_applicable'|'limited'|'incomplete'|'blocked';
export interface EvidenceInventoryEntry {
  status:EvidenceAvailability;record_count:number;referenced_ids:string[];artifact_ids:string[];
  latest_compatible_evidence:string|null;configuration_fingerprints:string[];
  evidence_timestamp:string|null;limitations:string[];availability_reason:string;
  [key:string]:unknown;
}
export interface ResearchEvidencePackage {
  schema_version:'research_evidence_package_v1';package_id:string;
  package_status:'READY'|'PARTIAL'|'INCOMPLETE'|'BLOCKED';
  package_fingerprint:string;configuration_fingerprint:string;
  created_at:string;created?:boolean;
  experiment:{id:string;name:string|null;status:string;configuration_fingerprint:string};
  dataset:{dataset_id:string;name:string;dataset_version_id:string|null;content_sha256:string;schema_fingerprint:string|null;target:string|null;target_type:string|null};
  models:Record<string,unknown>[];
  source_context:{type:'live_run'|'verified_demo_experiment';[key:string]:unknown};
  evidence_inventory:Record<string,EvidenceInventoryEntry>;
  provenance:{experiment_id:string;run_ids:string[];artifact_ids:string[];configuration_fingerprints:string[];evidence_source_fingerprints:string[]};
  integrity:{dataset_hash:string;model_artifact_hashes:string[];evidence_artifact_hashes:Record<string,string>;package_fingerprint:string;artifact_id:string;hash_algorithm:'sha256'};
  limitations:string[];evidence_gaps:{category:string;status:string;reason:string}[];
  artifact:{id:string;artifact_type:string;content_type:string;integrity_hash:string;hash_algorithm:string;immutable:boolean};
}
export interface EvidencePackagePreflight {
  feasible:boolean;package_status:ResearchEvidencePackage['package_status'];
  package_fingerprint_candidate:string;evidence_inventory:ResearchEvidencePackage['evidence_inventory'];
  blockers:{code:string;message?:string;record_id?:string}[];
  warnings:{code:string;message:string}[];
  missing_evidence:ResearchEvidencePackage['evidence_gaps'];core_missing_evidence:string[];
  manifest:ResearchEvidencePackage;
}
export interface Preview {train_count:number;test_count:number;input_features:string[];selected_features:string[];output_features:string[];selection_scores:{feature:string;score:number|null;selected:boolean}[];pca_explained_variance:number[];pca_loadings:number[][];split_hash:string;stages:string[];warnings:string[]}
export interface Circuit {model_type:string;execution_kind:string;backend:string;qubits:number;logical_depth:number|null;parameter_count:number;gate_counts:Record<string,number>;text:string;gates:{name:string;qubits:number[];parameters:string[]}[];limitation:string}
export interface ResourceAdvisorChange {field:string;from:number;to:number;reason:string}
export interface ResourceAdvisorResponse {
  requested_configuration:{model_type:'vqc'|'qsvc'|'qnn';quantum:QuantumConfig;feature_dimension:number;sample_count:number;dataset_id:string|null;experiment_id:string|null};
  resource_profile:{logical_qubits:number;feature_dimension:number;feature_map_repetitions:number;ansatz_repetitions:number;entanglement:string;logical_depth:number|null;gate_count:number|null;parameter_count:number|null;circuit_complexity:string;optimizer:string;optimizer_iteration_budget:number;optimization_workload:string;backend:string;execution_kind:string;shots_per_circuit_evaluation:number|null;measurement_workload:string;noise_probability:number;noise_mode:string;sample_count:number;bounded_quantum_sample_cap:number;sample_workload:string;structural_metadata_status:string;hardware_execution:boolean};
  budget_status:{status:'within_budget'|'near_budget'|'exceeds_budget';reasons:string[]};
  budget_policy:{version:string;scope:string;schema_bounds:Record<string,{minimum:number;maximum:number}>;bounded_prototype_limits:Record<string,number>;near_budget_fraction:number;safe_baseline:Record<string,number>;recommendation_order:string[];semantics:string};
  recommendation:{available:boolean;reason?:string;original_configuration:Record<string,unknown>;configuration:{model_type:'vqc'|'qsvc'|'qnn';quantum:QuantumConfig;feature_dimension:number;sample_count:number;dataset_id:string|null;experiment_id:string|null}|null;changes:ResourceAdvisorChange[];rationale:string;valid:boolean;policy_version:string;resource_profile_after?:ResourceAdvisorResponse['resource_profile'];budget_status_after?:ResourceAdvisorResponse['budget_status']};
  changed_parameters:ResourceAdvisorChange[];
  historical_evidence:{matched_runs:number;median_training_seconds:number|null;min_training_seconds:number|null;max_training_seconds:number|null;measured_fields:string[];matching_policy:string;runs:Record<string,unknown>[];limitations:string[]};
  limitations:string[];
}
export interface Influence {feature:string;magnitude:number;signed_mean?:number;contribution?:number;absolute_contribution?:number;direction?:'toward_positive'|'toward_negative'|'neutral';interpretation?:string;original_value?:string|number|boolean|null;std?:number;delta_plus?:number;delta_minus?:number;perturbation?:string}
export interface Explanation {id:string;model_id:string;method:string;created_at:string;result:{title:string;scope:string;sample_count:number;units:string;influence:Influence[];elapsed_seconds:number;limitations:string[];method_display?:string;model_type?:ModelKind;model_display_name?:string;output_semantics?:string;explanation_level?:'global_dataset';background_sample_count?:number;explained_case_count?:number}}
export interface HybridLocalExplanation {method:'shap';method_display:'SHAP — Final Hybrid Output';scope:'local_case';model_type:'hybrid_pennylane_torch';model_display_name:'PennyLane + PyTorch Hybrid';output_semantics:'final positive-class probability';prediction_context:{probability_positive:number;operating_threshold:number;threshold_source:string;predicted_class:string;positive_label:string;negative_label:string;research_risk_category:string|null;base_value:number};contributions:Influence[];background_source:'training partition only';background_sample_count:number;explained_case_count:1;limitations:string[]}
export interface Prediction {model_id:string;model_type:ModelKind;positive_label:string;negative_label:string;probability_status:string;decision_rule:string;operating_threshold:number;threshold_source:string;risk_thresholds:[number,number];predictions:{sample:string;predicted_class:string;probability_positive:number|null;decision_score:number|null;research_risk_category:string|null}[];influence:Influence[]|null;explanation:HybridLocalExplanation|null;limitations:string[];disclaimer:string}
export interface EvidenceValue {classical:number|null;quantum:number|null;delta_quantum_minus_classical:number|null}
export interface EvidenceTiming {final_training_seconds:number|null;cv_total_seconds:number|null;cv_mean_fold_seconds:number|null;test_inference_seconds:number|null;test_inference_seconds_per_sample:number|null}
export type PerturbationType='missingness'|'gaussian_noise'|'outliers'|'categorical';
export interface RobustnessScenario {perturbation_type:PerturbationType;level:number}
export interface RobustnessEvidence {id?:string;status:'evaluated'|'not_applicable'|'failed';reason:string|null;experiment_id:string;dataset_id:string;dataset_hash:string;split_hash:string|null;model_id:string;model_type:ModelKind;perturbation_type:PerturbationType;perturbation_level:number;random_seed:number;sample_count:number;baseline_metrics:Metrics;perturbed_metrics:Metrics|null;degradation_delta:Record<MetricName,number|null>;relative_degradation:Record<MetricName,number|null>;undefined_metrics:Record<string,string>;threshold_used:number;threshold_source:string;preprocessing_context:Record<string,unknown>;perturbation_metadata:Record<string,unknown>|null;execution_timing:{baseline_inference_seconds:number;perturbed_inference_seconds:number|null};limitations:string[];reproducibility_metadata:Record<string,unknown>;created_at?:string}
export interface RobustnessResponse {experiment_id:string;dataset_id:string;sample_count:number;model_count:number;condition_count:number;results:RobustnessEvidence[];limitations:string[]}
export interface RobustnessPairScenario {perturbation_type:PerturbationType;perturbation_level:number;random_seed:number;sample_count:number;classical:RobustnessEvidence|null;quantum:RobustnessEvidence|null;delta_difference_quantum_minus_classical:Record<MetricName,number|null>;interpretation:string}
export interface EvidencePair {
 benchmark_type?:string;
 model_identities?:{classical:{id:string;type:ModelKind;display_name:string};hybrid:{id:string;type:ModelKind;display_name:string}};
 quantum_model:string;classical_model:string;quantum_type:ModelKind;classical_type:ModelKind;
 performance:Record<MetricName,EvidenceValue>;metric_deltas?:Record<MetricName,number|null>;
 holdout_results?:{classical:Record<string,unknown>;hybrid:Record<string,unknown>;evaluation_population:string};
 computational_cost:{classical:EvidenceTiming;quantum:EvidenceTiming;deltas_quantum_minus_classical:EvidenceTiming;semantics:string};
 quantum_resources:{framework?:string|null;classical_framework?:string|null;backend:string|null;execution_kind:string|null;timing_label?:string;qubits:number|null;quantum_layers?:number|null;shots:number|null;logical_depth:number|null;gate_counts:Record<string,number>|null;total_parameter_count:number|null;trainable_parameter_count:number|null;optimizer:string|null;learning_rate?:number|null;epochs?:number|null;optimizer_objective_evaluations:number|null;noise_probability:number|null;real_hardware:boolean;resource_semantics:string};
 fairness:{dataset_id:string;dataset_hash:string|null;target?:string|null;positive_label?:string|null;negative_label?:string|null;experiment_id?:string;split_hash:string|null;sample_pool_hash?:string|null;train_partition_fingerprint?:string|null;test_population_fingerprint?:string|null;common_sample_count:number|null;source_sample_count:number|null;same_sample_budget?:boolean;preprocessing_fingerprint:string|null;comparison_fingerprint?:string|null;cv_fold_count:number|null;seed:number|null;test_size?:number|null;target_sensitivity?:number|null;threshold_strategy:string;controlled_comparison:boolean;status?:string;mismatch_reasons?:string[];missing_measurements?:string[];dataset_match?:boolean;dataset_hash_match?:boolean;sample_pool_match?:boolean;split_match?:boolean;split_hash_match?:boolean;preprocessing_match?:boolean;feature_representation_match?:boolean;pca_dimension_match?:boolean;sample_budget_match?:boolean;cv_fold_match?:boolean;seed_match?:boolean;threshold_strategy_match?:boolean;holdout_match?:boolean;common_representation?:Record<string,unknown>};
 common_representation?:Record<string,unknown>;operating_points:{classical:OperatingPoint;quantum:OperatingPoint;protocol?:string};robustness:{status:string;note:string;scenarios?:RobustnessPairScenario[];limitations?:string[]};conclusion:string;limitations:string[];neutrality?:string;test_metric_delta_quantum_minus_classical:Record<MetricName,number|null>;final_training_seconds_delta:number|null;controlled_protocol_pair?:ControlledComparisonPair|null
}
export interface ControlCheck {name:string;status:'PASS'|'FAIL'|'UNKNOWN';passed:boolean|null;reason:string;evidence:Record<string,unknown>}
export interface ControlledComparisonPair {pair_id:string;status:'CONTROLLED'|'CONTROLLED_WITH_LIMITATIONS'|'NOT_CONTROLLED'|'INCOMPLETE_EVIDENCE'|'BLOCKED';classical_model:{id:string;model_type:ModelKind};quantum_model:{id:string;model_type:ModelKind};control_checks:ControlCheck[];control_matrix:Record<string,boolean|null>;limitations:string[];[key:string]:unknown}
export interface ControlledComparisonProtocol {protocol_id:string;experiment_id:string;schema_version:string;status:string;created_at:string;configuration_fingerprint:string;protocol_fingerprint:string;classical_model_ids:string[];quantum_model_ids:string[];comparison_pairs:ControlledComparisonPair[];control_summary:Record<string,unknown>;provenance:Record<string,unknown>;limitations:string[];warnings:string[];artifact_id:string|null}
export interface Comparison {experiment_id:string;dataset_id:string;models:ModelRecord[];pairs:EvidencePair[];controlled_benchmarks?:EvidencePair[];controlled_protocol?:Pick<ControlledComparisonProtocol,'protocol_id'|'schema_version'|'status'|'protocol_fingerprint'|'artifact_id'|'control_summary'|'created_at'>|null;split:Record<string,unknown>;comparison_fingerprint:string;conclusion:string;limitations:string[]}
export interface Health {status:string;version:string;mode:string;authentication_required:boolean;quantum:{available:boolean;runtime_verified:boolean;execution:string};disclaimer:string}
export interface SystemStatus {status:string;version:string;mode:string;database_available:boolean;storage_available:boolean;quantum:Health['quantum'];model_capabilities:ModelCapability[];supported_models:{classical:string[];quantum:string[];qiskit_quantum:string[];pennylane_hybrid:string[]};jobs:{queued:number;running:number;active:number};}

export type ImplementationStatus='AVAILABLE'|'NOT_YET_IMPLEMENTED'|'UNAVAILABLE';
export interface ModelCapability {model_id:ModelKind;display_name:string;category:'classical'|'quantum'|'hybrid quantum-classical';implementation_status:ImplementationStatus;executable:boolean;quantum_framework?:string|null;classical_framework?:string|null;execution?:string|null;hardware_execution?:string|null;probability_output?:string|null;explainability?:string|null;supported_prediction?:string|null;supported_comparison?:string|null;supported_thresholding?:string|null;supported_robustness?:string|null;training?:string|null}
export interface FrameworkCapability {package_installed:boolean;package_importable:boolean;model_implemented:boolean;model_executable:boolean;simulator_available:boolean;real_hardware_available:boolean;runtime_verified:boolean}
export interface AlignmentContract {contract_version:string;models:ModelCapability[];frameworks:Record<'qiskit'|'qiskit_aer'|'pennylane'|'torch',FrameworkCapability>;showcase:{id:string;display_name:string;label:string;featured_dataset_slug:string;disease_domain:string;target:string;positive_class:string;dataset_hash:string;research_only_disclaimer:string;recommended_models:ModelKind[]};flagship_experiment_preset:{id:string;display_name:string;dataset_slug:string;models:ModelKind[];auto_start_training:false;threshold_strategy:'target_sensitivity';configuration?:Record<string,unknown>;scientific_status?:string;evidence_requirements:string[]};flagship_architecture:{model_id:'hybrid_pennylane_torch';status:'IMPLEMENTED'|'UNAVAILABLE';stages:string[]}}

export interface VerifiedRobustnessResult {model_id:string;model_type:ModelKind;condition:string;configuration:Record<string,unknown>;perturbation:Record<string,unknown>;baseline:Metrics;degraded:Metrics;delta:Record<string,number|null>;relative_delta:Record<string,number|null>;evaluation_indices:number[]}
export interface VerifiedPredictionCase {case_id:string;case_label:'flagged'|'not_flagged';model_id:string;model_type:ModelKind;row_index:number;input:Record<string,string|number|boolean|null>;probability_positive:number;threshold:number;threshold_source:string;predicted_class:string}
export interface VerifiedEvidencePackage {
  verified:true;precomputed:true;slug:string;artifact_version:string;manifest_sha256:string;
  dataset:Dataset;experiment:Experiment;models:ModelRecord[];
  evidence:{
    benchmark:{evidence_type:'benchmark';model_ids:string[];comparison_contract:Record<string,unknown>;models:{model_id:string;model_type:ModelKind;metrics:ModelMetrics;execution:Record<string,unknown>|null;operating_point:OperatingPoint;runtime:ModelMetrics['timing']}[];claims:{quantum_advantage:false;real_quantum_hardware:false}};
    robustness:{evidence_type:'robustness';model_ids:string[];method:string;results:VerifiedRobustnessResult[]};
    explainability:{evidence_type:'explainability';model_ids:string[];model_id:string;method:string;output_path:string;local:HybridLocalExplanation&{case_id:string};global_summary:{feature:string;mean_absolute_shap:number;mean_signed_shap:number}[]};
    predictions:{evidence_type:'predictions';model_ids:string[];model_id:string;cases:VerifiedPredictionCase[]};
    preprocessing:{evidence_type:'preprocessing';model_ids:string[];configuration:TrainingConfig;fitted_preprocessing:Record<string,unknown>;representation:Record<string,unknown>;split:Record<string,unknown>};
    provenance:{evidence_type:'provenance';model_ids:string[];dataset:Provenance};
  };
}
