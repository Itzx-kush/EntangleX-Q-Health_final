import {Link} from 'react-router-dom';
import {useState} from 'react';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {ArrowRight,Atom,BarChart3,Brain,Database,FlaskConical,GitCompareArrows,Play,RefreshCw,ShieldCheck,Trash2,Upload} from 'lucide-react';
import {MolecularBackground} from '../components/MolecularBackground';
import {SearchBar} from '../components/SearchBar';
import {Button,Card,Badge,Input,Select} from '../components/ui';
import {ErrorBanner,EmptyState,Loading,MetricCard,Notice,PageHeader,StatusBadge,JsonDisclosure,ResearchPipeline} from '../components/Shared';
import {ClassBalance,ValueBars} from '../components/Charts';
import {api,qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {shortId,dateTime} from '../utils/format';
import type {Dataset,DatasetInspection,Preview} from '../types/qhealth';
import {AnimatedSection,BlurText,BorderGlow,ClickSpark,GlareHover,GradientText,Magnet,QuantumVisual,Reveal,ShinyText,SpotlightPanel} from '../components/reactbits';

export const stages=[['Data','/datasets'],['Quality','/quality'],['Preprocess','/preprocessing'],['Features','/features'],['PCA','/pca'],['Train','/training'],['Compare','/comparison'],['Explain','/explainability'],['Predict','/prediction'],['Experiments','/experiments']] as const;
export function StageNav({current}:{current:string}){return <AnimatedSection className="flex flex-wrap gap-2 border-y py-3"><span className="stage-chip border-primary/20 text-primary"><ShinyText>RESEARCH PATHWAY</ShinyText></span>{stages.map((s,i)=><Link key={s[1]} to={s[1]} className={'stage-chip ' + (current===s[1]?'bg-primary/10 text-primary border-primary/20':'border-border text-muted-foreground')} style={{animationDelay:`${i*35}ms`}}>{s[0]} <ArrowRight size={10}/></Link>)}</AnimatedSection>}

export function Overview(){
 const summary=useQuery({queryKey:['summary'],queryFn:qh.summary,refetchInterval:7000}); const health=useQuery({queryKey:['health'],queryFn:qh.health,refetchInterval:15000});
 return <div>
  <section className="grid items-center gap-8 pb-10 pt-6 lg:grid-cols-[1.08fr_.92fr]">
   <AnimatedSection className="page-hero pb-0"><div className="eyebrow"><ShinyText>Biomedical ML · Quantum research · Evidence workspace</ShinyText></div><h1 className="headline"><BlurText>Illuminate model behavior through </BlurText><GradientText>controlled biomedical research.</GradientText></h1><p className="subhead">Q‑Health connects dataset evidence, reproducible preprocessing, classical and quantum learning, held-out comparison, explainability and research prediction in one traceable workflow.</p><div className="mt-7 max-w-2xl"><SearchBar/></div><div className="mt-6 flex flex-wrap gap-2"><Magnet><ClickSpark><Link className="btn btn-primary" to="/datasets">Enter Data Lab <ArrowRight size={14}/></Link></ClickSpark></Magnet><Magnet><Link className="btn btn-outline" to="/experiments">Explore experiments</Link></Magnet></div></AnimatedSection>
   <BorderGlow className="hero-visual"><div className="hero-visual-grid"/><MolecularBackground/><div className="hero-visual-content"><div className="text-center"><div className="stage-chip mx-auto mb-6"><ShinyText>RESEARCH PATHWAY</ShinyText></div><QuantumVisual/><div className="hero-orbit"><div className="hero-core grid place-items-center"><Atom size={30}/></div></div><div className="mt-5 grid grid-cols-2 gap-2 text-[10px] font-semibold"><span className="stage-chip">DATA</span><span className="stage-chip">CLASSICAL</span><span className="stage-chip">QUANTUM</span><span className="stage-chip">EVALUATION</span></div></div></div></BorderGlow>
  </section>
  <StageNav current="/"/>
  <ResearchPipeline/>
  <div className="stat-grid my-6">
   <MetricCard label="DATASETS" value={summary.data?.counts.datasets ?? '—'} detail="Registered biomedical inputs" icon={<Database size={16}/>}/>
   <MetricCard label="EXPERIMENTS" value={summary.data?.counts.experiments ?? '—'} detail="Recorded research runs" icon={<FlaskConical size={16}/>}/>
   <MetricCard label="READY MODELS" value={summary.data?.counts.ready_models ?? '—'} detail="Backend-reported models" icon={<Brain size={16}/>}/>
   <MetricCard label="ACTIVE JOBS" value={summary.data?.counts.active_jobs ?? '—'} detail="Queued or running jobs" icon={<RefreshCw size={16}/>}/>
  </div>
  <div className="content-grid">
   <Card title="Research landscape" description="A biomedical evidence workflow adapted from the research-product structure of TICTAC."><div className="grid gap-3 md:grid-cols-3"><Link to="/datasets" className="rounded-xl border p-4 hover:bg-muted"><Database className="text-primary"/><strong className="mt-3 block">Data Lab</strong><p className="mt-1 text-xs muted">Register and validate deidentified biomedical inputs.</p></Link><Link to="/training" className="rounded-xl border p-4 hover:bg-muted"><GitCompareArrows className="text-primary"/><strong className="mt-3 block">Model Lab</strong><p className="mt-1 text-xs muted">Run shared classical and quantum representations.</p></Link><Link to="/quantum" className="rounded-xl border p-4 hover:bg-muted"><Atom className="text-primary"/><strong className="mt-3 block">Quantum Lab</strong><p className="mt-1 text-xs muted">Inspect QNN, VQC and QSVC circuit structures.</p></Link></div></Card>
   <Card title="Runtime state"><div className="space-y-3 text-sm"><div className="flex justify-between"><span className="muted">Backend</span><strong>{health.isError ? 'Offline' : health.data ? 'Connected' : 'Checking'}</strong></div><div className="flex justify-between"><span className="muted">Quantum runtime</span><strong>{health.data?.quantum.available ? 'Available' : 'Not reported'}</strong></div><p className="text-xs muted">{health.data?.quantum.execution || 'Quantum execution state will appear here.'}</p></div></Card>
  </div>
  <div className="two-grid mt-5">
   <Card title="Recent experiments" description="Returned from the live summary endpoint.">{summary.isLoading?<Loading/>:summary.data?.recent_experiments?.length?<div className="space-y-2">{summary.data.recent_experiments.map(e=><Link to={'/experiments/' + e.id} className="flex items-center justify-between rounded-xl border p-3 hover:bg-muted" key={e.id}><div><strong className="text-sm">{shortId(e.id)}</strong><small className="ml-2 muted">{dateTime(e.created_at)}</small></div><StatusBadge value={e.status}/></Link>)}</div>:<EmptyState title="No experiments yet">Create the first experiment from Model Lab.</EmptyState>}</Card>
   <Card title="Research boundary"><Notice tone="amber">Predictions support research and decision support only. They are not clinical diagnoses or validation.</Notice></Card>
  </div>
 </div>
}

export function Datasets(){
 const {draft,selectDataset,clearDataset}=useDraft();
 const datasets=useQuery({queryKey:['datasets'],queryFn:qh.datasets});
 const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary});
 const qc=useQueryClient();
 const [selected,setSelected]=useState<Dataset|null>(null);
 const [file,setFile]=useState<File|null>(null);
 const [inspection,setInspection]=useState<DatasetInspection|null>(null);
 const [confirmed,setConfirmed]=useState(false);
 const [form,setForm]=useState({name:'',domain:'biomedical',source:'User-provided',source_url:'',version:'unspecified',target:'',positive_label:''});
 const choose=(dataset:Dataset)=>{selectDataset(dataset.id,dataset.provenance.recommended_duplicate_policy);setSelected(dataset)};
 const builtIn=useMutation({
  mutationFn:(slug:string)=>qh.registerBuiltIn(slug),
  onSuccess:dataset=>{choose(dataset);qc.invalidateQueries({queryKey:['datasets']})},
 });
 const remove=useMutation({mutationFn:qhDelete,onSuccess:id=>{clearDataset(id);setSelected(current=>current?.id===id?null:current);qc.invalidateQueries({queryKey:['datasets']})}});
 async function qhDelete(id:string){await api.remove('/datasets/' + id);return id}
 const inspect=useMutation({
  mutationFn:async(values?:{target?:string;positive_label?:string})=>{
   if(!file)throw new Error('Choose a CSV file first.');
   const body=new FormData();body.append('file',file);
   if(values?.target)body.append('target',values.target);
   if(values?.positive_label)body.append('positive_label',values.positive_label);
   return qh.inspectDataset(body);
  },
  onSuccess:data=>{
   setInspection(data);
   setForm(current=>({...current,
    name:current.name||data.filename.replace(/\.csv$/i,'').replaceAll('_',' '),
    target:data.detected_target||current.target,
    positive_label:data.positive_label||'',
   }));
  },
 });
 const upload=useMutation({
  mutationFn:async()=>{
   const body=new FormData();body.append('file',file as File);
   body.append('metadata_json',JSON.stringify({...form,source_url:form.source_url||null,deidentified:true,sampling_unit:'independent_samples'}));
   return qh.upload(body);
  },
  onSuccess:dataset=>{
   choose(dataset);qc.invalidateQueries({queryKey:['datasets']});
   setFile(null);setInspection(null);setConfirmed(false);
   setForm({name:'',domain:'biomedical',source:'User-provided',source_url:'',version:'unspecified',target:'',positive_label:''});
  },
 });
 const error=[datasets,library,builtIn,inspect,upload,remove].find(item=>item.error)?.error;
 const changeTarget=(target:string)=>{
  setForm(current=>({...current,target,positive_label:''}));
  inspect.mutate({target});
 };
 return <div>
  <PageHeader eyebrow="01 / Data Lab" title="Datasets" description="Choose a verified public medical benchmark or register a deidentified CSV, then carry its authoritative dataset ID through the existing Q‑Health pipeline."/>
  <StageNav current="/datasets"/>
  <ErrorBanner error={error instanceof Error?error.message:undefined}/>
  <Card className="mt-5" title="Medical Dataset Library" description="Five compact public datasets are packaged with the backend for deployment-safe, one-click registration. No model result is precomputed.">
   {library.isLoading?<Loading/>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{library.data?.map(item=><article className="rounded-xl border p-4" key={item.slug}>
    <div className="flex items-start justify-between gap-3"><div><Badge tone="green">Built-in</Badge><h3 className="mt-2 font-semibold">{item.name}</h3><p className="mt-1 text-xs muted">{item.description}</p></div><Database className="shrink-0 text-primary" size={18}/></div>
    <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><div><span className="metric-label">SAMPLES</span><strong className="block">{item.row_count.toLocaleString()}</strong></div><div><span className="metric-label">FEATURES</span><strong className="block">{item.feature_count}</strong></div><div><span className="metric-label">TARGET</span><strong className="block break-all">{item.target}</strong></div><div><span className="metric-label">DOMAIN</span><strong className="block capitalize">{item.domain}</strong></div></div>
    <div className="mt-3 flex flex-wrap gap-1">{item.class_labels.map(label=><Badge key={label}>{label}</Badge>)}</div>
    <p className="mt-3 text-[11px] muted">{item.source} · {item.license}</p>
    <Button className="mt-4 w-full" disabled={builtIn.isPending} onClick={()=>builtIn.mutate(item.slug)}>{builtIn.isPending?'Registering…':'Use Dataset'}</Button>
   </article>)}</div>}
  </Card>
  <div className="two-grid mt-5"><Card title="Registered datasets" description="Built-in and uploaded datasets remain separate immutable registry records."><div className="table-wrap"><table className="data-table"><thead><tr><th>Dataset</th><th>Samples</th><th>Features</th><th>Target</th><th/></tr></thead><tbody>{datasets.data?.map(dataset=><tr key={dataset.id} className={draft.dataset_id===dataset.id?'bg-primary/5':''}><td><button className="font-semibold text-primary hover:underline" onClick={()=>setSelected(dataset)}>{dataset.name}</button><small className="block muted">{shortId(dataset.id)} · {dataset.provenance.origin==='built_in'?'Built-in':'Uploaded'}</small></td><td>{dataset.provenance.row_count.toLocaleString()}</td><td>{dataset.provenance.feature_count}</td><td>{dataset.provenance.target}<small className="block muted">Positive: {dataset.provenance.positive_label}</small></td><td className="text-right"><Button variant="outline" onClick={()=>choose(dataset)}>{draft.dataset_id===dataset.id?'Selected':'Select'}</Button></td></tr>)}</tbody></table></div>{datasets.isLoading&&<Loading/>}{!datasets.isLoading&&!datasets.data?.length&&<EmptyState title="No datasets registered">Choose a built-in dataset or inspect a CSV below.</EmptyState>}</Card>
   <Card title={selected?selected.name:'Selected provenance'} description="The registered backend record is the single source of truth for every downstream stage.">{selected?<div className="space-y-3 text-sm"><div className="grid grid-cols-2 gap-3">{[['Rows',selected.provenance.row_count],['Features',selected.provenance.feature_count],['Target',selected.provenance.target],['Type',selected.provenance.target_type||'binary_classification']].map(x=><div className="rounded-xl border p-3" key={String(x[0])}><span className="metric-label">{x[0]}</span><strong className="mt-1 block break-all">{String(x[1])}</strong></div>)}</div><p className="muted">{selected.provenance.source}</p><p className="mono break-all text-[10px] muted">SHA-256: {selected.sha256}</p><JsonDisclosure label="Full provenance and target resolution" value={selected.provenance}/><Button variant="ghost" disabled={remove.isPending} onClick={()=>{if(window.confirm('Delete this dataset?'))remove.mutate(selected.id)}}><Trash2 size={13}/> Delete dataset</Button></div>:<EmptyState title="Choose a registry record">Open a registered dataset to inspect its provenance.</EmptyState>}</Card></div>
  <Card className="mt-5" title="Upload New Dataset" description="Inspect a deidentified CSV first. The backend ranks target candidates and never silently registers a low-confidence guess.">
   <div className="grid gap-4 md:grid-cols-[1fr_auto]"><label className="field"><span>CSV file</span><Input type="file" accept=".csv,text/csv" onChange={event=>{const next=event.target.files?.[0]||null;setFile(next);setInspection(null);setForm(current=>({...current,name:next?next.name.replace(/\.csv$/i,'').replaceAll('_',' '):'',target:'',positive_label:''}))}}/></label><div className="flex items-end"><Button variant="outline" disabled={!file||inspect.isPending} onClick={()=>inspect.mutate({})}><ShieldCheck size={14}/>{inspect.isPending?'Inspecting…':'Detect Target'}</Button></div></div>
   {inspection&&<div className="mt-5 rounded-xl border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><span className="metric-label">AUTOMATIC TARGET ANALYSIS</span><h3 className="mt-1 font-semibold">{inspection.detected_target||'Manual selection required'}</h3><p className="mt-1 text-xs muted">{inspection.target_type?.replaceAll('_',' ')||'No eligible target resolved'} · {inspection.confidence} heuristic confidence ({Math.round(inspection.confidence_score*100)}/100)</p></div><Badge tone={inspection.requires_manual_target?'amber':'green'}>{inspection.requires_manual_target?'Review required':'Resolved'}</Badge></div><p className="mt-2 text-[11px] muted">{inspection.heuristic_notice}</p><div className="mt-4 grid gap-4 md:grid-cols-2"><label className="field"><span>Target column · Change Target</span><Select value={form.target} onChange={event=>changeTarget(event.target.value)}><option value="">Select target</option>{inspection.columns.map(column=><option value={column} key={column}>{column}</option>)}</Select></label><label className="field"><span>Positive class</span><Select value={form.positive_label} onChange={event=>setForm(current=>({...current,positive_label:event.target.value}))}><option value="">Select positive class</option>{inspection.class_labels.map(label=><option value={label} key={label}>{label}</option>)}</Select></label></div><div className="mt-3 flex flex-wrap gap-1">{inspection.class_labels.map(label=><Badge key={label}>{label}: {inspection.class_distribution[label]??0}</Badge>)}</div><JsonDisclosure label="Candidate ranking and schema" value={{candidates:inspection.candidates,schema:inspection.schema}}/></div>}
   {inspection&&<details className="mt-5 rounded-xl border p-4"><summary className="cursor-pointer text-sm font-semibold">Dataset details and provenance</summary><div className="mt-4 grid gap-4 md:grid-cols-2">{(['name','domain','source','source_url','version'] as const).map(key=><label className="field" key={key}><span>{key.replaceAll('_',' ')}</span><Input value={form[key]} onChange={event=>setForm(current=>({...current,[key]:event.target.value}))}/></label>)}</div></details>}
   <label className="mt-4 flex items-start gap-2 text-xs muted"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I confirm this file contains no patient-identifiable information and represents independent samples.</label>
   <Button className="mt-4" disabled={!file||!inspection||!form.target||!form.positive_label||!form.name||!confirmed||upload.isPending} onClick={()=>upload.mutate()}><Upload size={14}/>{upload.isPending?'Registering…':'Register Dataset'}</Button>
  </Card>
 </div>;
}

function ActiveDataset({children}:{children:(d:Dataset)=>React.ReactNode}){const {draft}=useDraft();const q=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});if(q.isLoading)return <Loading/>;if(!q.data)return <EmptyState title="Select a dataset">Choose an input in Data Lab first.</EmptyState>;return <>{children(q.data)}{q.error&&<ErrorBanner error={(q.error as Error).message}/>}</>}

export function Quality(){const {draft}=useDraft();const [checked,setChecked]=useState<any>();const q=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});const mutation=useMutation({mutationFn:()=>qh.validate(draft.dataset_id,draft.features),onSuccess:setChecked});const quality=checked||q.data?.quality;return <div><PageHeader eyebrow="02 / Validate" title="Data quality" description="Inspect class balance, missingness, redundancy, target proxies and integrity flags before any model run." actions={<Button disabled={!draft.dataset_id||mutation.isPending} onClick={()=>mutation.mutate()}><ShieldCheck size={14}/>{mutation.isPending?'Validating…':'Validate selected inputs'}</Button>}/><StageNav current="/quality"/><div className="mt-5"><ActiveDataset>{d=><div className="two-grid"><Card title={d.name} description={d.provenance.target + ' · ' + d.provenance.row_count.toLocaleString() + ' samples'}><div className="grid grid-cols-2 gap-3"><MetricCard label="SAMPLES" value={d.provenance.row_count.toLocaleString()} detail="Registered rows" icon={<Database size={15}/>}/><MetricCard label="FEATURES" value={d.provenance.feature_count} detail="Available dimensions" icon={<BarChart3 size={15}/>}/></div><div className="mt-4"><div className="metric-label">CLASS DISTRIBUTION</div><ClassBalance dataset={d}/></div></Card><Card title="Quality gates"><Notice tone={quality?.blockers?.length?'amber':'green'}>{quality?.blockers?.length?'Backend returned blockers that require review.':'No blocking issue returned by the current checks.'}</Notice><div className="mt-3 space-y-2">{(quality?.blockers||[]).map((x:string)=><div className="text-xs text-red-700" key={x}>{x}</div>)}{(quality?.warnings||[]).map((x:string)=><div className="text-xs text-amber-700" key={x}>{x}</div>)}</div></Card></div>}</ActiveDataset></div>{quality&&<div className="mt-5 two-grid"><Card title="Integrity profile"><div className="space-y-2">{[['Minority fraction',quality.minority_fraction],['Duplicate rows',quality.duplicate_rows],['Duplicate feature rows',quality.duplicate_feature_rows],['Suspicious features',quality.suspiciously_predictive_features.length],['Identifier-like fields',quality.identifier_features.length]].map(x=><div className="flex justify-between border-b py-2 last:border-0" key={String(x[0])}><span className="text-xs muted">{x[0]}</span><strong className="text-xs">{String(x[1])}</strong></div>)}</div><JsonDisclosure label="Correlated pairs" value={quality.highly_correlated_pairs}/></Card><Card title="Missingness by feature"><div className="table-wrap max-h-[360px] overflow-auto"><table className="data-table"><thead><tr><th>Feature</th><th>Missing</th><th>Infinite</th></tr></thead><tbody>{Object.keys(quality.missing_values).map(k=><tr key={k}><td>{k}</td><td>{quality.missing_values[k]}</td><td>{quality.infinite_values[k]??0}</td></tr>)}</tbody></table></div></Card></div>}</div>}

export function PipelineStage({endpoint,title,eyebrow,description}:{endpoint:string;title:string;eyebrow:string;description:string}){
 const {draft,pipeline,update}=useDraft();
 const [preview,setPreview]=useState<Preview>();
 const m=useMutation({mutationFn:()=>qh.pipelinePreview(draft,endpoint),onSuccess:setPreview});
 const datasetQuery=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});
 const dataset=datasetQuery.data;
 const stage=endpoint.includes('preprocessing')?'preprocessing':endpoint.includes('feature-selection')?'features':'pca';
 const sourceFeatures=dataset?.provenance.features||[];
 const numeric=dataset?.provenance.numeric_features||[];
 const selected=draft.features||sourceFeatures;
 const addRatio=()=>pipeline({ratios:[...draft.pipeline.ratios,{name:'ratio_'+(draft.pipeline.ratios.length+1),numerator:'',denominator:''}]});
 return <div>
  <PageHeader eyebrow={eyebrow} title={title} description={description} actions={<Button disabled={!draft.dataset_id||m.isPending} onClick={()=>m.mutate()}><Play size={14}/>{m.isPending?'Calculating…':'Request backend preview'}</Button>}/>
  <StageNav current={stage==='preprocessing'?'/preprocessing':stage==='features'?'/features':'/pca'}/>
  {datasetQuery.isLoading?<div className="mt-5"><Loading/></div>:!dataset?<div className="mt-5"><EmptyState title="Select a dataset">Choose an input in Data Lab first.</EmptyState></div>:<div className="mt-5">
   <Card title="Research input" description="The selected dataset and feature representation remain shared across the downstream Q‑Health workflow.">
    <div className="grid gap-4 md:grid-cols-3"><MetricCard label="SAMPLES" value={dataset.provenance.row_count.toLocaleString()} detail="Registered rows"/><MetricCard label="FEATURES" value={dataset.provenance.feature_count} detail="Source dimensions"/><MetricCard label="TARGET" value={dataset.provenance.target} detail={'Positive: '+dataset.provenance.positive_label}/></div>
    {stage!=='pca'&&<label className="field mt-5"><span>Selected input features</span><select multiple size={8} className="select min-h-[180px]" value={selected} onChange={e=>update({features:Array.from(e.target.selectedOptions,o=>o.value)})}>{sourceFeatures.map(f=><option key={f} value={f}>{f}</option>)}</select><small>Target column is excluded by the backend. Review Data Quality before narrowing this list.</small></label>}
   </Card>
   {stage==='preprocessing'&&<div className="two-grid mt-5">
    <Card title="Core transformations" description="These settings map directly to the backend PipelineConfig contract."><div className="grid gap-4 md:grid-cols-2">
     <label className="field"><span>Imputation</span><Select value={draft.pipeline.imputer} onChange={e=>pipeline({imputer:e.target.value as any})}><option value="median">Median</option><option value="mean">Mean</option><option value="most_frequent">Most frequent</option></Select></label>
     <label className="field"><span>Scaling</span><Select value={draft.pipeline.scaler} onChange={e=>pipeline({scaler:e.target.value as any})}>{['standard','minmax','robust','none'].map(v=><option value={v} key={v}>{v}</option>)}</Select></label>
     <label className="field"><span>Outlier strategy</span><Select value={draft.pipeline.outlier_strategy} onChange={e=>pipeline({outlier_strategy:e.target.value as any})}><option value="none">Retain observations</option><option value="clip_quantiles">Clip training quantiles</option></Select></label>
     <label className="field"><span>Duplicate policy</span><Select value={draft.duplicate_policy} onChange={e=>update({duplicate_policy:e.target.value as any})}><option value="reject">Reject exact duplicates</option><option value="drop_exact">Drop exact duplicates</option></Select></label>
     <label className="field"><span>Lower quantile</span><Input type="number" min="0" max=".49" step=".01" value={draft.pipeline.lower_quantile} onChange={e=>pipeline({lower_quantile:Number(e.target.value)})}/></label>
     <label className="field"><span>Upper quantile</span><Input type="number" min=".51" max="1" step=".01" value={draft.pipeline.upper_quantile} onChange={e=>pipeline({upper_quantile:Number(e.target.value)})}/></label>
    </div></Card>
    <Card title="Feature engineering" description="Optional log and ratio transformations are stored in the shared draft and executed by the existing backend only when preview/training is requested."><label className="field"><span>log1p features</span><select multiple size={6} className="select min-h-[130px]" value={draft.pipeline.log_features} onChange={e=>pipeline({log_features:Array.from(e.target.selectedOptions,o=>o.value)})}>{numeric.filter(f=>selected.includes(f)).map(f=><option key={f} value={f}>{f}</option>)}</select><small>Use only on nonnegative numeric features.</small></label><div className="mt-4 space-y-3">{draft.pipeline.ratios.map((ratio,i)=><div className="rounded-xl border p-3" key={i}><div className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto]"><label className="field"><span>Name</span><Input value={ratio.name} onChange={e=>pipeline({ratios:draft.pipeline.ratios.map((r,j)=>j===i?{...r,name:e.target.value}:r)})}/></label><label className="field"><span>Numerator</span><Select value={ratio.numerator} onChange={e=>pipeline({ratios:draft.pipeline.ratios.map((r,j)=>j===i?{...r,numerator:e.target.value}:r)})}><option value="">Select</option>{numeric.filter(f=>selected.includes(f)).map(f=><option key={f}>{f}</option>)}</Select></label><label className="field"><span>Denominator</span><Select value={ratio.denominator} onChange={e=>pipeline({ratios:draft.pipeline.ratios.map((r,j)=>j===i?{...r,denominator:e.target.value}:r)})}><option value="">Select</option>{numeric.filter(f=>selected.includes(f)).map(f=><option key={f}>{f}</option>)}</Select></label><button type="button" className="btn btn-ghost self-end" onClick={()=>pipeline({ratios:draft.pipeline.ratios.filter((_,j)=>j!==i)})}>Remove</button></div></div>)}</div><Button variant="outline" className="mt-3" disabled={draft.pipeline.ratios.length>=20} onClick={addRatio}>Add ratio feature</Button></Card>
   </div>}
   {stage==='features'&&<Card className="mt-5" title="Feature selection controls" description="Selection remains training-only and is evaluated by the backend."><div className="grid gap-4 md:grid-cols-3"><label className="field"><span>Selection method</span><Select value={draft.pipeline.selection} onChange={e=>pipeline({selection:e.target.value as any})}><option value="anova">ANOVA F score</option><option value="mutual_info">Mutual information</option><option value="variance">Variance threshold</option><option value="none">No selection</option></Select></label><label className="field"><span>Maximum retained features</span><Input type="number" min="1" max="400" value={draft.pipeline.k_features} onChange={e=>pipeline({k_features:Number(e.target.value)})}/></label><label className="field"><span>Variance threshold</span><Input type="number" step=".001" min="0" max="10" value={draft.pipeline.variance_threshold} onChange={e=>pipeline({variance_threshold:Number(e.target.value)})}/></label></div><Notice>Selection scores are benchmark diagnostics, not biological feature importance.</Notice></Card>}
   {stage==='pca'&&<Card className="mt-5" title="Dimensionality reduction" description="For quantum comparisons, the backend requires PCA components to match the configured qubit count and shared angle scaling to remain enabled."><div className="grid gap-4 md:grid-cols-3"><label className="field"><span>PCA components</span><Input type="number" min="1" max="100" value={draft.pipeline.pca_components??''} onChange={e=>pipeline({pca_components:e.target.value?Number(e.target.value):null})}/></label><label className="flex items-center gap-2 pt-6 text-xs"><input type="checkbox" checked={draft.pipeline.pca_whiten} onChange={e=>pipeline({pca_whiten:e.target.checked})}/>Whiten components</label><label className="flex items-center gap-2 pt-6 text-xs"><input type="checkbox" checked={draft.pipeline.angle_scaling} onChange={e=>pipeline({angle_scaling:e.target.checked})}/>Shared angle scaling</label></div></Card>}
   {preview?<div className="two-grid mt-5"><Card title="Backend preview" description="This preview is returned by the configured backend pipeline; it is not a client-side estimate."><div className="grid grid-cols-2 gap-3"><MetricCard label="TRAIN" value={preview.train_count} detail="samples"/><MetricCard label="TEST" value={preview.test_count} detail="held-out samples"/></div><div className="mt-4 flex flex-wrap gap-1">{preview.stages.map((x:string)=><Badge tone="green" key={x}>{x}</Badge>)}</div>{stage==='features'&&preview.selection_scores?.length>0&&<div className="mt-5"><div className="metric-label mb-2">MEASURED SELECTION SCORES</div><ValueBars items={preview.selection_scores.slice().sort((a,b)=>(b.score??-Infinity)-(a.score??-Infinity)).slice(0,12).map(x=>({name:x.feature,value:Number(x.score??0)}))}/><div className="mt-2 flex flex-wrap gap-1">{preview.selection_scores.filter(x=>x.selected).map(x=><Badge tone="green" key={x.feature}>{x.feature}</Badge>)}</div></div>}{stage==='pca'&&<div className="mt-5"><div className="metric-label mb-2">EXPLAINED VARIANCE BY COMPONENT</div><ValueBars items={preview.pca_explained_variance.map((value,i)=>({name:`PC${i+1}`,value}))}/></div>}<JsonDisclosure label="Selection scores, PCA loadings and split metadata" value={preview}/></Card><Card title="Warnings">{preview.warnings?.length?preview.warnings.map((w:string)=><Notice tone="amber" key={w}>{w}</Notice>):<Notice tone="green">No warning was returned.</Notice>}<Notice>Preview output describes the configured research transform. It does not establish clinical validity.</Notice></Card></div>:<div className="mt-5"><EmptyState title="No backend preview yet">Request a real backend preview when the research stage configuration is ready.</EmptyState></div>}
  </div>}
 </div>;
}
