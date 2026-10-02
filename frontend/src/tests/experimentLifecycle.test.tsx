import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach,describe,expect,it,vi} from 'vitest';

import {Experiments} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';
import type {Experiment} from '../types/qhealth';


vi.mock('../lib/api',()=>({
  qh:{
    experiments:vi.fn(),
    deleteExperiment:vi.fn(),
    rerun:vi.fn(),
  },
}));
vi.mock('../hooks/useDraft',()=>({useDraft:()=>({update:vi.fn()})}));
vi.mock('../research/useResearchHistory',()=>({
  useResearchRecorder:()=>({record:vi.fn(),warning:null,clearWarning:vi.fn()}),
}));

const completed={
  id:'00000000-0000-0000-0000-000000000101',
  name:'Registry Dataset · Training 01',
  dataset_id:'00000000-0000-0000-0000-000000000201',
  parent_id:null,
  status:'succeeded',
  config:{models:['logistic_regression'],seed:42},
  summary:{},
  created_at:'2026-10-03T00:00:00Z',
} as Experiment;

const running={
  ...completed,
  id:'00000000-0000-0000-0000-000000000102',
  name:'Registry Dataset · Training 02',
  status:'running',
} as Experiment;

function renderRegistry(){
  const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/experiments']}><Experiments/></MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(()=>vi.clearAllMocks());

describe('experiment registry lifecycle',()=>{
  it('confirms deletion, protects running work, refreshes immediately, and reaches empty state',async()=>{
    vi.mocked(qh.experiments).mockResolvedValueOnce([completed,running]).mockResolvedValue([running]);
    vi.mocked(qh.deleteExperiment).mockResolvedValue({
      id:completed.id,status:'archived',deleted_at:'2026-10-03T00:01:00Z',
      already_deleted:false,preserved_records:{jobs:1,models:1,runs:1,artifacts:2},
    });
    renderRegistry();

    await screen.findByText(completed.name!);
    expect(screen.getAllByRole('link',{name:'Open'})[0]).toHaveAttribute('href',`/experiments/${completed.id}`);
    const deleteButtons=screen.getAllByRole('button',{name:'Delete'});
    expect(deleteButtons[0]).toBeEnabled();
    expect(deleteButtons[1]).toBeDisabled();
    expect(screen.getByText('Cancel and wait for completion before deleting.')).toBeInTheDocument();

    fireEvent.click(deleteButtons[0]);
    expect(screen.getByText('Delete experiment?')).toBeInTheDocument();
    expect(qh.deleteExperiment).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Cancel'}));
    expect(screen.queryByText('Delete experiment?')).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button',{name:'Delete'})[0]);
    fireEvent.click(screen.getByRole('button',{name:'Delete experiment'}));
    await waitFor(()=>expect(qh.deleteExperiment).toHaveBeenCalledWith(completed.id));
    await waitFor(()=>expect(screen.queryByText(completed.name!)).not.toBeInTheDocument());
    expect(screen.getByText(/was removed from the active registry/)).toBeInTheDocument();

    expect(screen.getByText(running.name!)).toBeInTheDocument();
  });

  it('shows delete errors and restores the confirmation controls',async()=>{
    vi.mocked(qh.experiments).mockResolvedValue([completed]);
    vi.mocked(qh.deleteExperiment).mockRejectedValue(new Error('Experiment is still active.'));
    renderRegistry();

    await screen.findByText(completed.name!);
    fireEvent.click(screen.getByRole('button',{name:'Delete'}));
    fireEvent.click(screen.getByRole('button',{name:'Delete experiment'}));
    await screen.findByText('Experiment is still active.');
    expect(screen.getByRole('button',{name:'Delete experiment'})).toBeEnabled();
    expect(screen.getAllByText(completed.name!).length).toBeGreaterThan(0);
  });

  it('renders the existing empty state when no experiments remain',async()=>{
    vi.mocked(qh.experiments).mockResolvedValue([]);
    renderRegistry();
    expect(await screen.findByText('No matching experiments')).toBeInTheDocument();
  });
});