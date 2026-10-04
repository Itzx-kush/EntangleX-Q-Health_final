import type {HybridModelConfig, QuantumConfig} from './qhealth';

export type QuantumVisualizationModelType='vqc'|'qsvc'|'qnn'|'hybrid_pennylane_torch';
export type QuantumVisualizationStatus='AVAILABLE'|'STRUCTURE_ONLY'|'SIMULATION_AVAILABLE'|'NOT_AVAILABLE'|'NOT_APPLICABLE'|'INSUFFICIENT_REPRESENTATION';

type PreviewContext={
  dataset_id?:string|null;
  dataset_version_id?:string|null;
  experiment_id?:string|null;
  representation_context?:{selected_feature_names?:string[]|null;source?:string|null;angle_scaling?:boolean|null}|null;
  sample_count?:number;
  seed?:number;
};

export type QuantumVisualizationPreviewRequest=PreviewContext&(
  | {model_type:'vqc'|'qsvc'|'qnn';quantum:QuantumConfig;hybrid?:never}
  | {model_type:'hybrid_pennylane_torch';hybrid:HybridModelConfig;quantum?:never}
);

export type QuantumVisualizationSimulationRequest=QuantumVisualizationPreviewRequest&{
  encoded_vector:number[];
  simulation_stage?:'encoding'|'full_model';
  ansatz_parameters?:number[];
};

export interface QuantumVisualizationFeatureMapping {
  feature_index:number;
  feature_name:string|null;
  qubit_index:number;
  parameter_name:string|null;
}

export interface QuantumVisualizationGate {
  gate_index:number;
  name:string;
  gate_type:string;
  qubits:number[];
  parameters:string[];
  control_qubits:number[];
  target_qubits:number[];
}

export interface QuantumVisualizationDatasetContext {
  status:'AVAILABLE'|'NOT_AVAILABLE'|'INSUFFICIENT_REPRESENTATION';
  dataset_id:string|null;
  dataset_version_id:string|null;
  dataset_name:string|null;
  dataset_hash:string|null;
  raw_feature_count:number|null;
  raw_feature_names:string[]|null;
  represented_feature_count:number|null;
  selected_feature_names:string[]|null;
  configured_input_features:string[]|null;
  representation_configuration:Record<string,unknown>;
  representation_status:QuantumVisualizationStatus;
  representation_source:string|null;
  row_count:number|null;
  experiment_id:string|null;
  limitations:string[];
}

export interface QuantumVisualizationEncoding {
  status:QuantumVisualizationStatus;
  method:string;
  description:string;
  feature_to_qubit_mapping:QuantumVisualizationFeatureMapping[];
  encoding_parameters:Record<string,unknown>;
  encoded_dimension:number|null;
  angle_scaling:boolean|null;
  limitations:string[];
}

export interface QuantumVisualizationCircuit {
  model_type:string;
  provider_id:string;
  backend_id:string;
  execution_mode:string;
  execution_kind:string;
  hardware_available:boolean;
  qubits:number|null;
  logical_depth:number|null;
  parameter_count:number|null;
  gate_counts:Record<string,number>;
  total_gates:number|null;
  gate_sequence:QuantumVisualizationGate[];
  circuit_text:string|null;
  feature_map:string|null;
  ansatz:string|null;
  entanglement_strategy:string|null;
  measurement_path:string|null;
  output_semantics:string|null;
  limitation:string|null;
}

export interface QuantumVisualizationProvider {
  provider_id:string;
  display_name:string;
  provider_type:'LOCAL_SIMULATOR'|'REMOTE_SIMULATOR'|'HARDWARE'|'CUSTOM';
  availability:string;
  backend_id:string;
  backend_type:string;
  backend_availability:string;
  execution_mode:string;
  hardware_available:boolean;
}

export interface QuantumVisualizationState {
  status:QuantumVisualizationStatus;
  execution_source:string|null;
  simulator:string|null;
  backend_id:string|null;
  circuit_scope:string|null;
  input_sample_count:number|null;
  basis_states:string[]|null;
  amplitude_real:number[]|null;
  amplitude_imaginary:number[]|null;
  amplitude_magnitude:number[]|null;
  phase:(number|null)[]|null;
  probability:number[]|null;
  normalized_probability:number[]|null;
  measurement_counts:Record<string,number>|null;
  shots:number|null;
  limitations:string[];
}

export interface QuantumVisualizationBlochQubit {
  qubit_index:number;
  x:number;
  y:number;
  z:number;
  polar_angle:number|null;
  azimuth:number|null;
  purity:number;
  state_representation_status:string;
}

export interface QuantumVisualizationBloch {
  status:'AVAILABLE'|'NOT_AVAILABLE'|'NOT_APPLICABLE';
  representation:string|null;
  qubits:QuantumVisualizationBlochQubit[]|null;
  limitation:string|null;
}

export interface QuantumVisualizationEntanglement {
  status:'AVAILABLE'|'STRUCTURE_ONLY'|'NOT_AVAILABLE'|'NOT_APPLICABLE';
  indicator:boolean|null;
  participating_qubits:number[]|null;
  method:string|null;
  reduced_state_measures:Array<{qubit_index:number;purity:number;linear_entropy:number}>|null;
  limitations:string[];
}

export interface QuantumVisualizationMeasurement {
  status:'AVAILABLE'|'STRUCTURE_ONLY'|'NOT_AVAILABLE'|'NOT_APPLICABLE';
  method:string|null;
  output_semantics:string|null;
  counts:Record<string,number>|null;
  shots:number|null;
  limitations:string[];
}

export interface QuantumVisualizationResources {
  status:'AVAILABLE'|'NOT_AVAILABLE';
  logical_qubits:number|null;
  circuit_depth:number|null;
  total_gates:number|null;
  parameterized_gates:number|null;
  entangling_gates:number|null;
  shots:number|null;
  sample_count:number|null;
  feature_dimension:number|null;
  optimizer_iterations:number|null;
  resource_category:string|null;
  bounded_policy_status:string;
  backend_availability:string;
  simulator_type:string;
  policy_version:string;
  limitations:string[];
}

export interface QuantumVisualizationHybridArchitecture {
  input_path:string[];
  quantum_operations:string[];
  output_path:string[];
  classical_hidden_dimensions:number[]|null;
  classical_activation:string|null;
  provider_id:string;
  backend_id:string;
  limitation:string;
}

export interface QuantumVisualizationContract {
  schema_version:string;
  request_fingerprint:string;
  status:'AVAILABLE'|'STRUCTURE_ONLY'|'SIMULATION_AVAILABLE'|'NOT_AVAILABLE';
  model_type:QuantumVisualizationModelType;
  dataset_context:QuantumVisualizationDatasetContext;
  encoding:QuantumVisualizationEncoding;
  circuit:QuantumVisualizationCircuit;
  provider:QuantumVisualizationProvider;
  state:QuantumVisualizationState;
  bloch:QuantumVisualizationBloch;
  entanglement:QuantumVisualizationEntanglement;
  measurement:QuantumVisualizationMeasurement;
  resources:QuantumVisualizationResources;
  hybrid_architecture:QuantumVisualizationHybridArchitecture|null;
  limitations:string[];
}