import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ExperimentLineagePanel} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{lineage:vi.fn()}}));

const experimentId='11111111-1111-4111-8111-111111111111';
const node=(id:string,type='experiment',depth=0)=>({
  id:`node-${id}`,object_type:type,object_id:id,label:`${type} ${id}`,
  status:'completed',version:type==='dataset_version'?'v1':null,
  fingerprint:`fingerprint-${id}`,created_at:'2026-10-03T00:00:00Z',
  exists:true,depth,metadata:{},
});
const snapshot=(overrides:Record<string,unknown>={})=>({
  experiment_id:experimentId,lineage_schema_version:'deep_experiment_lineage_v1',
  status:'COMPLETE',lineage_fingerprint:'a'.repeat(64),roots:['node-dataset'],
  nodes:[node('dataset','dataset',0),node('version','dataset_version',1),node(experimentId,'experiment',2)],
  edges:[
    {id:'edge-1',source_node_id:'node-dataset',target_node_id:'node-version',relationship_type:'has_version',schema_version:'deep_experiment_lineage_v1',relationship_fingerprint:'b'.repeat(64),recorded_at:'2026-10-03T00:00:00Z',metadata:{},capture_state:'recorded'},
    {id:'edge-2',source_node_id:'node-version',target_node_id:`node-${experimentId}`,relationship_type:'selected_by',schema_version:'deep_experiment_lineage_v1',relationship_fingerprint:'c'.repeat(64),recorded_at:'2026-10-03T00:00:00Z',metadata:{},capture_state:'recorded'},
  ],
  summary:{node_count:3,edge_count:2,root_count:1,max_depth:2,requested_depth:'3',direction:'both'},
  integrity:{missing_references:[],orphaned_edges:[],invalid_edges:[],duplicate_relationships:[],fingerprint_mismatches:[],cycles:[],legacy_reconstructed_edges:[],truncated:false},
  limitations:['Traceability only.'],...overrides,
}) as any;

function renderPanel(){
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><ExperimentLineagePanel experimentId={experimentId}/></QueryClientProvider>);
}

describe('Deep Experiment Lineage panel',()=>{
  beforeEach(()=>vi.clearAllMocks());

  it('loads and renders a responsive provenance graph',async()=>{
    vi.mocked(qh.lineage).mockResolvedValue(snapshot());
    const {container}=renderPanel();
    expect(await screen.findByText('COMPLETE')).toBeInTheDocument();
    expect(screen.getByText('dataset version')).toBeInTheDocument();
    expect(screen.getByText('has version')).toBeInTheDocument();
    expect(container.querySelector('.overflow-x-auto')).toBeInTheDocument();
    expect(qh.lineage).toHaveBeenCalledWith(experimentId,expect.objectContaining({depth:'3',direction:'both'}));
  });

  it('shows loading and meaningful empty states',async()=>{
    let resolve:(value:any)=>void=()=>{};
    vi.mocked(qh.lineage).mockReturnValue(new Promise(value=>{resolve=value}));
    const view=renderPanel();
    expect(screen.getByText('Loading research data…')).toBeInTheDocument();
    resolve(snapshot({nodes:[node(experimentId)],edges:[],summary:{node_count:1,edge_count:0,root_count:1,max_depth:0,requested_depth:'3',direction:'both'}}));
    expect(await screen.findByText('Lineage not available for this experiment')).toBeInTheDocument();
    view.unmount();
  });

  it('discloses partial legacy provenance without calling it a model failure',async()=>{
    vi.mocked(qh.lineage).mockResolvedValue(snapshot({
      status:'PARTIAL',
      integrity:{...snapshot().integrity,legacy_reconstructed_edges:['edge-1']},
    }));
    renderPanel();
    expect(await screen.findByText(/Partial provenance/)).toBeInTheDocument();
    expect(screen.getByText(/reconstructed from explicit persisted identifiers/)).toBeInTheDocument();
  });

  it('shows integrity review diagnostics',async()=>{
    vi.mocked(qh.lineage).mockResolvedValue(snapshot({
      status:'INTEGRITY_REVIEW',
      integrity:{...snapshot().integrity,cycles:[['a','b','a']],fingerprint_mismatches:[{node_id:'a'}]},
    }));
    renderPanel();
    expect(await screen.findByText(/Provenance integrity requires review/)).toBeInTheDocument();
    expect(screen.getByText(/2 structured issues detected/)).toBeInTheDocument();
  });

  it('supports deep graphs and bounded expansion',async()=>{
    const nodes=Array.from({length:75},(_,index)=>node(String(index),'run',index%7));
    vi.mocked(qh.lineage).mockResolvedValue(snapshot({
      nodes,edges:[],summary:{node_count:75,edge_count:0,root_count:75,max_depth:6,requested_depth:'all',direction:'both'},
    }));
    renderPanel();
    fireEvent.click(await screen.findByRole('button',{name:'Show all 75 nodes'}));
    expect(screen.getByRole('button',{name:'Show bounded view'})).toBeInTheDocument();
    expect(screen.getByText('run 74')).toBeInTheDocument();
  });

  it('selects a node and refetches traversal controls',async()=>{
    vi.mocked(qh.lineage).mockResolvedValue(snapshot());
    renderPanel();
    const versionLabel=await screen.findByText('dataset_version version');
    fireEvent.click(versionLabel.closest('button')!);
    expect(screen.getByText('fingerprint-version')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Direction'),{target:{value:'descendants'}});
    await waitFor(()=>expect(qh.lineage).toHaveBeenLastCalledWith(experimentId,expect.objectContaining({direction:'descendants'})));
  });
});