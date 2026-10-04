import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {DraftProvider} from '../hooks/useDraft';
import {Quantum} from '../pages/ResearchPagesModels';
import {qh} from '../lib/api';
import {QuantumCircuitExplorer} from '../components/quantum/QuantumCircuitExplorer';
import {QuantumContextPanel} from '../components/quantum/QuantumContextPanel';
import {QuantumStatePanel} from '../components/quantum/QuantumStatePanel';
import {QuantumEvidenceLab} from '../components/QuantumEvidenceLab';
import type {Circuit} from '../types/qhealth';
import type {QuantumVisualizationContract,QuantumVisualizationGate} from '../types/quantumVisualization';

type ContractOverrides=Omit<Partial<QuantumVisualizationContract>,'dataset_context'|'encoding'|'circuit'|'provider'|'state'|'bloch'|'entanglement'|'measurement'|'resources'>&{dataset_context?:Partial<QuantumVisualizationContract['dataset_context']>;encoding?:Partial<QuantumVisualizationContract['encoding']>;circuit?:Partial<QuantumVisualizationContract['circuit']>;provider?:Partial<QuantumVisualizationContract['provider']>;state?:Partial<QuantumVisualizationContract['state']>;bloch?:Partial<QuantumVisualizationContract['bloch']>;entanglement?:Partial<QuantumVisualizationContract['entanglement']>;measurement?:Partial<QuantumVisualizationContract['measurement']>;resources?:Partial<QuantumVisualizationContract['resources']>};

vi.mock('../lib/api',()=>({qh:{
 capabilities:vi.fn(),models:vi.fn(),experiments:vi.fn(),datasets:vi.fn(),dataset:vi.fn(),quantum_diagnostics_by_run:vi.fn(),
 quantumVisualizationPreview:vi.fn(),quantumVisualizationSimulate:vi.fn(),saveQuantumVisualizationEvidence:vi.fn(),fittedCircuit:vi.fn(),resourceAdvisor:vi.fn(),
 experimentArtifacts:vi.fn().mockResolvedValue([]),
}}));

const gate=(gate_index:number,name:string,qubits:number[],parameters:string[]=[]):QuantumVisualizationGate=>({gate_index,name,gate_type:name==='CX'?'controlled':'rotation',qubits,parameters,control_qubits:name==='CX'?[0]:[],target_qubits:name==='CX'?[1]:[]});
function makeContract(overrides:ContractOverrides={}):QuantumVisualizationContract{
 const base:QuantumVisualizationContract={
  schema_version:'quantum-visualization-v1',request_fingerprint:'test-fingerprint',status:'STRUCTURE_ONLY',model_type:'vqc',
  dataset_context:{status:'NOT_AVAILABLE',dataset_id:null,dataset_version_id:null,dataset_name:null,dataset_hash:null,raw_feature_count:null,raw_feature_names:null,represented_feature_count:null,selected_feature_names:null,configured_input_features:null,representation_configuration:{},representation_status:'NOT_AVAILABLE',representation_source:null,row_count:null,experiment_id:null,limitations:['No dataset context supplied.']},
  encoding:{status:'STRUCTURE_ONLY',method:'angle',description:'Backend structural encoding description.',feature_to_qubit_mapping:[],encoding_parameters:{},encoded_dimension:2,angle_scaling:null,limitations:[]},
  circuit:{model_type:'vqc',provider_id:'qiskit_local',backend_id:'statevector',execution_mode:'local_simulator',execution_kind:'local_simulator',hardware_available:false,qubits:2,logical_depth:2,parameter_count:1,gate_counts:{H:1,RY:1},total_gates:2,gate_sequence:[gate(1,'RY',[0],['theta_0']),gate(0,'H',[0])],circuit_text:'H q[0]\\nRY(theta_0) q[0]',feature_map:'ZZFeatureMap',ansatz:'RealAmplitudes',entanglement_strategy:'linear',measurement_path:'Z expectation',output_semantics:'Backend-reported expectation output',limitation:'Structural preview only.'},
  provider:{provider_id:'qiskit_local',display_name:'Qiskit local',provider_type:'LOCAL_SIMULATOR',availability:'AVAILABLE',backend_id:'statevector',backend_type:'statevector',backend_availability:'AVAILABLE',execution_mode:'local_simulator',hardware_available:false},
  state:{status:'STRUCTURE_ONLY',execution_source:null,simulator:null,backend_id:null,circuit_scope:null,input_sample_count:null,basis_states:null,amplitude_real:null,amplitude_imaginary:null,amplitude_magnitude:null,phase:null,probability:null,normalized_probability:null,measurement_counts:null,shots:null,limitations:['No simulation was run.']},
  bloch:{status:'NOT_AVAILABLE',representation:null,qubits:null,limitation:'No reduced-state computation was performed.'},
  entanglement:{status:'STRUCTURE_ONLY',indicator:null,participating_qubits:null,method:null,reduced_state_measures:null,limitations:['Gate connectivity alone does not establish state entanglement.']},
  measurement:{status:'STRUCTURE_ONLY',method:'Z measurement path',output_semantics:null,counts:null,shots:null,limitations:['No measurement executed.']},
  resources:{status:'AVAILABLE',logical_qubits:2,circuit_depth:2,total_gates:2,parameterized_gates:1,entangling_gates:0,shots:null,sample_count:null,feature_dimension:2,optimizer_iterations:100,resource_category:'small',bounded_policy_status:'within_budget',backend_availability:'AVAILABLE',simulator_type:'statevector',policy_version:'quantum-resource-policy-v1',limitations:[]},
  hybrid_architecture:null,limitations:['Preview does not simulate a state.'],
 };
 return {...base,...overrides,dataset_context:{...base.dataset_context,...overrides.dataset_context},encoding:{...base.encoding,...overrides.encoding},circuit:{...base.circuit,...overrides.circuit},provider:{...base.provider,...overrides.provider},state:{...base.state,...overrides.state},bloch:{...base.bloch,...overrides.bloch},entanglement:{...base.entanglement,...overrides.entanglement},measurement:{...base.measurement,...overrides.measurement},resources:{...base.resources,...overrides.resources}};
}

describe('Quantum Lab visualization contract components',()=>{
 it('shows saved backend visualization artifacts in the existing Quantum Evidence Lab',()=>{
  render(<MemoryRouter><QuantumEvidenceLab mode="live" models={[{id:'model-qsvc',experiment_id:'experiment-qsvc',dataset_id:'dataset-qsvc',model_type:'qsvc',status:'ready',details:{quantum:{}},metrics:{}} as never]} visualizationArtifacts={[{id:'artifact-1',experiment_id:'experiment-qsvc',model_id:'model-qsvc',run_id:'run-1',artifact_type:'quantum_visualization_evidence',name:'Quantum Lab simulation',description:'Backend-generated simulation evidence',details:{request_fingerprint:'fingerprint-1',contract:{status:'SIMULATION_AVAILABLE',state:{status:'AVAILABLE',execution_source:'local_simulator',simulator:'qiskit_local'},provider:{backend_id:'statevector'}}},created_at:'2026-10-04T12:00:00Z'} as never]}/></MemoryRouter>);
  expect(screen.getByText('Saved Quantum Lab simulation evidence')).toBeInTheDocument();
  expect(screen.getByText('artifact-1')).toBeInTheDocument();
  expect(screen.getByText('fingerprint-1')).toBeInTheDocument();
  expect(screen.getByRole('link',{name:/Open linked experiment report/})).toHaveAttribute('href','/experiments/experiment-qsvc');
 });
 it('renders backend gate order and keyboard-driven structural playback',()=>{
  const contract=makeContract();
  render(<QuantumCircuitExplorer circuit={contract.circuit} sourceLabel="Preview"/>);
  const explorer=screen.getByRole('region',{name:'Interactive backend circuit explorer'});
  const first=within(explorer).getByRole('button',{name:/Operation 1: H/});
  const second=within(explorer).getByRole('button',{name:/Operation 2: RY/});
  expect(first).toBeInTheDocument();expect(second).toBeInTheDocument();
  expect(screen.getByText('No state evolution')).toBeInTheDocument();
  fireEvent.keyDown(second,{key:'Enter'});
  expect(screen.getByText(/structural playback/i)).toBeInTheDocument();
  expect(within(explorer).getAllByText('RY').length).toBeGreaterThan(0);
 });
 it('labels a structural-only state and hides unsupported views',()=>{
  render(<QuantumStatePanel contract={makeContract()}/>);
  expect(screen.getAllByText('STRUCTURE ONLY').length).toBeGreaterThan(0);
  expect(screen.getByText(/Structural preview only/)).toBeInTheDocument();
  expect(screen.queryByRole('tab',{name:'Probability'})).not.toBeInTheDocument();
  expect(screen.queryByRole('tab',{name:'Bloch'})).not.toBeInTheDocument();
 });
 it('renders actual backend probability values and only the supported view',()=>{
  const contract=makeContract({status:'SIMULATION_AVAILABLE',state:{status:'AVAILABLE',execution_source:'local_simulator',simulator:'qiskit_aer',backend_id:'statevector',circuit_scope:'feature_map',input_sample_count:1,basis_states:['00','01'],amplitude_real:null,amplitude_imaginary:null,amplitude_magnitude:null,phase:null,probability:[.75,.25],normalized_probability:[.75,.25],measurement_counts:null,shots:null,limitations:[]}});
  render(<QuantumStatePanel contract={contract}/>);
  expect(screen.getByRole('tab',{name:'Probability'})).toHaveAttribute('aria-selected','true');
  expect(screen.queryByRole('tab',{name:'Amplitude'})).not.toBeInTheDocument();
  expect(screen.queryByRole('tab',{name:'Phase'})).not.toBeInTheDocument();
  expect(screen.queryByRole('tab',{name:'Bloch'})).not.toBeInTheDocument();
  expect(screen.getByText('75.00%')).toBeInTheDocument();expect(screen.getByText('|00⟩')).toBeInTheDocument();
 });
 it('exposes phase, reduced Bloch, and measurement views only from returned simulator values',()=>{
  const contract=makeContract({
   status:'SIMULATION_AVAILABLE',
   state:{status:'AVAILABLE',execution_source:'local_simulator',simulator:'qiskit_aer',backend_id:'statevector',circuit_scope:'full_model',input_sample_count:1,basis_states:['0','1'],amplitude_real:[Math.sqrt(.6),0],amplitude_imaginary:[0,Math.sqrt(.4)],amplitude_magnitude:[Math.sqrt(.6),Math.sqrt(.4)],phase:[0,Math.PI/2],probability:[.6,.4],normalized_probability:[.6,.4],measurement_counts:{'0':6,'1':4},shots:10,limitations:[]},
   bloch:{status:'AVAILABLE',representation:'reduced_density_matrix',limitation:null,qubits:[{qubit_index:0,x:.1,y:.2,z:.3,polar_angle:1.2,azimuth:.4,purity:.8,state_representation_status:'AVAILABLE'}]},
   measurement:{status:'AVAILABLE',method:'simulator shots',output_semantics:'backend counts',counts:{'0':6,'1':4},shots:10,limitations:[]},
  });
  render(<QuantumStatePanel contract={contract}/>);
  expect(screen.getByRole('tab',{name:'Phase'})).toBeInTheDocument();
  expect(screen.getByRole('tab',{name:'Bloch'})).toBeInTheDocument();
  expect(screen.getByRole('tab',{name:'Measurements'})).toBeInTheDocument();
  fireEvent.keyDown(screen.getByRole('tab',{name:'Probability'}),{key:'ArrowRight'});
  expect(screen.getByRole('tab',{name:'Amplitude'})).toHaveAttribute('aria-selected','true');
  expect(document.activeElement).toBe(screen.getByRole('tab',{name:'Amplitude'}));
  fireEvent.click(screen.getByRole('tab',{name:'Phase'}));
  expect(screen.getByText('1.571 rad')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab',{name:'Bloch'}));
  expect(screen.getByRole('img',{name:/Bloch projection for qubit 0/})).toBeInTheDocument();
  expect(screen.getByText(/2D x\/z projection/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('tab',{name:'Measurements'}));
  expect(screen.getByText('6')).toBeInTheDocument();
  expect(screen.getByText(/simulator outputs, not hardware measurements/)).toBeInTheDocument();
 });
 it('keeps fitted legacy circuit structure readable without implying state evolution',()=>{
  const fitted:Circuit={model_type:'qsvc',execution_kind:'local_simulator',backend:'statevector',qubits:2,logical_depth:1,parameter_count:0,gate_counts:{H:1},text:'H q[0]',gates:[{name:'H',qubits:[0],parameters:[]}],limitation:'Persisted circuit structure only.'};
  render(<QuantumCircuitExplorer circuit={fitted} sourceLabel="Fitted model"/>);
  expect(screen.getByRole('button',{name:/Operation 1: H/})).toBeInTheDocument();
  expect(screen.getByText('No state evolution')).toBeInTheDocument();
  expect(screen.getByText('Fitted model · operation order from backend')).toBeInTheDocument();
 });
 it('renders backend feature mapping and QSVC pathway metadata',()=>{
  const contract=makeContract({model_type:'qsvc',circuit:{model_type:'qsvc',feature_map:'ZZFeatureMap',ansatz:null,measurement_path:'Kernel overlap',output_semantics:'Backend-reported quantum kernel evaluation',limitation:'Kernel evaluation only.'},dataset_context:{status:'AVAILABLE',dataset_name:'Registered cohort',raw_feature_count:2,represented_feature_count:2,representation_status:'STRUCTURE_ONLY',representation_source:'registered_dataset'},encoding:{feature_to_qubit_mapping:[{feature_index:0,feature_name:'feature_a',qubit_index:0,parameter_name:'x[0]'},{feature_index:1,feature_name:'feature_b',qubit_index:1,parameter_name:'x[1]'}]}});
  render(<QuantumContextPanel contract={contract} modelType="qsvc" circuitSource="preview"/>);
  expect(screen.getByText('Registered cohort')).toBeInTheDocument();expect(screen.getByText('feature_a')).toBeInTheDocument();expect(screen.getByText('q[1]')).toBeInTheDocument();
  expect(screen.getByText('Kernel overlap')).toBeInTheDocument();
  expect(screen.getByText('Backend-reported quantum kernel evaluation')).toBeInTheDocument();expect(screen.getByText('Kernel evaluation only.')).toBeInTheDocument();
 });
 it('sends selected VQC, QSVC, and QNN previews with the registered dataset context',async()=>{
  localStorage.clear();vi.clearAllMocks();
  vi.mocked(qh.capabilities).mockResolvedValue({available:true,runtime_verified:true,execution:'Local simulator'});
  vi.mocked(qh.models).mockResolvedValue([]);
  vi.mocked(qh.experiments).mockResolvedValue([]);
  vi.mocked(qh.datasets).mockResolvedValue([{id:'dataset-1',name:'Cohort A'},{id:'dataset-2',name:'Custom upload B'}] as never);
  vi.mocked(qh.dataset).mockImplementation(async id=>({id,name:id==='dataset-2'?'Custom upload B':'Cohort A',provenance:{name:id==='dataset-2'?'Custom upload B':'Cohort A'}} as never));
  vi.mocked(qh.quantumVisualizationPreview).mockImplementation(async request=>makeContract({model_type:request.model_type,circuit:{model_type:request.model_type},dataset_context:{dataset_id:request.dataset_id||null,dataset_name:request.dataset_id==='dataset-2'?'Custom upload B':'Cohort A'},hybrid_architecture:request.model_type==='hybrid_pennylane_torch'?{input_path:['Classical input'],quantum_operations:['PennyLane circuit'],output_path:['PyTorch output head','positive-class probability'],classical_hidden_dimensions:[16,8],classical_activation:'relu',provider_id:'pennylane_local',backend_id:'default.qubit',limitation:'No fitted model weights are loaded.'}:null}));
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/quantum']}><DraftProvider><Quantum/></DraftProvider></MemoryRouter></QueryClientProvider>);
  await screen.findByRole('option',{name:'Cohort A'});
  const datasetSelect=screen.getByRole('combobox',{name:'Quantum dataset context'});
  fireEvent.change(datasetSelect,{target:{value:'dataset-1'}});
  const modelSelect=screen.getByRole('combobox',{name:'Quantum advisor model'});
  for(const modelType of ['vqc','qsvc','qnn','hybrid_pennylane_torch'] as const){
   fireEvent.change(modelSelect,{target:{value:modelType}});
   fireEvent.click(screen.getByRole('button',{name:'Generate structural preview'}));
   await waitFor(()=>expect(qh.quantumVisualizationPreview).toHaveBeenLastCalledWith(expect.objectContaining({model_type:modelType,dataset_id:'dataset-1',experiment_id:null})));
   expect(await screen.findByText(/operation order from backend/)).toBeInTheDocument();
   const request=vi.mocked(qh.quantumVisualizationPreview).mock.calls.at(-1)?.[0];
   if(modelType==='hybrid_pennylane_torch'){expect(request).toHaveProperty('hybrid');expect(request).not.toHaveProperty('quantum');expect(screen.getByText('PennyLane circuit')).toBeInTheDocument();expect(screen.getByRole('button',{name:/Advisor supports VQC/})).toBeDisabled()}
   else expect(request).toHaveProperty('quantum');
  }
  fireEvent.change(datasetSelect,{target:{value:'dataset-2'}});
  fireEvent.change(modelSelect,{target:{value:'vqc'}});
  fireEvent.click(screen.getByRole('button',{name:'Generate structural preview'}));
  await waitFor(()=>expect(qh.quantumVisualizationPreview).toHaveBeenLastCalledWith(expect.objectContaining({model_type:'vqc',dataset_id:'dataset-2'})));
  expect((await screen.findAllByText('Custom upload B')).length).toBeGreaterThan(1);
  expect(qh.quantumVisualizationPreview).toHaveBeenCalledTimes(6); // one automatic entry preview plus five explicit previews
 });
 it('loads backend circuit visuals on entry and simulates only an explicitly entered vector',async()=>{
  localStorage.clear();vi.clearAllMocks();
  const previewContract=makeContract();
  const simulatedContract=makeContract({status:'SIMULATION_AVAILABLE',state:{status:'AVAILABLE',execution_source:'local_simulator',simulator:'qiskit_local',backend_id:'statevector',circuit_scope:'feature_map',input_sample_count:1,basis_states:['00','01'],amplitude_real:[1,0],amplitude_imaginary:[0,0],amplitude_magnitude:[1,0],phase:[0,null],probability:[1,0],normalized_probability:[1,0],measurement_counts:null,shots:null,limitations:['Actual simulator response.']}});
  vi.mocked(qh.capabilities).mockResolvedValue({available:true,runtime_verified:true,execution:'Local simulator'});
  vi.mocked(qh.models).mockResolvedValue([]);vi.mocked(qh.experiments).mockResolvedValue([]);vi.mocked(qh.datasets).mockResolvedValue([]);
  vi.mocked(qh.quantumVisualizationPreview).mockResolvedValue(previewContract);
  vi.mocked(qh.quantumVisualizationSimulate).mockResolvedValue(simulatedContract);
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/quantum']}><DraftProvider><Quantum/></DraftProvider></MemoryRouter></QueryClientProvider>);
  expect(await screen.findByRole('button',{name:/Operation 1: H/})).toBeInTheDocument();
  expect(qh.quantumVisualizationPreview).toHaveBeenCalledTimes(1);
  const fields=Array.from({length:4},(_,index)=>screen.getByRole('spinbutton',{name:`Encoded value for qubit ${index}`}));
  expect(screen.getByRole('button',{name:'Simulate entered vector'})).toBeDisabled();
  fields.forEach((field,index)=>fireEvent.change(field,{target:{value:String(index/10)}}));
  fireEvent.click(screen.getByRole('button',{name:'Simulate entered vector'}));
  await waitFor(()=>expect(qh.quantumVisualizationSimulate).toHaveBeenCalledWith(expect.objectContaining({model_type:'vqc',simulation_stage:'encoding',encoded_vector:[0,.1,.2,.3],dataset_id:null})));
  expect(await screen.findByText('100.00%')).toBeInTheDocument();
  expect(screen.getByRole('tab',{name:'Probability'})).toBeInTheDocument();
 });
 it('saves a simulator snapshot only to the matching persisted model report',async()=>{
  localStorage.clear();vi.clearAllMocks();
  const qsvcSimulation=makeContract({model_type:'qsvc',status:'SIMULATION_AVAILABLE',circuit:{model_type:'qsvc'},state:{status:'AVAILABLE',execution_source:'local_simulator',simulator:'qiskit_local',backend_id:'statevector',circuit_scope:'feature_map',input_sample_count:1,basis_states:['00','01'],amplitude_real:[1,0],amplitude_imaginary:[0,0],amplitude_magnitude:[1,0],phase:[0,null],probability:[1,0],normalized_probability:[1,0],measurement_counts:null,shots:null,limitations:[]}});
  vi.mocked(qh.capabilities).mockResolvedValue({available:true,runtime_verified:true,execution:'Local simulator'});
  vi.mocked(qh.models).mockResolvedValue([{id:'model-qsvc',experiment_id:'experiment-qsvc',dataset_id:'dataset-qsvc',model_type:'qsvc',status:'ready',details:{quantum:{}},metrics:{}}] as never);
  vi.mocked(qh.experiments).mockResolvedValue([{id:'experiment-qsvc',dataset_id:'dataset-qsvc',created_at:'2026-10-01T00:00:00Z',config:{quantum:{qubits:4},hybrid:{}}}] as never);
  vi.mocked(qh.datasets).mockResolvedValue([{id:'dataset-qsvc',name:'Registered cohort'}] as never);
  vi.mocked(qh.dataset).mockResolvedValue({id:'dataset-qsvc',name:'Registered cohort',provenance:{name:'Registered cohort'}} as never);
  vi.mocked(qh.quantum_diagnostics_by_run).mockResolvedValue(null as never);
  vi.mocked(qh.quantumVisualizationPreview).mockResolvedValue(makeContract());
  vi.mocked(qh.quantumVisualizationSimulate).mockResolvedValue(qsvcSimulation);
  vi.mocked(qh.saveQuantumVisualizationEvidence).mockResolvedValue({artifact_id:'artifact-1',experiment_id:'experiment-qsvc',model_record_id:'model-qsvc',run_id:null,request_fingerprint:'saved-fingerprint',contract:qsvcSimulation});
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/quantum']}><DraftProvider><Quantum/></DraftProvider></MemoryRouter></QueryClientProvider>);
  const modelSelect=await screen.findByRole('combobox',{name:'Quantum persisted model'});
  await screen.findByRole('option',{name:/qsvc/i});
  fireEvent.change(modelSelect,{target:{value:'model-qsvc'}});
  fireEvent.change(screen.getByRole('combobox',{name:'Quantum advisor model'}),{target:{value:'qsvc'}});
  for(let index=0;index<4;index++)fireEvent.change(screen.getByRole('spinbutton',{name:`Encoded value for qubit ${index}`}),{target:{value:String(index/10)}});
  fireEvent.click(screen.getByRole('button',{name:'Simulate entered vector'}));
  const saveButton=await screen.findByRole('button',{name:'Save simulator evidence to model report'});
  fireEvent.click(saveButton);
  await waitFor(()=>expect(qh.saveQuantumVisualizationEvidence).toHaveBeenCalledWith(expect.objectContaining({model_record_id:'model-qsvc',simulation:expect.objectContaining({model_type:'qsvc',experiment_id:'experiment-qsvc',dataset_id:'dataset-qsvc'})})));
  expect(await screen.findByText(/artifact artifact-1/)).toBeInTheDocument();
 });
 it('offers the existing experiment report for the selected persisted quantum model',async()=>{
  localStorage.clear();vi.clearAllMocks();
  vi.mocked(qh.capabilities).mockResolvedValue({available:false,runtime_verified:false,execution:'Unavailable'});
  vi.mocked(qh.models).mockResolvedValue([{id:'model-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'qsvc',status:'ready',details:{quantum:{}},metrics:{test:{},validation:{summary:{}},timing:{}}}] as never);
  vi.mocked(qh.experiments).mockResolvedValue([{id:'experiment-1',dataset_id:'dataset-1',created_at:'2026-10-01T00:00:00Z',config:{quantum:{qubits:4,shots:1024},hybrid:{}}}] as never);
  vi.mocked(qh.datasets).mockResolvedValue([{id:'dataset-1',name:'Cohort A'}] as never);
  vi.mocked(qh.dataset).mockResolvedValue({id:'dataset-1',name:'Cohort A',provenance:{name:'Cohort A'}} as never);
  vi.mocked(qh.quantum_diagnostics_by_run).mockResolvedValue(null as never);
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/quantum']}><DraftProvider><Quantum/></DraftProvider></MemoryRouter></QueryClientProvider>);
  const modelSelect=await screen.findByRole('combobox',{name:'Quantum persisted model'});
  await screen.findByRole('option',{name:/qsvc/i});
  fireEvent.change(modelSelect,{target:{value:'model-1'}});
  const reportLink=await screen.findByRole('link',{name:'Experiment report'});
  expect(reportLink).toHaveAttribute('href','/experiments/experiment-1');
 });
});
