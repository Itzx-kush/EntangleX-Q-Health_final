import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {PipelineVersionPanel} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  experimentPipeline:vi.fn(),
  pipelines:vi.fn(),
  pipelineDiff:vi.fn(),
}}));

const experimentId='11111111-1111-4111-8111-111111111111';
const pipelineId='22222222-2222-4222-8222-222222222222';
const otherId='33333333-3333-4333-8333-333333333333';
const version=(id=pipelineId,label='v2')=>({
  pipeline_version_id:id,pipeline_definition_id:'definition',
  pipeline_name:'Clinical hybrid pipeline',version:label,version_number:2,
  schema_version:'pipeline_definition_v1',status:'ACTIVE',
  description:'Fixture',definition_fingerprint:'a'.repeat(64),
  parent_pipeline_version_id:null,controlled_comparison_protocol_id:null,
  artifact_id:null,source_context:{type:'test'},
  canonical_definition:{schema_version:'pipeline_definition_v1'},
  stages:[
    {stage_id:'stage-1',stage_order:1,stage_type:'data_validation',stage_name:'Data validation',configuration:{dataset_version_id:'dataset-v3'},component_version:'data-v1',fingerprint:'b'.repeat(64)},
    {stage_id:'stage-2',stage_order:2,stage_type:'preprocessing',stage_name:'Preprocessing',configuration:{scaler:'standard'},component_version:'prep-v1',fingerprint:'c'.repeat(64)},
  ],
  experiments:[experimentId],usage_count:1,
  published_at:'2026-10-03T00:00:00Z',created_at:'2026-10-02T00:00:00Z',
  scientific_boundary:'Pipeline identity is not a model-quality claim.',
}) as any;

function renderPanel(){
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><PipelineVersionPanel experimentId={experimentId}/></QueryClientProvider>);
}

describe('Pipeline Version Registry panel',()=>{
  beforeEach(()=>vi.clearAllMocks());

  it('loads and renders exact version identity and ordered stages responsively',async()=>{
    vi.mocked(qh.experimentPipeline).mockResolvedValue({experiment_id:experimentId,status:'AVAILABLE',pipeline_version:version()});
    vi.mocked(qh.pipelines).mockResolvedValue([version()]);
    const {container}=renderPanel();
    expect(await screen.findByText('Clinical hybrid pipeline')).toBeInTheDocument();
    expect(screen.getByText('v2')).toBeInTheDocument();
    expect(screen.getByText('1. Data validation')).toBeInTheDocument();
    expect(screen.getByText('2. Preprocessing')).toBeInTheDocument();
    expect(screen.getByText('aaaaaaaaaaaaaaaaaaaa…')).toBeInTheDocument();
    expect(container.querySelector('.md\\:grid-cols-2')).toBeInTheDocument();
    expect(qh.experimentPipeline).toHaveBeenCalledWith(experimentId);
  });

  it('shows loading and the legacy no-pipeline state without inventing a version',async()=>{
    let resolve:(value:any)=>void=()=>{};
    vi.mocked(qh.experimentPipeline).mockReturnValue(new Promise(value=>{resolve=value}));
    const view=renderPanel();
    expect(screen.getByText('Loading research data…')).toBeInTheDocument();
    resolve({experiment_id:experimentId,status:'LEGACY_UNRESOLVED',pipeline_version:null,reason:'No exact historical mapping.'});
    expect(await screen.findByText('Pipeline version unavailable')).toBeInTheDocument();
    expect(screen.getByText(/no version is fabricated/i)).toBeInTheDocument();
    view.unmount();
  });

  it('renders structured neutral version differences',async()=>{
    vi.mocked(qh.experimentPipeline).mockResolvedValue({experiment_id:experimentId,status:'AVAILABLE',pipeline_version:version()});
    vi.mocked(qh.pipelines).mockResolvedValue([version(),version(otherId,'v3')]);
    vi.mocked(qh.pipelineDiff).mockResolvedValue({
      from_version:pipelineId,to_version:otherId,from_fingerprint:'a'.repeat(64),to_fingerprint:'d'.repeat(64),
      changes:[{stage:'preprocessing',field:'scaler',change_type:'Changed',before:'standard',after:'minmax'}],
      stage_summaries:[{stage:'preprocessing',status:'Changed'},{stage:'feature_engineering',status:'Unchanged'}],
      has_computational_changes:true,interpretation:'Differences identify computational changes only.',
    });
    renderPanel();
    const select=await screen.findByDisplayValue('Select a Pipeline Version');
    fireEvent.change(select,{target:{value:otherId}});
    await waitFor(()=>expect(qh.pipelineDiff).toHaveBeenCalledWith(pipelineId,otherId));
    expect(await screen.findByText('preprocessing · Changed')).toBeInTheDocument();
    expect(screen.getByText('feature engineering · Unchanged')).toBeInTheDocument();
    expect(screen.getByText(/Changed: preprocessing · scaler/)).toBeInTheDocument();
    expect(screen.queryByText(/better|worse|superior/i)).not.toBeInTheDocument();
  });

  it('renders API errors',async()=>{
    vi.mocked(qh.experimentPipeline).mockRejectedValue(new Error('Pipeline service unavailable'));
    renderPanel();
    expect(await screen.findByText('Pipeline service unavailable')).toBeInTheDocument();
  });
});