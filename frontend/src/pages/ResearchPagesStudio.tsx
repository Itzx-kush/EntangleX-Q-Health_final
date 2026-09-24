import {Link,useNavigate,useParams} from 'react-router-dom';
import {useEffect,useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {ArrowLeft,Copy,Download,ExternalLink,RotateCcw} from 'lucide-react';
import {Button,Card,Select,Badge} from '../components/ui';
import {EmptyState,ErrorBanner,JsonDisclosure,Loading,MetricCard,Notice,PageHeader,StatusBadge} from '../components/Shared';
import {StageNav} from './ResearchPagesCore';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {dateTime,metric,modelLabels,seconds,shortId} from '../utils/format';
import type {Experiment} from '../types/qhealth';
import {GlareHover} from '../components/reactbits';
import {RegistryControls} from '../components/RegistryControls';

export function Experiments(){
  const list=useQuery({queryKey:['experiments'],queryFn:qh.experiments,refetchInterval:5000});
  const qc=useQueryClient();
  const {update}=useDraft();
  const navigate=useNavigate();
  const [query,setQuery]=useState('');
  const [status,setStatus]=useState('all');
  const [page,setPage]=useState(0);
  const [selected,setSelected]=useState<Experiment|null>(null);
  const rerun=useMutation({mutationFn:(id:string)=>qh.rerun(id),onSuccess:r=>{qc.invalidateQueries({queryKey:['experiments']});navigate('/experiments/'+r.experiment.id)}});
  const statuses=Array.from(new Set((list.data||[]).map(e=>e.status)));
  const rows=(list.data||[]).filter(e=>{
    const hay=(e.id+' '+e.status+' '+e.dataset_id+' '+(e.config.models||[]).join(' ')).toLowerCase();
    return hay.includes(query.toLowerCase())&&(status==='all'||e.status===status);
  });
  const sortedRows=rows.slice().sort((a,b)=>b.created_at.localeCompare(a.created_at)||b.id.localeCompare(a.id));
  const pages=Math.max(1,Math.ceil(sortedRows.length/10));
  const safePage=Math.min(page,pages-1);
  const visibleRows=sortedRows.slice(safePage*10,(safePage+1)*10);
  useEffect(()=>setPage(0),[query,status]);
  return <div>
    <PageHeader eyebrow="Research Studio · Registry" title="Experiments" description="Preserve every research decision: dataset reference, model set, seeds, execution state, measured output and limitations." actions={<Link className="btn btn-outline" to="/training">Start in Model Lab <RotateCcw size={13}/></Link>}/>
    <StageNav current="/experiments"/>
    <ErrorBanner error={(list.error as Error)?.message||(rerun.error as Error)?.message}/>
    <div className="stat-grid my-5">
      <MetricCard label="RECORDED" value={list.data?.length??'—'} detail="Backend experiment records"/>
      <MetricCard label="VISIBLE" value={rows.length} detail="Current registry filter"/>
      <MetricCard label="ACTIVE FILTER" value={status==='all'?'All states':status.replaceAll('_',' ')} detail="Status"/>
      <MetricCard label="REPRODUCIBILITY" value="Tracked" detail="Seed + configuration retained"/>
    </div>
    <Card title="Experiment registry" description="The main research landscape: searchable, filterable and drillable like a biomedical evidence dashboard.">
      <div className="controls mb-4">
        <label className="field min-w-[240px] flex-1"><span>Search</span><input className="input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Experiment, dataset, model…"/></label>
        <label className="field min-w-[180px]"><span>Status</span><Select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All states</option>{statuses.map(s=><option value={s} key={s}>{s.replaceAll('_',' ')}</option>)}</Select></label>
      </div>
      {list.isLoading?<Loading/>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Experiment</th><th>Created</th><th>Status</th><th>Models</th><th>Dataset</th><th/></tr></thead><tbody>{visibleRows.map((e,i)=><tr key={e.id} style={{animationDelay:`${i*30}ms`}} className="rb-reveal"><td><button className="font-semibold text-primary hover:underline" onClick={()=>setSelected(e)}>{shortId(e.id)}</button><small className="block muted">{e.parent_id?'Parent '+shortId(e.parent_id):'Root experiment'}</small></td><td>{dateTime(e.created_at)}</td><td><StatusBadge value={e.status}/></td><td>{(e.config.models||[]).map(m=>modelLabels[m]).join(', ')}<small className="block muted">Seed {e.config.seed}</small></td><td className="mono text-[10px]">{shortId(e.dataset_id)}</td><td className="text-right"><div className="flex justify-end gap-1"><Link className="btn btn-outline px-2" to={'/experiments/'+e.id}>Open</Link><Button variant="outline" disabled={rerun.isPending} onClick={()=>rerun.mutate(e.id)}><RotateCcw size={12}/>Rerun</Button><Button variant="ghost" onClick={()=>{update(e.config);navigate('/training')}}><Copy size={12}/>Draft</Button></div></td></tr>)}</tbody></table>{rows.length>0&&<RegistryControls page={safePage} pages={pages} total={rows.length} setPage={setPage}/>} {!rows.length&&<div className="p-6"><EmptyState title="No matching experiments">Change the registry filters or start a new run in Model Lab.</EmptyState></div>}</div>}
    </Card>
    {selected&&<div className="mt-5 two-grid"><Card title={'Experiment '+shortId(selected.id)} description="Registry detail"><div className="grid gap-3 text-sm"><div className="flex justify-between"><span className="muted">Status</span><StatusBadge value={selected.status}/></div><div className="flex justify-between"><span className="muted">Dataset</span><span className="mono text-xs">{selected.dataset_id}</span></div><div className="flex justify-between"><span className="muted">Created</span><span>{dateTime(selected.created_at)}</span></div><div><span className="muted">Models</span><div className="mt-2 flex flex-wrap gap-1">{selected.config.models.map(m=><Badge key={m}>{modelLabels[m]}</Badge>)}</div></div></div></Card><Card title="Exact configuration"><JsonDisclosure label="Open JSON configuration" value={selected.config}/><Link className="btn btn-outline mt-3" to={'/experiments/'+selected.id}>Open full evidence <ExternalLink size={13}/></Link></Card></div>}
  </div>
}

export function ExperimentDetail(){
  const {id=''}=useParams();
  const result=useQuery({queryKey:['experiment',id],queryFn:()=>qh.experiment(id),enabled:Boolean(id),refetchInterval:5000});
  const action=useMutation({mutationFn:(format:'html'|'json')=>qh.report(id,format)});
  const [expanded,setExpanded]=useState<string|null>(null);
  const detail=result.data;
  if(result.isLoading)return <div><PageHeader eyebrow="Research Studio · Evidence" title="Experiment detail" description="Loading the selected research record."/><Loading/></div>;
  if(result.error||!detail)return <div><PageHeader eyebrow="Research Studio · Evidence" title="Experiment not found" description="The selected research record could not be loaded."/><ErrorBanner error={(result.error as Error)?.message}/><Link className="btn btn-outline mt-4" to="/experiments"><ArrowLeft size={13}/>Back to registry</Link></div>;
  return <div>
    <PageHeader eyebrow="Research Studio · Evidence" title={'Experiment '+shortId(id)} description="Inspect provenance, job state, measured model records and the exact configuration behind one Q‑Health research experiment." actions={<Link className="btn btn-outline" to="/experiments"><ArrowLeft size={13}/>All experiments</Link>}/>
    <StageNav current="/experiments"/>
    <ErrorBanner error={(action.error as Error)?.message}/>
    <Card className="mt-5" title="Experiment context" description="A drill-down evidence surface modeled on TICTAC-style research detail views.">
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={detail.experiment.status}/><span className="text-xs muted">{dateTime(detail.experiment.created_at)}</span><span className="mono text-xs muted">Dataset {shortId(detail.experiment.dataset_id)}</span></div>
      <div className="mt-4 grid gap-4 md:grid-cols-3"><MetricCard label="MODELS" value={detail.models.length} detail="Backend model records"/><MetricCard label="JOBS" value={detail.jobs.length} detail="Execution records"/><MetricCard label="PARENT" value={detail.experiment.parent_id?shortId(detail.experiment.parent_id):'None'} detail="Experiment lineage"/></div>
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={action.isPending} onClick={()=>action.mutate('html')}><Download size={13}/>Export HTML</Button><Button variant="outline" disabled={action.isPending} onClick={()=>action.mutate('json')}><Download size={13}/>Export JSON</Button><Link className="btn btn-outline" to="/comparison">Open comparison →</Link></div>
    </Card>
    <div className="mt-5"><Card title="Measured model records" description="Only measurements returned by the backend are displayed.">
      {detail.models.length?detail.models.map(model=><GlareHover key={model.id} className="border-b py-5 last:border-b-0"><article className="py-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex items-center gap-2"><h3 className="font-semibold">{modelLabels[model.model_type]}</h3><StatusBadge value={model.status}/></div><small className="muted">Model {shortId(model.id)} · {dateTime(model.created_at)}</small></div><button className="btn btn-ghost" onClick={()=>setExpanded(expanded===model.id?null:model.id)}>{expanded===model.id?'Collapse':'Inspect'}</button></div>{model.metrics.test&&<div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.1fr]"><div className="rounded-xl border p-4"><div className="metric-label">HELD-OUT METRICS</div><div className="mt-3 space-y-1">{(['sensitivity','specificity','roc_auc','f1','accuracy','precision','recall'] as const).map(k=><div className="flex justify-between border-b py-1.5 last:border-0" key={k}><span className="text-xs muted">{k}</span><strong className="mono text-xs">{metric(model.metrics.test?.[k],k!=='roc_auc')}</strong></div>)}</div></div><div className="rounded-xl border p-4"><div className="metric-label">RUNTIME</div><div className="mt-3 space-y-1 text-xs">{[['Final training',seconds(model.metrics.timing?.final_training_seconds)],['CV total',seconds(model.metrics.timing?.cv_total_seconds)],['Test inference',seconds(model.metrics.timing?.test_inference_seconds_per_sample)+'/sample']].map(x=><div className="flex justify-between border-b py-1.5 last:border-0" key={String(x[0])}><span className="muted">{x[0]}</span><strong>{x[1]}</strong></div>)}</div></div></div>}{expanded===model.id&&<JsonDisclosure label="Model identity, provenance, metrics and limitations" value={{details:model.details,metrics:model.metrics}}/>}</article></GlareHover>):<EmptyState title="No model records">Model records appear when the backend training job completes or records a failure.</EmptyState>}
    </Card></div>
    <div className="two-grid mt-5"><Card title="Experiment provenance"><JsonDisclosure label="Summary / split / provenance" value={detail.experiment.summary}/><JsonDisclosure label="Exact training configuration" value={detail.experiment.config}/></Card><Card title="Execution records"><div className="space-y-2">{detail.jobs.map(job=><div className="rounded-xl border p-3" key={job.id}><div className="flex justify-between"><StatusBadge value={job.status}/><span className="text-xs muted">{job.progress}%</span></div><p className="mt-1 text-xs">{job.state}</p>{job.errors.length>0&&<JsonDisclosure label="Recorded failures" value={job.errors}/>}</div>)}</div></Card></div>
    <Notice tone="amber">Research prototype boundary: measured benchmark outputs do not establish clinical validation, diagnosis or treatment efficacy.</Notice>
  </div>
}
