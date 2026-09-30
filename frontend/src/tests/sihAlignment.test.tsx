import {render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {describe,expect,it,vi} from 'vitest';
import {DraftProvider} from '../hooks/useDraft';
import {Training} from '../pages/ResearchPagesModels';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  alignment:vi.fn(()=>Promise.resolve({models:[{model_id:'hybrid_pennylane_torch',display_name:'PennyLane + PyTorch Hybrid',category:'hybrid quantum-classical',implementation_status:'NOT_YET_IMPLEMENTED',executable:false}],showcase:{},flagship_architecture:{stages:[]}})),
  jobs:vi.fn(()=>Promise.resolve([])),datasetLibrary:vi.fn(()=>Promise.resolve([])),dataset:vi.fn(()=>Promise.resolve({})),createJob:vi.fn(),
}}));

describe('SIH hybrid model presentation',()=>{
 it('places the hybrid model in its own category and disables execution',async()=>{
  render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><DraftProvider><Training/></DraftProvider></MemoryRouter></QueryClientProvider>);
  expect(await screen.findByText('HYBRID QUANTUM-CLASSICAL')).toBeInTheDocument();
  const option=screen.getByRole('button',{name:/PennyLane \+ PyTorch Hybrid/i});
  await waitFor(()=>expect(option).toBeDisabled());
  expect(screen.getByText('Architecture prepared — implementation pending')).toBeInTheDocument();
 });
});
