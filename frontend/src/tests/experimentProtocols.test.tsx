import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ExperimentProtocolPanel} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  experimentProtocol:vi.fn(),
  experimentProtocolCompliance:vi.fn(),
  protocols:vi.fn(),
  protocolDiff:vi.fn(),
  protocolTemplates:vi.fn(),
  attachProtocol:vi.fn(),
}}));

const experimentId='11111111-1111-4111-8111-111111111111';
const protocolId='22222222-2222-4222-8222-222222222222';
const otherProtocolId='33333333-3333-4333-8333-333333333333';

const mockProtocolVersion=(id=protocolId,label='v1')=>({
  protocol_version_id:id,
  protocol_id:'proto-family-1',
  protocol_name:'Biomedical Classification Protocol',
  version:label,
  version_number:1,
  schema_version:'experiment_protocol_v1',
  status:'PUBLISHED',
  description:'Standardized benchmark protocol',
  definition_fingerprint:'f'.repeat(64),
  template_id:'tpl-biomed-classification',
  parent_protocol_version_id:null,
  pipeline_version_id:'pipe-v1',
  controlled_comparison_protocol_id:null,
  artifact_id:null,
  source_context:null,
  canonical_definition:{
    study:{task_type:'binary_classification',study_purpose:'Benchmarking'},
    dataset:{required_target_column:'target',selection_strategy:'frozen_benchmark'},
    split:{strategy:'stratified_kfold',cv_folds:5},
    randomness:{seed_policy:'fixed_seed_list',seed_list:[42,43,44,45,46]},
    evaluation:{primary_metric:'roc_auc',secondary_metrics:['pr_auc','f1']},
    threshold:{policy:'youden_index',lock:true},
    calibration:{requirement:'REQUIRED',method:'isotonic'},
    quantum_controls:{controlled_comparison:true},
  },
  study:{task_type:'binary_classification',study_purpose:'Benchmarking'},
  dataset:{required_target_column:'target',selection_strategy:'frozen_benchmark'},
  split:{strategy:'stratified_kfold',cv_folds:5},
  randomness:{seed_policy:'fixed_seed_list',seed_list:[42,43,44,45,46]},
  evaluation:{primary_metric:'roc_auc',secondary_metrics:['pr_auc','f1']},
  threshold:{policy:'youden_index',lock:true},
  calibration:{requirement:'REQUIRED',method:'isotonic'},
  quantum_controls:{controlled_comparison:true},
  constraints:{},
  experiments:[experimentId],
  usage_count:1,
  published_at:'2026-10-03T00:00:00Z',
  created_at:'2026-10-02T00:00:00Z',
  scientific_boundary:'A protocol specifies experimental rules, not scientific success or model quality.',
}) as any;

const mockComplianceResponse=()=>({
  experiment_id:experimentId,
  status:'AVAILABLE',
  protocol_version_id:protocolId,
  protocol_name:'Biomedical Classification Protocol',
  protocol_version:'v1',
  protocol_fingerprint:'f'.repeat(64),
  compliance_summary:{
    matched:4,
    missing:1,
    mismatched:0,
    not_applicable:1,
    unverifiable:0,
    total_checks:6,
  },
  checks:[
    {
      rule:'dataset_target_column',
      category:'dataset',
      requirement:'REQUIRED',
      expected:'target',
      actual:'target',
      status:'MATCHED',
      details:'Target column matches protocol specification.',
    },
    {
      rule:'split_cv_folds',
      category:'split',
      requirement:'REQUIRED',
      expected:5,
      actual:5,
      status:'MATCHED',
      details:'Cross-validation fold count matches.',
    },
    {
      rule:'calibration_performed',
      category:'calibration',
      requirement:'REQUIRED',
      expected:true,
      actual:false,
      status:'MISSING',
      details:'Calibration is required by protocol but was not recorded.',
    },
    {
      rule:'external_validation',
      category:'validation_extensions',
      requirement:'OPTIONAL',
      expected:null,
      actual:null,
      status:'NOT_APPLICABLE',
      details:'External validation was optional and not performed.',
    },
  ],
  interpretation:'Compliance records factual alignment with declared experimental rules; it does not compute a quality score, grade, or validation pass/fail.',
}) as any;

function renderPanel(){
  return render(
    <QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
      <ExperimentProtocolPanel experimentId={experimentId}/>
    </QueryClientProvider>
  );
}

describe('ExperimentProtocolPanel',()=>{
  beforeEach(()=>vi.clearAllMocks());

  it('loads and renders protocol identity, specifications, and factual compliance checklist responsively',async()=>{
    vi.mocked(qh.experimentProtocol).mockResolvedValue({experiment_id:experimentId,status:'AVAILABLE',protocol_version:mockProtocolVersion()});
    vi.mocked(qh.experimentProtocolCompliance).mockResolvedValue(mockComplianceResponse());
    vi.mocked(qh.protocols).mockResolvedValue([mockProtocolVersion()]);
    vi.mocked(qh.protocolTemplates).mockResolvedValue([]);

    renderPanel();

    expect(await screen.findByText('Biomedical Classification Protocol')).toBeInTheDocument();
    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('ffffffffffffffffffff…')).toBeInTheDocument();
    expect(screen.getByText('binary_classification')).toBeInTheDocument();
    expect(screen.getByText('stratified_kfold')).toBeInTheDocument();

    // Verify factual compliance checklist items
    expect(await screen.findByText('4 MATCHED')).toBeInTheDocument();
    expect(screen.getByText('1 MISSING')).toBeInTheDocument();
    expect(screen.getByText('1 N/A')).toBeInTheDocument();
    expect(screen.getByText('dataset target column')).toBeInTheDocument();
    expect(screen.getByText('calibration performed')).toBeInTheDocument();
    expect(screen.getByText('Calibration is required by protocol but was not recorded.')).toBeInTheDocument();

    // Verify no subjective quality scoring
    expect(screen.queryByText(/quality score:|grade:|superior model/i)).not.toBeInTheDocument();
  });

  it('shows loading and handles legacy unspecified experiment gracefully without fabricating a protocol',async()=>{
    let resolve:(value:any)=>void=()=>{};
    vi.mocked(qh.experimentProtocol).mockReturnValue(new Promise(val=>{resolve=val;}));
    vi.mocked(qh.protocols).mockResolvedValue([mockProtocolVersion()]);
    vi.mocked(qh.protocolTemplates).mockResolvedValue([]);

    const view=renderPanel();
    expect(screen.getByText('Loading research data…')).toBeInTheDocument();

    resolve({
      experiment_id:experimentId,
      status:'LEGACY_UNSPECIFIED',
      protocol_version:null,
      reason:'No protocol was attached when this experiment was executed.',
    });

    expect(await screen.findByText('Experiment protocol unavailable')).toBeInTheDocument();
    expect(screen.getByText(/no protocol version is fabricated/i)).toBeInTheDocument();
    expect(await screen.findByText('ATTACH PUBLISHED PROTOCOL')).toBeInTheDocument();
    view.unmount();
  });

  it('renders structured neutral protocol version differences without quality judgments',async()=>{
    vi.mocked(qh.experimentProtocol).mockResolvedValue({experiment_id:experimentId,status:'AVAILABLE',protocol_version:mockProtocolVersion()});
    vi.mocked(qh.experimentProtocolCompliance).mockResolvedValue(mockComplianceResponse());
    vi.mocked(qh.protocols).mockResolvedValue([
      mockProtocolVersion(),
      mockProtocolVersion(otherProtocolId,'v2'),
    ]);
    vi.mocked(qh.protocolTemplates).mockResolvedValue([]);
    vi.mocked(qh.protocolDiff).mockResolvedValue({
      from_version:protocolId,
      to_version:otherProtocolId,
      from_fingerprint:'f'.repeat(64),
      to_fingerprint:'e'.repeat(64),
      changes:[
        {category:'split',field:'cv_folds',change_type:'Changed',before:5,after:10},
        {category:'calibration',field:'requirement',change_type:'Changed',before:'REQUIRED',after:'OPTIONAL'},
      ],
      change_count:2,
      identical:false,
      category_summaries:[
        {category:'split',status:'Changed'},
        {category:'calibration',status:'Changed'},
        {category:'dataset',status:'Unchanged'},
      ],
      has_protocol_changes:true,
      interpretation:'Protocol differences identify explicit specification changes only.',
    } as any);

    renderPanel();

    const select=await screen.findByDisplayValue('Select a Protocol Version');
    fireEvent.change(select,{target:{value:otherProtocolId}});

    await waitFor(()=>expect(qh.protocolDiff).toHaveBeenCalledWith(protocolId,otherProtocolId));
    expect(await screen.findByText('split · Changed')).toBeInTheDocument();
    expect(screen.getByText('calibration · Changed')).toBeInTheDocument();
    expect(screen.getByText('dataset · Unchanged')).toBeInTheDocument();
    expect(screen.getByText(/Changed: split · cv_folds/)).toBeInTheDocument();
    expect(screen.getByText('Protocol differences identify explicit specification changes only.')).toBeInTheDocument();
    expect(screen.queryByText(/superior|improved|worse|downgrade/i)).not.toBeInTheDocument();
  });

  it('renders API error banners cleanly',async()=>{
    vi.mocked(qh.experimentProtocol).mockRejectedValue(new Error('Protocol service unreachable'));
    vi.mocked(qh.protocols).mockResolvedValue([]);
    vi.mocked(qh.protocolTemplates).mockResolvedValue([]);

    renderPanel();
    expect(await screen.findByText('Protocol service unreachable')).toBeInTheDocument();
  });
});
