import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Activity,ArrowLeft,ArrowRight,Atom,CheckCircle2,Database,FlaskConical,MonitorCog,Moon,PlayCircle,ShieldCheck,Sparkles,Zap} from 'lucide-react';
import {Badge,Button,Card,Select} from '../components/ui';
import {ErrorBanner,Notice,PageHeader,StatusBadge} from '../components/Shared';
import {deriveDemoState,type DemoStageKey,type DemoStageStatus} from '../lib/demoState';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {modelLabels,shortId} from '../utils/format';

const demoStages:{key:DemoStageKey;label:string;copy:string;path:string;action:string}[]=[
  {key:'dataset',label:'Dataset',copy:'Select a packaged public medical dataset or register an authorized deidentified CSV.',path:'/datasets',action:'Choose Dataset'},
  {key:'quality',label:'Quality',copy:'Review missingness, class balance, identifiers, duplicates and integrity blockers.',path:'/quality',action:'Open Data Quality'},
  {key:'preprocessing',label:'Preprocessing',copy:'Configure leakage-safe imputation, scaling and optional training-only transforms.',path:'/preprocessing',action:'Configure Pipeline'},
  {key:'features',label:'Feature Engineering',copy:'Choose the measured feature representation without making causal claims.',path:'/features',action:'Select Features'},
  {key:'pca',label:'PCA',copy:'Inspect the configured reduced representation used by compatible model paths.',path:'/pca',action:'Configure PCA'},
  {key:'training',label:'Training',copy:'Create one real backend experiment under shared evaluation conditions.',path:'/training',action:'Run Training'},
  {key:'quantum',label:'Classical / Quantum',copy:'Inspect supported classical models and simulator-backed quantum execution honestly.',path:'/quantum',action:'Open Quantum Lab'},
  {key:'comparison',label:'Comparison',copy:'Compare at least two ready models from the same completed experiment.',path:'/comparison',action:'Compare Models'},
  {key:'explainability',label:'Explainability',copy:'Measure feature influence for a ready model without implying biological causation.',path:'/explainability',action:'View Explanation'},
  {key:'prediction',label:'Prediction',copy:'Generate a research-only output from the exact ready-model input schema.',path:'/prediction',action:'Make Prediction'},
  {key:'report',label:'Report',copy:'Review experiment provenance, model records, limitations and report exports.',path:'/experiments',action:'View Experiment'},
];

const tone=(status:DemoStageStatus):'green'|'amber'|'red'|'blue'=>
  status==='COMPLETED'||status==='READY'?'green':
  status==='BLOCKED'||status==='UNAVAILABLE'?'red':
  status==='IN PROGRESS'?'amber':'blue';

export function DemoCenter(){
  const {draft,selectDataset}=useDraft();
  const qc=useQueryClient();
  const health=useQuery({queryKey:['health'],queryFn:qh.health,refetchInterval:15000});
  const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:5000});
  const models=useQuery({queryKey:['models'],queryFn:qh.models,refetchInterval:10000});
  const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments,refetchInterval:10000});
  const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary,staleTime:300000});
  const selectedDataset=useQuery({
    queryKey:['dataset',draft.dataset_id],
    queryFn:()=>qh.dataset(draft.dataset_id),
    enabled:Boolean(draft.dataset_id),
  });
  const [step,setStep]=useState(0);
  const register=useMutation({
    mutationFn:(slug:string)=>qh.registerBuiltIn(slug),
    onSuccess:dataset=>{
      selectDataset(dataset.id,dataset.provenance.recommended_duplicate_policy);
      setStep(1);
      qc.invalidateQueries({queryKey:['datasets']});
      qc.invalidateQueries({queryKey:['summary']});
      qc.invalidateQueries({queryKey:['experiments']});
      qc.invalidateQueries({queryKey:['models']});
    },
  });
  const dataset=selectedDataset.data;
  const activeDatasetId=dataset?.id===draft.dataset_id?draft.dataset_id:'';
  const state=deriveDemoState(
    activeDatasetId,
    experiments.data,
    models.data,
    jobs.data,
    health.isError?false:health.data?.quantum.available,
  );
  const readyCount=library.data?.filter(item=>item.demo_readiness.status==='ready').length??0;
  const processingCount=library.data?.filter(item=>item.demo_readiness.status==='requires_processing').length??0;
  const activeReadiness=library.data?.find(item=>item.slug===dataset?.provenance.library_slug)?.demo_readiness;
  const current=demoStages[step];
  const active=jobs.data?.filter(job=>['queued','running','cancel_requested'].includes(job.status)).length||0;
  const experiment=state.currentExperiment;
  const experimentPath=experiment?`/experiments/${experiment.id}`:'/experiments';
  const stageDetail=(key:DemoStageKey)=>{
    if(!activeDatasetId&&key!=='dataset')return 'Select a valid registered dataset before this stage can use the research pipeline.';
    if(key==='dataset')return dataset?'Active registered dataset is available to downstream routes.':'No active dataset is selected.';
    if(['preprocessing','features','pca'].includes(key))return 'Configuration is ready; preview execution is not persisted as completed state.';
    if(key==='quality')return 'The registered quality profile is available; open the stage to revalidate selected inputs.';
    if(key==='training'){
      if(state.currentJob)return state.currentJob.state;
      return experiment?`Latest current-dataset experiment: ${experiment.status}.`:'No experiment exists for the active dataset.';
    }
    if(key==='quantum')return health.data?.quantum.execution||'Quantum capability has not been reported yet.';
    if(key==='comparison')return state.readyModels.length>=2?'Two or more ready models belong to the current experiment.':'Requires two ready models from the current completed experiment.';
    if(key==='explainability'||key==='prediction')return state.readyModels.length?'A ready model belongs to the current completed experiment.':'Requires a ready model from the current dataset experiment.';
    if(key==='report')return experiment?'Experiment evidence and report export are tied to the current dataset.':'Requires a completed experiment for the active dataset.';
    return '';
  };
  const error=[health,jobs,models,experiments,library,selectedDataset,register].find(query=>query.error)?.error;
  return <div>
    <PageHeader eyebrow="SIH 2026 · Judge workflow" title="SIH Demo Center" description="Hybrid quantum–classical machine learning research platform for controlled medical classification experiments." actions={<Link className="btn btn-primary" to={current.key==='report'&&experiment?experimentPath:current.path}><PlayCircle size={14}/>{current.action}</Link>}/>
    <ErrorBanner error={error instanceof Error?error.message:undefined}/>
    <div className="demo-hero">
      <div><p className="eyebrow">TRUTHFUL, TRACEABLE DEMONSTRATION</p><h2>From public medical data to measured research evidence.</h2><p>Select a dataset, inspect each real pipeline stage, and review only artifacts that actually exist. Verified packages expose genuine precomputed research results; every dataset still supports live training.</p><div className="demo-facts"><span><Database size={14}/> {dataset?'1 active dataset':'No active dataset'}</span><span><FlaskConical size={14}/> {experiment?'Current experiment':'No current experiment'}</span><span><Activity size={14}/> {active} active jobs</span><span><CheckCircle2 size={14}/> {readyCount} verified demo ready</span><span><MonitorCog size={14}/> {processingCount} require processing</span></div></div>
      <div className="demo-visual"><Atom size={22}/><span>DATA</span><i/><span>CONTROLLED MODELS</span><i/><span>EVIDENCE</span></div>
    </div>

    <div className="two-grid mt-5" aria-live="polite">
      <Card title="Current dataset" description="The active registered dataset is the single source of truth for every downstream stage.">
        {dataset?<div className="space-y-3"><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-semibold">{dataset.name}</h3><p className="mt-1 text-xs muted">{dataset.provenance.domain} · {dataset.provenance.source}</p></div><div className="flex flex-wrap gap-1"><Badge tone="green">ACTIVE</Badge>{activeReadiness&&<Badge tone={activeReadiness.status==='ready'?'blue':'amber'}>{activeReadiness.status==='ready'?'VERIFIED DEMO READY':'REQUIRES PROCESSING'}</Badge>}</div></div><div className="grid grid-cols-2 gap-3 text-xs"><div><span className="metric-label">SAMPLES</span><strong className="block">{dataset.provenance.row_count.toLocaleString()}</strong></div><div><span className="metric-label">FEATURES</span><strong className="block">{dataset.provenance.feature_count}</strong></div><div><span className="metric-label">TARGET</span><strong className="block break-all">{dataset.provenance.target}</strong></div><div><span className="metric-label">CLASSES</span><strong className="block">{dataset.provenance.negative_label} / {dataset.provenance.positive_label}</strong></div></div><Link className="btn btn-outline" to="/datasets">Review provenance <ArrowRight size={13}/></Link></div>:<div><p className="text-sm muted">No dataset is selected. Choose one of the five packaged public datasets below or open Data Lab for a custom CSV.</p><Link className="btn btn-primary mt-4" to="/datasets">Choose Dataset <ArrowRight size={13}/></Link></div>}
      </Card>
      <Card title="Current experiment and model state" description="Only records related to the active dataset and its latest experiment appear here.">
        {experiment?<div className="space-y-3"><div className="flex items-center justify-between gap-3"><span className="mono text-xs">{shortId(experiment.id)}</span><StatusBadge value={experiment.status}/></div><p className="text-xs muted">Dataset {shortId(experiment.dataset_id)} · {(experiment.config.models||[]).map(kind=>modelLabels[kind]).join(', ')}</p><div className="flex flex-wrap gap-1">{state.readyModels.length?state.readyModels.map(model=><Badge tone="green" key={model.id}>{modelLabels[model.model_type]} · READY</Badge>):<Badge tone="amber">NO READY MODEL</Badge>}</div>{state.currentJob&&<div><div className="flex justify-between text-xs"><span className="muted">{state.currentJob.state}</span><strong>{state.currentJob.progress}%</strong></div><progress className="job-progress mt-2 w-full" max="100" value={state.currentJob.progress}/></div>}<Link className="btn btn-outline" to={experimentPath}>View Experiment <ArrowRight size={13}/></Link></div>:<p className="text-sm muted">No experiment exists for the active dataset. Previous experiments for other datasets do not unlock this workflow.</p>}
      </Card>
    </div>

    <Card className="mt-5" title="Quickstart · Medical Dataset Library" description="Register one verified packaged dataset directly. Source files, SHA-256 integrity, targets and provenance remain owned by the existing backend catalog.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">{library.data?.map(item=>{const selected=dataset?.provenance.library_slug===item.slug;return <article className={'rounded-xl border p-3 '+(selected?'border-primary bg-primary/5':'')} key={item.slug}><div className="flex items-start justify-between gap-2"><div className="flex flex-wrap gap-1"><Badge tone={selected?'green':'blue'}>{selected?'ACTIVE':'BUILT-IN'}</Badge><Badge tone={item.demo_readiness.status==='ready'?'blue':'amber'}>{item.demo_readiness.status==='ready'?'VERIFIED DEMO READY':'REQUIRES PROCESSING'}</Badge></div><span className="text-[10px] muted">{item.domain}</span></div><h3 className="mt-2 text-sm font-semibold">{item.name}</h3><p className="mt-2 text-[11px] muted">{item.row_count.toLocaleString()} samples · {item.feature_count} features</p><p className="mt-1 text-[11px]"><strong>Target:</strong> {item.target}</p><p className="mt-1 text-[10px] muted">{item.negative_label} / {item.positive_label}</p><p className="mt-1 text-[10px] muted">{item.demo_readiness.status==='ready'?'Instant research result available':'Run live training to generate results'}</p><Button className="mt-3 w-full" variant={selected?'outline':'primary'} disabled={register.isPending||selected} onClick={()=>register.mutate(item.slug)}>{selected?'Selected':'Use Dataset'}</Button></article>})}</div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs muted">Need a custom deidentified CSV or full attribution details?</p><Link className="btn btn-outline" to="/datasets">Open Medical Dataset Library <ArrowRight size={13}/></Link></div>
    </Card>

    <Card className="mt-5" title="Judge path · Research pipeline" description="READY means the next real action is available. COMPLETED is used only for persisted backend execution state.">
      <div className="demo-spotlight"><div><div className="eyebrow">CURRENT STAGE · {String(step+1).padStart(2,'0')}</div><h2>{current.label}</h2><p>{stageDetail(current.key)}</p></div><Badge tone={tone(state.stages[current.key])}>{state.stages[current.key]}</Badge></div>
      <div className="demo-controls"><Button variant="outline" disabled={step===0} onClick={()=>setStep(index=>Math.max(0,index-1))}><ArrowLeft size={13}/>Previous</Button><div className="demo-step-count">Step {step+1} of {demoStages.length}</div><Button variant="outline" disabled={step===demoStages.length-1} onClick={()=>setStep(index=>Math.min(demoStages.length-1,index+1))}>Next<ArrowRight size={13}/></Button></div>
      <div className="demo-timeline">{demoStages.map((stage,index)=><div className={'demo-step '+(index===step?'is-selected':'')} data-stage={stage.key} key={stage.key}><button type="button" className="demo-step-marker" aria-label={`Select ${stage.label} stage`} onClick={()=>setStep(index)}>{String(index+1).padStart(2,'0')}</button>{index<demoStages.length-1&&<div className="demo-step-line"/>}<div className="demo-step-copy"><div className="flex items-center justify-between gap-3"><div><h3>{stage.label}</h3><p>{stage.copy}</p><small className="mt-1 block muted">{stageDetail(stage.key)}</small></div><div className="flex items-center gap-2"><Badge tone={tone(state.stages[stage.key])}>{state.stages[stage.key]}</Badge><Link className="btn btn-outline px-3" to={stage.key==='report'&&experiment?experimentPath:stage.path} onClick={()=>setStep(index)}>{stage.action} <ArrowRight size={13}/></Link></div></div></div></div>)}</div>
    </Card>

    <div className="two-grid mt-5">
      <Card title="Live backend readiness"><div className="space-y-3"><div className="readiness-row"><span><span className={'status-dot '+(health.data?'is-live':'is-offline')}/>Backend</span><strong>{health.data?'Connected':'Unavailable'}</strong></div><div className="readiness-row"><span><span className={'status-dot '+(dataset?'is-live':'is-offline')}/>Active dataset</span><strong>{dataset?dataset.name:'Not selected'}</strong></div><div className="readiness-row"><span><span className={'status-dot '+(health.data?.quantum.available?'is-live':'is-offline')}/>Quantum capability</span><strong>{health.data?.quantum.available?'Local simulation available':'Not available'}</strong></div></div><Notice tone="amber">Present only a backend-verified packaged result or a completed live experiment. This page never manufactures readiness.</Notice></Card>
      <Card title="Scientific guardrails"><div className="space-y-3"><p className="text-sm muted"><ShieldCheck size={15} className="mr-2 inline text-emerald-600"/>Measured benchmark outputs are research evidence, not clinical validation.</p><p className="text-sm muted"><Zap size={15} className="mr-2 inline text-purple-600"/>Quantum execution is local simulation unless the backend explicitly reports otherwise; no advantage is claimed.</p><p className="text-sm muted"><Sparkles size={15} className="mr-2 inline text-amber-600"/>Predictions are research outputs, never diagnoses, treatment guidance or medical recommendations.</p></div></Card>
    </div>
  </div>;
}

export function SettingsPage(){
  const [theme,setTheme]=useState<'research'|'dark'>(()=>localStorage.getItem('qhealth-theme')==='dark'?'dark':'research');
  const [density,setDensity]=useState<'comfortable'|'compact'>(()=>(localStorage.getItem('qhealth-density') as 'comfortable'|'compact')||'comfortable');
  const [motion,setMotion]=useState<'full'|'reduced'>(()=>(localStorage.getItem('qhealth-motion') as 'full'|'reduced')||'full');
  const [inspector,setInspector]=useState(localStorage.getItem('qhealth-inspector')!=='hidden');
  useEffect(()=>{localStorage.setItem('qhealth-theme',theme);localStorage.setItem('qhealth-density',density);localStorage.setItem('qhealth-motion',motion);localStorage.setItem('qhealth-inspector',inspector?'visible':'hidden');window.dispatchEvent(new Event('qhealth-settings-changed'))},[theme,density,motion,inspector]);
  return <div><PageHeader eyebrow="Workspace controls" title="Settings center" description="Tune presentation density, motion and research-facing preferences. Credentials and biomedical records are never stored here."/><div className="settings-grid"><Card title="Appearance" description="Keep the default research-light surface for judge presentations or switch to a deep research theme."><div className="settings-option-grid"><button className={'settings-option '+(theme==='research'?'is-selected':'')} onClick={()=>setTheme('research')}><MonitorCog size={18}/><span><strong>Research light</strong><small>White surfaces · navy evidence UI</small></span></button><button className={'settings-option '+(theme==='dark'?'is-selected':'')} onClick={()=>setTheme('dark')}><Moon size={18}/><span><strong>Deep research</strong><small>Low-glare dark workspace</small></span></button></div></Card><Card title="Layout & motion" description="Preferences apply immediately and remain local to this browser."><div className="settings-form"><label className="field"><span>Density</span><Select value={density} onChange={e=>setDensity(e.target.value as typeof density)}><option value="comfortable">Comfortable</option><option value="compact">Compact</option></Select></label><label className="field"><span>Motion</span><Select value={motion} onChange={e=>setMotion(e.target.value as typeof motion)}><option value="full">Full motion</option><option value="reduced">Reduced motion</option></Select></label><label className="settings-check"><input type="checkbox" checked={inspector} onChange={e=>setInspector(e.target.checked)}/><span><strong>Show context inspector</strong><small>Live backend, registry and job context on wide screens.</small></span></label></div></Card><Card title="Research safeguards" description="These defaults are product constraints, not decorative copy."><div className="space-y-3"><div className="safeguard-row"><CheckCircle2 size={16}/><span>Clinical disclaimer remains visible across the workspace.</span></div><div className="safeguard-row"><CheckCircle2 size={16}/><span>Quantum capability is reported, never inferred as advantage.</span></div><div className="safeguard-row"><CheckCircle2 size={16}/><span>API tokens stay in memory and are omitted from local storage.</span></div></div><Link className="btn btn-outline mt-4" to="/demo"><PlayCircle size={14}/>Open SIH Demo Center</Link></Card><Card title="Connection" description="Use the connection control in the top bar to provide an optional local bearer token."><div className="flex items-start gap-3 text-sm muted"><Activity size={17} className="mt-0.5 text-primary"/><p>The live connection indicator and status inspector are driven by the health, summary and job endpoints. No secrets or filesystem paths are exposed.</p></div></Card></div></div>;
}