import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ScientificAuditTimelinePanel} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';
import type {AuditTimeline,ScientificAuditEvent} from '../types/qhealth';

vi.mock('../lib/api',()=>({qh:{
  experimentAudit:vi.fn(),
  experimentAuditExport:vi.fn(),
}}));

const experimentId='11111111-1111-4111-8111-111111111111';

const sampleEvent1:ScientificAuditEvent={
  id:'evt-1',
  schema_version:'scientific_audit_event_v1',
  event_type:'EXPERIMENT_CREATED',
  event_category:'EXPERIMENT',
  occurred_at:'2026-10-03T10:00:00Z',
  recorded_at:'2026-10-03T10:00:00.100Z',
  actor_type:'user',
  actor_reference:'researcher_1',
  source_component:'backend.jobs.manager',
  operation_key:'create_exp_123',
  object_type:'experiment',
  object_id:experimentId,
  parent_object_type:null,
  parent_object_id:null,
  before_fingerprint:null,
  after_fingerprint:'after_hash_1',
  previous_event_fingerprint:null,
  event_fingerprint:'evt_hash_11111111111111111111111111111111',
  metadata:{experiment_name:'SIH Benchmark',seed:42},
};

const sampleEvent2:ScientificAuditEvent={
  id:'evt-2',
  schema_version:'scientific_audit_event_v1',
  event_type:'RUN_STARTED',
  event_category:'RUN',
  occurred_at:'2026-10-03T10:01:00Z',
  recorded_at:'2026-10-03T10:01:00.200Z',
  actor_type:'system',
  actor_reference:null,
  source_component:'backend.runs.service',
  operation_key:'run_op_456',
  object_type:'run',
  object_id:'run-99999999-9999-9999-9999-999999999999',
  parent_object_type:'experiment',
  parent_object_id:experimentId,
  before_fingerprint:null,
  after_fingerprint:'after_run_hash',
  previous_event_fingerprint:'evt_hash_11111111111111111111111111111111',
  event_fingerprint:'evt_hash_22222222222222222222222222222222',
  metadata:{run_index:0,hardware_target:'simulator'},
};

const sampleTimeline:AuditTimeline={
  object_type:'experiment',
  object_id:experimentId,
  events:[sampleEvent1,sampleEvent2],
  integrity:{
    verified:true,
    total_events:2,
    issues:[],
    checked_at:'2026-10-03T10:05:00Z',
  },
  disclaimer:'Audit history is recorded from platform upgrade (2026-10-03). Earlier platform activity was not captured.',
};

function renderPanel(){
  return render(
    <QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
      <ScientificAuditTimelinePanel experimentId={experimentId}/>
    </QueryClientProvider>
  );
}

describe('Scientific Audit Timeline panel',()=>{
  beforeEach(()=>vi.clearAllMocks());

  it('loads and renders timeline events, badges, and integrity status',async()=>{
    vi.mocked(qh.experimentAudit).mockResolvedValue(sampleTimeline);
    renderPanel();

    expect(await screen.findByText('INTEGRITY VERIFIED')).toBeInTheDocument();
    expect(screen.getByText('2 RECORDED EVENTS')).toBeInTheDocument();
    expect(screen.getByText('EXPERIMENT CREATED')).toBeInTheDocument();
    expect(screen.getByText('RUN STARTED')).toBeInTheDocument();
    expect(screen.getByText(/Audit history is recorded from platform upgrade/i)).toBeInTheDocument();
    expect(screen.getByText(/The Scientific Audit Timeline records platform events and persisted state transitions/i)).toBeInTheDocument();
    expect(qh.experimentAudit).toHaveBeenCalledWith(experimentId,'all');
  });

  it('supports interactive event detail expansion for fingerprints and metadata',async()=>{
    vi.mocked(qh.experimentAudit).mockResolvedValue(sampleTimeline);
    renderPanel();

    expect(await screen.findByText('EXPERIMENT CREATED')).toBeInTheDocument();
    const detailButtons=screen.getAllByRole('button',{name:'Details'});
    expect(detailButtons.length).toBe(2);

    // Click Details on first event
    fireEvent.click(detailButtons[0]);

    expect(screen.getByText('EVENT FINGERPRINT (SHA-256)')).toBeInTheDocument();
    expect(screen.getByText('evt_hash_11111111111111111111111111111111')).toBeInTheDocument();
    expect(screen.getByText('(chain root)')).toBeInTheDocument();

    // Toggle back to Hide
    const hideButton=screen.getByRole('button',{name:'Hide'});
    fireEvent.click(hideButton);
    expect(screen.queryByText('EVENT FINGERPRINT (SHA-256)')).not.toBeInTheDocument();
  });

  it('triggers category filter on select change',async()=>{
    vi.mocked(qh.experimentAudit).mockResolvedValue(sampleTimeline);
    renderPanel();

    expect(await screen.findByText('Filter Category')).toBeInTheDocument();
    const select=screen.getByRole('combobox');
    fireEvent.change(select,{target:{value:'RUN'}});

    await waitFor(()=>{
      expect(qh.experimentAudit).toHaveBeenCalledWith(experimentId,'RUN');
    });
  });

  it('displays integrity warnings when verification fails',async()=>{
    const warningTimeline:AuditTimeline={
      ...sampleTimeline,
      integrity:{
        verified:false,
        total_events:2,
        issues:[{event_id:'evt-2',issue_type:'fingerprint_mismatch',description:'Computed hash does not match'}],
        checked_at:'2026-10-03T10:05:00Z',
      },
    };
    vi.mocked(qh.experimentAudit).mockResolvedValue(warningTimeline);
    renderPanel();

    expect(await screen.findByText('INTEGRITY WARNING')).toBeInTheDocument();
    expect(screen.getByText(/Audit integrity warning: Computed hash does not match/i)).toBeInTheDocument();
  });

  it('invokes export API on button click',async()=>{
    vi.mocked(qh.experimentAudit).mockResolvedValue(sampleTimeline);
    renderPanel();

    const exportButton=await screen.findByRole('button',{name:/Export Audit JSON/i});
    fireEvent.click(exportButton);
    expect(qh.experimentAuditExport).toHaveBeenCalledWith(experimentId);
  });

  it('handles empty events gracefully',async()=>{
    const emptyTimeline:AuditTimeline={
      ...sampleTimeline,
      events:[],
    };
    vi.mocked(qh.experimentAudit).mockResolvedValue(emptyTimeline);
    renderPanel();

    expect(await screen.findByText('No audit events found')).toBeInTheDocument();
    expect(screen.getByText(/No recorded platform events match the active category filter/i)).toBeInTheDocument();
  });
});
