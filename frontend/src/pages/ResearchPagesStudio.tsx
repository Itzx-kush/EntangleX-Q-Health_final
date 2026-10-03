import {Link,useNavigate,useParams} from 'react-router-dom';
import {useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {ArrowLeft,Copy,Download,ExternalLink,RotateCcw,Trash2} from 'lucide-react';
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
import type {Experiment} from '../types/qhealth';
import {GlareHover} from '../components/reactbits';
import {DistributionStrip,PipelineFlow,WorkbenchRail} from '../components/TremorWorkbench';
import {ModelCardPanel} from '../components/ModelCardPanel';
import {useResearchRecorder} from '../research/useResearchHistory';
import {experimentActivity} from '../research/historyRecords';

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

export function ResearchEvidencePackagePanel({experimentId}:{experimentId:string}){
  const qc=useQueryClient();
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
  return <Card className="mt-5" title="Research Evidence Package" description="Immutable, machine-readable manifest of the persisted evidence associated with this experiment.">
    <ErrorBanner error={(generate.error as Error)?.message}/>
    {!value?<div>
      <p className="text-sm muted">{packageQuery.isLoading?'Checking for an existing package…':'No package has been generated for the current evidence state.'}</p>
      <Button className="mt-3" disabled={packageQuery.isLoading||generate.isPending} onClick={()=>generate.mutate()}>{generate.isPending?'Running preflight…':'Generate package'}</Button>
    </div>:<>
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={value.package_status}/><Badge tone={value.artifact.immutable?'green':'amber'}>{value.artifact.immutable?'IMMUTABLE ARTIFACT':'INTEGRITY UNAVAILABLE'}</Badge><span className="text-xs muted">{dateTime(value.created_at)}</span></div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div><span className="metric-label">PACKAGE ID</span><strong className="mono block text-xs">{value.package_id}</strong></div>
        <div><span className="metric-label">FINGERPRINT</span><strong className="mono block text-xs" title={value.package_fingerprint}>{value.package_fingerprint.slice(0,20)}…</strong></div>
        <div><span className="metric-label">SOURCE</span><strong className="block text-sm">{value.source_context.type.replaceAll('_',' ')}</strong></div>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{categories.map(([name,entry])=><div className="rounded-xl border p-3" key={name}><div className="flex items-center justify-between gap-2"><span className="text-xs font-semibold">{name.replaceAll('_',' ')}</span><StatusBadge value={entry.status}/></div><small className="muted">{entry.record_count} persisted record{entry.record_count===1?'':'s'}</small></div>)}</div>
      {value.evidence_gaps.length>0&&<Notice tone="amber">{value.evidence_gaps.length} evidence categor{value.evidence_gaps.length===1?'y is':'ies are'} unavailable, incomplete, or limited. This is an evidence state, not a quality score.</Notice>}
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={generate.isPending} onClick={()=>generate.mutate()}><RotateCcw size={13}/>{generate.isPending?'Refreshing…':'Refresh package'}</Button><Button variant="outline" onClick={()=>setInspect(current=>!current)}>{inspect?'Close package':'Inspect package'}</Button><Button variant="outline" onClick={()=>qh.downloadEvidencePackage(experimentId,value.package_id)}><Download size={13}/>Download JSON</Button></div>
      {inspect&&<div className="mt-4"><div className="two-grid"><div className="rounded-xl border p-4"><div className="metric-label">PROVENANCE</div><p className="mt-2 text-xs">Runs: {value.provenance.run_ids.length} · Referenced artifacts: {value.provenance.artifact_ids.length}</p><p className="mt-1 mono text-[10px] break-all">Artifact {value.integrity.artifact_id}</p></div><div className="rounded-xl border p-4"><div className="metric-label">LIMITATIONS</div><ul className="mt-2 list-disc pl-4 text-xs">{value.limitations.map(item=><li key={item}>{item}</li>)}</ul></div></div><JsonDisclosure label="Open full machine-readable package" value={value}/></div>}
    </>}
  </Card>
}

export function ExperimentDetail(){
  const {id=''}=useParams();
  const result=useQuery({queryKey:['experiment',id],queryFn:()=>qh.experiment(id),enabled:Boolean(id),refetchInterval:query=>['queued','running','cancel_requested'].includes(query.state.data?.experiment.status||'')?5000:false});
  const action=useMutation({mutationFn:(format:'html'|'json')=>qh.report(id,format)});
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
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={action.isPending} onClick={()=>action.mutate('html')}><Download size={13}/>Export HTML</Button><Button variant="outline" disabled={action.isPending} onClick={()=>action.mutate('json')}><Download size={13}/>Export JSON</Button><Link className="btn btn-outline" to="/comparison">Open comparison →</Link></div>
    </Card>
    <ResearchEvidencePackagePanel experimentId={id}/>
    <div className="mt-5"><Card title="Measured model records" description="Only measurements returned by the backend are displayed.">
      {detail.models.length?detail.models.map(model=><GlareHover key={model.id} className="border-b py-5 last:border-b-0"><article className="py-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-semibold">{modelLabels[model.model_type]}</h3><StatusBadge value={model.status}/></div><small className="muted">Model {shortId(model.id)} · {dateTime(model.created_at)}</small></div><button className="btn btn-ghost" onClick={()=>setExpanded(expanded===model.id?null:model.id)}>{expanded===model.id?'Collapse':'Inspect'}</button></div>{model.model_type==='hybrid_pennylane_torch'&&model.details.quantum&&<div className="mt-4 rounded-xl border p-4"><div className="metric-label">HYBRID EXECUTION EVIDENCE</div><div className="mt-3 grid gap-3 md:grid-cols-3"><div><span className="metric-label">FRAMEWORKS</span><strong className="block">{model.details.quantum.framework} + {model.details.quantum.classical_framework}</strong></div><div><span className="metric-label">EXECUTION</span><strong className="block">{model.details.quantum.execution_kind}</strong></div><div><span className="metric-label">BACKEND</span><strong className="block">{model.details.quantum.backend}</strong></div><div><span className="metric-label">QUBITS / LAYERS</span><strong className="block">{model.details.quantum.qubits} / {model.details.quantum.quantum_layers}</strong></div><div><span className="metric-label">PROBABILITY</span><strong className="block">Measured positive-class output</strong></div><div><span className="metric-label">HARDWARE</span><strong className="block">Not implemented</strong></div></div><Notice tone="amber">Quantum advantage: not established. Operating threshold is selected from out-of-fold validation evidence.</Notice></div>}{model.metrics.test&&<div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.1fr]"><div className="rounded-xl border p-4"><div className="metric-label">HELD-OUT METRICS</div><div className="mt-3 space-y-1">{(['sensitivity','specificity','roc_auc','f1','accuracy','precision','recall'] as const).map(k=><div className="flex justify-between border-b py-1.5 last:border-0" key={k}><span className="text-xs muted">{k}</span><strong className="mono text-xs">{metric(model.metrics.test?.[k],k!=='roc_auc')}</strong></div>)}</div></div><div className="rounded-xl border p-4"><div className="metric-label">RUNTIME</div><div className="mt-3 space-y-1 text-xs">{[['Final training',seconds(model.metrics.timing?.final_training_seconds)],['CV total',seconds(model.metrics.timing?.cv_total_seconds)],['Test inference',seconds(model.metrics.timing?.test_inference_seconds_per_sample)+'/sample']].map(x=><div className="flex justify-between border-b py-1.5 last:border-0" key={String(x[0])}><span className="muted">{x[0]}</span><strong>{x[1]}</strong></div>)}</div></div></div>}{expanded===model.id&&<><ModelCardPanel model={model}/><CalibrationLaboratory model={model} />
                            <ThresholdAnalysis model={model} /><QuantumDiagnostics model={model} /><JsonDisclosure label="Model identity, provenance, metrics and limitations" value={{details:model.details,metrics:model.metrics}}/></>}</article></GlareHover>):<EmptyState title="No model records">Model records appear when the backend training job completes or records a failure.</EmptyState>}
    </Card></div>
    <div className="two-grid mt-5"><Card title="Experiment provenance"><JsonDisclosure label="Summary / split / provenance" value={detail.experiment.summary}/><JsonDisclosure label="Exact training configuration" value={detail.experiment.config}/></Card><Card title="Execution records"><div className="space-y-2">{detail.jobs.map(job=><div className="rounded-xl border p-3" key={job.id}><div className="flex justify-between"><StatusBadge value={job.status}/><span className="text-xs muted">{job.progress}%</span></div><p className="mt-1 text-xs">{job.state}</p>{job.errors.length>0&&<JsonDisclosure label="Recorded failures" value={job.errors}/>}</div>)}</div></Card></div>
    <AblationLaboratory experiment={detail.experiment} />
    <Notice tone="amber">Research prototype boundary: measured benchmark outputs do not establish clinical validation, diagnosis or treatment efficacy.</Notice>
  </div>
}
