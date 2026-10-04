import {Link,useNavigate,useParams} from 'react-router-dom';
import {useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {ArrowLeft,BookmarkPlus,Copy,Download,ExternalLink,GitBranch,History,LogIn,RotateCcw,Trash2} from 'lucide-react';
import {Button,Card,Select,Badge} from '../components/ui';
import {EmptyState,ErrorBanner,JsonDisclosure,Loading,MetricCard,Notice,PageHeader,StatusBadge} from '../components/Shared';
import {StageNav} from './ResearchPagesCore';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {dateTime,metric,modelLabels,seconds,shortId} from '../utils/format';
import { CalibrationLaboratory } from './CalibrationLaboratory';
import { ThresholdAnalysis } from './ThresholdAnalysis';
import { QuantumDiagnostics } from './QuantumDiagnostics';
import { AblationLaboratory } from './AblationLaboratory';
import { BiomedicalSubgroupAnalysisPanel } from './BiomedicalSubgroupAnalysis';
import type {Experiment,LineageNode,SavedResearchReport} from '../types/qhealth';
import {GlareHover} from '../components/reactbits';
import {DistributionStrip,PipelineFlow,WorkbenchRail} from '../components/TremorWorkbench';
import {ModelCardPanel} from '../components/ModelCardPanel';
import {DatasetQualityPanel} from './DatasetQualityScorecard';
import {FinalResearchEvidence} from '../components/FinalResearchEvidence';
import {useResearchRecorder} from '../research/useResearchHistory';
import {experimentActivity} from '../research/historyRecords';
import {useAuth} from '../auth/AuthProvider';

export function Experiments(){
  const list=useQuery({queryKey:['experiments'],queryFn:qh.experiments,refetchInterval:5000});
  const qc=useQueryClient();
  const {update}=useDraft();
  const navigate=useNavigate();
  const history=useResearchRecorder();
  const [query,setQuery]=useState('');
  const [status,setStatus]=useState('all');
  const [selected,setSelected]=useState<Experiment|null>(null);
  const [pendingDelete,setPendingDelete]=useState<Experiment|null>(null);
  const [deleteMessage,setDeleteMessage]=useState('');
  const rerun=useMutation({mutationFn:(id:string)=>qh.rerun(id),onSuccess:r=>{qc.invalidateQueries({queryKey:['experiments']});void history.record(experimentActivity(r.experiment));navigate('/experiments/'+r.experiment.id)}});
  const remove=useMutation({
    mutationFn:(experiment:Experiment)=>qh.deleteExperiment(experiment.id),
    onSuccess:(_result,experiment)=>{
      qc.setQueryData<Experiment[]>(['experiments'],current=>(current||[]).filter(item=>item.id!==experiment.id));
      if(selected?.id===experiment.id)setSelected(null);
      setPendingDelete(null);
      setDeleteMessage(`${experiment.name||`Experiment ${shortId(experiment.id)}`} was removed from the active registry. Scientific records were preserved.`);
      void qc.invalidateQueries({queryKey:['experiments']});
      void qc.invalidateQueries({queryKey:['summary']});
    }
  });
  const deletableStatuses=new Set(['completed','succeeded','partial','failed','cancelled','interrupted']);
  const activeStatuses=new Set(['queued','running','cancel_requested']);
  const statuses=Array.from(new Set((list.data||[]).map(e=>e.status)));
  const rows=(list.data||[]).filter(e=>{
    const hay=((e.name||'')+' '+e.id+' '+e.status+' '+e.dataset_id+' '+(e.config.models||[]).join(' ')).toLowerCase();
    return hay.includes(query.toLowerCase())&&(status==='all'||e.status===status);
  });
  return <div>
    <PageHeader eyebrow="Research Studio · Registry" title="Experiments" description="Preserve every research decision: dataset reference, model set, seeds, execution state, measured output and limitations." actions={<Link className="btn btn-outline" to="/training">Start in Model Lab <RotateCcw size={13}/></Link>}/>
    <StageNav current="/experiments"/>
    <ErrorBanner error={(list.error as Error)?.message||(rerun.error as Error)?.message||(remove.error as Error)?.message}/>
    {deleteMessage&&<Notice tone="blue">{deleteMessage}</Notice>}
    <WorkbenchRail items={[{label:'Recorded',value:list.data?.length??'—',detail:'Backend experiment records',tone:'blue'},{label:'Visible',value:rows.length,detail:'Current registry filter',tone:'purple'},{label:'Active filter',value:status==='all'?'All states':status.replaceAll('_',' '),detail:'Status scope',tone:'amber'},{label:'Reproducibility',value:'Tracked',detail:'Seed + configuration retained',tone:'green'}]}/>
    <div className="mt-3"><DistributionStrip items={statuses.map((value,index)=>({label:value.replaceAll('_',' '),value:(list.data||[]).filter(item=>item.status===value).length,tone:(['green','blue','amber','purple'] as const)[index%4]}))}/></div>
    <Card title="Experiment registry" description="The main research landscape: searchable, filterable and drillable like a biomedical evidence dashboard.">
      <div className="controls mb-4">
        <label className="field min-w-[240px] flex-1"><span>Search</span><input className="input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Experiment, dataset, model…"/></label>
        <label className="field min-w-[180px]"><span>Status</span><Select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All states</option>{statuses.map(s=><option value={s} key={s}>{s.replaceAll('_',' ')}</option>)}</Select></label>
      </div>
      {list.isLoading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Experiment</th><th>Created</th><th>Status</th><th>Models</th><th>Dataset</th><th/></tr></thead><tbody>{rows.map((e,i)=>{const canDelete=deletableStatuses.has(e.status);const active=activeStatuses.has(e.status);return <tr key={e.id} style={{animationDelay:`${i*30}ms`}} className="rb-reveal"><td><button className="font-semibold text-primary hover:underline" onClick={()=>setSelected(e)}>{e.name||`Experiment ${shortId(e.id)}`}</button><small className="block muted">{e.summary.experiment_kind==='precomputed_verified_demo'?'Precomputed verified demo experiment':e.parent_id?'Parent '+shortId(e.parent_id):'Live root experiment'} · {shortId(e.id)}</small></td><td>{dateTime(e.created_at)}</td><td><StatusBadge value={e.status}/></td><td>{(e.config.models||[]).map(m=>modelLabels[m]).join(', ')}<small className="block muted">Seed {e.config.seed}</small></td><td className="mono text-[10px]">{shortId(e.dataset_id)}</td><td className="text-right"><div className="flex justify-end gap-1"><Link className="btn btn-outline px-2" to={'/experiments/'+e.id}>Open</Link><Button variant="outline" disabled={rerun.isPending} onClick={()=>rerun.mutate(e.id)}><RotateCcw size={12}/>Rerun</Button><Button variant="ghost" onClick={()=>{update(e.config);navigate('/training')}}><Copy size={12}/>Draft</Button><Button variant="ghost" disabled={!canDelete||remove.isPending} title={active?'Cancel this experiment and wait for a terminal state before deleting it.':canDelete?'Delete experiment':'This experiment is not in a deletable terminal state.'} onClick={()=>{setDeleteMessage('');setPendingDelete(e)}}><Trash2 size={12}/>Delete</Button></div>{active&&<small className="mt-1 block muted">Cancel and wait for completion before deleting.</small>}</td></tr>})}</tbody></table>{!rows.length&&<div className="p-6"><EmptyState title="No matching experiments">Change the registry filters or start a new run in Model Lab.</EmptyState></div>}</div>}
    </Card>
    {pendingDelete&&<Card className="mt-5" title="Delete experiment?" description={pendingDelete.name||`Experiment ${shortId(pendingDelete.id)}`}>
      <p className="text-sm">This will remove the experiment from the active Experiment Registry.</p>
      <Notice tone="amber">Immutable runs, models, manifests, artifacts, datasets and dataset versions will be preserved for research integrity.</Notice>
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={remove.isPending} onClick={()=>setPendingDelete(null)}>Cancel</Button><Button disabled={remove.isPending} onClick={()=>remove.mutate(pendingDelete)}><Trash2 size={13}/>{remove.isPending?'Deleting…':'Delete experiment'}</Button></div>
    </Card>}
    {selected&&<div className="mt-5 two-grid"><Card title={selected.name||`Experiment ${shortId(selected.id)}`} description="Registry detail"><div className="grid gap-3 text-sm"><div className="flex justify-between"><span className="muted">Status</span><StatusBadge value={selected.status}/></div><div className="flex justify-between"><span className="muted">Dataset</span><span className="mono text-xs">{selected.dataset_id}</span></div><div className="flex justify-between"><span className="muted">Created</span><span>{dateTime(selected.created_at)}</span></div><div><span className="muted">Models</span><div className="mt-2 flex flex-wrap gap-1">{selected.config.models.map(m=><Badge key={m}>{modelLabels[m]}</Badge>)}</div></div></div></Card><Card title="Exact configuration"><JsonDisclosure label="Open JSON configuration" value={selected.config}/><Link className="btn btn-outline mt-3" to={'/experiments/'+selected.id}>Open full evidence <ExternalLink size={13}/></Link></Card></div>}
  </div>
}

const lineageTone=(type:string):'blue'|'green'|'amber'|'purple'=>type==='experiment'?'purple':type.includes('dataset')?'green':type==='artifact'||type.includes('package')?'amber':'blue';

export function ExperimentProtocolPanel({experimentId}:{experimentId:string}){
  const qc=useQueryClient();
  const protocol=useQuery({queryKey:['experiment-protocol',experimentId],queryFn:()=>qh.experimentProtocol(experimentId),retry:false});
  const current=protocol.data?.status==='AVAILABLE'?protocol.data.protocol_version:null;
  const compliance=useQuery({
    queryKey:['experiment-protocol-compliance',experimentId],
    queryFn:()=>qh.experimentProtocolCompliance(experimentId),
    enabled:Boolean(current),
    retry:false,
  });
  const protocols=useQuery({queryKey:['protocols'],queryFn:qh.protocols,enabled:Boolean(protocol.data)});
  const templates=useQuery({queryKey:['protocol-templates'],queryFn:qh.protocolTemplates,enabled:Boolean(protocol.data)});
  const [compareTo,setCompareTo]=useState('');
  const diff=useQuery({
    queryKey:['protocol-diff',current?.protocol_version_id,compareTo],
    queryFn:()=>qh.protocolDiff(current!.protocol_version_id,compareTo),
    enabled:Boolean(current&&compareTo),
    retry:false,
  });
  const [attachId,setAttachId]=useState('');
  const attach=useMutation({
    mutationFn:(protoId:string)=>qh.attachProtocol(experimentId,protoId),
    onSuccess:()=>{
      qc.invalidateQueries({queryKey:['experiment-protocol',experimentId]});
      qc.invalidateQueries({queryKey:['experiment-protocol-compliance',experimentId]});
      qc.invalidateQueries({queryKey:['experiment',experimentId]});
    }
  });

  const complianceTone=(status:string):'green'|'amber'|'red'|'blue'|'purple'=>{
    switch(status){
      case 'MATCHED':return 'green';
      case 'MISSING':return 'amber';
      case 'MISMATCHED':return 'red';
      case 'NOT_APPLICABLE':return 'blue';
      case 'UNVERIFIABLE':return 'purple';
      default:return 'blue';
    }
  };

  return <Card className="mt-5" title="Experiment Protocol" description="The explicit immutable experimental specification and verification checklist for this experiment.">
    <ErrorBanner error={(protocol.error as Error)?.message||(compliance.error as Error)?.message||(diff.error as Error)?.message||(attach.error as Error)?.message}/>
    {protocol.isLoading?<Loading/>:protocol.data?.status==='LEGACY_UNSPECIFIED'?<div>
      <EmptyState title="Experiment protocol unavailable">{protocol.data.reason} Historical configuration remains accessible, but no protocol version is fabricated.</EmptyState>
      {protocols.data&&protocols.data.length>0&&<div className="mt-4 rounded-xl border p-4">
        <div className="metric-label">ATTACH PUBLISHED PROTOCOL</div>
        <p className="mt-1 text-xs muted">Assign a published protocol version to this legacy experiment to record its experimental rules.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <Select className="flex-1 min-w-[220px]" value={attachId} onChange={e=>setAttachId(e.target.value)}>
            <option value="">Select published protocol</option>
            {protocols.data.map(p=><option key={p.protocol_version_id} value={p.protocol_version_id}>{p.protocol_name} · {p.version}</option>)}
          </Select>
          <Button disabled={!attachId||attach.isPending} onClick={()=>attach.mutate(attachId)}>
            {attach.isPending?'Attaching…':'Attach Protocol'}
          </Button>
        </div>
      </div>}
      {templates.data&&templates.data.length>0&&<div className="mt-4">
        <JsonDisclosure label="Browse reusable research protocol templates" value={templates.data}/>
      </div>}
    </div>:current?<>
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge value={current.status}/>
        <Badge tone="purple">{current.version}</Badge>
        <span className="text-sm font-semibold">{current.protocol_name}</span>
        <span className="mono text-[10px] muted" title={current.definition_fingerprint}>{current.definition_fingerprint.slice(0,20)}…</span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div><span className="metric-label">PROTOCOL VERSION ID</span><strong className="mono block break-all text-[10px]">{current.protocol_version_id}</strong></div>
        <div><span className="metric-label">SCHEMA</span><strong className="block text-xs">{current.schema_version}</strong></div>
        <div><span className="metric-label">USED BY</span><strong className="block text-xs">{current.usage_count} experiment{current.usage_count===1?'':'s'}</strong></div>
        <div><span className="metric-label">PUBLISHED</span><strong className="block text-xs">{current.published_at?dateTime(current.published_at):'Draft'}</strong></div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border p-3">
          <div className="metric-label">STUDY &amp; DATASET</div>
          <div className="mt-1 text-xs font-semibold">{String((current.study as any)?.task_type||'—')}</div>
          <p className="mt-1 text-[11px] muted line-clamp-2">{String((current.study as any)?.study_purpose||'—')}</p>
          <div className="mt-2 text-[10px] muted">Target: <span className="font-mono">{String((current.dataset as any)?.required_target_column||'—')}</span></div>
        </div>
        <div className="rounded-xl border p-3">
          <div className="metric-label">SPLIT &amp; RANDOMNESS</div>
          <div className="mt-1 text-xs font-semibold">{String((current.split as any)?.strategy||'—')}</div>
          <div className="mt-1 text-[11px] muted">Folds: {String((current.split as any)?.cv_folds??'—')}</div>
          <div className="mt-2 text-[10px] muted">Seeds: {Array.isArray((current.randomness as any)?.seed_list)?(current.randomness as any).seed_list.join(', '):String((current.randomness as any)?.primary_seed??'—')}</div>
        </div>
        <div className="rounded-xl border p-3">
          <div className="metric-label">EVALUATION &amp; THRESHOLD</div>
          <div className="mt-1 text-xs font-semibold">Primary: {String((current.evaluation as any)?.primary_metric||'—')}</div>
          <div className="mt-1 text-[11px] muted">Threshold: {String((current.threshold as any)?.policy||'—')}</div>
          <div className="mt-2 text-[10px] muted">Lock: {(current.threshold as any)?.lock?'Locked':'Unlocked'}</div>
        </div>
        <div className="rounded-xl border p-3">
          <div className="metric-label">CALIBRATION &amp; CONTROLS</div>
          <div className="mt-1 text-xs font-semibold">Calibration: {String((current.calibration as any)?.requirement||((current.calibration as any)?.required?'REQUIRED':'OPTIONAL'))}</div>
          <div className="mt-1 text-[11px] muted">Quantum Controls: {(current.quantum_controls as any)?.controlled_comparison?'REQUIRED':'DISABLED'}</div>
          <div className="mt-2 text-[10px] muted">Pipeline: {current.pipeline_version_id?current.pipeline_version_id.slice(0,12)+'…':'None'}</div>
        </div>
      </div>
      <JsonDisclosure label="Open canonical protocol definition" value={current.canonical_definition}/>

      {/* Compliance Checklist */}
      <div className="mt-5 rounded-xl border p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="metric-label">PROTOCOL COMPLIANCE VERIFICATION</div>
            <p className="mt-0.5 text-xs muted">Factual evaluation against recorded experiment artifacts and metrics.</p>
          </div>
          {compliance.data?.compliance_summary&&<div className="flex flex-wrap gap-1">
            <Badge tone="green">{compliance.data.compliance_summary.matched} MATCHED</Badge>
            <Badge tone="amber">{compliance.data.compliance_summary.missing} MISSING</Badge>
            {compliance.data.compliance_summary.mismatched>0&&<Badge tone="red">{compliance.data.compliance_summary.mismatched} MISMATCHED</Badge>}
            {compliance.data.compliance_summary.not_applicable>0&&<Badge tone="blue">{compliance.data.compliance_summary.not_applicable} N/A</Badge>}
            {compliance.data.compliance_summary.unverifiable>0&&<Badge tone="purple">{compliance.data.compliance_summary.unverifiable} UNVERIFIABLE</Badge>}
          </div>}
        </div>
        {compliance.isLoading?<div className="mt-3"><Loading/></div>:compliance.data?.status==='AVAILABLE'?<div className="mt-3">
          <div className="max-h-72 space-y-2 overflow-y-auto">
            {compliance.data.checks.map((check,index)=><div className="flex flex-wrap items-start justify-between gap-2 border-b pb-2 text-xs last:border-0" key={`${check.rule}-${index}`}>
              <div className="flex-1 min-w-[200px]">
                <div className="flex items-center gap-2">
                  <strong className="text-xs">{check.rule.replaceAll('_',' ')}</strong>
                  <Badge tone={check.requirement==='REQUIRED'?'blue':check.requirement==='OPTIONAL'?'amber':'purple'}>{check.requirement}</Badge>
                </div>
                <p className="mt-1 text-[11px] muted">{check.details}</p>
                <div className="mt-1 text-[10px] mono muted">Expected: {JSON.stringify(check.expected)} | Actual: {JSON.stringify(check.actual)}</div>
              </div>
              <Badge tone={complianceTone(check.status)}>{check.status}</Badge>
            </div>)}
          </div>
          <p className="mt-3 text-[11px] muted">{compliance.data.interpretation}</p>
        </div>:<EmptyState title="Compliance unavailable">{compliance.data?.reason||'No compliance record available.'}</EmptyState>}
      </div>

      {/* Protocol Version Diff */}
      {(protocols.data?.filter(item=>item.protocol_version_id!==current.protocol_version_id).length||0)>0&&<div className="mt-4 rounded-xl border p-4">
        <div className="metric-label">COMPARE PROTOCOL VERSION</div>
        <Select className="mt-2" value={compareTo} onChange={event=>setCompareTo(event.target.value)}>
          <option value="">Select a Protocol Version</option>
          {protocols.data?.filter(item=>item.protocol_version_id!==current.protocol_version_id).map(item=><option key={item.protocol_version_id} value={item.protocol_version_id}>{item.protocol_name} · {item.version}</option>)}
        </Select>
        {diff.isLoading&&<Loading/>}
        {diff.data&&<div className="mt-3">
          <div className="flex flex-wrap gap-2">{diff.data.category_summaries.map(item=><Badge key={item.category} tone={item.status==='Unchanged'?'green':'amber'}>{item.category.replaceAll('_',' ')} · {item.status}</Badge>)}</div>
          {diff.data.changes.length?<div className="mt-3 max-h-56 space-y-2 overflow-y-auto">{diff.data.changes.map((change,index)=><div className="border-b pb-2 text-xs last:border-0" key={`${change.category}-${change.field}-${index}`}><strong>{change.change_type}: {change.category.replaceAll('_',' ')} · {change.field}</strong><div className="mono mt-1 break-all text-[10px] muted">{JSON.stringify(change.before)} → {JSON.stringify(change.after)}</div></div>)}</div>:<p className="mt-2 text-xs muted">No protocol changes.</p>}
          <p className="mt-2 text-xs muted">{diff.data.interpretation}</p>
        </div>}
      </div>}

      {/* Templates Reference */}
      {templates.data&&templates.data.length>0&&<JsonDisclosure label="Browse reusable research protocol templates" value={templates.data}/>}

      <div className="mt-4 text-xs muted">{current.scientific_boundary}</div>
    </>:<EmptyState title="Experiment protocol unavailable">No protocol registry response is available.</EmptyState>}
  </Card>;
}

export function PipelineVersionPanel({experimentId}:{experimentId:string}){
  const pipeline=useQuery({queryKey:['experiment-pipeline',experimentId],queryFn:()=>qh.experimentPipeline(experimentId),retry:false});
  const versions=useQuery({queryKey:['pipelines'],queryFn:qh.pipelines,enabled:pipeline.data?.status==='AVAILABLE'});
  const [compareTo,setCompareTo]=useState('');
  const current=pipeline.data?.status==='AVAILABLE'?pipeline.data.pipeline_version:null;
  const diff=useQuery({
    queryKey:['pipeline-diff',current?.pipeline_version_id,compareTo],
    queryFn:()=>qh.pipelineDiff(current!.pipeline_version_id,compareTo),
    enabled:Boolean(current&&compareTo),
    retry:false,
  });
  return <Card className="mt-5" title="Pipeline Version" description="The immutable computational definition recorded for this experiment.">
    <ErrorBanner error={(pipeline.error as Error)?.message||(versions.error as Error)?.message||(diff.error as Error)?.message}/>
    {pipeline.isLoading?<Loading/>:pipeline.data?.status==='LEGACY_UNRESOLVED'?<EmptyState title="Pipeline version unavailable">{pipeline.data.reason} Historical configuration remains accessible, but no version is fabricated.</EmptyState>:current?<>
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={current.status}/><Badge tone="purple">{current.version}</Badge><span className="text-sm font-semibold">{current.pipeline_name}</span><span className="mono text-[10px] muted" title={current.definition_fingerprint}>{current.definition_fingerprint.slice(0,20)}…</span></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div><span className="metric-label">VERSION ID</span><strong className="mono block break-all text-[10px]">{current.pipeline_version_id}</strong></div>
        <div><span className="metric-label">SCHEMA</span><strong className="block text-xs">{current.schema_version}</strong></div>
        <div><span className="metric-label">USED BY</span><strong className="block text-xs">{current.usage_count} experiment{current.usage_count===1?'':'s'}</strong></div>
        <div><span className="metric-label">PUBLISHED</span><strong className="block text-xs">{current.published_at?dateTime(current.published_at):'Draft'}</strong></div>
      </div>
      <ol className="mt-4 grid gap-2 md:grid-cols-2">{current.stages.map(stage=><li className="rounded-xl border p-3" key={stage.stage_id}><div className="flex items-center justify-between gap-2"><strong className="text-sm">{stage.stage_order}. {stage.stage_name}</strong><Badge tone="blue">{stage.stage_type.replaceAll('_',' ')}</Badge></div><span className="mono mt-1 block truncate text-[10px] muted" title={stage.fingerprint}>{stage.fingerprint.slice(0,18)}…</span><JsonDisclosure label="Inspect stage configuration" value={stage.configuration}/></li>)}</ol>
      <JsonDisclosure label="Open canonical pipeline definition" value={current.canonical_definition}/>
      {(versions.data?.filter(item=>item.pipeline_version_id!==current.pipeline_version_id).length||0)>0&&<div className="mt-4 rounded-xl border p-4">
        <div className="metric-label">COMPARE VERSION</div>
        <Select className="mt-2" value={compareTo} onChange={event=>setCompareTo(event.target.value)}><option value="">Select a Pipeline Version</option>{versions.data?.filter(item=>item.pipeline_version_id!==current.pipeline_version_id).map(item=><option key={item.pipeline_version_id} value={item.pipeline_version_id}>{item.pipeline_name} · {item.version}</option>)}</Select>
        {diff.isLoading&&<Loading/>}
        {diff.data&&<div className="mt-3"><div className="flex flex-wrap gap-2">{diff.data.stage_summaries.map(item=><Badge key={item.stage} tone={item.status==='Unchanged'?'green':item.status==='Removed'?'amber':'blue'}>{item.stage.replaceAll('_',' ')} · {item.status}</Badge>)}</div>{diff.data.changes.length?<div className="mt-3 max-h-56 space-y-2 overflow-y-auto">{diff.data.changes.map((change,index)=><div className="border-b pb-2 text-xs last:border-0" key={`${change.stage}-${change.field}-${index}`}><strong>{change.change_type}: {change.stage.replaceAll('_',' ')}{change.field?` · ${change.field}`:''}</strong><div className="mono mt-1 break-all text-[10px] muted">{JSON.stringify(change.before)} → {JSON.stringify(change.after)}</div></div>)}</div>:<p className="mt-2 text-xs muted">No computational changes.</p>}<p className="mt-2 text-xs muted">{diff.data.interpretation}</p></div>}
      </div>}
      <div className="mt-4 text-xs muted">{current.scientific_boundary}</div>
    </>:<EmptyState title="Pipeline version unavailable">No pipeline registry response is available.</EmptyState>}
  </Card>
}

export function ExperimentLineagePanel({experimentId}:{experimentId:string}){
  const [depth,setDepth]=useState('3');
  const [direction,setDirection]=useState<'ancestors'|'descendants'|'both'>('both');
  const [includeArtifacts,setIncludeArtifacts]=useState(true);
  const [includeEvidence,setIncludeEvidence]=useState(true);
  const [selected,setSelected]=useState<LineageNode|null>(null);
  const [showAll,setShowAll]=useState(false);
  const lineage=useQuery({
    queryKey:['experiment-lineage',experimentId,depth,direction,includeArtifacts,includeEvidence],
    queryFn:()=>qh.lineage(experimentId,{depth,direction,include_artifacts:includeArtifacts,include_evidence:includeEvidence}),
    retry:false,
  });
  const value=lineage.data;
  const issueCount=value?value.integrity.missing_references.length+value.integrity.orphaned_edges.length+value.integrity.invalid_edges.length+value.integrity.fingerprint_mismatches.length+value.integrity.cycles.length:0;
  const visibleNodes=value?.nodes.slice(0,showAll?value.nodes.length:60)||[];
  const layers=Array.from(new Set(visibleNodes.map(node=>node.depth))).sort((a,b)=>a-b);
  return <Card className="mt-5" title="Lineage / Provenance" description="Trace explicit persisted relationships from datasets and parent experiments through executions, models, evidence, and packages.">
    <ErrorBanner error={(lineage.error as Error)?.message}/>
    <div className="controls mb-4">
      <label className="field"><span>Depth</span><Select value={depth} onChange={event=>setDepth(event.target.value)}><option value="1">1</option><option value="3">3</option><option value="6">6</option><option value="all">All (bounded)</option></Select></label>
      <label className="field"><span>Direction</span><Select value={direction} onChange={event=>setDirection(event.target.value as typeof direction)}><option value="both">Origins + descendants</option><option value="ancestors">Origins only</option><option value="descendants">Descendants only</option></Select></label>
      <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={includeEvidence} onChange={event=>setIncludeEvidence(event.target.checked)}/>Evidence</label>
      <label className="flex items-center gap-2 text-xs"><input type="checkbox" checked={includeArtifacts} onChange={event=>setIncludeArtifacts(event.target.checked)}/>Artifacts</label>
    </div>
    {lineage.isLoading?<Loading/>:!value?<EmptyState title="Lineage not available for this experiment">No provenance snapshot could be loaded.</EmptyState>:<>
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={value.status}/><Badge tone="blue">{value.summary.node_count} NODES</Badge><Badge tone="blue">{value.summary.edge_count} EDGES</Badge><span className="mono text-[10px] muted" title={value.lineage_fingerprint}>{value.lineage_fingerprint.slice(0,20)}…</span></div>
      {value.status==='PARTIAL'&&<Notice tone="amber">Partial provenance — some historical relationships were reconstructed from explicit persisted identifiers.</Notice>}
      {value.status==='LEGACY_UNRESOLVED'&&<Notice tone="amber">Partial provenance — some historical references are unavailable. This is not a model failure.</Notice>}
      {(value.status==='INTEGRITY_REVIEW'||issueCount>0)&&<Notice tone="amber">Provenance integrity requires review. {issueCount} structured issue{issueCount===1?'':'s'} detected.</Notice>}
      {value.nodes.length<=1?<EmptyState title="Lineage not available for this experiment">No supported persisted relationships are available yet.</EmptyState>:<div className="mt-4 overflow-x-auto">
        <div className="flex min-w-max items-start gap-4 pb-2">{layers.map((layer,index)=><div className="w-56" key={layer}>
          <div className="mb-2 flex items-center gap-2"><span className="metric-label">{index===0?'ORIGIN':'DEPTH '+layer}</span>{index>0&&<span className="muted">→</span>}</div>
          <div className="space-y-2">{visibleNodes.filter(node=>node.depth===layer).map(node=><button key={node.id} onClick={()=>setSelected(node)} className={`w-full rounded-xl border p-3 text-left transition ${selected?.id===node.id?'border-primary bg-primary/5':'hover:border-primary/40'}`}>
            <div className="flex items-center justify-between gap-2"><Badge tone={lineageTone(node.object_type)}>{node.object_type.replaceAll('_',' ')}</Badge>{!node.exists&&<Badge tone="amber">unresolved</Badge>}</div>
            <strong className="mt-2 block truncate text-xs">{node.label}</strong><span className="mono mt-1 block truncate text-[10px] muted">{node.object_id}</span>
          </button>)}</div>
        </div>)}</div>
      </div>}
      {value.nodes.length>60&&<Button variant="outline" className="mt-3" onClick={()=>setShowAll(current=>!current)}>{showAll?'Show bounded view':`Show all ${value.nodes.length} nodes`}</Button>}
      <div className="mt-4 two-grid">
        <div className="rounded-xl border p-4"><div className="metric-label">RELATIONSHIPS</div><div className="mt-2 max-h-56 space-y-2 overflow-y-auto">{value.edges.slice(0,80).map(edge=><div className="border-b pb-2 text-xs last:border-0" key={edge.id}><div className="flex justify-between gap-2"><strong>{edge.relationship_type.replaceAll('_',' ')}</strong><span className="muted">{edge.capture_state.replaceAll('_',' ')}</span></div><span className="mono text-[10px] muted">{edge.source_node_id.slice(0,8)} → {edge.target_node_id.slice(0,8)}</span></div>)}</div></div>
        <div className="rounded-xl border p-4"><div className="metric-label">SELECTED NODE</div>{selected?<div className="mt-2 space-y-2 text-xs"><div><strong>{selected.object_type.replaceAll('_',' ')}</strong><span className="mono block break-all text-[10px]">{selected.object_id}</span></div><div className="flex justify-between"><span className="muted">Status</span><span>{selected.status||'not recorded'}</span></div><div className="flex justify-between"><span className="muted">Version</span><span>{selected.version||'not recorded'}</span></div><div><span className="muted">Fingerprint</span><span className="mono block break-all text-[10px]">{selected.fingerprint||'not recorded'}</span></div><div className="flex justify-between"><span className="muted">Recorded</span><span>{selected.created_at?dateTime(selected.created_at):'not recorded'}</span></div></div>:<p className="mt-2 text-xs muted">Select a node to inspect its identity, version, fingerprint, and status.</p>}</div>
      </div>
      <div className="mt-4 flex items-center gap-2 text-xs muted"><GitBranch size={14}/>Lineage records traceability metadata; it does not establish causality, scientific validity, or model quality.</div>
      <JsonDisclosure label="Open lineage integrity and machine-readable graph" value={{summary:value.summary,integrity:value.integrity,roots:value.roots,nodes:value.nodes,edges:value.edges}}/>
    </>}
  </Card>
}

export function ResearchEvidencePackagePanel({experimentId}:{experimentId:string}){
  const qc=useQueryClient();
  const preflight=useQuery({
    queryKey:['evidence-package-preflight',experimentId],
    queryFn:()=>qh.evidencePackagePreflight(experimentId),
    retry:false,
  });
  const packageQuery=useQuery({
    queryKey:['evidence-package',experimentId],
    queryFn:()=>qh.evidencePackage(experimentId),
    retry:false,
  });
  const generate=useMutation({
    mutationFn:()=>qh.createEvidencePackage(experimentId),
    onSuccess:value=>qc.setQueryData(['evidence-package',experimentId],value),
  });
  const [inspect,setInspect]=useState(false);
  const value=packageQuery.data;
  const categories=value?Object.entries(value.evidence_inventory):[];
  const readiness=preflight.data;
  return <Card className="mt-5" title="Research Evidence Package" description="Immutable, machine-readable manifest of the persisted evidence associated with this experiment.">
    <ErrorBanner error={(preflight.error as Error)?.message||(generate.error as Error)?.message}/>
    {!value?<div>
      <p className="text-sm muted">{packageQuery.isLoading?'Checking for an existing package…':'No package has been generated for the current evidence state.'}</p>
      {readiness&&<div className="mt-3 rounded-xl border p-4">
        <div className="flex flex-wrap items-center gap-2"><span className="metric-label">PACKAGE PREFLIGHT</span><StatusBadge value={readiness.package_status}/><Badge tone={readiness.feasible?'green':'amber'}>{readiness.feasible?'CREATION READY':'CREATION BLOCKED'}</Badge></div>
        <p className="mt-2 text-xs muted">{Object.values(readiness.evidence_inventory).filter(item=>item.status==='available').length} evidence categories available · {readiness.missing_evidence.length} recorded gaps.</p>
        {readiness.blockers.length>0&&<Notice tone="amber">{readiness.blockers.map(item=>item.message||item.code).join('; ')}</Notice>}
        {readiness.warnings.length>0&&<JsonDisclosure label="Inspect preflight warnings" value={readiness.warnings}/>}
      </div>}
      <Button className="mt-3" disabled={packageQuery.isLoading||preflight.isLoading||!readiness?.feasible||generate.isPending} onClick={()=>generate.mutate()}>{generate.isPending?'Generating package…':'Generate package'}</Button>
      <p className="mt-2 text-[11px] muted">Package creation is a deliberate archival action. It does not train models or recompute scientific evidence.</p>
    </div>:<>
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={value.package_status}/><Badge tone={value.artifact.immutable?'green':'amber'}>{value.artifact.immutable?'IMMUTABLE ARTIFACT':'INTEGRITY UNAVAILABLE'}</Badge><span className="text-xs muted">{dateTime(value.created_at)}</span></div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div><span className="metric-label">PACKAGE ID</span><strong className="mono block text-xs">{value.package_id}</strong></div>
        <div><span className="metric-label">FINGERPRINT</span><strong className="mono block text-xs" title={value.package_fingerprint}>{value.package_fingerprint.slice(0,20)}…</strong></div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{categories.map(([name,entry])=><div className="rounded-xl border p-3" key={name}><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold">{name.replaceAll('_',' ')}</span><StatusBadge value={entry.status}/></div><small className="muted">{entry.record_count} persisted record{entry.record_count===1?'':'s'}</small></div>)}</div>
      {value.evidence_gaps.length>0&&<Notice tone="amber">{value.evidence_gaps.length} evidence categor{value.evidence_gaps.length===1?'y is':'ies are'} unavailable, incomplete, or limited. This is an evidence state, not a quality score.</Notice>}
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={generate.isPending||preflight.isLoading||!readiness?.feasible} onClick={()=>generate.mutate()}><RotateCcw size={13}/>{generate.isPending?'Refreshing…':'Refresh package'}</Button><Button variant="outline" onClick={()=>setInspect(current=>!current)}>{inspect?'Close package':'Inspect package'}</Button><Button variant="outline" onClick={()=>qh.downloadEvidencePackage(experimentId,value.package_id)}><Download size={13}/>Download JSON</Button></div>
      {inspect&&<div className="mt-4"><div className="two-grid"><div className="rounded-xl border p-4"><div className="metric-label">PROVENANCE</div><p className="mt-2 text-xs">Runs: {value.provenance.run_ids.length} · Referenced artifacts: {value.provenance.artifact_ids.length}</p><p className="mt-1 mono text-[10px] break-all">Artifact {value.integrity.artifact_id}</p></div><div className="rounded-xl border p-4"><div className="metric-label">LIMITATIONS</div><ul className="mt-2 list-disc pl-4 text-xs">{value.limitations.map(item=><li key={item}>{item}</li>)}</ul></div></div><JsonDisclosure label="Open full machine-readable package" value={value}/></div>}
    </>}
  </Card>
}

const auditCategoryTone=(category:string):'blue'|'green'|'amber'|'red'|'purple'=>{
  switch(category.toUpperCase()){
    case 'EXPERIMENT':
    case 'MODEL':
      return 'purple';
    case 'DATASET':
    case 'EVIDENCE':
      return 'green';
    case 'RUN':
    case 'JOB':
    case 'PIPELINE':
      return 'blue';
    case 'ARTIFACT':
    case 'CONFIGURATION':
      return 'amber';
    default:
      return 'blue';
  }
};

export function ScientificAuditTimelinePanel({experimentId}:{experimentId:string}){
  const [selectedCategory,setSelectedCategory]=useState<string>('all');
  const [expandedEventId,setExpandedEventId]=useState<string|null>(null);

  const timeline=useQuery({
    queryKey:['experiment-audit',experimentId,selectedCategory],
    queryFn:()=>qh.experimentAudit(experimentId,selectedCategory),
    retry:false,
  });
  const integrity=useQuery({
    queryKey:['audit-integrity',experimentId],
    queryFn:()=>qh.auditIntegrity('experiment',experimentId),
    retry:false,
  });

  const value=timeline.data;
  const categories=['all','EXPERIMENT','RUN','JOB','PIPELINE','MODEL','EVIDENCE','ARTIFACT','CONFIGURATION'];

  return <Card className="mt-5" title="Scientific Audit Timeline" description="Immutable, chronological record of research-platform events recording operations and resulting persisted state.">
    <ErrorBanner error={(timeline.error as Error)?.message}/>
    <ErrorBanner error={(integrity.error as Error)?.message}/>
    <div className="controls mb-4">
      <label className="field"><span>Filter Category</span><Select value={selectedCategory} onChange={event=>setSelectedCategory(event.target.value)}>{categories.map(cat=><option key={cat} value={cat}>{cat==='all'?'All categories':cat.replaceAll('_',' ')}</option>)}</Select></label>
    </div>

    {timeline.isLoading?<Loading/>:!value?<EmptyState title="Audit timeline not available for this experiment">No audit snapshot could be loaded.</EmptyState>:<>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={(integrity.data?.valid ?? (value.integrity_status==='VERIFIED'))?'green':'amber'}>{(integrity.data?.valid ?? (value.integrity_status==='VERIFIED'))?'INTEGRITY VERIFIED':'INTEGRITY WARNING'}</Badge>
          <Badge tone="blue">{value.total_events} RECORDED EVENT{value.total_events===1?'':'S'}</Badge>
        </div>
        <Button variant="outline" onClick={()=>qh.experimentAuditExport(experimentId)}><Download size={13}/>Export Audit JSON</Button>
      </div>

      {integrity.data?.issues.length? <Notice tone="amber">Audit integrity warning: {integrity.data.issues.map(i=>i.message).join('; ')}</Notice>:null}
      {value.legacy_disclaimer&&<Notice tone="blue">{value.legacy_disclaimer}</Notice>}

      {value.events.length===0?<EmptyState title="No audit events found">No recorded platform events match the active category filter.</EmptyState>:<div className="mt-4 space-y-3">
        {value.events.map(event=>{
          const isExpanded=expandedEventId===event.id;
          return <div key={event.id} className="rounded-xl border p-3.5 transition hover:border-primary/30">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={auditCategoryTone(event.event_category)}>{event.event_category}</Badge>
                <strong className="text-xs font-semibold">{event.event_type.replaceAll('_',' ')}</strong>
                <span className="mono text-[10px] muted">{event.object_type}: {shortId(event.object_id)}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs muted">{dateTime(event.occurred_at)}</span>
                <Button variant="ghost" className="px-2 py-1 text-xs" onClick={()=>setExpandedEventId(isExpanded?null:event.id)}>{isExpanded?'Hide':'Details'}</Button>
              </div>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] muted">
              <span>Actor: {event.actor_type}</span>
              <span>·</span>
              <span>Source: {event.source_component}</span>
              {event.operation_key&&<><span>·</span><span className="mono truncate max-w-xs" title={event.operation_key}>Op: {event.operation_key}</span></>}
            </div>

            {isExpanded&&<div className="mt-3 border-t pt-3 space-y-2 text-xs">
              <div className="grid gap-2 sm:grid-cols-2">
                <div><span className="metric-label">EVENT FINGERPRINT (SHA-256)</span><span className="mono block truncate text-[10px] text-primary" title={event.event_fingerprint}>{event.event_fingerprint}</span></div>
                <div><span className="metric-label">PREVIOUS EVENT POINTER</span><span className="mono block truncate text-[10px] muted" title={event.previous_event_fingerprint||'Chain root'}>{event.previous_event_fingerprint||'(chain root)'}</span></div>
              </div>
              {(event.before_fingerprint||event.after_fingerprint)&&<div className="grid gap-2 sm:grid-cols-2">
                <div><span className="metric-label">STATE BEFORE</span><span className="mono block truncate text-[10px] muted" title={event.before_fingerprint||'None'}>{event.before_fingerprint||'(none)'}</span></div>
                <div><span className="metric-label">STATE AFTER</span><span className="mono block truncate text-[10px] muted" title={event.after_fingerprint||'None'}>{event.after_fingerprint||'(none)'}</span></div>
              </div>}
              {event.parent_object_id&&<div className="text-[11px] muted">Parent: {event.parent_object_type} · {event.parent_object_id}</div>}
              <JsonDisclosure label="Inspect structured event metadata" value={event.metadata}/>
            </div>}
          </div>;
        })}
      </div>}

      <div className="mt-4 flex items-center gap-2 text-xs muted">
        <History size={14}/>The Scientific Audit Timeline records platform events and persisted state transitions. It does not establish scientific validity, causal relationships, model quality, or performance.
      </div>
    </>}
  </Card>;
}


type ResearchReportSectionProps={
  id:string;
  isAuthenticated:boolean;
  savedReport?:SavedResearchReport;
  savedLoading:boolean;
  pdfBusy:boolean;
  pdfSuccess:boolean;
  saveBusy:boolean;
  saveSuccess:boolean;
  error?:string;
  onDownload:()=>void;
  onSave:()=>void;
  onSignIn:()=>void;
};

export function ResearchReportSection({id,isAuthenticated,savedReport,savedLoading,pdfBusy,pdfSuccess,saveBusy,saveSuccess,error,onDownload,onSave,onSignIn}:ResearchReportSectionProps){
  return <section className="mt-5" aria-label="Research Report">
    <Card title="Research Report" description="Export the persisted research evidence for this experiment as a formatted PDF.">
      <p className="text-sm muted">Generate a professionally formatted PDF containing the persisted results, evidence, provenance, limitations, and reproducibility information for this experiment.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <MetricCard label="STATUS" value={pdfBusy?'Generating report…':'PDF report available'} detail="Generated read-only by the backend"/>
        <MetricCard label="EXPERIMENT ID" value={shortId(id)} detail="Included in every page footer"/>
        <MetricCard label="REPORT SCOPE" value="Persisted evidence" detail="No training or scientific recomputation"/>
      </div>
      <ErrorBanner error={error}/>
      {pdfSuccess&&<Notice tone="blue">PDF downloaded successfully.</Notice>}
      {saveSuccess&&<Notice tone="blue">Research report saved to My Research.</Notice>}
      <div className="mt-4 flex flex-wrap gap-2"><Button disabled={pdfBusy} onClick={onDownload}><Download size={14}/>{pdfBusy?'Generating report…':'Download PDF Report'}</Button>{isAuthenticated?<Button variant="outline" disabled={Boolean(savedReport)||savedLoading||saveBusy} onClick={onSave}><BookmarkPlus size={14}/>{saveBusy?'Saving…':savedReport?'Saved to My Research':'Save to My Research'}</Button>:<Button variant="outline" onClick={onSignIn}><LogIn size={14}/>Sign in to save</Button>}</div>
      {savedReport&&<p className="mt-3 text-xs muted">Saved to My Research {dateTime(savedReport.saved_at)} · <Link className="text-primary hover:underline" to={`/my-research/reports/${savedReport.saved_report_id}`}>View saved report</Link></p>}
      {!isAuthenticated&&<p className="mt-3 text-xs muted">Sign in with Google or GitHub to save this report to My Research. Guest PDF download remains available.</p>}
      <p className="mt-3 text-xs muted">Research use only. The report does not establish diagnosis, clinical validation, causality, statistical significance, or quantum advantage.</p>
    </Card>
  </section>;
}

export function ExperimentDetail(){
  const {id=''}=useParams();
  const {session,isAuthenticated,leaveGuestMode}=useAuth();
  const queryClient=useQueryClient();
  const accessToken=session?.access_token||'';
  const result=useQuery({queryKey:['experiment',id],queryFn:()=>qh.experiment(id),enabled:Boolean(id),refetchInterval:query=>['queued','running','cancel_requested'].includes(query.state.data?.experiment.status||'')?5000:false});
  const action=useMutation({mutationFn:(format:'html'|'json')=>qh.report(id,format)});
  const pdfAction=useMutation({mutationFn:()=>qh.report(id,'pdf')});
  const savedState=useQuery({queryKey:['saved-research-report-state',id],queryFn:()=>qh.savedResearchReports(accessToken,id),enabled:Boolean(isAuthenticated&&accessToken&&id),retry:false});
  const savedReport=savedState.data?.[0];
  const saveReport=useMutation({mutationFn:()=>qh.saveResearchReport(id,accessToken),onSuccess:async()=>{await Promise.all([queryClient.invalidateQueries({queryKey:['saved-research-report-state',id]}),queryClient.invalidateQueries({queryKey:['saved-research-reports']})])}});
  const [expanded,setExpanded]=useState<string|null>(null);
  const detail=result.data;
  if(result.isLoading)return <div><PageHeader eyebrow="Research Studio · Evidence" title="Experiment detail" description="Loading the selected research record."/><Loading/></div>;
  if(result.error||!detail)return <div><PageHeader eyebrow="Research Studio · Evidence" title="Experiment not found" description="The selected research record could not be loaded."/><ErrorBanner error={(result.error as Error)?.message}/><Link className="btn btn-outline mt-4" to="/experiments"><ArrowLeft size={13}/>Back to registry</Link></div>;
  return <div>
    <PageHeader eyebrow="Research Studio · Evidence" title={detail.experiment.name||`Experiment ${shortId(id)}`} description="Inspect provenance, job state, measured model records and the exact configuration behind one Q‑Health research experiment." actions={<Link className="btn btn-outline" to="/experiments"><ArrowLeft size={13}/>All experiments</Link>}/>
    <StageNav current="/experiments"/>
    <WorkbenchRail items={[{label:'Status',value:detail.experiment.status.replaceAll('_',' '),detail:'Backend experiment state',tone:detail.experiment.status==='completed'?'green':'amber'},{label:'Models',value:detail.models.length,detail:'Persisted model records',tone:'purple'},{label:'Ready models',value:detail.models.filter(model=>model.status==='ready').length,detail:'Measured evidence available',tone:'green'},{label:'Jobs',value:detail.jobs.length,detail:'Execution records',tone:'blue'}]}/>
    <PipelineFlow items={[
      {label:'Configured',detail:'Dataset, split and seed',status:'complete'},
      {label:'Queued',detail:'Backend execution record',status:detail.jobs.length?'complete':'waiting'},
      {label:'Trained',detail:'Persisted model outputs',status:detail.models.length?'complete':'waiting'},
      {label:'Measured',detail:'Held-out metrics',status:detail.models.some(model=>Boolean(model.metrics.test))?'complete':'waiting'},
      {label:'Reported',detail:'Evidence export available',status:detail.models.length?'current':'waiting'}
    ]}/>
    <ErrorBanner error={(action.error as Error)?.message}/>
    <Card className="mt-5" title="Experiment context" description="A drill-down evidence surface modeled on TICTAC-style research detail views.">
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={detail.experiment.status}/><Badge tone={detail.experiment.summary.experiment_kind==='precomputed_verified_demo'?'blue':'green'}>{detail.experiment.summary.experiment_kind==='precomputed_verified_demo'?'PRECOMPUTED VERIFIED DEMO EXPERIMENT':'LIVE RESEARCH EXPERIMENT'}</Badge><span className="text-xs muted">{dateTime(detail.experiment.created_at)}</span><span className="mono text-xs muted">Dataset {shortId(detail.experiment.dataset_id)}</span></div>
      <div className="mt-4 grid gap-4 md:grid-cols-3"><MetricCard label="MODELS" value={detail.models.length} detail="Backend model records"/><MetricCard label="JOBS" value={detail.jobs.length} detail="Execution records"/><MetricCard label="PARENT" value={detail.experiment.parent_id?shortId(detail.experiment.parent_id):'None'} detail="Experiment lineage"/></div>
      <div className="mt-4 flex flex-wrap gap-2"><Link className="btn btn-outline" to="/comparison">Open comparison →</Link></div>
    </Card>
    <FinalResearchEvidence detail={detail} reportBusy={action.isPending} onReport={format=>action.mutate(format)} packagePanel={<ResearchEvidencePackagePanel experimentId={id}/>}/>
    <ExperimentProtocolPanel experimentId={id}/>
    <PipelineVersionPanel experimentId={id}/>
    <ExperimentLineagePanel experimentId={id}/>
    <ScientificAuditTimelinePanel experimentId={id}/>
    <DatasetQualityPanel experimentId={id} datasetId={detail.experiment.dataset_id} />
    <BiomedicalSubgroupAnalysisPanel experimentId={id}/>
    <div className="mt-5"><Card title="Measured model records" description="Only measurements returned by the backend are displayed.">
      {detail.models.length?detail.models.map(model=><GlareHover key={model.id} className="border-b py-5 last:border-b-0"><article className="py-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-semibold">{modelLabels[model.model_type]}</h3><StatusBadge value={model.status}/></div><small className="muted">Model {shortId(model.id)} · {dateTime(model.created_at)}</small></div><button className="btn btn-ghost" onClick={()=>setExpanded(expanded===model.id?null:model.id)}>{expanded===model.id?'Collapse':'Inspect'}</button></div>{model.model_type==='hybrid_pennylane_torch'&&model.details.quantum&&<div className="mt-4 rounded-xl border p-4"><div className="metric-label">HYBRID EXECUTION EVIDENCE</div><div className="mt-3 grid gap-3 md:grid-cols-3"><div><span className="metric-label">FRAMEWORKS</span><strong className="block">{model.details.quantum.framework} + {model.details.quantum.classical_framework}</strong></div><div><span className="metric-label">EXECUTION</span><strong className="block">{model.details.quantum.execution_kind}</strong></div><div><span className="metric-label">BACKEND</span><strong className="block">{model.details.quantum.backend}</strong></div><div><span className="metric-label">QUBITS / LAYERS</span><strong className="block">{model.details.quantum.qubits} / {model.details.quantum.quantum_layers}</strong></div><div><span className="metric-label">PROBABILITY</span><strong className="block">Measured positive-class output</strong></div><div><span className="metric-label">HARDWARE</span><strong className="block">Not implemented</strong></div></div><Notice tone="amber">Quantum advantage: not established. Operating threshold is selected from out-of-fold validation evidence.</Notice></div>}{model.metrics.test&&<div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.1fr]"><div className="rounded-xl border p-4"><div className="metric-label">HELD-OUT METRICS</div><div className="mt-3 space-y-1">{(['sensitivity','specificity','roc_auc','f1','accuracy','precision','recall'] as const).map(k=><div className="flex justify-between border-b py-1.5 last:border-0" key={k}><span className="text-xs muted">{k}</span><strong className="mono text-xs">{metric(model.metrics.test?.[k],k!=='roc_auc')}</strong></div>)}</div></div><div className="rounded-xl border p-4"><div className="metric-label">RUNTIME</div><div className="mt-3 space-y-1 text-xs">{[['Final training',seconds(model.metrics.timing?.final_training_seconds)],['CV total',seconds(model.metrics.timing?.cv_total_seconds)],['Test inference',seconds(model.metrics.timing?.test_inference_seconds_per_sample)+'/sample']].map(x=><div className="flex justify-between border-b py-1.5 last:border-0" key={String(x[0])}><span className="muted">{x[0]}</span><strong>{x[1]}</strong></div>)}</div></div></div>}{expanded===model.id&&<><ModelCardPanel model={model}/><CalibrationLaboratory model={model} />
                            <ThresholdAnalysis model={model} /><QuantumDiagnostics model={model} /><JsonDisclosure label="Model identity, provenance, metrics and limitations" value={{details:model.details,metrics:model.metrics}}/></>}</article></GlareHover>):<EmptyState title="No model records">Model records appear when the backend training job completes or records a failure.</EmptyState>}
    </Card></div>
    <div className="two-grid mt-5"><Card title="Experiment provenance"><JsonDisclosure label="Summary / split / provenance" value={detail.experiment.summary}/><JsonDisclosure label="Exact training configuration" value={detail.experiment.config}/></Card><Card title="Execution records"><div className="space-y-2">{detail.jobs.map(job=><div className="rounded-xl border p-3" key={job.id}><div className="flex justify-between"><StatusBadge value={job.status}/><span className="text-xs muted">{job.progress}%</span></div><p className="mt-1 text-xs">{job.state}</p>{job.errors.length>0&&<JsonDisclosure label="Recorded failures" value={job.errors}/>}</div>)}</div></Card></div>
    <AblationLaboratory experiment={detail.experiment} />
    <Notice tone="amber">Research prototype boundary: measured benchmark outputs do not establish clinical validation, diagnosis or treatment efficacy.</Notice>
    <ResearchReportSection id={id} isAuthenticated={isAuthenticated} savedReport={savedReport} savedLoading={savedState.isLoading} pdfBusy={pdfAction.isPending} pdfSuccess={pdfAction.isSuccess} saveBusy={saveReport.isPending} saveSuccess={saveReport.isSuccess} error={(pdfAction.error as Error)?.message||(savedState.error as Error)?.message||(saveReport.error as Error)?.message} onDownload={()=>pdfAction.mutate()} onSave={()=>saveReport.mutate()} onSignIn={leaveGuestMode}/>
  </div>
}
