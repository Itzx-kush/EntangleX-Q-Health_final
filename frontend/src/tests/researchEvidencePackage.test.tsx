import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ResearchEvidencePackagePanel} from '../pages/ResearchPagesStudio';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  evidencePackage:vi.fn(),
  evidencePackagePreflight:vi.fn(),
  createEvidencePackage:vi.fn(),
  downloadEvidencePackage:vi.fn(),
}}));

const experimentId='11111111-1111-4111-8111-111111111111';
const packageValue={
  schema_version:'research_evidence_package_v1',
  package_id:'22222222-2222-4222-8222-222222222222',
  package_status:'PARTIAL',
  package_fingerprint:'a'.repeat(64),
  configuration_fingerprint:'b'.repeat(64),
  created_at:'2026-10-03T00:00:00Z',
  experiment:{id:experimentId,name:'Fixture',status:'completed',configuration_fingerprint:'b'.repeat(64)},
  dataset:{dataset_id:'dataset',name:'Fixture',dataset_version_id:'version',content_sha256:'c'.repeat(64),schema_fingerprint:'d'.repeat(64),target:'outcome',target_type:'binary_classification'},
  models:[],
  source_context:{type:'live_run'},
  evidence_inventory:{
    evaluation:{status:'available',record_count:1,referenced_ids:['model'],artifact_ids:[],latest_compatible_evidence:'model',configuration_fingerprints:[],evidence_timestamp:null,limitations:[],availability_reason:'persisted'},
    calibration:{status:'not_available',record_count:0,referenced_ids:[],artifact_ids:[],latest_compatible_evidence:null,configuration_fingerprints:[],evidence_timestamp:null,limitations:[],availability_reason:'missing'},
  },
  provenance:{experiment_id:experimentId,run_ids:['run'],artifact_ids:['artifact'],configuration_fingerprints:['b'.repeat(64)],evidence_source_fingerprints:[]},
  integrity:{dataset_hash:'c'.repeat(64),model_artifact_hashes:[],evidence_artifact_hashes:{},package_fingerprint:'a'.repeat(64),artifact_id:'artifact',hash_algorithm:'sha256'},
  limitations:['Research manifest only.'],
  evidence_gaps:[{category:'calibration',status:'not_available',reason:'missing'}],
  artifact:{id:'artifact',artifact_type:'research_evidence_package',content_type:'application/json',integrity_hash:'e'.repeat(64),hash_algorithm:'sha256',immutable:true},
} as any;
const preflightValue={
  feasible:true,
  package_status:'PARTIAL',
  package_fingerprint_candidate:'f'.repeat(64),
  evidence_inventory:packageValue.evidence_inventory,
  blockers:[],
  warnings:[],
  missing_evidence:packageValue.evidence_gaps,
  core_missing_evidence:[],
  manifest:packageValue,
} as any;

function renderPanel(){
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}><ResearchEvidencePackagePanel experimentId={experimentId}/></QueryClientProvider>);
}

describe('Research Evidence Package panel',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();
    vi.mocked(qh.evidencePackagePreflight).mockResolvedValue(preflightValue);
  });

  it('shows partial availability, fingerprint, provenance, and immutable artifact state',async()=>{
    vi.mocked(qh.evidencePackage).mockResolvedValue(packageValue);
    renderPanel();
    expect(await screen.findByText('PARTIAL')).toBeInTheDocument();
    expect(screen.getByText('IMMUTABLE ARTIFACT')).toBeInTheDocument();
    expect(screen.getByText('aaaaaaaaaaaaaaaaaaaa…')).toBeInTheDocument();
    expect(screen.getByText('not available')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Inspect package'}));
    expect(screen.getByText(/Runs: 1/)).toBeInTheDocument();
    expect(screen.getByText('Research manifest only.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Download JSON'}));
    expect(qh.downloadEvidencePackage).toHaveBeenCalledWith(experimentId,packageValue.package_id);
  });

  it('generates a package when none exists',async()=>{
    vi.mocked(qh.evidencePackage).mockRejectedValue(new Error('No package'));
    vi.mocked(qh.createEvidencePackage).mockResolvedValue(packageValue);
    renderPanel();
    const generate=await screen.findByRole('button',{name:'Generate package'});
    await waitFor(()=>expect(generate).toBeEnabled());
    generate.click();
    await waitFor(()=>expect(qh.createEvidencePackage).toHaveBeenCalledWith(experimentId));
    expect(await screen.findByText('PARTIAL')).toBeInTheDocument();
  });
});