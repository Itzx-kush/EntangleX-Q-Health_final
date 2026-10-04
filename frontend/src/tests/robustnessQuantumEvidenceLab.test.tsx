import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {RobustnessEvidenceLab} from '../components/RobustnessEvidenceLab';
import {QuantumEvidenceLab} from '../components/QuantumEvidenceLab';
import type {Circuit,Dataset,Experiment,ModelRecord,QuantumDiagnosticReport,VerifiedRobustnessResult} from '../types/qhealth';

const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'succeeded',config:{models:['random_forest','vqc'],seed:42,test_size:.2,cv_folds:5,max_samples:40,duplicate_policy:'reject',probability_threshold:.5,threshold_strategy:'fixed',target_sensitivity:.8,calibration:'none',calibration_folds:3,features:null,dataset_id:'dataset-1',pipeline:{imputer:'median',scaler:'standard',outlier_strategy:'none',lower_quantile:.01,upper_quantile:.99,log_features:[],ratios:[],selection:'none',k_features:8,variance_threshold:0,pca_components:2,pca_whiten:false,angle_scaling:true},quantum:{backend:'aer',qubits:2,feature_map_reps:1,ansatz_reps:2,entanglement:'linear',optimizer:'COBYLA',maxiter:30,shots:1024,noise_probability:0,provider_id:'qiskit_local',execution_mode:'local_simulator'},hybrid:{model_type:'hybrid_pennylane_torch',qubits:2,feature_map:'angle',quantum_layers:2,classical_hidden_dimensions:[8],classical_activation:'relu',optimizer:'adam',learning_rate:.01,epochs:10,batch_size:8,deterministic_seed:42,sample_cap:40,backend:'default.qubit'},parameters:{logistic_c:1,svm_c:1,svm_kernel:'rbf',forest_trees:50,forest_max_depth:null,class_weight:null}},summary:{},created_at:'2026-10-04T00:00:00Z'} as Experiment;
const dataset={id:'dataset-1',name:'Research dataset',sha256:'hash-1',provenance:{row_count:40,feature_count:2},quality:{},created_at:'2026-10-04T00:00:00Z'} as Dataset;
const classical={id:'classical-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'random_forest',status:'ready',details:{},metrics:{test:{roc_auc:.9},validation:{summary:{roc_auc:{mean:.88,std:.02,valid_folds:5}}},timing:{final_training_seconds:1.2}},created_at:'2026-10-04T00:00:00Z'} as ModelRecord;
const quantum={id:'quantum-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'vqc',status:'ready',details:{quantum:{framework:'Qiskit',provider_id:'qiskit_local',backend:'aer',execution_kind:'local simulation',real_hardware:false,qubits:2,quantum_parameter_count:6}},metrics:{test:{roc_auc:.84},validation:{summary:{roc_auc:{mean:.82,std:.03,valid_folds:5}}},timing:{final_training_seconds:4.2,cv_total_seconds:12,cv_fold_seconds:[2,2.5],test_inference_seconds:.2,test_inference_seconds_per_sample:.01}},created_at:'2026-10-04T00:00:00Z'} as unknown as ModelRecord;
const verified={model_id:quantum.id,model_type:'vqc',condition:'gaussian_noise',configuration:{level:.1},perturbation:{changed_cells:8},baseline:{accuracy:.8,roc_auc:.84,sample_count:20},degraded:{accuracy:.7,roc_auc:.74,sample_count:20},delta:{accuracy:-.1,roc_auc:-.1},relative_delta:{accuracy:-.125,roc_auc:-.119},evaluation_indices:[1,2]} as unknown as VerifiedRobustnessResult;
const circuit={model_type:'vqc',execution_kind:'local simulation',backend:'aer',qubits:2,logical_depth:5,parameter_count:6,gate_counts:{RY:4,CX:2},text:'q0',gates:[{name:'RY',qubits:[0],parameters:['theta0']},{name:'CX',qubits:[0,1],parameters:[]}],limitation:'Logical simulator circuit.'} as Circuit;
const diagnostic={id:'diag-1',experiment_id:'experiment-1',model_record_id:quantum.id,model_type:'vqc',status:'completed',created_at:'2026-10-04T00:00:00Z',model_configuration:{},feature_encoding:{encoded_features:2},circuit_structure:{parameterized_gates:6},resource_profile:{qubits_observed:2,shots_configured:1024,parameter_count:6,circuit_depth:5},optimizer_profile:{optimizer:'COBYLA',iterations:30},training_profile:{},execution_profile:{backend:'aer',execution_mode:'local_simulator',real_hardware:false},stability_profile:{},noise_profile:{noise_model:'NO_NOISE_MODEL',noise_enabled:false},warnings:[],limitations:['Local simulation evidence does not represent real quantum hardware timing.','This diagnostic report does not establish quantum advantage.'],configuration_fingerprint:'fingerprint-1',provenance:{}} as QuantumDiagnosticReport;
const wrap=(node:React.ReactNode)=>render(<MemoryRouter>{node}</MemoryRouter>);

describe('Robustness and Quantum Evidence Labs',()=>{
 it('presents packaged degradation and bounded conclusions',()=>{
  wrap(<RobustnessEvidenceLab mode="verified" experiment={experiment} dataset={dataset} models={[classical,quantum]} verifiedRecords={[verified]} method="controlled-perturbation-v1"/>);
  expect(screen.getByText('Robustness overview')).toBeInTheDocument();
  expect(screen.getByText('gaussian noise · 0.1')).toBeInTheDocument();
  expect(screen.getAllByText('-10.00 pp').length).toBeGreaterThan(0);
  expect(screen.getByText(/does not establish generalization/i)).toBeInTheDocument();
  expect(screen.getByText(/Subgroup evidence is not available/i)).toBeInTheDocument();
 });
 it('distinguishes simulator execution from hardware and exposes diagnostics',()=>{
  wrap(<QuantumEvidenceLab mode="live" models={[classical,quantum]} experiment={experiment} dataset={dataset} selectedModelId={quantum.id} diagnostic={diagnostic} circuit={circuit}/>);
  expect(screen.getByText('Quantum execution summary')).toBeInTheDocument();
  expect(screen.getByText('NOT USED')).toBeInTheDocument();
  expect(screen.getByText(/Local simulation boundary/i)).toBeInTheDocument();
  expect(screen.getByText('Persisted quantum diagnostics')).toBeInTheDocument();
  expect(screen.getAllByText('COMPLETED').length).toBeGreaterThan(0);
  expect(screen.getAllByText(/does not establish quantum advantage/i).length).toBeGreaterThan(0);
  expect(screen.getByText('Quantum circuit evidence')).toBeInTheDocument();
  expect(screen.getAllByText('1024').length).toBeGreaterThan(0);
 });
});
