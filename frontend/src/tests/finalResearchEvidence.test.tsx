import {fireEvent,render,screen} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {FinalResearchEvidence} from '../components/FinalResearchEvidence';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  dataset:vi.fn(),evidencePackagePreflight:vi.fn(),evidencePackage:vi.fn(),lineage:vi.fn(),experimentAudit:vi.fn(),auditIntegrity:vi.fn(),
}}));

const experimentId='11111111-1111-4111-8111-111111111111';
const inventory={
  evaluation:{status:'available',record_count:2,referenced_ids:['model-a','model-b'],artifact_ids:[],latest_compatible_evidence:'model-a',configuration_fingerprints:[],evidence_timestamp:null,limitations:[],availability_reason:'Persisted model metrics'},
  calibration:{status:'not_available',record_count:0,referenced_ids:[],artifact_ids:[],latest_compatible_evidence:null,configuration_fingerprints:[],evidence_timestamp:null,limitations:[],availability_reason:'Not evaluated'},
};
const manifest={
  schema_version:'research_evidence_package_v1',package_id:'candidate',package_status:'PARTIAL',package_fingerprint:'a'.repeat(64),configuration_fingerprint:'b'.repeat(64),created_at:'2026-10-03T00:00:00Z',
  experiment:{id:experimentId,name:'Evidence fixture',status:'completed',configuration_fingerprint:'b'.repeat(64)},
  dataset:{dataset_id:'dataset-1',name:'Dataset fixture',dataset_version_id:'version-1',content_sha256:'c'.repeat(64),schema_fingerprint:'d'.repeat(64),target:'outcome',target_type:'binary_classification'},
  models:[],source_context:{type:'live_run'},evidence_inventory:inventory,
  provenance:{experiment_id:experimentId,run_ids:['run-1'],artifact_ids:[],configuration_fingerprints:[],evidence_source_fingerprints:[]},
  integrity:{dataset_hash:'c'.repeat(64),model_artifact_hashes:[],evidence_artifact_hashes:{},package_fingerprint:'a'.repeat(64),artifact_id:'artifact-1',hash_algorithm:'sha256'},
  limitations:['Evidence scope is limited to recorded studies.'],evidence_gaps:[{category:'calibration',status:'not_available',reason:'Not evaluated'}],
  artifact:{id:'artifact-1',artifact_type:'research_evidence_package',content_type:'application/json',integrity_hash:'e'.repeat(64),hash_algorithm:'sha256',immutable:true},
} as any;
const detail={
  experiment:{id:experimentId,name:'Evidence fixture',dataset_id:'dataset-1',parent_id:null,pipeline_version_id:'pipeline-1',protocol_version_id:'protocol-1',protocol_fingerprint:'p'.repeat(64),status:'completed',created_at:'2026-10-03T00:00:00Z',summary:{experiment_kind:'live'},config:{seed:42,test_size:.2,cv_folds:5}},
  models:[
    {id:'model-a',experiment_id:experimentId,dataset_id:'dataset-1',model_type:'random_forest',status:'ready',created_at:'2026-10-03T00:00:00Z',details:{},metrics:{test:{roc_auc:.91},validation:{summary:{roc_auc:{mean:.89,std:.02,valid_folds:5}}}}},
    {id:'model-b',experiment_id:experimentId,dataset_id:'dataset-1',model_type:'qsvc',status:'ready',created_at:'2026-10-03T00:00:00Z',details:{},metrics:{test:{roc_auc:.84}}},
  ],jobs:[],
} as any;
const lineage={experiment_id:experimentId,lineage_schema_version:'deep_experiment_lineage_v1',status:'INTEGRITY_REVIEW',lineage_fingerprint:'l'.repeat(64),roots:['experiment'],nodes:[{object_type:'experiment'}],edges:[],summary:{node_count:1,edge_count:0,root_count:1,max_depth:0,requested_depth:'3',direction:'both'},integrity:{missing_references:[{}],orphaned_edges:[],invalid_edges:[],duplicate_relationships:[],fingerprint_mismatches:[],cycles:[],legacy_reconstructed_edges:[],truncated:false},limitations:['Traceability only.']} as any;

function renderView(onReport=vi.fn()){
  return {onReport,...render(<MemoryRouter><QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><FinalResearchEvidence detail={detail} reportBusy={false} onReport={onReport} packagePanel={<div>Package controls</div>}/></QueryClientProvider></MemoryRouter>)};
}

describe('Final Research Evidence',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();
    vi.mocked(qh.dataset).mockResolvedValue({id:'dataset-1',name:'Dataset fixture',sha256:'c'.repeat(64),created_at:'2026-10-03T00:00:00Z',provenance:{row_count:520,feature_count:16},quality:{}} as any);
    vi.mocked(qh.evidencePackage).mockRejectedValue(new Error('No package'));
    vi.mocked(qh.evidencePackagePreflight).mockResolvedValue({feasible:false,package_status:'PARTIAL',package_fingerprint_candidate:'f'.repeat(64),evidence_inventory:inventory,blockers:[{code:'core_missing',message:'Core evidence missing'}],warnings:[],missing_evidence:manifest.evidence_gaps,core_missing_evidence:['calibration'],manifest} as any);
    vi.mocked(qh.lineage).mockResolvedValue(lineage);
    vi.mocked(qh.experimentAudit).mockResolvedValue({object_type:'experiment',object_id:experimentId,total_events:3,events:[{event_type:'package_preflight',occurred_at:'2026-10-03T00:00:00Z'}],categories_present:['EXPERIMENT','EVIDENCE'],integrity_status:'INTEGRITY_WARNING',legacy_disclaimer:null,scientific_boundary:'Research only'} as any);
    vi.mocked(qh.auditIntegrity).mockResolvedValue({valid:false,total_events:3,issues:[{message:'Chain mismatch'}],interpretation:'Review'} as any);
  });

  it('aggregates the leading result, package gaps, lineage, and audit integrity without fabricating evidence',async()=>{
    renderView();
    expect(await screen.findByText('Final Research Evidence')).toBeInTheDocument();
    expect(screen.getAllByText('Random Forest').length).toBeGreaterThan(0);
    expect(screen.getByText('91.0%')).toBeInTheDocument();
    expect(await screen.findByText((_,element)=>element?.textContent==='PACKAGE PARTIAL')).toBeInTheDocument();
    expect(await screen.findByText(/Package creation is blocked/)).toBeInTheDocument();
    expect(await screen.findByText('INTEGRITY WARNING')).toBeInTheDocument();
    expect(screen.getAllByText('Not evaluated').length).toBeGreaterThan(0);
    expect(screen.getByText('Package controls')).toBeInTheDocument();
    expect(screen.getByText('Quantum computation evidence')).toBeInTheDocument();
  });

  it('uses existing backend report actions for final downloads',async()=>{
    const {onReport}=renderView();
    fireEvent.click(await screen.findByRole('button',{name:'Download HTML report'}));
    fireEvent.click(screen.getByRole('button',{name:'Download JSON report'}));
    expect(onReport).toHaveBeenNthCalledWith(1,'html');
    expect(onReport).toHaveBeenNthCalledWith(2,'json');
  });
});
