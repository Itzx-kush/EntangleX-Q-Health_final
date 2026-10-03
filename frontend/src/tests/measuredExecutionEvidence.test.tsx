import {render,screen,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {DraftProvider} from '../hooks/useDraft';
import {Training} from '../pages/ResearchPagesModels';

const metric=(sample_count:number)=>({accuracy:.8,precision:.8,recall:.8,sensitivity:.8,specificity:.8,f1:.8,roc_auc:.8,true_positive:1,true_negative:1,false_positive:0,false_negative:0,confusion_matrix:[[1,0],[0,1]],sample_count,roc_curve:null,undefined_metrics:[]});
const timing={final_training_seconds:1.25,cv_total_seconds:2.5,cv_fold_seconds:[1.2,1.3],test_inference_seconds:0,test_inference_seconds_per_sample:0};
const operating_point={cv_fold_count:2};
const baseModel={experiment_id:'experiment-1',dataset_id:'dataset-1',status:'ready',progress:100,created_at:'2026-10-03T20:00:00Z'};
const classical={...baseModel,id:'classical-1',model_type:'logistic_regression',details:{common_representation:{selected_feature_count:12,final_representation_dimension:4}},metrics:{training:metric(128),test:metric(32),timing,operating_point}};
const quantum={...baseModel,id:'quantum-1',model_type:'qnn',details:{common_representation:{selected_feature_count:12,final_representation_dimension:4},quantum:{execution_kind:'finite-shot local quantum simulation',backend:'aer',qubits:4,objective_evaluations:7,shots:1024,noise_probability:0,real_hardware:false,configuration:{shots:1024}}},metrics:{training:metric(128),test:metric(32),timing,operating_point}};
const hybrid={...baseModel,id:'hybrid-1',model_type:'hybrid_pennylane_torch',details:{common_representation:{selected_feature_count:12,final_representation_dimension:4},quantum:{execution_kind:'local PennyLane quantum simulation',backend:'default.qubit',qubits:4,quantum_layers:2,epochs:8,real_hardware:false}},metrics:{training:metric(128),test:metric(32),timing,operating_point}};
const historical={...baseModel,id:'historical-1',model_type:'svm',status:'failed',details:{},metrics:{}};
const job={id:'job-1',experiment_id:'experiment-1',status:'succeeded',progress:100,state:'Finished',errors:[],created_at:'2026-10-03T20:00:00Z',updated_at:'2026-10-03T20:00:15Z',requested_at:'2026-10-03T20:00:00Z',started_at:'2026-10-03T20:00:02Z',completed_at:'2026-10-03T20:00:12Z',cancelled_at:null,experiment_name:'Measured run',models:[classical,quantum,hybrid,historical]};

vi.mock('../lib/api',()=>({qh:{
 jobs:vi.fn(()=>Promise.resolve([job])),dataset:vi.fn(()=>Promise.resolve({provenance:{}})),datasetLibrary:vi.fn(()=>Promise.resolve([])),alignment:vi.fn(()=>Promise.resolve({models:[]})),createJob:vi.fn(),
 pauseJob:vi.fn(),resumeJob:vi.fn(),retryJob:vi.fn(),cancelJob:vi.fn(),
}}));

function view(){
 return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><DraftProvider><Training/></DraftProvider></MemoryRouter></QueryClientProvider>);
}

describe('measured execution evidence',()=>{
 beforeEach(()=>{localStorage.clear();vi.clearAllMocks()});
 it('renders persisted runtime, workload and quantum metadata without inventing missing values',async()=>{
  view();
  const panel=(await screen.findByText('Measured execution evidence')).closest('details') as HTMLElement;
  expect(within(panel).getByText('2.000 s')).toBeInTheDocument();
  expect(within(panel).getByText('10.000 s')).toBeInTheDocument();
  expect(within(panel).getByText('12.000 s')).toBeInTheDocument();
  expect(within(panel).getAllByText('1.250 s').length).toBe(3);
  expect(within(panel).getAllByText('2.500 s').length).toBe(3);
  expect(within(panel).getAllByText('0.000 s').length).toBe(3);
  expect(within(panel).getAllByText('128 / 32').length).toBe(3);
  expect(within(panel).getAllByText('12 / 4').length).toBe(3);
  expect(within(panel).getByText('finite-shot local quantum simulation')).toBeInTheDocument();
  expect(within(panel).getByText('local PennyLane quantum simulation')).toBeInTheDocument();
  expect(within(panel).getByText('1024')).toBeInTheDocument();
  expect(within(panel).getAllByText('No — local simulation').length).toBe(2);
  expect(within(panel).getAllByText('Not measured').length).toBeGreaterThan(0);
  expect(within(panel).getAllByText('Not recorded').length).toBeGreaterThan(0);
  expect(within(panel).queryByText(/cost savings|faster|cheaper|ROI/i)).not.toBeInTheDocument();
 });
 it('keeps cancelled and historical timestamps safe when fields are absent',async()=>{
  const cancelled={...job,id:'job-2',status:'cancelled',started_at:null,completed_at:null,cancelled_at:'2026-10-03T20:00:05Z',models:[historical]};
  const api=await import('../lib/api');
  vi.mocked(api.qh.jobs).mockResolvedValueOnce([cancelled] as never);
  view();
  const panel=(await screen.findByText('Measured execution evidence')).closest('details') as HTMLElement;
  expect(within(panel).getByText('5.000 s')).toBeInTheDocument();
  expect(within(panel).getAllByText('Not measured').length).toBeGreaterThan(0);
  expect(within(panel).queryByText('QUANTUM EXECUTION')).not.toBeInTheDocument();
 });
});
