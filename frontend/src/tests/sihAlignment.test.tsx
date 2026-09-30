import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {defaultDraft,DraftProvider} from '../hooks/useDraft';
import {Training} from '../pages/ResearchPagesModels';
import {qh} from '../lib/api';

let executable=true;
vi.mock('../lib/api',()=>({qh:{
  alignment:vi.fn(()=>Promise.resolve({models:[{model_id:'hybrid_pennylane_torch',display_name:'PennyLane + PyTorch Hybrid',category:'hybrid quantum-classical',implementation_status:executable?'AVAILABLE':'UNAVAILABLE',executable}],showcase:{},flagship_architecture:{stages:[]}})),
  jobs:vi.fn(()=>Promise.resolve([])),datasetLibrary:vi.fn(()=>Promise.resolve([])),dataset:vi.fn(()=>Promise.resolve({provenance:{}})),
  createJob:vi.fn((config)=>Promise.resolve({job:{},experiment:{dataset_id:config.dataset_id}})),
}}));

function view(){return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><DraftProvider><Training/></DraftProvider></MemoryRouter></QueryClientProvider>)}

describe('SIH executable hybrid model presentation',()=>{
 beforeEach(()=>{localStorage.clear();executable=true;vi.clearAllMocks()});
 it('shows available hybrid controls without exposing Qiskit settings for hybrid-only selection',async()=>{
  localStorage.setItem('qhealth-tictac-draft',JSON.stringify({...defaultDraft,models:[]}));view();
  expect(await screen.findByText(/PENNYLANE HYBRID.*HYBRID QUANTUM-CLASSICAL/)).toBeInTheDocument();
  const option=await screen.findByRole('button',{name:/PennyLane \+ PyTorch Hybrid/i});
  await waitFor(()=>expect(option).toBeEnabled());fireEvent.click(option);
  expect(await screen.findByText('Hybrid qubits')).toBeInTheDocument();
  expect(screen.getByText('Quantum layers')).toBeInTheDocument();
  expect(screen.getByText('Hidden dimensions')).toBeInTheDocument();
  expect(screen.queryByText('Qiskit quantum configuration')).not.toBeInTheDocument();
  expect(screen.getByText(/Shared comparison representation: 4 dimensions/i)).toBeInTheDocument();
 });
 it('disables hybrid selection when backend dependencies are unavailable',async()=>{
  executable=false;view();
  const option=await screen.findByRole('button',{name:/PennyLane \+ PyTorch Hybrid/i});
  await waitFor(()=>expect(option).toBeDisabled());
  expect(screen.getByText('Dependencies unavailable — execution disabled')).toBeInTheDocument();
 });
 it('persists and sends the bounded hybrid configuration',async()=>{
  localStorage.setItem('qhealth-tictac-draft',JSON.stringify({...defaultDraft,dataset_id:'dataset-1',models:[]}));view();
  const option=await screen.findByRole('button',{name:/PennyLane \+ PyTorch Hybrid/i});
  await waitFor(()=>expect(option).toBeEnabled());fireEvent.click(option);
  fireEvent.change(await screen.findByLabelText('Epochs'),{target:{value:'7'}});
  fireEvent.click(screen.getByRole('button',{name:/Create training experiment/i}));
  await waitFor(()=>expect(qh.createJob).toHaveBeenCalled());
  const sent=vi.mocked(qh.createJob).mock.calls[0][0];
  expect(sent.models).toContain('hybrid_pennylane_torch');
  expect(sent.hybrid.epochs).toBe(7);
  expect(sent.pipeline.pca_components).toBe(sent.hybrid.qubits);
 });
});
