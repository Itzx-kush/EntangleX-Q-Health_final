import {useEffect,useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {ArrowRight,FileText,Play,ShieldAlert,SlidersHorizontal} from 'lucide-react';
import {Button,Card,Badge,Input,Select} from '../components/ui';
import {ErrorBanner,EmptyState,Loading,MetricCard,ModelSelect,Notice,PageHeader,StatusBadge,JsonDisclosure,metricNames} from '../components/Shared';
import {InfluenceBars} from '../components/Charts';
import {StageNav} from './ResearchPagesCore';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {dateTime,metric,modelLabels,seconds,shortId,isHybridModel,isQiskitQuantumModel,isQuantumFamilyModel} from '../utils/format';
import type {EvidencePair,Experiment,Influence,Job,ModelKind,ModelRecord,PerturbationType,RobustnessEvidence} from '../types/qhealth';
import {GlareHover,BorderGlow} from '../components/reactbits';
import {DistributionStrip,PipelineFlow,ProbabilityBand,StatusStrip,WorkbenchRail} from '../components/TremorWorkbench';
import {VerifiedComparison,VerifiedExplainability,VerifiedPrediction,VerifiedRobustness,VerifiedTraining} from '../components/VerifiedDemoViews';
import {ResearchResultsCenter} from '../components/ResearchResultsCenter';
import {ExplainabilityResearchLab} from '../components/ExplainabilityResearchLab';
import {ResearchPredictionLab,type CrossModelPrediction} from '../components/ResearchPredictionLab';
import {RobustnessEvidenceLab} from '../components/RobustnessEvidenceLab';
import {QuantumEvidenceLab} from '../components/QuantumEvidenceLab';
import {QuantumCircuitExplorer,QuantumContextPanel,QuantumPipeline,QuantumResourcePanel,QuantumStatePanel} from '../components/quantum';
import type {QuantumVisualizationContract,QuantumVisualizationEvidenceRequest,QuantumVisualizationPreviewRequest,QuantumVisualizationSimulationRequest} from '../types/quantumVisualization';
import type {Circuit} from '../types/qhealth';
import {useVerifiedDemo} from '../hooks/useVerifiedDemo';
import {useResearchRecorder} from '../research/useResearchHistory';
import {experimentActivity,explanationActivity,predictionActivity} from '../research/historyRecords';


function latestExperimentForDataset(experiments:Experiment[]|undefined,datasetId:string){
 return (experiments||[]).filter(experiment=>experiment.dataset_id===datasetId).sort((a,b)=>b.created_at.localeCompare(a.created_at))[0];
}

function contextModels(models:ModelRecord[]|undefined,experiments:Experiment[]|undefined,datasetId:string,scope:'active'|'all'){
 if(scope==='all'||!datasetId)return models||[];
 const experiment=latestExperimentForDataset(experiments,datasetId);
 return experiment?(models||[]).filter(model=>model.dataset_id===datasetId&&model.experiment_id===experiment.id):[];
}

function measuredDifference(quantum:number|null|undefined,classical:number|null|undefined){
 return quantum===null||quantum===undefined||classical===null||classical===undefined?null:quantum-classical;
}

const activeJobStatuses=['queued','running','resuming','checkpointing','pause_requested','cancel_requested'];
function executionLabel(model:ModelRecord){
 if(model.status==='ready'||model.status==='completed')return {icon:'✓',label:'Completed',tone:'text-emerald-600'};
 if(model.status==='failed')return {icon:'✕',label:'Failed',tone:'text-red-600'};
 if(model.status==='cancelled')return {icon:'—',label:'Cancelled',tone:'muted'};
 if(model.status==='running'){
  const progress=model.progress==null?'':` · ${model.progress}%`;
  return {icon:'◉',label:`Training${progress}`,tone:'text-primary'};
 }
 return {icon:'○',label:'Queued',tone:'muted'};
}
function TrainingJobCard({job,busy,onAction}:{job:Job;busy:boolean;onAction:(action:'pause'|'resume'|'retry'|'cancel')=>void}){
 const title=job.experiment_name||`Experiment ${shortId(job.experiment_id)}`; const models=job.models||[]; const determinate=job.total_units!==null&&job.total_units!==undefined;
 return <div className="rounded-xl border p-3"><div className="flex items-center justify-between gap-3"><Link className="font-semibold text-primary" to={'/experiments/'+job.experiment_id}>{title}</Link><StatusBadge value={job.status}/></div><p className="mt-1 text-xs muted">{job.state}</p>
  <div className="mt-3 flex items-center justify-between text-xs"><span className="muted">{job.current_phase||'Overall progress'}</span><strong>{determinate?`${job.progress}%`:'In progress'}</strong></div><progress className="job-progress mt-2 w-full" max="100" value={determinate?job.progress:undefined}/>
  <div className="mt-2 flex flex-wrap gap-3 text-xs muted"><span>{job.completed_units??0}/{job.total_units??'—'} units complete</span><span>Attempt {job.attempt_count??0}</span><span>Resumes {job.resume_count??0}</span>{job.current_checkpoint_id&&<span>Checkpoint {shortId(job.current_checkpoint_id)}</span>}</div>
  <details className="mt-3 rounded-lg border px-3 py-2"><summary className="cursor-pointer text-xs font-semibold">Model execution details · {models.length} model{models.length===1?'':'s'} selected</summary><div className="mt-2 divide-y">{models.map(model=>{const state=executionLabel(model);return <div className="flex items-center justify-between gap-3 py-2 text-xs" key={model.id}><span className="flex min-w-0 items-center gap-2"><span aria-hidden className={state.tone}>{state.icon}</span><span className="truncate font-medium">{modelLabels[model.model_type]}</span></span><span className={state.tone}>{state.label}</span></div>})}</div></details>
  <div className="mt-2 flex flex-wrap gap-2">{['running','resuming','checkpointing'].includes(job.status)&&<Button variant="outline" disabled={busy} onClick={()=>onAction('pause')}>Pause safely</Button>}{['paused','recoverable'].includes(job.status)&&<Button variant="outline" disabled={busy} onClick={()=>onAction('resume')}>Resume</Button>}{['failed','recoverable','interrupted'].includes(job.status)&&<Button variant="outline" disabled={busy} onClick={()=>onAction('retry')}>Retry from start</Button>}{!['succeeded','partial','failed','cancelled'].includes(job.status)&&<Button variant="outline" disabled={busy} onClick={()=>onAction('cancel')}>{busy?'Updating…':'Request cancellation'}</Button>}</div>
  {job.errors.length>0&&<JsonDisclosure label="Recorded model failures" value={job.errors}/>}</div>;
}

export function Training(){
 const demo=useVerifiedDemo();
 return demo.active?<VerifiedTraining/>:<LiveTraining/>;
}
function LiveTraining(){
 const {draft,update,pipeline,quantum}=useDraft();
 const history=useResearchRecorder();
 const [busyJobId,setBusyJobId]=useState('');
 const [controlError,setControlError]=useState('');
 const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:query=>query.state.data?.some(job=>activeJobStatuses.includes(job.status))?3000:false});
 const dataset=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});
 const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary,staleTime:300000});
 const alignment=useQuery({queryKey:['alignment'],queryFn:qh.alignment,staleTime:300000});
 const readiness=library.data?.find(item=>item.slug===dataset.data?.provenance.library_slug)?.demo_readiness;
 const mutation=useMutation({mutationFn:()=>qh.createJob(draft),onSuccess:r=>{update({dataset_id:r.experiment.dataset_id});jobs.refetch();void history.record(experimentActivity(r.experiment))}});
 const controlJob=async(job:Job,action:'pause'|'resume'|'retry'|'cancel')=>{setBusyJobId(job.id);setControlError('');try{if(action==='pause')await qh.pauseJob(job.id);else if(action==='resume')await qh.resumeJob(job.id);else if(action==='retry')await qh.retryJob(job.id);else await qh.cancelJob(job.id);await jobs.refetch()}catch(error){setControlError(error instanceof Error?error.message:'The job action could not be completed. Refresh the job list and try again.')}finally{setBusyJobId('')}};
 const qiskitSelected=draft.models.some(isQiskitQuantumModel);const hybridSelected=draft.models.some(isHybridModel);const quantumFamilySelected=draft.models.some(isQuantumFamilyModel);
 const dimensionsConflict=qiskitSelected&&hybridSelected&&draft.quantum.qubits!==draft.hybrid.qubits;
 const toggle=(kind:ModelKind)=>{const next=draft.models.includes(kind)?draft.models.filter(x=>x!==kind):[...draft.models,kind];const addsQiskit=isQiskitQuantumModel(kind)&&!draft.models.includes(kind);const addsHybrid=isHybridModel(kind)&&!draft.models.includes(kind);update({models:next});if(addsQiskit&&!next.some(isHybridModel))pipeline({pca_components:draft.quantum.qubits,angle_scaling:true});if(addsHybrid&&!next.some(isQiskitQuantumModel))pipeline({pca_components:draft.hybrid.qubits,angle_scaling:true})};
 const option=(kind:ModelKind,category:'Classical'|'Quantum'|'Hybrid quantum-classical',enabled=true)=>{const capability=alignment.data?.models.find(item=>item.model_id===kind);const runnable=enabled&&(capability?.executable??kind!=='hybrid_pennylane_torch');return <GlareHover key={kind}><button type="button" disabled={!runnable} aria-disabled={!runnable} onClick={()=>runnable&&toggle(kind)} className={'w-full rounded-xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-60 '+(draft.models.includes(kind)?'border-primary bg-primary/5':'hover:bg-muted')}><div className="flex items-center justify-between gap-2"><strong>{modelLabels[kind]}</strong><Badge tone={runnable?(draft.models.includes(kind)?(category==='Classical'?'blue':'purple'):'blue'):'amber'}>{runnable?(draft.models.includes(kind)?'Selected':category):(capability?.implementation_status||'Pending')}</Badge></div><small className="mt-1 block muted">{runnable?(category==='Classical'?'Classical baseline':category):capability?.implementation_status==='UNAVAILABLE'?'Dependencies unavailable — execution disabled':'Capability status loading'}</small></button></GlareHover>};
 return <div>
  <PageHeader eyebrow="01 / Train" title="Training" description="Configure one controlled experiment with shared partitions, preprocessing and evaluation conditions across supported classical and quantum models." actions={<Button disabled={!draft.dataset_id||!draft.models.length||mutation.isPending||dimensionsConflict} onClick={()=>mutation.mutate()}><Play size={14}/>{mutation.isPending?'Creating job…':'Create training experiment'}</Button>}/>
  <StageNav current="/training"/><WorkbenchRail items={[{label:'Dataset',value:draft.dataset_id?shortId(draft.dataset_id):'None',detail:'Active training input',tone:dataset.data?'green':'amber'},{label:'Models selected',value:draft.models.length,detail:'Classical, quantum and hybrid',tone:draft.models.length?'blue':'slate'},{label:'Active jobs',value:(jobs.data||[]).filter(job=>activeJobStatuses.includes(job.status)).length,detail:'Backend execution queue',tone:'purple'},{label:'Readiness',value:readiness?.status||'Not reported',detail:'Demo artifact availability',tone:readiness?.status==='ready'?'green':'slate'}]}/><PipelineFlow items={[{label:'Dataset',detail:'Registered research input',status:draft.dataset_id?'complete':'blocked'},{label:'Models',detail:`${draft.models.length} selected`,status:draft.models.length?'complete':'current'},{label:'Configure',detail:'Shared evaluation contract',status:draft.dataset_id&&draft.models.length?'current':'waiting'},{label:'Execute',detail:'Backend training job',status:(jobs.data||[]).some(job=>activeJobStatuses.includes(job.status))?'current':'waiting'},{label:'Evidence',detail:'Persisted experiment record',status:(jobs.data||[]).some(job=>['succeeded','partial'].includes(job.status))?'complete':'waiting'}]}/><ErrorBanner error={(mutation.error as Error)?.message}/>{readiness&&<Notice tone={readiness.status==='ready'?'blue':'amber'}>{readiness.status==='ready'?'A verified precomputed SIH demo is available for this dataset. You can still start a new live experiment.':'This dataset requires processing; no precomputed demo artifact is packaged. Live training remains available.'}</Notice>}
  <Card className="mt-5" title="Model families" description="Choose the estimators that receive the same configured representation.">
   <p className="metric-label mb-2">CLASSICAL BASELINES</p><div className="grid gap-3 md:grid-cols-3">{(['logistic_regression','svm','random_forest'] as ModelKind[]).map(x=>option(x,'Classical'))}</div>
   <div className="my-5 border-t"/><p className="metric-label mb-2">QISKIT QUANTUM MODELS</p>
   <div className="grid gap-3 md:grid-cols-3">{(['vqc','qsvc','qnn'] as ModelKind[]).map(x=>option(x,'Quantum'))}</div>
   <div className="my-5 border-t"/><p className="metric-label mb-2">PENNYLANE HYBRID · HYBRID QUANTUM-CLASSICAL</p>
   <div className="grid gap-3 md:grid-cols-3">{option('hybrid_pennylane_torch','Hybrid quantum-classical')}</div>
   {quantumFamilySelected&&<Notice>Quantum-family comparisons use one shared reduced representation, calibration disabled and no class-weighting. No quantum-advantage claim is made.</Notice>}{dimensionsConflict&&<Notice tone="amber">Qiskit and PennyLane qubits must match for the shared comparison representation.</Notice>}<p className="mt-3 text-xs muted">Shared comparison representation: {draft.pipeline.pca_components??'disabled'} dimensions</p>
  </Card>
  <div className="two-grid mt-5">
   <Card title="Shared evaluation contract" description="These settings are common to the selected model set."><div className="grid gap-4 md:grid-cols-2">
    <label className="field"><span>Random seed</span><Input type="number" value={draft.seed} onChange={e=>update({seed:Number(e.target.value)})}/></label>
    <label className="field"><span>Held-out test fraction</span><Input type="number" min=".1" max=".4" step=".05" value={draft.test_size} onChange={e=>update({test_size:Number(e.target.value)})}/></label>
    <label className="field"><span>CV folds</span><Input type="number" min="2" max="10" value={draft.cv_folds} onChange={e=>update({cv_folds:Number(e.target.value)})}/></label>
    <label className="field"><span>Maximum samples</span><Input type="number" min="30" value={draft.max_samples??''} onChange={e=>update({max_samples:e.target.value?Number(e.target.value):null})}/></label>
	    <label className="field"><span>Operating point</span><Select value={draft.threshold_strategy} onChange={e=>update({threshold_strategy:e.target.value as 'fixed'|'target_sensitivity'})}><option value="fixed">Fixed threshold</option><option value="target_sensitivity">Sensitivity-first</option></Select></label>
	    {draft.threshold_strategy==='fixed'?<label className="field"><span>Fixed research threshold</span><Input type="number" min=".01" max=".99" step=".01" value={draft.probability_threshold} onChange={e=>update({probability_threshold:Number(e.target.value)})}/></label>:<label className="field"><span>Target sensitivity</span><Input type="number" min=".01" max="1" step=".01" value={draft.target_sensitivity} onChange={e=>update({target_sensitivity:Number(e.target.value)})}/><small>Selected from out-of-fold validation; not a clinically validated screening cutoff.</small></label>}
    <label className="field"><span>Duplicate policy</span><Select value={draft.duplicate_policy} onChange={e=>update({duplicate_policy:e.target.value as any})}><option value="reject">Reject exact duplicates</option><option value="drop_exact">Drop exact duplicates</option></Select></label>
    <label className="field"><span>Calibration</span><Select disabled={quantumFamilySelected} value={draft.calibration} onChange={e=>update({calibration:e.target.value as any})}><option value="none">None</option><option value="sigmoid">Sigmoid / Platt</option><option value="isotonic">Isotonic</option></Select></label>
    <label className="field"><span>Calibration folds</span><Input type="number" min="2" max="5" disabled={draft.calibration==='none'||quantumFamilySelected} value={draft.calibration_folds} onChange={e=>update({calibration_folds:Number(e.target.value)})}/></label>
   </div></Card>
   <Card title="Classical parameters" description="Only values accepted by the backend training schema are exposed."><div className="grid gap-4 md:grid-cols-2">
    <label className="field"><span>Logistic C</span><Input type="number" min=".001" value={draft.parameters.logistic_c} onChange={e=>update({parameters:{...draft.parameters,logistic_c:Number(e.target.value)}})}/></label>
    <label className="field"><span>SVM / QSVC C</span><Input type="number" min=".001" value={draft.parameters.svm_c} onChange={e=>update({parameters:{...draft.parameters,svm_c:Number(e.target.value)}})}/></label>
    <label className="field"><span>SVM kernel</span><Select value={draft.parameters.svm_kernel} onChange={e=>update({parameters:{...draft.parameters,svm_kernel:e.target.value as any}})}><option value="rbf">RBF</option><option value="linear">Linear</option></Select></label>
    <label className="field"><span>Random forest trees</span><Input type="number" min="10" max="500" value={draft.parameters.forest_trees} onChange={e=>update({parameters:{...draft.parameters,forest_trees:Number(e.target.value)}})}/></label>
    <label className="field"><span>Forest maximum depth</span><Input type="number" min="1" max="100" value={draft.parameters.forest_max_depth??''} onChange={e=>update({parameters:{...draft.parameters,forest_max_depth:e.target.value?Number(e.target.value):null}})}/></label>
    <label className="field"><span>Class weighting</span><Select disabled={quantumFamilySelected} value={draft.parameters.class_weight||'none'} onChange={e=>update({parameters:{...draft.parameters,class_weight:e.target.value==='balanced'?'balanced':null}})}><option value="none">None</option><option value="balanced">Balanced</option></Select></label>
   </div></Card>
  </div>
  {qiskitSelected&&<BorderGlow className="mt-5"><Card title="Qiskit quantum configuration" description="QNN, VQC and QSVC use the existing Qiskit configuration contract.">
   <div className="grid gap-4 md:grid-cols-3">
    <label className="field"><span>Provider</span><Input disabled value="Qiskit Local Simulator"/></label>
    <label className="field"><span>Backend</span><Select value={draft.quantum.backend} onChange={e=>quantum({backend:e.target.value as any})}><option value="statevector">Statevector</option><option value="aer">Aer</option></Select></label>
    <label className="field"><span>Qubits</span><Input type="number" min="2" max="8" value={draft.quantum.qubits} onChange={e=>{const q=Number(e.target.value);quantum({qubits:q});if(qiskitSelected)pipeline({pca_components:q})}}/></label>
    <label className="field"><span>Feature-map reps</span><Input type="number" min="1" max="3" value={draft.quantum.feature_map_reps} onChange={e=>quantum({feature_map_reps:Number(e.target.value)})}/></label>
    <label className="field"><span>Ansatz reps</span><Input type="number" min="1" max="3" value={draft.quantum.ansatz_reps} onChange={e=>quantum({ansatz_reps:Number(e.target.value)})}/></label>
    <label className="field"><span>Entanglement</span><Select value={draft.quantum.entanglement} onChange={e=>quantum({entanglement:e.target.value as any})}><option value="linear">Linear</option><option value="full">Full</option></Select></label>
    <label className="field"><span>Optimizer</span><Select value={draft.quantum.optimizer} onChange={e=>quantum({optimizer:e.target.value as any})}><option value="COBYLA">COBYLA</option><option value="SPSA">SPSA</option></Select></label>
    <label className="field"><span>Maximum iterations</span><Input type="number" min="5" max="300" value={draft.quantum.maxiter} onChange={e=>quantum({maxiter:Number(e.target.value)})}/></label>
    <label className="field"><span>Shots</span><Input type="number" min="128" max="16384" value={draft.quantum.shots} onChange={e=>quantum({shots:Number(e.target.value)})}/></label>
    <label className="field"><span>Noise probability</span><Input type="number" min="0" max=".1" step=".01" disabled={draft.quantum.backend!=='aer'} value={draft.quantum.noise_probability} onChange={e=>quantum({noise_probability:Number(e.target.value)})}/></label>
   </div>
   <div className="mt-4 flex flex-wrap gap-4 text-xs"><label className="flex items-center gap-2"><input type="checkbox" checked={draft.pipeline.angle_scaling} onChange={e=>pipeline({angle_scaling:e.target.checked})}/>Shared angle scaling</label><label className="flex items-center gap-2"><input type="checkbox" checked={draft.pipeline.pca_components!==null} onChange={e=>pipeline({pca_components:e.target.checked?draft.quantum.qubits:null})}/>Enable PCA</label></div>
  </Card></BorderGlow>}
  {hybridSelected&&<BorderGlow className="mt-5"><Card title="PennyLane + PyTorch Hybrid" description="Classical preprocessing → PennyLane trainable quantum feature layer → expectation values → PyTorch classifier."><div className="grid gap-4 md:grid-cols-3"><label className="field"><span>Provider</span><Input disabled value="PennyLane Local Simulator"/></label><label className="field"><span>Hybrid qubits</span><Input type="number" min="2" max="8" value={draft.hybrid.qubits} onChange={e=>{const qubits=Number(e.target.value);update({hybrid:{...draft.hybrid,qubits}});if(!qiskitSelected)pipeline({pca_components:qubits,angle_scaling:true})}}/></label><label className="field"><span>Quantum layers</span><Input type="number" min="1" max="6" value={draft.hybrid.quantum_layers} onChange={e=>update({hybrid:{...draft.hybrid,quantum_layers:Number(e.target.value)}})}/></label><label className="field"><span>Feature map</span><Input disabled value="AngleEmbedding"/></label><label className="field"><span>Hidden dimensions</span><Input value={draft.hybrid.classical_hidden_dimensions.join(",")} onChange={e=>update({hybrid:{...draft.hybrid,classical_hidden_dimensions:e.target.value.split(",").map(value=>Number(value.trim())).filter(Number.isFinite)}})}/></label><label className="field"><span>Activation</span><Select value={draft.hybrid.classical_activation} onChange={e=>update({hybrid:{...draft.hybrid,classical_activation:e.target.value as "relu"|"tanh"}})}><option value="relu">ReLU</option><option value="tanh">Tanh</option></Select></label><label className="field"><span>Optimizer</span><Select value={draft.hybrid.optimizer} onChange={e=>update({hybrid:{...draft.hybrid,optimizer:e.target.value as "adam"|"sgd"}})}><option value="adam">Adam</option><option value="sgd">SGD</option></Select></label><label className="field"><span>Learning rate</span><Input type="number" step="0.0001" value={draft.hybrid.learning_rate} onChange={e=>update({hybrid:{...draft.hybrid,learning_rate:Number(e.target.value)}})}/></label><label className="field"><span>Epochs</span><Input type="number" min="1" max="500" value={draft.hybrid.epochs} onChange={e=>update({hybrid:{...draft.hybrid,epochs:Number(e.target.value)}})}/></label><label className="field"><span>Batch size</span><Input type="number" min="1" max="256" value={draft.hybrid.batch_size} onChange={e=>update({hybrid:{...draft.hybrid,batch_size:Number(e.target.value)}})}/></label><label className="field"><span>Sample cap</span><Input type="number" min="30" max="2000" value={draft.hybrid.sample_cap} onChange={e=>update({hybrid:{...draft.hybrid,sample_cap:Number(e.target.value)}})}/></label><label className="field"><span>Backend</span><Input disabled value={draft.hybrid.backend}/></label></div><Notice tone="amber">CPU local simulation only. Hardware execution is unavailable; quantum advantage is not established.</Notice></Card></BorderGlow>}
  <Card className="mt-5" title="Execution state" description="Durable jobs refresh automatically and expose safe pause, resume, retry, and cancellation controls."><ErrorBanner error={controlError||undefined}/><div className="space-y-3">{jobs.isLoading?<Loading/>:jobs.data?.length?jobs.data.slice(0,8).map(job=><TrainingJobCard key={job.id} job={job} busy={busyJobId===job.id} onAction={action=>void controlJob(job,action)}/>):<EmptyState title="No training jobs">Create an experiment to populate the execution registry.</EmptyState>}</div></Card>
 </div>;
}

export function Comparison(){
 const demo=useVerifiedDemo();
 return demo.active?<VerifiedComparison/>:<LiveComparison/>;
}
function LiveComparison(){
 const {draft}=useDraft();
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const [id,setId]=useState('');
 const visibleExperiments=scope==='active'&&draft.dataset_id?(experiments.data||[]).filter(item=>item.dataset_id===draft.dataset_id):experiments.data||[];
 const selected=useQuery({queryKey:['comparison',id],queryFn:()=>qh.comparison(id),enabled:Boolean(id),refetchInterval:5000});
 const protocol=useMutation({mutationFn:()=>qh.createControlledComparison(id),onSuccess:()=>void selected.refetch()});
 const [pairKey,setPairKey]=useState('');
 useEffect(()=>{if(!visibleExperiments.some(item=>item.id===id)){setId(visibleExperiments[0]?.id||'');setPairKey('')}},[id,scope,draft.dataset_id,experiments.data]);
 const data=selected.data;
 const experiment=visibleExperiments.find(item=>item.id===id);
 const dataset=useQuery({queryKey:['dataset',data?.dataset_id],queryFn:()=>qh.dataset(data!.dataset_id),enabled:Boolean(data?.dataset_id),staleTime:300000});
 const pair=data?.pairs.find(item=>`${item.quantum_model}:${item.classical_model}`===pairKey)||data?.pairs[0];
 const evidenceMetrics=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 return <div>
  <PageHeader eyebrow="02 / Results" title="Research Results Center" description="Understand the persisted experiment outcome, compare model families, inspect stability, and continue into deeper research evidence." actions={<Link className="btn btn-outline" to="/explainability"><ArrowRight size={14}/>Explainability</Link>}/>
  <StageNav current="/comparison"/><WorkbenchRail items={[{label:'Experiment',value:id?shortId(id):'None',detail:'Controlled evidence context',tone:id?'blue':'slate'},{label:'Models',value:data?.models.length??'—',detail:'Persisted model records',tone:'purple'},{label:'Ready models',value:data?.models.filter(item=>item.status==='ready').length??'—',detail:'Measured outputs available',tone:'green'},{label:'Evidence pairs',value:data?.pairs.length??'—',detail:'Classical / quantum comparisons',tone:'amber'}]}/>{data&&<DistributionStrip items={[{label:'Classical',value:data.models.filter(item=>!isQuantumFamilyModel(item.model_type)).length,tone:'blue'},{label:'Qiskit quantum',value:data.models.filter(item=>isQiskitQuantumModel(item.model_type)).length,tone:'purple'},{label:'PennyLane hybrid',value:data.models.filter(item=>isHybridModel(item.model_type)).length,tone:'amber'}]}/>}<ErrorBanner error={(experiments.error as Error)?.message||(selected.error as Error)?.message}/>
  <Card className="mt-5" title="Experiment context"><div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Record scope</span><Select aria-label="Comparison record scope" value={scope} onChange={e=>setScope(e.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset (all its experiments)</option><option value="all">All registered models</option></Select></label><label className="field"><span>Experiment</span><Select value={id} onChange={e=>{setId(e.target.value);setPairKey('')}}><option value="">Select experiment</option>{visibleExperiments.map(item=><option value={item.id} key={item.id}>{shortId(item.id)} · {item.status}</option>)}</Select></label></div>{scope==='active'&&<Notice tone="blue">Only experiments for the active dataset are shown. Historical experiments remain available through “All registered models”.</Notice>}</Card>
  {selected.isLoading&&id&&<div className="mt-4"><Loading/></div>}
  {data&&experiment&&<>
   <div className="mt-5"><ResearchResultsCenter experiment={experiment} dataset={dataset.data} models={data.models} comparison={data} mode="live"/></div>
   <Card className="mt-5" title="Controlled comparison protocol" description="Persisted scientific matching evidence; never a model ranking.">
    <div className="flex flex-wrap items-center justify-between gap-3"><div>{data.controlled_protocol?<><StatusBadge value={data.controlled_protocol.status}/><span className="ml-2 mono text-[10px] muted">{data.controlled_protocol.protocol_fingerprint}</span></>:<Badge tone="amber">INCOMPLETE EVIDENCE · LEGACY / NOT PERSISTED</Badge>}</div><Button variant="outline" disabled={protocol.isPending||!data.pairs.length} onClick={()=>protocol.mutate()}><ShieldAlert size={13}/>{protocol.isPending?'Verifying…':'Verify and persist protocol'}</Button></div>
    <ErrorBanner error={(protocol.error as Error)?.message}/>
    {pair?.controlled_protocol_pair?<div className="mt-4"><Notice tone={pair.controlled_protocol_pair.status.startsWith('CONTROLLED')?'blue':'amber'}><strong>{pair.controlled_protocol_pair.status.replaceAll('_',' ')}</strong> — status describes experimental control, not model quality.</Notice><div className="table-wrap mt-3"><table className="data-table"><thead><tr><th>Control</th><th>Status</th><th>Evidence</th></tr></thead><tbody>{pair.controlled_protocol_pair.control_checks.map(check=><tr key={check.name}><td>{check.name.replaceAll('_',' ')}</td><td><StatusBadge value={check.status}/></td><td className="text-xs muted">{check.reason}</td></tr>)}</tbody></table></div></div>:<Notice tone="amber">No persisted protocol exists for this selected pair. Historical fairness fields are not promoted to controlled status.</Notice>}
   </Card>
   <Card className="mt-5" title="Controlled classical vs hybrid evidence" description="Persisted backend evidence reports observed differences without ranking.">
    {data.pairs.length?<><label className="field"><span>Evidence pair</span><Select aria-label="Evidence pair" value={pair?`${pair.quantum_model}:${pair.classical_model}`:''} onChange={e=>setPairKey(e.target.value)}>{data.pairs.map(item=><option key={`${item.quantum_model}:${item.classical_model}`} value={`${item.quantum_model}:${item.classical_model}`}>{modelLabels[item.quantum_type]} vs {modelLabels[item.classical_type]}</option>)}</Select></label>{pair&&<EvidencePanel pair={pair}/>}</>:<EmptyState title="No classical / quantum pair">Complete at least one classical and one quantum model in the same experiment.</EmptyState>}
   </Card>
   <JsonDisclosure label="Comparison conditions and complete evidence" value={{split:data.split,fingerprint:data.comparison_fingerprint,limitations:data.limitations,pairs:data.pairs}}/>
  </>}
 </div>;
}

function EvidencePanel({pair}:{pair:EvidencePair}){
 const metrics=['sensitivity','specificity','precision','recall','f1','roc_auc','accuracy'] as const;
 const costs:[string,keyof EvidencePair['computational_cost']['classical']][]=[['Final training','final_training_seconds'],['CV total','cv_total_seconds'],['Mean CV fold','cv_mean_fold_seconds'],['Test inference','test_inference_seconds'],['Inference / sample','test_inference_seconds_per_sample']];
 const resources=pair.quantum_resources;
 const fairness=pair.fairness;
 const controlled=Boolean(fairness.controlled_comparison);
 const status=fairness.status||(controlled?'CONTROLLED COMPARISON':'NOT CONTROLLED');
 const representation=(pair.common_representation||fairness.common_representation||{}) as Record<string,unknown>;
 return <div className="mt-4 space-y-5">
  {pair.benchmark_type==='fair_controlled_diabetes_benchmark'&&<div>
   <div className="metric-label mb-2">CONTROLLED DIABETES BENCHMARK</div>
   <Notice tone={controlled?'green':'amber'}><strong>{status}</strong>{fairness.mismatch_reasons?.length?` — ${fairness.mismatch_reasons.join(', ')}`:' — fairness conditions were verified from persisted backend metadata.'}</Notice>
   <div className="mt-3 grid gap-3 md:grid-cols-3">
    <MetricCard label="DATASET" value={fairness.target||'Early Stage Diabetes Risk Prediction'} detail={`${fairness.dataset_id} · SHA-256 ${fairness.dataset_hash||'not recorded'}`}/>
    <MetricCard label="SHARED SAMPLES" value={fairness.common_sample_count??'—'} detail={`Same sample budget = ${fairness.same_sample_budget?'true':'false'}`}/>
    <MetricCard label="SHARED SPLIT" value={fairness.split_match?'verified':'not verified'} detail={fairness.split_hash||'Split hash not recorded'}/>
    <MetricCard label="PCA / QUBITS" value={`${String(representation.pca_components??'—')} / ${String(representation.hybrid_qubits??resources.qubits??'—')}`} detail={`${String(representation.selected_feature_count??'—')} selected features`}/>
    <MetricCard label="CV FOLDS" value={fairness.cv_fold_count??'—'} detail={`Seed ${fairness.seed??'—'} · test size ${fairness.test_size??'—'}`}/>
    <MetricCard label="THRESHOLD STRATEGY" value={fairness.threshold_strategy} detail={`Target sensitivity ${fairness.target_sensitivity??'—'}`}/>
   </div>
  </div>}
  <div><div className="metric-label mb-2">SHARED HELD-OUT BENCHMARK</div><div className="table-wrap"><table className="data-table"><thead><tr><th>Metric</th><th>Random Forest / classical</th><th>PennyLane + PyTorch hybrid</th><th>Observed difference (Hybrid − Classical)</th></tr></thead><tbody>{metrics.map(name=><tr key={name}><td>{name}</td><td>{metric(pair.performance[name].classical,name!=='roc_auc')}</td><td>{metric(pair.performance[name].quantum,name!=='roc_auc')}</td><td>{metric(pair.performance[name].delta_quantum_minus_classical,name!=='roc_auc')}</td></tr>)}</tbody></table></div></div>
  <div className="two-grid">
   <Card title="OOF validation threshold" description="Selected only from training cross-validation predictions, then frozen."><div className="space-y-2 text-xs"><div className="flex justify-between"><span>Classical threshold</span><strong>{pair.operating_points.classical.selected_threshold??'undefined'}</strong></div><div className="flex justify-between"><span>Hybrid threshold</span><strong>{pair.operating_points.quantum.selected_threshold??'undefined'}</strong></div><div className="flex justify-between"><span>Classical OOF samples</span><strong>{pair.operating_points.classical.number_of_oof_samples??'—'}</strong></div><div className="flex justify-between"><span>Hybrid OOF samples</span><strong>{pair.operating_points.quantum.number_of_oof_samples??'—'}</strong></div></div></Card>
   <Card title="Untouched holdout evaluation" description="Both models were evaluated on the identical persisted test indices."><div className="space-y-2 text-xs"><div className="flex justify-between"><span>Classical sensitivity / specificity</span><strong>{metric(pair.operating_points.classical.holdout_metrics?.sensitivity)} / {metric(pair.operating_points.classical.holdout_metrics?.specificity)}</strong></div><div className="flex justify-between"><span>Hybrid sensitivity / specificity</span><strong>{metric(pair.operating_points.quantum.holdout_metrics?.sensitivity)} / {metric(pair.operating_points.quantum.holdout_metrics?.specificity)}</strong></div></div></Card>
  </div>
  <div><div className="metric-label mb-2">COMPUTATIONAL MEASUREMENTS</div><div className="table-wrap"><table className="data-table"><thead><tr><th>Measure</th><th>Classical baseline</th><th>PennyLane + PyTorch hybrid</th><th>Observed difference</th></tr></thead><tbody>{costs.map(([label,key])=><tr key={key}><td>{label}</td><td>{seconds(pair.computational_cost.classical[key])}</td><td>{seconds(pair.computational_cost.quantum[key])}</td><td>{seconds(pair.computational_cost.deltas_quantum_minus_classical[key])}</td></tr>)}</tbody></table></div><p className="mt-2 text-xs muted">{pair.computational_cost.semantics}</p></div>
  <div><div className="metric-label mb-2">HYBRID EXECUTION CONTEXT</div><div className="grid gap-3 md:grid-cols-4"><MetricCard label="BACKEND" value={resources.backend||'Not recorded'} detail={resources.execution_kind||'Execution not recorded'}/><MetricCard label="QUBITS / LAYERS" value={`${resources.qubits??'—'} / ${resources.quantum_layers??'—'}`} detail={resources.shots===null||resources.shots===undefined?'Exact expectations · no shots configured':`${resources.shots} shots`}/><MetricCard label="PARAMETERS" value={resources.trainable_parameter_count??'—'} detail={`${resources.total_parameter_count??'—'} total · ${resources.optimizer||'optimizer not recorded'}`}/><MetricCard label="REAL HARDWARE" value={resources.real_hardware?'true':'false'} detail={resources.timing_label||'Simulator execution'}/></div><p className="mt-2 text-xs muted">{resources.resource_semantics}</p></div>
  <div><div className="metric-label mb-2">PAIRED ROBUSTNESS</div><Notice tone="blue">{pair.robustness.note}</Notice></div>
  <Notice tone="blue"><strong>Neutral interpretation:</strong> {pair.conclusion}</Notice>
  <Notice tone="amber"><strong>Scientific limitations:</strong> {pair.limitations.join(' ')}</Notice>
 </div>;
}

export function Robustness(){
 const demo=useVerifiedDemo();
 return demo.active?<VerifiedRobustness/>:<LiveRobustness/>;
}
function LiveRobustness(){
 const {draft}=useDraft();
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const [experimentId,setExperimentId]=useState('');
 const [classicalId,setClassicalId]=useState('');
 const [quantumId,setQuantumId]=useState('');
 const [kind,setKind]=useState<PerturbationType>('missingness');
 const [level,setLevel]=useState(.05);
 const [seed,setSeed]=useState(42);
 const [maxSamples,setMaxSamples]=useState(32);
 const visibleExperiments=scope==='active'&&draft.dataset_id?(experiments.data||[]).filter(item=>item.dataset_id===draft.dataset_id):experiments.data||[];
 const selectedExperiment=visibleExperiments.find(item=>item.id===experimentId);
 const experimentModels=(models.data||[]).filter(model=>model.experiment_id===experimentId&&model.status==='ready');
 const classical=experimentModels.filter(model=>!isQuantumFamilyModel(model.model_type));
 const quantumModels=experimentModels.filter(model=>isQuantumFamilyModel(model.model_type));
 const levels=kind==='outliers'?[3]:[.05,.1];
 useEffect(()=>{if(experiments.isSuccess&&!visibleExperiments.some(item=>item.id===experimentId)){setExperimentId(visibleExperiments[0]?.id||'');setClassicalId('');setQuantumId('')}},[scope,draft.dataset_id,experiments.data,experimentId,experiments.isSuccess]);
 useEffect(()=>{if(!levels.includes(level))setLevel(levels[0])},[kind]);
 const persisted=useQuery({queryKey:['robustness-history',experimentId],queryFn:()=>qh.robustnessHistory(experimentId),enabled:Boolean(experimentId),staleTime:30000});
 const subgroups=useQuery({queryKey:['subgroup-studies',experimentId],queryFn:()=>qh.subgroupStudies(experimentId),enabled:Boolean(experimentId),staleTime:30000});
 const dataset=useQuery({queryKey:['dataset',selectedExperiment?.dataset_id],queryFn:()=>qh.dataset(selectedExperiment!.dataset_id),enabled:Boolean(selectedExperiment?.dataset_id),staleTime:300000});
 const run=useMutation({mutationFn:()=>qh.robustness(experimentId,{model_ids:[classicalId,quantumId].filter(Boolean),scenarios:[{perturbation_type:kind,level}],random_seed:seed,max_samples:maxSamples}),onSuccess:()=>void persisted.refetch()});
 const persistedRecords=persisted.data?.map(item=>({...item.result,id:item.id}))||[];
 const records=run.data?.results||[];
 const allRecords=[...persistedRecords,...records.filter(record=>!persistedRecords.some(item=>item.id===record.id))];
 return <div>
  <PageHeader eyebrow="03 / Robustness Evidence" title="Robustness Lab" description="Inspect persisted model behavior under evaluated perturbations and subgroup studies, with explicit observed degradation and evidence limitations." actions={<Link className="btn btn-outline" to="/comparison"><ArrowRight size={14}/>Comparison</Link>}/>
  <StageNav current="/robustness"/><WorkbenchRail items={[{label:'Experiment',value:experimentId?shortId(experimentId):'None',detail:'Frozen evaluation context',tone:experimentId?'blue':'slate'},{label:'Scenario',value:kind.replaceAll('_',' '),detail:kind==='outliers'?`±${level} training SD`:`${Math.round(level*100)}% perturbation`,tone:'amber'},{label:'Models selected',value:[classicalId,quantumId].filter(Boolean).length,detail:'Same bounded sample matrix',tone:'purple'},{label:'Evidence records',value:allRecords.length||'—',detail:'Persisted backend results',tone:allRecords.length?'green':'slate'}]}/><PipelineFlow items={[{label:'Experiment',detail:'Frozen completed run',status:experimentId?'complete':'current'},{label:'Models',detail:'Classical and quantum pair',status:classicalId||quantumId?'complete':'waiting'},{label:'Perturb',detail:kind.replaceAll('_',' '),status:experimentId?'current':'waiting'},{label:'Evaluate',detail:'Same samples and seed',status:run.isPending?'current':records.length?'complete':'waiting'},{label:'Interpret',detail:'Neutral degradation evidence',status:allRecords.length?'current':'waiting'}]}/><ErrorBanner error={(experiments.error as Error)?.message||(models.error as Error)?.message||(persisted.error as Error)?.message||(subgroups.error as Error)?.message||(dataset.error as Error)?.message||(run.error as Error)?.message}/>
  <Notice tone="amber">Research evaluation only. The locked research operating threshold remains unchanged; models are not refit and no clinical robustness or quantum advantage is claimed.</Notice>
  <Card className="mt-5" title="Controlled benchmark condition" description="Select one bounded perturbation. Both selected models receive the same perturbed sample matrix and seed.">
   <div className="grid gap-4 md:grid-cols-3">
    <label className="field"><span>Record scope</span><Select aria-label="Robustness record scope" value={scope} onChange={event=>setScope(event.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset (all its experiments)</option><option value="all">All registered models</option></Select></label>
    <label className="field"><span>Experiment</span><Select aria-label="Robustness experiment" value={experimentId} onChange={event=>{setExperimentId(event.target.value);setClassicalId('');setQuantumId('')}}><option value="">Select experiment</option>{visibleExperiments.map(item=><option value={item.id} key={item.id}>{shortId(item.id)} · {item.status}</option>)}</Select></label>
    <label className="field"><span>Scenario</span><Select aria-label="Perturbation scenario" value={kind} onChange={event=>setKind(event.target.value as PerturbationType)}><option value="missingness">Missingness</option><option value="gaussian_noise">Gaussian noise</option><option value="outliers">Numerical outliers</option><option value="categorical">Categorical perturbation</option></Select></label>
    <label className="field"><span>Level</span><Select aria-label="Perturbation level" value={level} onChange={event=>setLevel(Number(event.target.value))}>{levels.map(value=><option value={value} key={value}>{kind==='outliers'?`±${value} training SD`:`${Math.round(value*100)}%`}</option>)}</Select></label>
    <label className="field"><span>Classical model</span><Select aria-label="Classical robustness model" value={classicalId} onChange={event=>setClassicalId(event.target.value)}><option value="">None</option>{classical.map(model=><option value={model.id} key={model.id}>{modelLabels[model.model_type]} · {shortId(model.id)}</option>)}</Select></label>
    <label className="field"><span>Quantum model</span><Select aria-label="Quantum robustness model" value={quantumId} onChange={event=>setQuantumId(event.target.value)}><option value="">None</option>{quantumModels.map(model=><option value={model.id} key={model.id}>{modelLabels[model.model_type]} · {shortId(model.id)}</option>)}</Select></label>
    <label className="field"><span>Random seed</span><Input aria-label="Robustness random seed" type="number" value={seed} onChange={event=>setSeed(Number(event.target.value))}/></label>
    <label className="field"><span>Maximum held-out samples</span><Input aria-label="Robustness maximum samples" type="number" min="8" max="64" value={maxSamples} onChange={event=>setMaxSamples(Number(event.target.value))}/></label>
   </div>
   <Button className="mt-4" disabled={!experimentId||(!classicalId&&!quantumId)||run.isPending} onClick={()=>run.mutate()}><Play size={14}/>{run.isPending?'Evaluating controlled perturbation…':'Run robustness condition'}</Button>
  </Card>
  {run.isPending&&<div className="mt-5"><Loading/></div>}
  {experimentId&&<div className="mt-5"><RobustnessEvidenceLab mode="live" experiment={selectedExperiment} dataset={dataset.data} models={experimentModels} liveRecords={allRecords} subgroupStudies={subgroups.data||[]} method="controlled perturbation"/></div>}
 </div>;
}

export function Quantum(){
 const {draft,update,pipeline,quantum}=useDraft();
 const queryClient=useQueryClient();
 const cap=useQuery({queryKey:['quantum-capabilities'],queryFn:qh.capabilities});
 const [kind,setKind]=useState<'vqc'|'qsvc'|'qnn'|'hybrid_pennylane_torch'>('vqc');
 const [contract,setContract]=useState<QuantumVisualizationContract|null>(null);
 const [circuit,setCircuit]=useState<Circuit>();
 const [circuitSource,setCircuitSource]=useState<'preview'|'fitted'|null>(null);
 const [modelId,setModelId]=useState('');
 const [datasetId,setDatasetId]=useState(draft.dataset_id);
 const [encodedValues,setEncodedValues]=useState<string[]>([]);
 const [lastSimulationRequest,setLastSimulationRequest]=useState<QuantumVisualizationSimulationRequest|null>(null);
 const [savedEvidenceId,setSavedEvidenceId]=useState('');
 const autoPreviewStarted=useRef(false);
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const datasets=useQuery({queryKey:['datasets'],queryFn:qh.datasets,staleTime:30000});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const selectedModel=models.data?.find(model=>model.id===modelId);
 const selectedExperiment=experiments.data?.find(item=>item.id===selectedModel?.experiment_id);
 const visualizationArtifacts=useQuery({
  queryKey:['experiment-artifacts',selectedExperiment?.id],
  queryFn:()=>qh.experimentArtifacts(selectedExperiment!.id),
  enabled:Boolean(modelId&&selectedExperiment?.id),
  staleTime:30000,
 });
 const evidenceDataset=useQuery({queryKey:['dataset',selectedModel?.dataset_id],queryFn:()=>qh.dataset(selectedModel!.dataset_id),enabled:Boolean(selectedModel?.dataset_id),staleTime:300000});
 const selectedDatasetId=datasetId||selectedModel?.dataset_id||draft.dataset_id||'';
 const dataset=useQuery({queryKey:['dataset',selectedDatasetId],queryFn:()=>qh.dataset(selectedDatasetId),enabled:Boolean(selectedDatasetId),staleTime:300000});
 const diagnostics=useQuery({queryKey:['quantum-diagnostics',modelId],queryFn:()=>qh.quantum_diagnostics_by_run(modelId),enabled:Boolean(modelId),retry:false,staleTime:30000});
 const preview=useMutation({
  mutationFn:(request:QuantumVisualizationPreviewRequest)=>qh.quantumVisualizationPreview(request),
  onMutate:()=>{setContract(null);setCircuit(undefined);setCircuitSource(null)},
  onSuccess:(result)=>{setContract(result);setCircuit(undefined);setCircuitSource('preview')},
 });
 const fitted=useMutation({
  mutationFn:()=>qh.fittedCircuit(modelId),
  onMutate:()=>{setContract(null);setCircuit(undefined);setCircuitSource(null);setLastSimulationRequest(null);setSavedEvidenceId('')},
  onSuccess:(result)=>{setCircuit(result);setContract(null);setCircuitSource('fitted')},
 });
 const simulation=useMutation({
  mutationFn:(request:QuantumVisualizationSimulationRequest)=>qh.quantumVisualizationSimulate(request),
  onSuccess:(result)=>{setContract(result);setCircuit(undefined);setCircuitSource('preview');setSavedEvidenceId('')},
 });
 const saveEvidence=useMutation({
  mutationFn:(request:QuantumVisualizationEvidenceRequest)=>qh.saveQuantumVisualizationEvidence(request),
  onSuccess:(result)=>{setContract(result.contract);setCircuit(undefined);setCircuitSource('preview');setSavedEvidenceId(result.artifact_id);void queryClient.invalidateQueries({queryKey:['experiment-artifacts',result.experiment_id]})},
 });
 const advisor=useMutation({mutationFn:()=>{if(kind==='hybrid_pennylane_torch')throw new Error('The resource advisor supports VQC, QSVC, and QNN only.');return qh.resourceAdvisor({model_type:kind,quantum:draft.quantum,feature_dimension:draft.pipeline.pca_components??draft.quantum.qubits,sample_count:draft.max_samples??160,dataset_id:selectedDatasetId||null,experiment_id:selectedModel?.dataset_id===selectedDatasetId?selectedModel.experiment_id:null})}});
 useEffect(()=>{setDatasetId(draft.dataset_id)},[draft.dataset_id]);
 useEffect(()=>{advisor.reset()},[kind,draft.quantum,draft.pipeline.pca_components,draft.max_samples,draft.dataset_id,datasetId]);
 useEffect(()=>{setEncodedValues(Array.from({length:kind==='hybrid_pennylane_torch'?draft.hybrid.qubits:draft.quantum.qubits},()=>''));setLastSimulationRequest(null);setSavedEvidenceId('');simulation.reset();saveEvidence.reset()},[kind,draft.quantum,draft.hybrid]);
 useEffect(()=>{setContract(null);setCircuit(undefined);setCircuitSource(null);setLastSimulationRequest(null);setSavedEvidenceId('');simulation.reset();saveEvidence.reset()},[modelId,kind,datasetId,draft.quantum,draft.dataset_id,draft.pipeline.pca_components]);
 const advice=advisor.data;
 const history=advice?.historical_evidence;
 const applyRecommendation=()=>{const recommendation=advice?.recommendation.configuration;if(!recommendation)return;quantum(recommendation.quantum);pipeline({pca_components:recommendation.feature_dimension,angle_scaling:true});update({max_samples:recommendation.sample_count})};
 const requestPreview=()=>{
  setLastSimulationRequest(null);setSavedEvidenceId('');simulation.reset();saveEvidence.reset();
  const context={dataset_id:selectedDatasetId||null,experiment_id:selectedModel?.dataset_id===selectedDatasetId?selectedModel.experiment_id:null,seed:draft.seed,...(draft.max_samples?{sample_count:draft.max_samples}:{})};
  if(kind==='hybrid_pennylane_torch')preview.mutate({...context,model_type:kind,hybrid:draft.hybrid});
  else preview.mutate({...context,model_type:kind,quantum:draft.quantum});
 };
 const requestSimulation=()=>{
  if(kind==='hybrid_pennylane_torch')return;
  const vector=encodedValues.map(value=>Number(value));
  if(vector.length!==draft.quantum.qubits||encodedValues.some(value=>value.trim()==='')||vector.some(value=>!Number.isFinite(value)))return;
  const request:QuantumVisualizationSimulationRequest={
   model_type:kind,quantum:draft.quantum,encoded_vector:vector,simulation_stage:'encoding',seed:draft.seed,
   dataset_id:selectedDatasetId||null,
   experiment_id:selectedModel?.dataset_id===selectedDatasetId?selectedModel.experiment_id:null,
  };
  setLastSimulationRequest(request);setSavedEvidenceId('');saveEvidence.reset();simulation.mutate(request);
 };
 const persistSimulation=()=>{
  if(!lastSimulationRequest||!selectedModel||selectedModel.model_type!==kind)return;
  saveEvidence.mutate({model_record_id:modelId,simulation:lastSimulationRequest});
 };
 const vectorValid=kind!=='hybrid_pennylane_torch'&&encodedValues.length===draft.quantum.qubits&&encodedValues.every(value=>value.trim()!==''&&Number.isFinite(Number(value)));
 useEffect(()=>{
  if(!autoPreviewStarted.current&&cap.data?.available){autoPreviewStarted.current=true;requestPreview()}
 },[cap.data?.available,requestPreview]);
 return <div className="quantum-lab-page">
  <PageHeader eyebrow="04 / Quantum" title="Quantum Lab" description="Explore backend-derived circuit structure, dataset representation context, bounded resources, and simulator evidence without conflating structural previews with execution." actions={<><a className="btn btn-outline" href="#quantum-evidence">{modelId?'View diagnostics & evidence':'Model evidence'}</a>{selectedExperiment&&<Link className="btn btn-outline" to={`/experiments/${selectedExperiment.id}`}><FileText size={14}/>Experiment report</Link>}<Link className="btn btn-outline" to="/training"><ArrowRight size={14}/>Configure in Model Lab</Link></>}/>
  <StageNav current="/quantum"/>
  <WorkbenchRail items={[
   {label:'Model family',value:kind.toUpperCase(),detail:'Backend visualization context',tone:'purple'},
   {label:'Runtime',value:contract?.provider.availability||(kind==='hybrid_pennylane_torch'?'PennyLane path':cap.data?.available?'Available':'Unavailable'),detail:contract?.provider.display_name||(kind==='hybrid_pennylane_torch'?'Provider status loads with preview':cap.data?.execution||'Capability loading'),tone:contract?'green':cap.data?.available||kind==='hybrid_pennylane_torch'?'blue':'amber'},
   {label:'Logical qubits',value:contract?.circuit.qubits??circuit?.qubits??(kind==='hybrid_pennylane_torch'?draft.hybrid.qubits:draft.quantum.qubits),detail:'Backend-reported logical width',tone:'blue'},
   {label:'Circuit structure',value:contract?.circuit.gate_sequence.length??circuit?.gates.length??'Not loaded',detail:contract?'Ordered backend operations':circuit?'Persisted fitted operations':'No circuit loaded',tone:contract||circuit?'green':'slate'},
  ]}/>
  <ErrorBanner error={(cap.error as Error)?.message||(models.error as Error)?.message||(experiments.error as Error)?.message||(dataset.error as Error)?.message||(datasets.error as Error)?.message||(evidenceDataset.error as Error)?.message||(preview.error as Error)?.message||(fitted.error as Error)?.message||(advisor.error as Error)?.message||(simulation.error as Error)?.message||(saveEvidence.error as Error)?.message||(visualizationArtifacts.error as Error)?.message}/>

  <QuantumContextPanel contract={contract} datasetName={dataset.data?.provenance.name} modelType={kind} capabilityMessage={kind==='hybrid_pennylane_torch'?'PennyLane local path; backend preview required':cap.data?.execution} circuitSource={circuitSource}/>
  <QuantumPipeline contract={contract} hasPersistedEvidence={Boolean(selectedModel)} hasDatasetContext={Boolean(dataset.data?.id)} hasCircuitStructure={Boolean(circuit?.gates.length)}/>

  <section className="ql-setup-grid" aria-label="Quantum Lab configuration">
   <Card title="Quantum capability and preview" description="Generate a bounded structural contract from the current quantum configuration. Preview does not train, create jobs, or simulate a state.">
    <div className="ql-form-grid">
     <label className="field"><span>Quantum model</span><Select aria-label="Quantum advisor model" value={kind} onChange={event=>setKind(event.target.value as 'vqc'|'qsvc'|'qnn'|'hybrid_pennylane_torch')}><option value="vqc">VQC · variational classifier</option><option value="qsvc">QSVC · feature-map kernel</option><option value="qnn">QNN · quantum neural network</option><option value="hybrid_pennylane_torch">PennyLane + PyTorch hybrid</option></Select></label>
     <label className="field"><span>Dataset context</span><Select aria-label="Quantum dataset context" value={datasetId} onChange={event=>setDatasetId(event.target.value)}><option value="">No registered dataset context</option>{datasetId&&!((datasets.data||[]).some(item=>item.id===datasetId))&&<option value={datasetId}>Active draft dataset · {shortId(datasetId)}</option>}{(datasets.data||[]).map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
    </div>
    <div className="ql-persisted-model-row"><label className="field"><span>Persisted model for diagnostics / fitted circuit</span><Select aria-label="Quantum persisted model" value={modelId} onChange={event=>setModelId(event.target.value)}><option value="">No persisted model selected</option>{(models.data||[]).filter(model=>isQiskitQuantumModel(model.model_type)).map(model=><option key={model.id} value={model.id}>{modelLabels[model.model_type]} · {shortId(model.id)}</option>)}</Select></label></div>
   <div className="ql-context-note"><span className="ql-eyebrow">CURRENT CONFIGURATION</span><p>{kind==='hybrid_pennylane_torch'?`${draft.hybrid.qubits} qubits · ${draft.hybrid.quantum_layers} PennyLane circuit layers · ${draft.hybrid.backend} local simulator`:`${draft.quantum.qubits} qubits · ${draft.quantum.feature_map_reps} feature-map repetitions · ${draft.quantum.ansatz_reps} ansatz repetitions · ${draft.quantum.backend} local simulator`}</p></div>
    <div className="ql-action-row">
     <Button disabled={(kind!=='hybrid_pennylane_torch'&&cap.data?.available===false)||preview.isPending} onClick={requestPreview}><Play size={14}/>{preview.isPending?'Building backend contract…':'Generate structural preview'}</Button>
     {modelId&&<Button variant="outline" disabled={fitted.isPending} onClick={()=>fitted.mutate()}>{fitted.isPending?'Loading fitted circuit…':'Retrieve fitted circuit evidence'}</Button>}
    </div>
    {circuitSource==='fitted'&&<Notice tone="blue">Fitted circuit structure is persisted model evidence. State, probability, phase, and Bloch output are not included unless the backend explicitly supplies them.</Notice>}
   </Card>
   <Card title="Quantum execution boundary" description="Provider and backend claims follow the backend contract; no hardware execution is available in this path.">
    <div className="ql-runtime-summary"><span><small>Provider</small><strong>{contract?.provider.display_name||'Qiskit local'}</strong></span><span><small>Backend</small><strong>{contract?.provider.backend_id||draft.quantum.backend}</strong></span><span><small>Execution mode</small><strong>{contract?.provider.execution_mode||cap.data?.execution||'Local simulator'}</strong></span><span><small>Hardware availability</small><strong>{contract?.provider.hardware_available?'Reported available':'Not available in this execution path'}</strong></span></div>
    <p className="ql-boundary-note">Circuit preview describes structure only. No simulator state, measurement, or quantum advantage is inferred from gate connectivity.</p>
   </Card>
  </section>

  <section className="ql-main-grid" aria-label="Quantum visualization panels">
   <div className="ql-main-primary">
    <Card title="Circuit explorer" description={contract?.circuit.limitation||circuit?.limitation||'Backend-ordered gates are interactive. Structural playback highlights operations only; it does not evolve or invent a quantum state.'}>
     {preview.isPending?<div className="ql-empty-state" role="status">Preparing backend circuit structure…</div>:contract||circuit?<QuantumCircuitExplorer circuit={contract?.circuit||circuit!} sourceLabel={circuitSource==='fitted'?'Persisted fitted circuit':'Quantum visualization preview'}/>:<EmptyState title="No circuit structure loaded">Generate a backend preview or select a persisted quantum model to retrieve its fitted circuit.</EmptyState>}
    </Card>
    <Card title="Explicit encoded-vector simulation" description="Enter an encoded vector and run one bounded local simulation. The values are manual inputs—not values read from the selected dataset—and are never prefilled.">
     {kind==='hybrid_pennylane_torch'?<Notice tone="amber">Hybrid simulation is unavailable without fitted PennyLane/PyTorch model weights.</Notice>:<>
      <div className="ql-encoded-vector-grid">{Array.from({length:draft.quantum.qubits},(_,index)=><label className="field" key={`encoded-${index}`}><span>Encoded value · q[{index}]</span><Input aria-label={`Encoded value for qubit ${index}`} type="number" step="any" value={encodedValues[index]??''} onChange={event=>setEncodedValues(values=>values.map((value,valueIndex)=>valueIndex===index?event.target.value:value))}/></label>)}</div>
      <p className="ql-state-footnote">Encoding-only circuit simulation; QSVC kernel evaluation and fitted classifier output are not computed. Results are local-simulator outputs, not hardware measurements.</p>
      {draft.quantum.noise_probability>0&&<Notice tone="amber">This preview simulator does not apply the configured noise model. Set noise probability to zero to simulate this encoding.</Notice>}
      <div className="ql-action-row"><Button disabled={!vectorValid||simulation.isPending||cap.data?.available===false||draft.quantum.noise_probability>0} onClick={requestSimulation}><Play size={14}/>{simulation.isPending?'Simulating bounded circuit…':'Simulate entered vector'}</Button>
       {lastSimulationRequest&&contract?.status==='SIMULATION_AVAILABLE'&&<Button variant="outline" disabled={!modelId||!selectedModel||selectedModel.model_type!==kind||selectedModel.dataset_id!==lastSimulationRequest.dataset_id||saveEvidence.isPending||Boolean(savedEvidenceId)} onClick={persistSimulation}>{saveEvidence.isPending?'Saving simulator evidence…':savedEvidenceId?'Evidence saved':'Save simulator evidence to model report'}</Button>}
      </div>
      {selectedModel&&selectedModel.model_type!==kind&&<p className="ql-state-footnote">Select a persisted {kind.toUpperCase()} model to attach this simulation snapshot to its experiment report.</p>}
      {savedEvidenceId&&<Notice tone="green">Backend-generated simulation evidence saved as artifact {savedEvidenceId}. It will appear in the linked experiment report/PDF.</Notice>}
     </>}
    </Card>
    <QuantumStatePanel contract={contract} unavailableReason={circuitSource==='fitted'?'The fitted circuit endpoint returned persisted circuit structure only. No statevector, probabilities, phases, reduced Bloch vectors, or measurements were returned.':'No simulator output is available yet. The structural circuit appears automatically when the backend is available; enter a vector above to request an actual bounded simulation.'}/>
   </div>
   <div className="ql-main-secondary">
    <QuantumResourcePanel contract={contract}/>
    {contract&&<Card title="Contract and limitations" description={`Version ${contract.schema_version} · fingerprint ${contract.request_fingerprint}`}>
     <div className="ql-contract-meta"><span><small>Model semantics</small><strong>{contract.circuit.output_semantics||contract.circuit.measurement_path||'Not reported'}</strong></span><span><small>Gate operations</small><strong>{contract.circuit.total_gates??contract.circuit.gate_sequence.length}</strong></span><span><small>Execution kind</small><strong>{contract.circuit.execution_kind}</strong></span></div>
     <ul className="ql-limitation-list">{contract.limitations.map((limitation,index)=><li key={`${index}-${limitation}`}>{limitation}</li>)}</ul>
    </Card>}
   </div>
  </section>

  <Card title="Quantum Resource Advisor" description="Existing deterministic, bounded backend resource advice. Recommendations are applied only after an explicit action; the advisor never starts training.">
   <div className="grid gap-3 md:grid-cols-4"><MetricCard label="BACKEND" value={draft.quantum.backend} detail={draft.quantum.noise_probability?`Noise ${draft.quantum.noise_probability}`:'No configured noise'}/><MetricCard label="QUBITS / PCA" value={`${draft.quantum.qubits} / ${draft.pipeline.pca_components??'off'}`} detail="Logical width / configured feature dimension"/><MetricCard label="CIRCUIT REPS" value={`${draft.quantum.feature_map_reps} + ${draft.quantum.ansatz_reps}`} detail="Feature map + ansatz"/><MetricCard label="ITERATIONS / SHOTS" value={`${draft.quantum.maxiter} / ${draft.quantum.shots}`} detail={`${draft.quantum.optimizer} · ${draft.max_samples??160} samples`}/></div>
   <Button className="mt-4" disabled={advisor.isPending||kind==='hybrid_pennylane_torch'} onClick={()=>advisor.mutate()}><SlidersHorizontal size={14}/>{kind==='hybrid_pennylane_torch'?'Advisor supports VQC, QSVC, and QNN':advisor.isPending?'Analyzing configuration…':'Analyze resource profile'}</Button>
  </Card>
  {advice&&<div className="mt-5 space-y-5">
   <Card title="Resource profile" description={advice.budget_policy.semantics}><div className="grid gap-3 md:grid-cols-3"><MetricCard label="CIRCUIT COMPLEXITY" value={advice.resource_profile.circuit_complexity.toUpperCase()} detail={`${advice.resource_profile.logical_qubits} qubits · ${advice.resource_profile.entanglement} entanglement`}/><MetricCard label="OPTIMIZATION" value={advice.resource_profile.optimization_workload.toUpperCase()} detail={`${advice.resource_profile.optimizer_iteration_budget} requested iterations`}/><MetricCard label="MEASUREMENT" value={advice.resource_profile.measurement_workload.replaceAll('_',' ').toUpperCase()} detail={advice.resource_profile.shots_per_circuit_evaluation===null?'Exact statevector; configured shots are unused':`${advice.resource_profile.shots_per_circuit_evaluation} shots`}/><MetricCard label="SAMPLE WORKLOAD" value={advice.resource_profile.sample_workload.toUpperCase()} detail={`${advice.resource_profile.sample_count} / ${advice.resource_profile.bounded_quantum_sample_cap} bounded samples`}/><MetricCard label="BUDGET STATUS" value={advice.budget_status.status.replaceAll('_',' ').toUpperCase()} detail={advice.budget_policy.version}/><MetricCard label="EXECUTION" value="SIMULATOR" detail={advice.resource_profile.execution_kind}/></div><Notice tone={advice.budget_status.status==='exceeds_budget'?'amber':'blue'}>{advice.budget_status.reasons.join(' ')}</Notice></Card>
   <Card title="Configuration recommendation" description={advice.recommendation.rationale}>{advice.recommendation.available?<><div className="table-wrap"><table className="data-table"><thead><tr><th>Parameter</th><th>Requested</th><th>Recommended</th><th>Reason</th></tr></thead><tbody>{advice.recommendation.changes.map(change=><tr key={change.field}><td>{change.field}</td><td>{change.from}</td><td>{change.to}</td><td>{change.reason}</td></tr>)}</tbody></table></div><Button className="mt-4" onClick={applyRecommendation}>Apply recommended configuration</Button><p className="mt-2 text-xs muted">Explicit action only. Applying updates the existing draft and never starts training.</p></>:<Notice tone="blue">Configuration is within the bounded prototype resource policy. No draft changes are recommended.</Notice>}</Card>
   <Card title="Observed historical runs" description={history?.matching_policy}>{history&&history.matched_runs>0?<div className="grid gap-3 md:grid-cols-3"><MetricCard label="MATCHED RUNS" value={history.matched_runs} detail="Recorded completed models"/><MetricCard label="MEDIAN TRAINING" value={seconds(history.median_training_seconds)} detail="Observed, not estimated"/><MetricCard label="OBSERVED RANGE" value={`${seconds(history.min_training_seconds)} – ${seconds(history.max_training_seconds)}`} detail="Recorded final-fit timing"/></div>:<Notice>Insufficient historical evidence for a measured runtime comparison.</Notice>}<p className="mt-3 text-xs muted">Observed historical runtime is not a guaranteed runtime estimate for this request.</p></Card>
   <Notice tone="amber">Hardware execution is not available in the current verified configuration. Logical resources and simulator workload do not predict real-QPU performance.</Notice>
  </div>}

  <div id="quantum-evidence" className="ql-evidence-anchor">
   {modelId?<QuantumEvidenceLab mode="live" models={models.data||[]} experiment={selectedExperiment} dataset={evidenceDataset.data} selectedModelId={modelId} onModelChange={setModelId} diagnostic={diagnostics.data||null} circuit={circuit||null} onLoadCircuit={()=>fitted.mutate()} loadingCircuit={fitted.isPending} visualizationArtifacts={visualizationArtifacts.data} visualizationArtifactsLoading={visualizationArtifacts.isPending}/>:<Card title="Persisted model evidence" description="Select a registered quantum model above to inspect its diagnostics and persisted model evidence."><p className="ql-evidence-prompt">Model evidence remains separate from structural previews and is never created by this visualization flow.</p></Card>}
  </div>
 </div>;
}

export function Explainability(){
 const demo=useVerifiedDemo();
 return demo.active?<VerifiedExplainability/>:<LiveExplainability/>;
}
function LiveExplainability(){
 const {draft}=useDraft();
 const history=useResearchRecorder();
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const visibleModels=contextModels(models.data,experiments.data,draft.dataset_id,scope);
 const [id,setId]=useState('');const [method,setMethod]=useState('permutation');const [samples,setSamples]=useState(8);const [repeats,setRepeats]=useState(3);const [maxFeatures,setMaxFeatures]=useState(30);
 useEffect(()=>{if(models.isSuccess&&experiments.isSuccess&&!visibleModels.some(model=>model.id===id))setId('')},[scope,draft.dataset_id,models.data,experiments.data,id,models.isSuccess,experiments.isSuccess]);
 const result=useQuery({queryKey:['explanations',id],queryFn:()=>qh.explanations(id),enabled:Boolean(id),staleTime:30000});
 const selectedModel=visibleModels.find(model=>model.id===id);
 const experiment=experiments.data?.find(item=>item.id===selectedModel?.experiment_id);
 const dataset=useQuery({queryKey:['dataset',selectedModel?.dataset_id],queryFn:()=>qh.dataset(selectedModel!.dataset_id),enabled:Boolean(selectedModel?.dataset_id),staleTime:300000});
 const effectiveMethod=isQiskitQuantumModel(selectedModel?.model_type)?'perturbation':isHybridModel(selectedModel?.model_type)?'shap':method;
 const run=useMutation({mutationFn:()=>qh.explain(id,{method:effectiveMethod,max_samples:samples,repeats,max_features:maxFeatures}),onSuccess:explanation=>{void result.refetch();if(selectedModel)void history.record(explanationActivity(explanation,selectedModel))}});
 const current=result.data?.[0];
 return <div>
  <PageHeader eyebrow="03 / Explain" title="Explainability Research Lab" description="Investigate global feature influence, local research-case contributions, provenance, and limitations without turning post-hoc model behavior into medical causation." actions={<Link className="btn btn-outline" to="/prediction"><ArrowRight size={14}/>Prediction</Link>}/>
  <StageNav current="/explainability"/>
  <WorkbenchRail items={[{label:'Model',value:selectedModel?modelLabels[selectedModel.model_type]:'None',detail:'Frozen backend model record',tone:selectedModel?'blue':'slate'},{label:'Method',value:effectiveMethod.toUpperCase(),detail:'Backend-supported method',tone:'purple'},{label:'Persisted records',value:result.data?.length??'—',detail:'No automatic generation',tone:result.data?.length?'green':'slate'},{label:'Explained cases',value:current?.result.explained_case_count??current?.result.sample_count??'—',detail:'Bounded research evidence',tone:current?'green':'slate'}]}/>
  <ErrorBanner error={(models.error as Error)?.message||(experiments.error as Error)?.message||(dataset.error as Error)?.message||(result.error as Error)?.message||(run.error as Error)?.message}/>
  <Card className="mt-5" title="Explanation evidence context" description="Select a model to load only its persisted explanation records. Another model's evidence is never used as fallback."><div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Model scope</span><Select aria-label="Explainability model scope" value={scope} onChange={event=>setScope(event.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + current experiment</option><option value="all">All registered models</option></Select></label><ModelSelect models={visibleModels} value={id} onChange={value=>{setId(value);const model=visibleModels.find(item=>item.id===value);if(isHybridModel(model?.model_type))setMethod('shap');else if(isQiskitQuantumModel(model?.model_type))setMethod('perturbation')}}/></div></Card>
  {selectedModel?<div className="mt-5"><ExplainabilityResearchLab model={selectedModel} models={visibleModels.filter(item=>item.status==='ready')} experiment={experiment} dataset={dataset.data} records={result.data||[]} mode="live" onModelChange={setId}/></div>:<div className="mt-5"><EmptyState title="Select a completed model">Choose a model to inspect its own persisted explanation evidence.</EmptyState></div>}
  {selectedModel&&<Card className="mt-5" title="Generate a bounded explanation" description="Explicit user-triggered workflow preserved from the existing application. Nothing runs automatically when this page opens or when models are switched."><div className="grid gap-4 md:grid-cols-4"><label className="field"><span>Method</span><Select aria-label="Explanation method" value={effectiveMethod} disabled={isQiskitQuantumModel(selectedModel.model_type)||isHybridModel(selectedModel.model_type)} onChange={event=>setMethod(event.target.value)}><option value="permutation">Permutation importance</option><option value="shap">{isHybridModel(selectedModel.model_type)?'SHAP — Final Hybrid Output':'SHAP'}</option><option value="perturbation">Feature perturbation / sensitivity</option></Select></label><label className="field"><span>Samples</span><Input type="number" min="2" max="32" value={samples} onChange={event=>setSamples(Number(event.target.value))}/></label><label className="field"><span>Repeats</span><Input type="number" min="1" max="10" value={repeats} onChange={event=>setRepeats(Number(event.target.value))}/></label><label className="field"><span>Maximum features</span><Input type="number" min="1" max="60" value={maxFeatures} onChange={event=>setMaxFeatures(Number(event.target.value))}/></label></div>{isHybridModel(selectedModel.model_type)&&<div className="mt-4"><Notice tone="blue">SHAP explains contribution to the final PennyLane + PyTorch positive-class probability. It does not fully explain circuit internals.</Notice></div>}<Button className="mt-4" disabled={run.isPending} onClick={()=>run.mutate()}><Play size={14}/>{run.isPending?'Calculating…':'Calculate explanation explicitly'}</Button></Card>}
 </div>;
}

export function PredictionPage(){
 const demo=useVerifiedDemo();
 return demo.active?<VerifiedPrediction/>:<LivePredictionPage/>;
}
function LivePredictionPage(){
 const {draft}=useDraft();
 const history=useResearchRecorder();
 const queryClient=useQueryClient();
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const visibleModels=contextModels(models.data,experiments.data,draft.dataset_id,scope);
 const [id,setId]=useState('');
 const selected=visibleModels.find(model=>model.id===id);
 const experiment=experiments.data?.find(item=>item.id===selected?.experiment_id);
 const relatedModels=visibleModels.filter(model=>model.status==='ready'&&model.experiment_id===selected?.experiment_id);
 const dataset=useQuery({queryKey:['dataset',selected?.dataset_id],queryFn:()=>qh.dataset(selected!.dataset_id),enabled:Boolean(selected?.dataset_id),staleTime:300000});
 const schema=useQuery({queryKey:['schema',id],queryFn:()=>qh.schema(id),enabled:Boolean(id),staleTime:300000});
 const [values,setValues]=useState<Record<string,string>>({});
 const [submittedInput,setSubmittedInput]=useState<Record<string,string|number|boolean|null>>();
 const [low,setLow]=useState(.33);const [high,setHigh]=useState(.66);const [influence,setInfluence]=useState(true);
 const buildRow=()=>Object.fromEntries((schema.data?.features||[]).map(field=>[field.name,values[field.name]===undefined||values[field.name]===''?null:field.type==='number'?Number(values[field.name]):values[field.name]])) as Record<string,string|number|boolean|null>;
 const sample=useMutation({mutationFn:()=>qh.sample(id),onSuccess:data=>setValues(Object.fromEntries(Object.entries(data.features).map(([key,value])=>[key,value===null?'':String(value)])))});
 const pred=useMutation({mutationFn:(row:Record<string,string|number|boolean|null>)=>qh.predict(id,{samples:[row],risk_thresholds:[low,high],include_influence:influence}),onSuccess:(prediction,row)=>{setSubmittedInput(row);if(selected)void history.record(predictionActivity(prediction,selected))}});
 const schemaKey=(value:NonNullable<typeof schema.data>)=>JSON.stringify({features:[...value.features].sort((a,b)=>a.name.localeCompare(b.name)),positive_label:value.positive_label,negative_label:value.negative_label});
 const cross=useMutation({mutationFn:async()=>{
  if(!selected||!schema.data)throw new Error('Select a model with a loaded input schema.');
  const row=buildRow();const selectedSchemaKey=schemaKey(schema.data);
  const rows=await Promise.all(relatedModels.map(async model=>{
   try{
    const candidateSchema=model.id===selected.id?schema.data:await queryClient.fetchQuery({queryKey:['schema',model.id],queryFn:()=>qh.schema(model.id),staleTime:300000});
    if(schemaKey(candidateSchema)!==selectedSchemaKey)return {model,reason:'Input schema or class-label contract is not compatible.'} satisfies CrossModelPrediction;
    const canReuse=model.id===selected.id&&pred.data&&submittedInput&&JSON.stringify(submittedInput)===JSON.stringify(row);
    const prediction=canReuse?pred.data:await qh.predict(model.id,{samples:[row],risk_thresholds:[low,high],include_influence:false});
    return {model,prediction} satisfies CrossModelPrediction;
   }catch(error){return {model,reason:error instanceof Error?error.message:'Prediction output unavailable.'} satisfies CrossModelPrediction}
  }));
  return {rows,input:row,sameInputVerified:true};
 }});
 useEffect(()=>{setValues({});setSubmittedInput(undefined);pred.reset();cross.reset()},[id]);
 useEffect(()=>{setSubmittedInput(undefined);pred.reset();cross.reset()},[values]);
 useEffect(()=>{if(models.data&&experiments.data&&!visibleModels.some(model=>model.id===id))setId('')},[scope,draft.dataset_id,models.data,experiments.data,id]);
 return <div>
  <PageHeader eyebrow="04 / Predict" title="Research Prediction Lab" description="Inspect an exact research input, model output, persisted operating point, and explicit same-input cross-model comparison without changing prediction mathematics."/>
  <StageNav current="/prediction"/>
  <WorkbenchRail items={[{label:'Selected model',value:selected?modelLabels[selected.model_type]:'None',detail:'Never substituted automatically',tone:selected?'blue':'slate'},{label:'Input schema',value:schema.data?`${schema.data.features.length} fields`:'Not loaded',detail:'Backend-provided contract',tone:schema.data?'green':'slate'},{label:'Primary output',value:pred.data?'Completed':'Waiting',detail:'Explicit prediction request',tone:pred.data?'green':'slate'},{label:'Cross-model',value:cross.data?`${cross.data.rows.filter(row=>row.prediction).length} evaluated`:'Not requested',detail:'Explicit compatible-schema action',tone:cross.data?'purple':'slate'}]}/>
  <ErrorBanner error={(models.error as Error)?.message||(experiments.error as Error)?.message||(dataset.error as Error)?.message||(schema.error as Error)?.message||(sample.error as Error)?.message||(pred.error as Error)?.message||(cross.error as Error)?.message}/>
  <Card className="mt-5" title="Research input and selected model" description="Inputs are submitted only when you deliberately request a prediction; typing does not execute a model."><div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Model scope</span><Select aria-label="Prediction model scope" value={scope} onChange={event=>setScope(event.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + current experiment</option><option value="all">All registered models</option></Select></label><ModelSelect models={visibleModels} value={id} onChange={setId}/></div>{schema.data&&<><div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={!id||sample.isPending} onClick={()=>sample.mutate()}>{sample.isPending?'Loading sample…':'Load one public benchmark sample'}</Button><Badge tone="amber">Anonymous research input · no patient identity</Badge></div><div className="mt-4 grid gap-3 md:grid-cols-3">{schema.data.features.map(field=><label className="field" key={field.name}><span><strong>{field.name}</strong><small className="ml-1 muted">· {field.type}{field.nullable?' · nullable':''}</small></span><Input aria-label={field.name} type={field.type==='number'?'number':'text'} value={values[field.name]||''} onChange={event=>setValues(state=>({...state,[field.name]:event.target.value}))} placeholder="Missing / impute"/></label>)}</div></>}{sample.data&&<Notice tone="blue">Loaded: {sample.data.sample} · Source: {sample.data.source}. Target remains withheld.</Notice>}<div className="mt-4 grid gap-4 md:grid-cols-3"><label className="field"><span>Low research category threshold</span><Input type="number" min=".01" max=".98" step=".01" value={low} onChange={event=>setLow(Number(event.target.value))}/></label><label className="field"><span>High research category threshold</span><Input type="number" min=".02" max=".99" step=".01" value={high} onChange={event=>setHigh(Number(event.target.value))}/></label><label className="flex items-center gap-2 pt-6 text-xs"><input type="checkbox" checked={influence} onChange={event=>setInfluence(event.target.checked)}/>Request existing local explanation capability</label></div><Button className="mt-4" disabled={!schema.data||pred.isPending||!(0<low&&low<high&&high<1)} onClick={()=>pred.mutate(buildRow())}><Play size={14}/>{pred.isPending?'Calculating…':'Generate research prediction'}</Button></Card>
  <div className="mt-5">{pred.data&&submittedInput&&selected?<ResearchPredictionLab mode="live" model={selected} models={relatedModels} experiment={experiment} dataset={dataset.data} schema={schema.data} input={submittedInput} prediction={pred.data} crossResults={cross.data?.rows||[]} sameInputVerified={Boolean(cross.data?.sameInputVerified)} onCompare={()=>cross.mutate()} comparing={cross.isPending}/>:<EmptyState title="No prediction calculated">Select a completed model, provide one anonymous research input, and deliberately submit it.</EmptyState>}</div>
 </div>;
}
