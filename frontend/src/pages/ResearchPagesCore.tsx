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
import {TremorBarChart,TremorDonut,TremorMetric,TremorProgressBar,TremorTracker} from '../components/TremorUI';
import {DistributionStrip,PipelineFlow,StatusStrip,WorkbenchRail} from '../components/TremorWorkbench';
import {VerifiedPipeline,VerifiedQuality} from '../components/VerifiedDemoViews';
import {useFlagshipData,useVerifiedDemo} from '../hooks/useVerifiedDemo';

export const stages=[['Data','/datasets'],['Quality','/quality'],['Preprocess','/preprocessing'],['Features','/features'],['PCA','/pca'],['Train','/training'],['Compare','/comparison'],['Robustness','/robustness'],['Explain','/explainability'],['Predict','/prediction'],['Experiments','/experiments']] as const;
export function StageNav({current}:{current:string}){return <AnimatedSection className="flex flex-wrap gap-2 border-y py-3"><span className="stage-chip border-primary/20 text-primary"><ShinyText>RESEARCH PATHWAY</ShinyText></span>{stages.map((s,i)=><Link key={s[1]} to={s[1]} className={'stage-chip ' + (current===s[1]?'bg-primary/10 text-primary border-primary/20':'border-border text-muted-foreground')} style={{animationDelay:`${i*35}ms`}}>{s[0]} <ArrowRight size={10}/></Link>)}</AnimatedSection>}

export function Overview(){
 const flagship=useFlagshipData();
 const summary=useQuery({queryKey:['summary'],queryFn:qh.summary,refetchInterval:7000});
 const health=useQuery({queryKey:['health'],queryFn:qh.health,refetchInterval:15000});
 const datasets=useQuery({queryKey:['datasets'],queryFn:qh.datasets,refetchInterval:15000});
 const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary,refetchInterval:30000});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments,refetchInterval:12000});
 const system=useQuery({queryKey:['system-status'],queryFn:qh.systemStatus,refetchInterval:15000});
 const datasetScale=(library.data??[]).slice(0,7).map(item=>({name:item.name.length>18?item.name.slice(0,17)+'…':item.name,samples:item.row_count,features:item.feature_count}));
 const registered=datasets.data??[];
 const statusCounts=Object.entries((experiments.data??[]).reduce<Record<string,number>>((acc,e)=>{acc[e.status]=(acc[e.status]??0)+1;return acc},{})).map(([name,value])=>({name:name.replaceAll('_',' '),value}));
 const healthBlocks=registered.slice(0,12).map(d=>({label:d.name,status:d.quality.blockers.length?'error':d.quality.warnings.length?'warning':'good',tooltip:d.name+' · '+(d.quality.blockers.length?'blocked':d.quality.warnings.length?'warning':'clear')} as const));
 const capabilityCount=system.data?.model_capabilities?.length??0;
 const implementedCount=system.data?.model_capabilities?.filter(m=>m.implementation_status==='AVAILABLE').length??0;
 const executableCount=system.data?.model_capabilities?.filter(m=>m.executable).length??0;
 const modelReadiness=system.data?.model_capabilities?.slice(0,6).map(m=>({label:m.display_name,detail:m.category, value:m.implementation_status==='AVAILABLE'?(m.executable?100:75):0}))??[];
 const focus=registered[0];
 const focusClass=focus?Object.entries(focus.provenance.class_distribution).map(([name,value])=>({name,value})):[];
 return <div className="tremor-dashboard">
  <section className="flagship-hero">
   <div className="flagship-hero-copy"><div className="flex flex-wrap gap-2"><Badge tone="purple">VERIFIED SIH DEMONSTRATION</Badge><Badge tone={flagship.available?'green':'red'}>{flagship.available?'READY INSTANTLY':'VERIFIED DEMO UNAVAILABLE'}</Badge></div><p className="eyebrow mt-5">ENTANGLEX Q-HEALTH</p><h1>{flagship.item?.name||flagship.alignment.data?.showcase.display_name||'Early Stage Diabetes Risk Prediction'}</h1><p>Open a complete verified research record immediately—dataset, preprocessing, seven-model comparison, robustness, hybrid SHAP, and representative predictions. No upload or training required.</p><div className="flagship-stats"><div><span>SAMPLES</span><strong>{flagship.item?.row_count.toLocaleString()??'—'}</strong></div><div><span>FEATURES</span><strong>{flagship.item?.feature_count??'—'}</strong></div><div><span>MODELS</span><strong>{flagship.item?.demo_readiness.model_ids.length??'—'}</strong></div><div><span>RESULT</span><strong>{flagship.available?'Precomputed':'Unavailable'}</strong></div></div><div className="flex flex-wrap gap-2 mt-6"><Link className="btn btn-primary" to="/demo">Explore instant results <ArrowRight size={14}/></Link><Link className="btn btn-outline" to="/datasets">Explore your own data</Link></div></div>
   <div className="flagship-hero-visual" aria-label="Classical quantum and hybrid verified evidence"><ShieldCheck size={28}/><strong>VERIFIED ARTIFACT BUNDLE</strong><div><span>CLASSICAL</span><span>QUANTUM</span><span>HYBRID</span></div><p>Benchmark · Robustness · SHAP · Prediction</p></div>
  </section>
  {!flagship.available&&!flagship.library.isLoading&&<Notice tone="amber">Verified demo unavailable. Scientific placeholders are never substituted; use the normal processing workflow below.</Notice>}
  <section className="tremor-dashboard-top">
   <div><div className="eyebrow">ENTANGLEX Q-HEALTH · RESEARCH CONTROL CENTER</div><h1 className="tremor-dashboard-title">Biomedical AI &amp; quantum research workspace</h1><p className="tremor-dashboard-subtitle">A production-style analytics surface for datasets, model runs, controlled comparisons, robustness evidence and explainability. Every metric below is sourced from the existing Q‑Health APIs.</p></div>
   <div className="tremor-dashboard-actions"><Link className="btn btn-primary" to="/datasets">Open Data Lab <ArrowRight size={14}/></Link><Link className="btn btn-outline" to="/experiments">Experiment registry</Link></div>
  </section>

  <div className="tremor-grid-4">
   <TremorMetric label="DATASETS" value={summary.data?.counts.datasets??'—'} detail="Registered biomedical inputs" icon={<Database size={15}/>}/>
   <TremorMetric label="EXPERIMENTS" value={summary.data?.counts.experiments??'—'} detail="Recorded research runs" icon={<FlaskConical size={15}/>}/>
   <TremorMetric label="READY MODELS" value={summary.data?.counts.ready_models??'—'} detail="Backend-reported ready artifacts" icon={<Brain size={15}/>}/>
   <TremorMetric label="ACTIVE JOBS" value={summary.data?.counts.active_jobs??'—'} detail="Queued or running work" icon={<RefreshCw size={15}/>}/>
  </div>

  <div className="tremor-grid-main">
   <Card title="Dataset scale" description="Registered built-in datasets and their available sample counts.">
    {datasetScale.length?<TremorBarChart data={datasetScale} category="name" value="samples" height={270} showGrid/>:<EmptyState title="No datasets in the library">The backend has not returned dataset library records yet.</EmptyState>}
   </Card>
   <Card title="Experiment status" description="Current experiment registry state from the live API.">
    {statusCounts.length?<TremorDonut data={statusCounts} nameKey="name" valueKey="value" centerLabel={statusCounts.reduce((s,x)=>s+x.value,0)} height={190}/>:<EmptyState title="No experiments yet">Create a run from Model Lab to populate this distribution.</EmptyState>}
   </Card>
  </div>

  <div className="tremor-grid-wide">
   <Card title="Dataset readiness tracker" description={healthBlocks.length?'Each block represents one registered dataset; hover for its live quality status.':'Register datasets to activate the tracker.'}>
    {healthBlocks.length?<TremorTracker items={healthBlocks}/>:<TremorTracker items={Array.from({length:10},(_,i)=>({label:String(i+1),status:'neutral' as const}))}/>}
    <div className="mt-3 flex flex-wrap gap-3 text-[10px] muted"><span><i className="inline-block size-2 rounded-full bg-emerald-500 mr-1"/>Clear</span><span><i className="inline-block size-2 rounded-full bg-amber-500 mr-1"/>Warnings</span><span><i className="inline-block size-2 rounded-full bg-red-500 mr-1"/>Blockers</span><span className="ml-auto">{registered.length} registered</span></div>
   </Card>
   <Card title="Model capability surface" description="Backend-reported implementation and execution states.">
    <div className="space-y-3">
     {modelReadiness.length?modelReadiness.map(item=><TremorProgressBar key={item.label} value={item.value} label={item.label} detail={item.detail}/>):<TremorProgressBar value={0} label="Waiting for capability metadata" detail="System status endpoint not yet available"/>}
     <div className="grid grid-cols-3 gap-2 pt-2"><TremorMetric label="CAPABILITIES" value={capabilityCount}/><TremorMetric label="AVAILABLE" value={implementedCount}/><TremorMetric label="EXECUTABLE" value={executableCount}/></div>
    </div>
   </Card>
  </div>

  <div className="tremor-grid-main">
   <Card title="Current dataset class balance" description={focus?focus.name:'Select a dataset in Data Lab'}>
    {focusClass.length?<div className="grid gap-4 md:grid-cols-[1.2fr_.8fr]"><ValueBars items={focusClass}/><div className="space-y-3">{[['Samples',focus.provenance.row_count.toLocaleString()],['Features',String(focus.provenance.feature_count)],['Target',focus.provenance.target],['Positive',focus.provenance.positive_label]].map(([k,v])=><div className="tremor-list-row" key={k}><span className="tremor-metric-label">{k}</span><strong className="ml-auto text-xs break-all text-right">{v}</strong></div>)}</div></div>:<EmptyState title="No registered dataset">Use Data Lab to register the early-stage diabetes dataset or another biomedical benchmark.</EmptyState>}
   </Card>
   <Card title="Runtime monitor" description="Live backend state; no capability is inferred by the UI.">
    <div className="space-y-4"><div className="flex items-center justify-between"><span className="tremor-metric-label">BACKEND</span><Badge tone={health.isError?'red':'green'}>{health.isError?'Offline':health.data?'Connected':'Checking'}</Badge></div><div className="flex items-center justify-between"><span className="tremor-metric-label">QUANTUM</span><Badge tone={health.data?.quantum.available?'purple':'amber'}>{health.data?.quantum.available?'Available':'Not reported'}</Badge></div><div className="flex items-center justify-between"><span className="tremor-metric-label">RUNTIME VERIFIED</span><strong className="text-xs">{health.data?.quantum.runtime_verified?'Yes':'No'}</strong></div><div className="rounded-lg border p-3 text-[11px] muted">{health.data?.quantum.execution||'Quantum execution state will appear when reported by the backend.'}</div></div>
   </Card>
  </div>

  <div className="tremor-grid-main">
   <Card title="Recent experiments" description="Live registry entries returned by the existing experiment API.">
    {summary.isLoading?<Loading/>:summary.data?.recent_experiments?.length?<div>{summary.data.recent_experiments.slice(0,6).map(e=><Link key={e.id} to={'/experiments/'+e.id} className="tremor-list-row"><div><strong className="text-xs">{shortId(e.id)}</strong><p className="mt-1 text-[10px] muted">{dateTime(e.created_at)}</p></div><span className="ml-auto"><StatusBadge value={e.status}/></span></Link>)}</div>:<EmptyState title="No experiments yet">Create the first run from Model Lab.</EmptyState>}
   </Card>
   <Card title="Research guardrails" description="The UI surfaces evidence without turning research output into clinical claims.">
    <Notice tone="amber">Predictions support research and decision support only. They are not clinical diagnoses, treatment decisions, or validation.</Notice>
    <div className="mt-4 space-y-2 text-xs muted"><div className="flex items-center justify-between"><span>Shared API source</span><strong className="text-foreground">Live backend</strong></div><div className="flex items-center justify-between"><span>Selection threshold</span><strong className="text-foreground">Backend-defined</strong></div><div className="flex items-center justify-between"><span>Model comparison</span><strong className="text-foreground">Evidence-based</strong></div></div>
   </Card>
  </div>

  <StageNav current="/"/>
  <ResearchPipeline/>
 </div>
}
export function Datasets(){
 const {draft,selectDataset,clearDataset}=useDraft();
 const demo=useVerifiedDemo();
 const datasets=useQuery({queryKey:['datasets'],queryFn:qh.datasets});
 const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary});
 const qc=useQueryClient();
 const [selected,setSelected]=useState<Dataset|null>(null);
 const [file,setFile]=useState<File|null>(null);
 const [inspection,setInspection]=useState<DatasetInspection|null>(null);
 const [confirmed,setConfirmed]=useState(false);
 const [form,setForm]=useState({name:'',domain:'biomedical',source:'User-provided',source_url:'',version:'unspecified',target:'',positive_label:''});
 const choose=(dataset:Dataset)=>{demo.deactivate();selectDataset(dataset.id,dataset.provenance.recommended_duplicate_policy);setSelected(dataset)};
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
  <WorkbenchRail items={[
   {label:'Registered',value:(datasets.data||[]).length,detail:'Existing dataset records',tone:'blue'},
   {label:'Library',value:(library.data||[]).length,detail:'Backend catalog sources',tone:'purple'},
   {label:'Active context',value:draft.dataset_id?shortId(draft.dataset_id):'None',detail:'Current research workflow',tone:draft.dataset_id?'green':'amber'},
   {label:'CSV inspection',value:inspection?'Ready':'Waiting',detail:inspection?'Metadata received':'No local file inspected',tone:inspection?'green':'slate'}
  ]}/>
  <PipelineFlow items={[
   {label:'Source',detail:'Library or deidentified CSV',status:(library.data?.length||file)?'complete':'current'},
   {label:'Inspect',detail:'Schema and target resolution',status:inspection?'complete':file?'current':'waiting'},
   {label:'Register',detail:'Immutable backend record',status:(datasets.data?.length||0)>0?'complete':inspection?'current':'waiting'},
   {label:'Select',detail:'Shared workflow context',status:draft.dataset_id?'complete':(datasets.data?.length||0)>0?'current':'waiting'},
   {label:'Validate',detail:'Quality gates and integrity',status:draft.dataset_id?'current':'waiting'}
  ]}/>
  <ErrorBanner error={error instanceof Error?error.message:undefined}/>
  <Card className="mt-5 featured-dataset-card" title="Featured SIH Demo" description="The backend-designated instant demonstration. Metadata and readiness are loaded from the dataset library API.">
   {library.isLoading?<Loading/>:library.data?.filter(item=>item.demo_readiness.status==='ready').map(item=><article className="rounded-xl border p-5" key={item.slug}>
    <div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex flex-wrap gap-1"><Badge tone="purple">Featured SIH dataset</Badge><Badge tone="green">Verified instant demo</Badge><Badge tone="blue">Precomputed</Badge></div><h2 className="mt-3 text-xl font-semibold">{item.name}</h2><p className="mt-1 text-sm muted">{item.description}</p></div><ShieldCheck className="text-primary" size={28}/></div>
    <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-5">{[['Samples',item.row_count],['Features',item.feature_count],['Target',item.target],['Classes',item.class_labels.join(' / ')],['Models',item.demo_readiness.model_ids.length]].map(([k,v])=><div className="rounded-xl border p-3" key={String(k)}><span className="metric-label">{k}</span><strong className="block mt-1 break-all">{String(v)}</strong></div>)}</div>
    <p className="mt-4 text-xs muted">{item.source} · {item.attribution} · {item.license}</p><div className="mt-4 flex flex-wrap gap-2"><Link className="btn btn-primary" to="/demo">Explore instant results <ArrowRight size={14}/></Link><Button variant="outline" disabled={builtIn.isPending} onClick={()=>builtIn.mutate(item.slug)}>Use Dataset</Button></div>
   </article>)}
  </Card>
  <Card className="mt-5" title="Medical Dataset Library" description="Other built-in datasets remain available for the normal research workflow. Their readiness labels come directly from the backend.">
   {library.isLoading?<Loading/>:<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{library.data?.filter(item=>item.demo_readiness.status!=='ready').map(item=><article className="rounded-xl border p-4" key={item.slug}>
    <div className="flex items-start justify-between gap-3"><div><div className="flex flex-wrap gap-1"><Badge tone="green">Built-in</Badge><Badge tone={item.demo_readiness.status==='ready'?'blue':'amber'}>{item.demo_readiness.status==='ready'?'Verified Demo Ready':'Requires Processing'}</Badge></div><h3 className="mt-2 font-semibold">{item.name}</h3><p className="mt-1 text-xs muted">{item.description}</p></div><Database className="shrink-0 text-primary" size={18}/></div>
    <div className="mt-4 grid grid-cols-2 gap-2 text-xs"><div><span className="metric-label">SAMPLES</span><strong className="block">{item.row_count.toLocaleString()}</strong></div><div><span className="metric-label">FEATURES</span><strong className="block">{item.feature_count}</strong></div><div><span className="metric-label">TARGET</span><strong className="block break-all">{item.target}</strong></div><div><span className="metric-label">DOMAIN</span><strong className="block capitalize">{item.domain}</strong></div></div>
    <div className="mt-3 flex flex-wrap gap-1">{item.class_labels.map(label=><Badge key={label}>{label}</Badge>)}</div>
    <p className="mt-3 text-[11px] muted">{item.source} · {item.license}</p><p className="mt-2 text-[11px] muted">{item.demo_readiness.status==='ready'?'Precomputed research result available; live training remains available.':'No precomputed result is packaged; run normal live training.'}</p>
    <Button className="mt-4 w-full" disabled={builtIn.isPending} onClick={()=>builtIn.mutate(item.slug)}>{builtIn.isPending?'Registering…':'Use Dataset'}</Button>
   </article>)}</div>}
  </Card>
  <div className="two-grid mt-5"><Card title="Registered datasets" description="Built-in and uploaded datasets remain separate immutable registry records."><div className="table-wrap"><table className="data-table"><thead><tr><th>Dataset</th><th>Samples</th><th>Features</th><th>Target</th><th/></tr></thead><tbody>{datasets.data?.map(dataset=><tr key={dataset.id} className={draft.dataset_id===dataset.id?'bg-primary/5':''}><td><button className="font-semibold text-primary hover:underline" onClick={()=>setSelected(dataset)}>{dataset.name}</button><small className="block muted">{shortId(dataset.id)} · {dataset.provenance.origin==='built_in'?'Built-in':'Uploaded'}</small></td><td>{dataset.provenance.row_count.toLocaleString()}</td><td>{dataset.provenance.feature_count}</td><td>{dataset.provenance.target}<small className="block muted">Positive: {dataset.provenance.positive_label}</small></td><td className="text-right"><Button variant="outline" onClick={()=>choose(dataset)}>{draft.dataset_id===dataset.id?'Selected':'Select'}</Button></td></tr>)}</tbody></table></div>{datasets.isLoading&&<Loading/>}{!datasets.isLoading&&!datasets.data?.length&&<EmptyState title="No datasets registered">Choose a built-in dataset or inspect a CSV below.</EmptyState>}</Card>
   <Card title={selected?selected.name:'Selected provenance'} description="The registered backend record is the single source of truth for every downstream stage.">{selected?<div className="space-y-3 text-sm"><div className="grid grid-cols-2 gap-3">{[['Rows',selected.provenance.row_count],['Features',selected.provenance.feature_count],['Target',selected.provenance.target],['Type',selected.provenance.target_type||'binary_classification']].map(x=><div className="rounded-xl border p-3" key={String(x[0])}><span className="metric-label">{x[0]}</span><strong className="mt-1 block break-all">{String(x[1])}</strong></div>)}</div><p className="muted">{selected.provenance.source}</p><p className="mono break-all text-[10px] muted">SHA-256: {selected.sha256}</p><JsonDisclosure label="Full provenance and target resolution" value={selected.provenance}/><Button variant="ghost" disabled={remove.isPending} onClick={()=>{if(window.confirm('Delete this dataset?'))remove.mutate(selected.id)}}><Trash2 size={13}/> Delete dataset</Button></div>:<EmptyState title="Choose a registry record">Open a registered dataset to inspect its provenance.</EmptyState>}</Card></div>
  <Card className="mt-5" title="Explore Your Own Data · Upload CSV" description="Run the full Q-Health processing pipeline on another dataset. Inspect a deidentified CSV first; the backend never silently registers a low-confidence target guess.">
   <div className="grid gap-4 md:grid-cols-[1fr_auto]"><label className="field"><span>CSV file</span><Input type="file" accept=".csv,text/csv" onChange={event=>{const next=event.target.files?.[0]||null;setFile(next);setInspection(null);setForm(current=>({...current,name:next?next.name.replace(/\.csv$/i,'').replaceAll('_',' '):'',target:'',positive_label:''}))}}/></label><div className="flex items-end"><Button variant="outline" disabled={!file||inspect.isPending} onClick={()=>inspect.mutate({})}><ShieldCheck size={14}/>{inspect.isPending?'Inspecting…':'Detect Target'}</Button></div></div>
   {inspection&&<div className="mt-5 rounded-xl border p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><span className="metric-label">AUTOMATIC TARGET ANALYSIS</span><h3 className="mt-1 font-semibold">{inspection.detected_target||'Manual selection required'}</h3><p className="mt-1 text-xs muted">{inspection.target_type?.replaceAll('_',' ')||'No eligible target resolved'} · {inspection.confidence} heuristic confidence ({Math.round(inspection.confidence_score*100)}/100)</p></div><Badge tone={inspection.requires_manual_target?'amber':'green'}>{inspection.requires_manual_target?'Review required':'Resolved'}</Badge></div><p className="mt-2 text-[11px] muted">{inspection.heuristic_notice}</p><div className="mt-4 grid gap-4 md:grid-cols-2"><label className="field"><span>Target column · Change Target</span><Select value={form.target} onChange={event=>changeTarget(event.target.value)}><option value="">Select target</option>{inspection.columns.map(column=><option value={column} key={column}>{column}</option>)}</Select></label><label className="field"><span>Positive class</span><Select value={form.positive_label} onChange={event=>setForm(current=>({...current,positive_label:event.target.value}))}><option value="">Select positive class</option>{inspection.class_labels.map(label=><option value={label} key={label}>{label}</option>)}</Select></label></div><div className="mt-3 flex flex-wrap gap-1">{inspection.class_labels.map(label=><Badge key={label}>{label}: {inspection.class_distribution[label]??0}</Badge>)}</div><JsonDisclosure label="Candidate ranking and schema" value={{candidates:inspection.candidates,schema:inspection.schema}}/></div>}
   {inspection&&<details className="mt-5 rounded-xl border p-4"><summary className="cursor-pointer text-sm font-semibold">Dataset details and provenance</summary><div className="mt-4 grid gap-4 md:grid-cols-2">{(['name','domain','source','source_url','version'] as const).map(key=><label className="field" key={key}><span>{key.replaceAll('_',' ')}</span><Input value={form[key]} onChange={event=>setForm(current=>({...current,[key]:event.target.value}))}/></label>)}</div></details>}
   <label className="mt-4 flex items-start gap-2 text-xs muted"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I confirm this file contains no patient-identifiable information and represents independent samples.</label>
   <Button className="mt-4" disabled={!file||!inspection||!form.target||!form.positive_label||!form.name||!confirmed||upload.isPending} onClick={()=>upload.mutate()}><Upload size={14}/>{upload.isPending?'Registering…':'Register Dataset'}</Button>
  </Card>
 </div>;
}

function ActiveDataset({children}:{children:(d:Dataset)=>React.ReactNode}){const {draft}=useDraft();const q=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});if(q.isLoading)return <Loading/>;if(!q.data)return <EmptyState title="Select a dataset">Choose an input in Data Lab first.</EmptyState>;return <>{children(q.data)}{q.error&&<ErrorBanner error={(q.error as Error).message}/>}</>}

export function Quality(){const demo=useVerifiedDemo();return demo.active?<VerifiedQuality/>:<LiveQuality/>}
function LiveQuality(){const {draft}=useDraft();const [checked,setChecked]=useState<any>();const q=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});const mutation=useMutation({mutationFn:()=>qh.validate(draft.dataset_id,draft.features),onSuccess:setChecked});const quality=checked||q.data?.quality;return <div><PageHeader eyebrow="02 / Validate" title="Data quality" description="Inspect class balance, missingness, redundancy, target proxies and integrity flags before any model run." actions={<Button disabled={!draft.dataset_id||mutation.isPending} onClick={()=>mutation.mutate()}><ShieldCheck size={14}/>{mutation.isPending?'Validating…':'Validate selected inputs'}</Button>}/><StageNav current="/quality"/><WorkbenchRail items={[{label:'Quality state',value:quality?'Measured':'Not validated',detail:'Backend quality contract',tone:quality?'green':'slate'},{label:'Blockers',value:quality?.blockers?.length??'—',detail:'Must be reviewed',tone:quality?.blockers?.length?'red':'green'},{label:'Warnings',value:quality?.warnings?.length??'—',detail:'Non-blocking findings',tone:quality?.warnings?.length?'amber':'green'},{label:'Minority share',value:quality?`${(quality.minority_fraction*100).toFixed(1)}%`:'—',detail:'Measured class balance',tone:quality&&quality.minority_fraction<.2?'amber':'green'}]}/>{quality&&<StatusStrip items={[{label:'Validation',value:quality.blockers.length?'Blocked':quality.warnings.length?'Review':'Healthy',status:quality.blockers.length?'bad':quality.warnings.length?'warning':'good'},{label:'Missingness',value:Object.values(quality.missing_values).some(Number)?'Detected':'Clear',status:Object.values(quality.missing_values).some(Number)?'warning':'good'},{label:'Duplicates',value:String(quality.duplicate_rows),status:quality.duplicate_rows?'warning':'good'},{label:'Target proxies',value:String(quality.suspiciously_predictive_features.length),status:quality.suspiciously_predictive_features.length?'warning':'good'}]}/>}<div className="mt-5"><ActiveDataset>{d=><div className="quality-evidence-grid"><Card title={d.name} description={d.provenance.target + ' · ' + d.provenance.row_count.toLocaleString() + ' samples'}><div className="grid grid-cols-2 gap-3"><MetricCard label="SAMPLES" value={d.provenance.row_count.toLocaleString()} detail="Registered rows" icon={<Database size={15}/>}/><MetricCard label="FEATURES" value={d.provenance.feature_count} detail="Available dimensions" icon={<BarChart3 size={15}/>}/></div><div className="mt-4"><div className="metric-label">CLASS DISTRIBUTION</div><ClassBalance dataset={d}/></div></Card><Card title="Quality gates"><Notice tone={quality?.blockers?.length?'amber':'green'}>{quality?.blockers?.length?'Backend returned blockers that require review.':'No blocking issue returned by the current checks.'}</Notice><div className="mt-3 space-y-2">{(quality?.blockers||[]).map((x:string)=><div className="text-xs text-red-700" key={x}>{x}</div>)}{(quality?.warnings||[]).map((x:string)=><div className="text-xs text-amber-700" key={x}>{x}</div>)}</div></Card></div>}</ActiveDataset></div>{quality&&<div className="mt-5 two-grid"><Card title="Integrity profile"><div className="space-y-2">{[['Minority fraction',quality.minority_fraction],['Duplicate rows',quality.duplicate_rows],['Duplicate feature rows',quality.duplicate_feature_rows],['Suspicious features',quality.suspiciously_predictive_features.length],['Identifier-like fields',quality.identifier_features.length]].map(x=><div className="flex justify-between border-b py-2 last:border-0" key={String(x[0])}><span className="text-xs muted">{x[0]}</span><strong className="text-xs">{String(x[1])}</strong></div>)}</div><JsonDisclosure label="Correlated pairs" value={quality.highly_correlated_pairs}/></Card><Card title="Missingness by feature"><div className="table-wrap max-h-[360px] overflow-auto"><table className="data-table"><thead><tr><th>Feature</th><th>Missing</th><th>Infinite</th></tr></thead><tbody>{Object.keys(quality.missing_values).map(k=><tr key={k}><td>{k}</td><td>{quality.missing_values[k]}</td><td>{quality.infinite_values[k]??0}</td></tr>)}</tbody></table></div></Card></div>}</div>}

export function PipelineStage({endpoint,title,eyebrow,description}:{endpoint:string;title:string;eyebrow:string;description:string}){
 const demo=useVerifiedDemo();
 if(demo.active)return <VerifiedPipeline stage={endpoint.includes('preprocessing')?'preprocessing':endpoint.includes('feature-selection')?'features':'pca'}/>;
 return <LivePipelineStage endpoint={endpoint} title={title} eyebrow={eyebrow} description={description}/>;
}
function LivePipelineStage({endpoint,title,eyebrow,description}:{endpoint:string;title:string;eyebrow:string;description:string}){
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
  <WorkbenchRail items={[
   {label:'Stage',value:stage==='preprocessing'?'Prepare':stage==='features'?'Select':'Reduce',detail:'Backend-authoritative step',tone:'blue'},
   {label:'Source features',value:sourceFeatures.length||'—',detail:'Registered dimensions',tone:'purple'},
   {label:'Selected inputs',value:selected.length||'—',detail:'Current draft configuration',tone:'green'},
   {label:'Preview',value:preview?'Ready':'Not run',detail:preview?'Measured response available':'Request backend preview',tone:preview?'green':'slate'}
  ]}/>
  <PipelineFlow items={[
   {label:'Input',detail:`${selected.length||0} selected features`,status:dataset?'complete':'blocked'},
   {label:'Transform',detail:stage==='preprocessing'?`${draft.pipeline.imputer} · ${draft.pipeline.scaler}`:'Shared preprocessing',status:stage==='preprocessing'?'current':preview?'complete':'waiting'},
   {label:'Select',detail:stage==='features'?draft.pipeline.selection:'Training-only selection',status:stage==='features'?'current':stage==='pca'&&preview?'complete':'waiting'},
   {label:'Reduce',detail:stage==='pca'?`${draft.pipeline.pca_components??'No'} components`:'Optional PCA',status:stage==='pca'?'current':'waiting'},
   {label:'Preview',detail:'Backend-measured output',status:preview?'complete':'waiting'}
  ]}/>
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
   {preview?<div className="two-grid mt-5"><Card title="Backend preview" description="This preview is returned by the configured backend pipeline; it is not a client-side estimate."><DistributionStrip items={[{label:'Training',value:preview.train_count,tone:'blue'},{label:'Held out',value:preview.test_count,tone:'purple'}]}/><div className="mt-4 flex flex-wrap gap-1">{preview.stages.map((x:string)=><Badge tone="green" key={x}>{x}</Badge>)}</div>{stage==='features'&&preview.selection_scores?.length>0&&<div className="mt-5"><div className="metric-label mb-2">MEASURED SELECTION SCORES</div><ValueBars items={preview.selection_scores.slice().sort((a,b)=>(b.score??-Infinity)-(a.score??-Infinity)).slice(0,12).map(x=>({name:x.feature,value:Number(x.score??0)}))}/><div className="mt-2 flex flex-wrap gap-1">{preview.selection_scores.filter(x=>x.selected).map(x=><Badge tone="green" key={x.feature}>{x.feature}</Badge>)}</div></div>}{stage==='pca'&&<div className="mt-5"><div className="metric-label mb-2">EXPLAINED VARIANCE BY COMPONENT</div><ValueBars items={preview.pca_explained_variance.map((value,i)=>({name:`PC${i+1}`,value}))}/></div>}<JsonDisclosure label="Selection scores, PCA loadings and split metadata" value={preview}/></Card><Card title="Warnings">{preview.warnings?.length?preview.warnings.map((w:string)=><Notice tone="amber" key={w}>{w}</Notice>):<Notice tone="green">No warning was returned.</Notice>}<Notice>Preview output describes the configured research transform. It does not establish clinical validity.</Notice></Card></div>:<div className="mt-5"><EmptyState title="No backend preview yet">Request a real backend preview when the research stage configuration is ready.</EmptyState></div>}
  </div>}
 </div>;
}
