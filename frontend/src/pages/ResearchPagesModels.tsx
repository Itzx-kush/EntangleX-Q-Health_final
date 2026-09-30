import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {useMutation,useQuery} from '@tanstack/react-query';
import {ArrowRight,Atom,BarChart3,Brain,CheckCircle2,Play,RotateCcw,ShieldAlert,SlidersHorizontal} from 'lucide-react';
import {Button,Card,Badge,Input,Select} from '../components/ui';
import {ErrorBanner,EmptyState,Loading,MetricCard,ModelSelect,Notice,PageHeader,StatusBadge,JsonDisclosure,metricNames} from '../components/Shared';
import {MetricBars,InfluenceBars,RocChart,ThresholdTradeoffChart,RobustnessDeltaChart} from '../components/Charts';
import {StageNav} from './ResearchPagesCore';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {dateTime,metric,modelLabels,seconds,shortId,isQuantum} from '../utils/format';
import type {EvidencePair,Experiment,ModelKind,ModelRecord,PerturbationType,RobustnessEvidence} from '../types/qhealth';
import {GlareHover,BorderGlow,Reveal,QuantumVisual,SpotlightPanel} from '../components/reactbits';


function CircuitViz({circuit}:{circuit:{qubits:number;gates:{name:string;qubits:number[];parameters:string[]}[]}}){
 const byQubit=Array.from({length:circuit.qubits},(_,qubit)=>({qubit,gates:circuit.gates.filter(g=>g.qubits.includes(qubit))}));
 return <div className="circuit-view" aria-label="Logical circuit visualization">
  <div className="circuit-view-head"><span>Qubit</span><span>Measured gates returned by backend</span></div>
  {byQubit.map(row=><div className="circuit-row" key={row.qubit}><strong>q[{row.qubit}]</strong><div className="circuit-wire">{row.gates.length?row.gates.map((gate,index)=><span className="circuit-gate" key={`${gate.name}-${index}`} title={gate.parameters.join(', ')}>{gate.name}{gate.parameters.length>0&&<small>{gate.parameters.join(', ')}</small>}</span>):<span className="circuit-idle">No gate on this wire</span>}</div></div>)}
 </div>;
}

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

export function Training(){
 const {draft,update,pipeline,quantum}=useDraft();
 const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:3000});
 const dataset=useQuery({queryKey:['dataset',draft.dataset_id],queryFn:()=>qh.dataset(draft.dataset_id),enabled:Boolean(draft.dataset_id)});
 const library=useQuery({queryKey:['dataset-library'],queryFn:qh.datasetLibrary,staleTime:300000});
 const readiness=library.data?.find(item=>item.slug===dataset.data?.provenance.library_slug)?.demo_readiness;
 const mutation=useMutation({mutationFn:()=>qh.createJob(draft),onSuccess:r=>{update({dataset_id:r.experiment.dataset_id});jobs.refetch()}});
 const quantumSelected=draft.models.some(isQuantum);
 const toggle=(kind:ModelKind)=>{const next=draft.models.includes(kind)?draft.models.filter(x=>x!==kind):[...draft.models,kind];update({models:next});if(next.some(isQuantum))pipeline({pca_components:draft.quantum.qubits,angle_scaling:true})};
 const option=(kind:ModelKind,quantumModel:boolean)=><GlareHover key={kind}><button type="button" onClick={()=>toggle(kind)} className={'w-full rounded-xl border p-4 text-left transition '+(draft.models.includes(kind)?'border-primary bg-primary/5':'hover:bg-muted')}><div className="flex items-center justify-between"><strong>{modelLabels[kind]}</strong><Badge tone={draft.models.includes(kind)?(quantumModel?'purple':'blue'):'blue'}>{draft.models.includes(kind)?'Selected':quantumModel?'Quantum':'Classical'}</Badge></div><small className="mt-1 block muted">{quantumModel?'Hybrid / quantum model':'Classical baseline'}</small></button></GlareHover>;
 return <div>
  <PageHeader eyebrow="01 / Train" title="Training" description="Configure one controlled experiment with shared partitions, preprocessing and evaluation conditions across supported classical and quantum models." actions={<Button disabled={!draft.dataset_id||!draft.models.length||mutation.isPending} onClick={()=>mutation.mutate()}><Play size={14}/>{mutation.isPending?'Creating job…':'Create training experiment'}</Button>}/>
  <StageNav current="/training"/><ErrorBanner error={(mutation.error as Error)?.message}/>{readiness&&<Notice tone={readiness.status==='ready'?'blue':'amber'}>{readiness.status==='ready'?'A verified precomputed SIH demo is available for this dataset. You can still start a new live experiment.':'This dataset requires processing; no precomputed demo artifact is packaged. Live training remains available.'}</Notice>}
  <Card className="mt-5" title="Model families" description="Choose the estimators that receive the same configured representation.">
   <div className="grid gap-3 md:grid-cols-3">{(['logistic_regression','svm','random_forest'] as ModelKind[]).map(x=>option(x,false))}</div>
   <div className="my-5 border-t"/>
   <div className="grid gap-3 md:grid-cols-3">{(['vqc','qsvc','qnn'] as ModelKind[]).map(x=>option(x,true))}</div>
   {quantumSelected&&<Notice>Quantum comparisons require PCA components equal to qubits, shared angle scaling, calibration disabled and no class-weighting. The interface makes no quantum-advantage claim.</Notice>}
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
    <label className="field"><span>Calibration</span><Select disabled={quantumSelected} value={draft.calibration} onChange={e=>update({calibration:e.target.value as any})}><option value="none">None</option><option value="sigmoid">Sigmoid / Platt</option><option value="isotonic">Isotonic</option></Select></label>
    <label className="field"><span>Calibration folds</span><Input type="number" min="2" max="5" disabled={draft.calibration==='none'||quantumSelected} value={draft.calibration_folds} onChange={e=>update({calibration_folds:Number(e.target.value)})}/></label>
   </div></Card>
   <Card title="Classical parameters" description="Only values accepted by the backend training schema are exposed."><div className="grid gap-4 md:grid-cols-2">
    <label className="field"><span>Logistic C</span><Input type="number" min=".001" value={draft.parameters.logistic_c} onChange={e=>update({parameters:{...draft.parameters,logistic_c:Number(e.target.value)}})}/></label>
    <label className="field"><span>SVM / QSVC C</span><Input type="number" min=".001" value={draft.parameters.svm_c} onChange={e=>update({parameters:{...draft.parameters,svm_c:Number(e.target.value)}})}/></label>
    <label className="field"><span>SVM kernel</span><Select value={draft.parameters.svm_kernel} onChange={e=>update({parameters:{...draft.parameters,svm_kernel:e.target.value as any}})}><option value="rbf">RBF</option><option value="linear">Linear</option></Select></label>
    <label className="field"><span>Random forest trees</span><Input type="number" min="10" max="500" value={draft.parameters.forest_trees} onChange={e=>update({parameters:{...draft.parameters,forest_trees:Number(e.target.value)}})}/></label>
    <label className="field"><span>Forest maximum depth</span><Input type="number" min="1" max="100" value={draft.parameters.forest_max_depth??''} onChange={e=>update({parameters:{...draft.parameters,forest_max_depth:e.target.value?Number(e.target.value):null}})}/></label>
    <label className="field"><span>Class weighting</span><Select disabled={quantumSelected} value={draft.parameters.class_weight||'none'} onChange={e=>update({parameters:{...draft.parameters,class_weight:e.target.value==='balanced'?'balanced':null}})}><option value="none">None</option><option value="balanced">Balanced</option></Select></label>
   </div></Card>
  </div>
  <BorderGlow className="mt-5"><Card title="Quantum configuration" description="QNN, VQC and QSVC use the existing backend quantum configuration contract.">
   <div className="grid gap-4 md:grid-cols-3">
    <label className="field"><span>Backend</span><Select value={draft.quantum.backend} onChange={e=>quantum({backend:e.target.value as any})}><option value="statevector">Statevector</option><option value="aer">Aer</option></Select></label>
    <label className="field"><span>Qubits</span><Input type="number" min="2" max="8" value={draft.quantum.qubits} onChange={e=>{const q=Number(e.target.value);quantum({qubits:q});if(quantumSelected)pipeline({pca_components:q})}}/></label>
    <label className="field"><span>Feature-map reps</span><Input type="number" min="1" max="3" value={draft.quantum.feature_map_reps} onChange={e=>quantum({feature_map_reps:Number(e.target.value)})}/></label>
    <label className="field"><span>Ansatz reps</span><Input type="number" min="1" max="3" value={draft.quantum.ansatz_reps} onChange={e=>quantum({ansatz_reps:Number(e.target.value)})}/></label>
    <label className="field"><span>Entanglement</span><Select value={draft.quantum.entanglement} onChange={e=>quantum({entanglement:e.target.value as any})}><option value="linear">Linear</option><option value="full">Full</option></Select></label>
    <label className="field"><span>Optimizer</span><Select value={draft.quantum.optimizer} onChange={e=>quantum({optimizer:e.target.value as any})}><option value="COBYLA">COBYLA</option><option value="SPSA">SPSA</option></Select></label>
    <label className="field"><span>Maximum iterations</span><Input type="number" min="5" max="300" value={draft.quantum.maxiter} onChange={e=>quantum({maxiter:Number(e.target.value)})}/></label>
    <label className="field"><span>Shots</span><Input type="number" min="128" max="16384" value={draft.quantum.shots} onChange={e=>quantum({shots:Number(e.target.value)})}/></label>
    <label className="field"><span>Noise probability</span><Input type="number" min="0" max=".1" step=".01" disabled={draft.quantum.backend!=='aer'} value={draft.quantum.noise_probability} onChange={e=>quantum({noise_probability:Number(e.target.value)})}/></label>
   </div>
   <div className="mt-4 flex flex-wrap gap-4 text-xs"><label className="flex items-center gap-2"><input type="checkbox" checked={draft.pipeline.angle_scaling} onChange={e=>pipeline({angle_scaling:e.target.checked})}/>Shared angle scaling</label><label className="flex items-center gap-2"><input type="checkbox" checked={draft.pipeline.pca_components!==null} onChange={e=>pipeline({pca_components:e.target.checked?draft.quantum.qubits:null})}/>Enable PCA</label></div>
  </Card></BorderGlow>
  <Card className="mt-5" title="Execution state" description="Backend-reported jobs refresh automatically."><div className="space-y-3">{jobs.isLoading?<Loading/>:jobs.data?.length?jobs.data.slice(0,8).map(job=><div className="rounded-xl border p-3" key={job.id}><div className="flex items-center justify-between"><Link className="font-semibold text-primary" to={'/experiments/'+job.experiment_id}>Experiment {shortId(job.experiment_id)}</Link><StatusBadge value={job.status}/></div><p className="mt-1 text-xs muted">{job.state}</p><progress className="job-progress mt-2 w-full" max="100" value={job.progress}/><small className="block mt-1 muted">{job.progress}% backend-reported progress.</small>{['queued','running'].includes(job.status)&&<Button className="mt-2" variant="outline" onClick={()=>qh.cancelJob(job.id).then(()=>jobs.refetch())}>Request cancellation</Button>}{job.errors.length>0&&<JsonDisclosure label="Recorded model failures" value={job.errors}/>}</div>):<EmptyState title="No training jobs">Create an experiment to populate the execution registry.</EmptyState>}</div></Card>
 </div>;
}

export function Comparison(){
 const {draft}=useDraft();
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const [id,setId]=useState('');
 const visibleExperiments=scope==='active'&&draft.dataset_id?(experiments.data||[]).filter(item=>item.dataset_id===draft.dataset_id):experiments.data||[];
 const selected=useQuery({queryKey:['comparison',id],queryFn:()=>qh.comparison(id),enabled:Boolean(id),refetchInterval:5000});
 const [modelId,setModelId]=useState('');
 const [pairKey,setPairKey]=useState('');
 useEffect(()=>{if(!visibleExperiments.some(item=>item.id===id)){setId(visibleExperiments[0]?.id||'');setModelId('');setPairKey('')}},[id,scope,draft.dataset_id,experiments.data]);
 const data=selected.data;
 const model=data?.models.find(item=>item.id===modelId)||data?.models.find(item=>item.status==='ready')||data?.models[0];
 const pair=data?.pairs.find(item=>`${item.quantum_model}:${item.classical_model}`===pairKey)||data?.pairs[0];
 const evidenceMetrics=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 const operating=model?.metrics.operating_point;
 return <div>
  <PageHeader eyebrow="02 / Compare" title="Model comparison" description="Controlled held-out evidence with measured model deltas, runtime, logical quantum resources and neutral interpretation." actions={<Link className="btn btn-outline" to="/explainability"><ArrowRight size={14}/>Explainability</Link>}/>
  <StageNav current="/comparison"/><ErrorBanner error={(experiments.error as Error)?.message||(selected.error as Error)?.message}/>
  <Card className="mt-5" title="Experiment context"><div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Record scope</span><Select aria-label="Comparison record scope" value={scope} onChange={e=>setScope(e.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + latest workflow</option><option value="all">All registered models</option></Select></label><label className="field"><span>Experiment</span><Select value={id} onChange={e=>{setId(e.target.value);setModelId('');setPairKey('')}}><option value="">Select experiment</option>{visibleExperiments.map(item=><option value={item.id} key={item.id}>{shortId(item.id)} · {item.status}</option>)}</Select></label></div>{scope==='active'&&<Notice tone="blue">Only experiments for the active dataset are shown. Historical experiments remain available through “All registered models”.</Notice>}</Card>
  {selected.isLoading&&id&&<div className="mt-4"><Loading/></div>}
  {data&&<>
   <Card className="mt-5" title="Held-out performance" description={data.conclusion}><div className="table-wrap"><table className="data-table"><thead><tr><th>Model</th><th>Status</th>{metricNames.map(name=><th key={name}>{name}</th>)}</tr></thead><tbody>{data.models.map(item=><tr key={item.id} className={model?.id===item.id?'bg-primary/5':''}><td><button className="font-semibold text-primary" onClick={()=>setModelId(item.id)}>{modelLabels[item.model_type]}</button></td><td><StatusBadge value={item.status}/></td>{metricNames.map(name=><td key={name}>{metric(item.metrics.test?.[name],name!=='roc_auc')}</td>)}</tr>)}</tbody></table></div></Card>
   {operating&&<div className="two-grid mt-5"><Card title="Research operating point" description={operating.interpretation}>{operating.threshold_feasible?<div className="grid grid-cols-3 gap-3"><MetricCard label="THRESHOLD" value={operating.selected_threshold===null?'—':operating.selected_threshold.toFixed(4)} detail={operating.threshold_source}/><MetricCard label="VALIDATION SENSITIVITY" value={metric(operating.validation_metrics?.sensitivity)} detail="Out-of-fold"/><MetricCard label="VALIDATION SPECIFICITY" value={metric(operating.validation_metrics?.specificity)} detail="Out-of-fold"/></div>:<Notice tone="amber">{operating.infeasible_reason||'Target sensitivity is not achievable on the validation folds under the current model configuration.'}</Notice>}</Card><Card title="Validation threshold trade-off"><ThresholdTradeoffChart operatingPoint={operating}/></Card></div>}
   <div className="two-grid mt-5">{model?.metrics.test&&<Card title={modelLabels[model.model_type]+' · held-out metrics'}><MetricBars metrics={model.metrics.test}/><JsonDisclosure label="Confusion matrix and metric record" value={model.metrics.test}/></Card>}<Card title="ROC comparison"><RocChart models={data.models}/></Card></div>
   <Card className="mt-5" title="Validation, holdout, and runtime"><div className="table-wrap"><table className="data-table"><thead><tr><th>Metric</th><th>CV mean</th><th>CV SD</th><th>Test</th></tr></thead><tbody>{metricNames.map(name=><tr key={name}><td>{name}</td><td>{metric(model?.metrics.validation?.summary?.[name]?.mean,name!=='roc_auc')}</td><td>{metric(model?.metrics.validation?.summary?.[name]?.std,name!=='roc_auc')}</td><td>{metric(model?.metrics.test?.[name],name!=='roc_auc')}</td></tr>)}</tbody></table></div></Card>
   <Card className="mt-5" title="Quantum vs classical evidence" description="Measured deltas are quantum minus classical. Unfavorable quantum results remain visible.">
    {data.pairs.length?<><label className="field"><span>Evidence pair</span><Select aria-label="Evidence pair" value={pair?`${pair.quantum_model}:${pair.classical_model}`:''} onChange={e=>setPairKey(e.target.value)}>{data.pairs.map(item=><option key={`${item.quantum_model}:${item.classical_model}`} value={`${item.quantum_model}:${item.classical_model}`}>{modelLabels[item.quantum_type]} vs {modelLabels[item.classical_type]}</option>)}</Select></label>{pair&&<EvidencePanel pair={pair}/>}</>:<EmptyState title="No classical / quantum pair">Complete at least one classical and one quantum model in the same experiment.</EmptyState>}
   </Card>
   <JsonDisclosure label="Comparison conditions and complete evidence" value={{split:data.split,fingerprint:data.comparison_fingerprint,limitations:data.limitations,pairs:data.pairs}}/>
  </>}
 </div>;
}

function EvidencePanel({pair}:{pair:EvidencePair}){
 const metrics=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 const costs:[string,keyof EvidencePair['computational_cost']['classical']][]=[['Training','final_training_seconds'],['CV total','cv_total_seconds'],['CV mean fold','cv_mean_fold_seconds'],['Inference / sample','test_inference_seconds_per_sample']];
 const resources=pair.quantum_resources;
 const gates=resources.gate_counts?Object.values(resources.gate_counts).reduce((sum,value)=>sum+value,0):null;
 return <div className="mt-4 space-y-5">
  <div className="table-wrap"><table className="data-table"><thead><tr><th>Metric</th><th>Classical</th><th>Quantum</th><th>Δ Q-C</th></tr></thead><tbody>{metrics.map(name=><tr key={name}><td>{name}</td><td>{metric(pair.performance[name].classical,name!=='roc_auc')}</td><td>{metric(pair.performance[name].quantum,name!=='roc_auc')}</td><td>{metric(pair.performance[name].delta_quantum_minus_classical,name!=='roc_auc')}</td></tr>)}</tbody></table></div>
  <div><div className="metric-label mb-2">COMPUTATIONAL COST</div><div className="table-wrap"><table className="data-table"><thead><tr><th>Measure</th><th>Classical</th><th>Quantum</th><th>Δ Q-C</th></tr></thead><tbody>{costs.map(([label,key])=><tr key={key}><td>{label}</td><td>{seconds(pair.computational_cost.classical[key])}</td><td>{seconds(pair.computational_cost.quantum[key])}</td><td>{seconds(pair.computational_cost.deltas_quantum_minus_classical[key])}</td></tr>)}</tbody></table></div></div>
  <div><div className="metric-label mb-2">QUANTUM RESOURCES</div><div className="grid gap-3 md:grid-cols-4"><MetricCard label="BACKEND" value={resources.backend||'Not recorded'} detail={resources.execution_kind||'Legacy record'}/><MetricCard label="QUBITS / SHOTS" value={`${resources.qubits??'—'} / ${resources.shots??'—'}`} detail="Logical width / simulator shots"/><MetricCard label="DEPTH / GATES" value={`${resources.logical_depth??'—'} / ${gates??'—'}`} detail="Logical resources"/><MetricCard label="PARAMETERS" value={`${resources.trainable_parameter_count??0} trainable`} detail={`${resources.total_parameter_count??'—'} total · ${resources.optimizer||'optimizer not recorded'}`}/></div><p className="mt-2 text-xs muted">{resources.resource_semantics}</p></div>
  <div><div className="metric-label mb-2">VALIDATION CONTEXT</div><div className="grid gap-3 md:grid-cols-4"><MetricCard label="DATASET" value={shortId(pair.fairness.dataset_id)} detail={pair.fairness.dataset_hash?`Hash ${pair.fairness.dataset_hash.slice(0,10)}…`:'Hash not recorded'}/><MetricCard label="SAMPLES" value={pair.fairness.common_sample_count??'—'} detail="Common evaluated sample budget"/><MetricCard label="SPLIT / CV" value={pair.fairness.cv_fold_count??'—'} detail={pair.fairness.split_hash?`CV folds · ${pair.fairness.split_hash.slice(0,10)}…`:'CV folds'}/><MetricCard label="THRESHOLD" value={pair.fairness.threshold_strategy} detail="Research operating-point strategy"/></div></div>
  <Notice tone="blue"><strong>Interpretation:</strong> {pair.conclusion}</Notice>
  <Notice tone="amber"><strong>Limitations:</strong> {pair.limitations.join(' ')}</Notice>
 </div>;
}

export function Robustness(){
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
 const experimentModels=(models.data||[]).filter(model=>model.experiment_id===experimentId&&model.status==='ready');
 const classical=experimentModels.filter(model=>!isQuantum(model.model_type));
 const quantumModels=experimentModels.filter(model=>isQuantum(model.model_type));
 const levels=kind==='outliers'?[3]:[.05,.1];
 useEffect(()=>{if(!visibleExperiments.some(item=>item.id===experimentId)){setExperimentId(visibleExperiments[0]?.id||'');setClassicalId('');setQuantumId('')}},[scope,draft.dataset_id,experiments.data,experimentId]);
 useEffect(()=>{if(!levels.includes(level))setLevel(levels[0])},[kind]);
 const run=useMutation({mutationFn:()=>qh.robustness(experimentId,{model_ids:[classicalId,quantumId].filter(Boolean),scenarios:[{perturbation_type:kind,level}],random_seed:seed,max_samples:maxSamples})});
 const records=run.data?.results||[];
 const shownMetrics=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 return <div>
  <PageHeader eyebrow="03 / Robustness" title="Robustness Lab" description="Measure frozen classical and quantum model behavior under identical, deterministic perturbations of the same bounded held-out samples." actions={<Link className="btn btn-outline" to="/comparison"><ArrowRight size={14}/>Comparison</Link>}/>
  <StageNav current="/robustness"/><ErrorBanner error={(experiments.error as Error)?.message||(models.error as Error)?.message||(run.error as Error)?.message}/>
  <Notice tone="amber">Research evaluation only. The locked research operating threshold remains unchanged; models are not refit and no clinical robustness or quantum advantage is claimed.</Notice>
  <Card className="mt-5" title="Controlled benchmark condition" description="Select one bounded perturbation. Both selected models receive the same perturbed sample matrix and seed.">
   <div className="grid gap-4 md:grid-cols-3">
    <label className="field"><span>Record scope</span><Select aria-label="Robustness record scope" value={scope} onChange={event=>setScope(event.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + latest workflow</option><option value="all">All registered models</option></Select></label>
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
  {run.data&&<div className="mt-5 space-y-5">
   <Card title="Observed degradation under controlled perturbation" description={`Benchmark condition: ${kind.replaceAll('_',' ')} at ${level}. Degradation Δ means perturbed − baseline.`}><RobustnessDeltaChart records={records}/></Card>
   <div className="grid gap-5 lg:grid-cols-2">{records.map(record=><RobustnessResult key={record.id||record.model_id} record={record} metrics={shownMetrics}/>)}</div>
   {records.length===2&&records.every(record=>record.status==='evaluated')&&<Card title="Paired observed differences" description="The values below compare each model's degradation delta (quantum − classical). They are descriptive measurements, not a winner or advantage claim."><div className="table-wrap"><table className="data-table"><thead><tr><th>Metric</th><th>Quantum Δ − Classical Δ</th></tr></thead><tbody>{shownMetrics.map(name=><tr key={name}><td>{name}</td><td>{metric(measuredDifference(records.find(record=>isQuantum(record.model_type))?.degradation_delta[name],records.find(record=>!isQuantum(record.model_type))?.degradation_delta[name]),name!=='roc_auc')}</td></tr>)}</tbody></table></div></Card>}
   <JsonDisclosure label="Reproducibility metadata and limitations" value={run.data}/>
  </div>}
 </div>;
}

function RobustnessResult({record,metrics}:{record:RobustnessEvidence;metrics:readonly ('accuracy'|'sensitivity'|'specificity'|'f1'|'roc_auc')[]}){
 return <Card title={modelLabels[record.model_type]} description={`${record.perturbation_type.replaceAll('_',' ')} · seed ${record.random_seed} · ${record.sample_count} held-out samples`}>
  {record.status!=='evaluated'?<Notice tone="amber"><strong>{record.status.replaceAll('_',' ')}:</strong> {record.reason||'This condition could not be evaluated.'}</Notice>:<div className="table-wrap"><table className="data-table"><thead><tr><th>Metric</th><th>Baseline</th><th>Perturbed</th><th>Δ</th></tr></thead><tbody>{metrics.map(name=><tr key={name}><td>{name}</td><td>{metric(record.baseline_metrics[name],name!=='roc_auc')}</td><td>{metric(record.perturbed_metrics?.[name],name!=='roc_auc')}</td><td>{metric(record.degradation_delta[name],name!=='roc_auc')}</td></tr>)}</tbody></table></div>}
  <p className="mt-3 text-xs muted">Threshold {record.threshold_used.toFixed(4)} · {record.threshold_source.replaceAll('_',' ')} · frozen model, no threshold reselection.</p>
 </Card>;
}

export function Quantum(){
 const {draft}=useDraft(); const cap=useQuery({queryKey:['quantum-capabilities'],queryFn:qh.capabilities}); const [kind,setKind]=useState<'vqc'|'qsvc'|'qnn'>('vqc');const [circuit,setCircuit]=useState<any>();const [modelId,setModelId]=useState('');const [mode,setMode]=useState<'explain'|'technical'>('explain');const models=useQuery({queryKey:['models'],queryFn:qh.models});const preview=useMutation({mutationFn:()=>qh.circuit({quantum:draft.quantum,model_type:kind,seed:draft.seed}),onSuccess:setCircuit});const fitted=useMutation({mutationFn:()=>qh.fittedCircuit(modelId),onSuccess:setCircuit});
 return <div><PageHeader eyebrow="Quantum Lab" title="Quantum circuit" description="Inspect the structural representation used by QNN, VQC and QSVC models. This view reports logical metadata and local simulation limitations rather than hardware performance." actions={<Link className="btn btn-outline" to="/training"><ArrowRight size={14}/>Configure in Model Lab</Link>}/><StageNav current="/quantum"/><ErrorBanner error={(cap.error as Error)?.message||(models.error as Error)?.message||(preview.error as Error)?.message||(fitted.error as Error)?.message}/><Reveal className="mb-5"><SpotlightPanel className="rb-quantum-stage p-4"><div className="flex flex-wrap items-center gap-5"><QuantumVisual/><div className="max-w-md"><div className="eyebrow">STRUCTURAL QUANTUM VIEW</div><h2 className="section-title mt-2">Logical circuits, measured honestly.</h2><p className="section-copy mt-2">The ambient visual communicates circuit structure only; every value below comes from the existing backend contract.</p></div></div></SpotlightPanel></Reveal><div className="mt-5 two-grid"><Card title="Quantum capability"><div className="grid gap-3"><div className="flex justify-between text-sm"><span className="muted">Dependencies</span><StatusBadge value={cap.data?.available?'ready':'unavailable'}/></div><p className="text-xs muted">{cap.data?.execution||'Loading quantum runtime capability…'}</p><label className="field"><span>Model</span><Select value={kind} onChange={e=>setKind(e.target.value as any)}><option value="vqc">VQC</option><option value="qsvc">QSVC</option><option value="qnn">QNN</option></Select></label><Button disabled={cap.data?.available===false||preview.isPending} onClick={()=>preview.mutate()}><Play size={14}/>{preview.isPending?'Generating…':'Generate circuit representation'}</Button></div></Card><Card title="Registered quantum model"><ModelSelect models={models.data||[]} value={modelId} onChange={setModelId} quantumOnly/><Button className="mt-3" disabled={!modelId||fitted.isPending} onClick={()=>fitted.mutate()} variant="outline">Retrieve fitted circuit</Button></Card></div>{circuit?<Card className="mt-5" title={String(circuit.model_type).toUpperCase() + ' · ' + circuit.execution_kind} description={circuit.limitation}><div className="mode-tabs" role="tablist" aria-label="Quantum view mode"><button className={mode==='explain'?'is-active':''} onClick={()=>setMode('explain')} role="tab" aria-selected={mode==='explain'}>Explain mode</button><button className={mode==='technical'?'is-active':''} onClick={()=>setMode('technical')} role="tab" aria-selected={mode==='technical'}>Technical mode</button></div>{mode==='explain'?<div className="quantum-explain-grid mt-4">{['Classical features','Encoding / feature map','Parameterized ansatz','Measurement','Classical optimization'].map((step,index)=><div className="quantum-explain-step" key={step}><span>{String(index+1).padStart(2,'0')}</span><strong>{step}</strong><small>{index===0?'The configured input representation enters the circuit.':index===1?'Features are encoded into logical qubit rotations.':index===2?'Trainable circuit parameters are evaluated by the selected runtime.':index===3?'The backend measures the circuit output for the estimator.':'A classical optimizer updates parameters during training.'}</small></div>)}</div>:<div className="grid gap-3 md:grid-cols-3 mt-4"><MetricCard label="BACKEND" value={circuit.backend} detail="Reported execution target"/><MetricCard label="EXECUTION" value={circuit.execution_kind} detail="Reported mode"/><MetricCard label="GATE TYPES" value={Object.keys(circuit.gate_counts).length} detail="Returned gate categories"/></div>}<div className="grid grid-cols-3 gap-3 mt-5"><MetricCard label="QUBITS" value={circuit.qubits} detail="Logical width" icon={<Atom size={15}/>}/><MetricCard label="DEPTH" value={circuit.logical_depth} detail="Logical depth" icon={<BarChart3 size={15}/>}/><MetricCard label="PARAMETERS" value={circuit.parameter_count} detail="Trainable parameters" icon={<SlidersHorizontal size={15}/>}/></div><CircuitViz circuit={circuit}/><details className="mt-5 rounded-xl border p-4"><summary className="cursor-pointer text-xs font-semibold">Raw circuit text</summary><pre className="mono mt-3 max-h-[360px] overflow-auto whitespace-pre-wrap text-xs leading-relaxed">{circuit.text}</pre></details><JsonDisclosure label="Gate counts and limitations" value={{gate_counts:circuit.gate_counts,limitation:circuit.limitation}}/></Card>:<div className="mt-5"><EmptyState title="No circuit representation">Generate or retrieve a backend-described circuit.</EmptyState></div>}</div>
}

export function Explainability(){
 const {draft}=useDraft();
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const visibleModels=contextModels(models.data,experiments.data,draft.dataset_id,scope);
 const [id,setId]=useState('');const [method,setMethod]=useState('permutation');const [samples,setSamples]=useState(8);const [repeats,setRepeats]=useState(3);const [maxFeatures,setMaxFeatures]=useState(30);
 useEffect(()=>{if(!visibleModels.some(model=>model.id===id))setId('')},[scope,draft.dataset_id,models.data,experiments.data,id]);
 const result=useQuery({queryKey:['explanations',id],queryFn:()=>qh.explanations(id),enabled:Boolean(id)});const selectedModel=visibleModels.find(model=>model.id===id);const effectiveMethod=isQuantum(selectedModel?.model_type)?'perturbation':method;const run=useMutation({mutationFn:()=>qh.explain(id,{method:effectiveMethod,max_samples:samples,repeats,max_features:maxFeatures}),onSuccess:()=>result.refetch()});const current=result.data?.[0];
 return <div><PageHeader eyebrow="03 / Explain" title="Explainability" description="Drill into measured model behavior without turning feature influence into a medical causation claim." actions={<Link className="btn btn-outline" to="/prediction"><ArrowRight size={14}/>Prediction</Link>}/><StageNav current="/explainability"/><ErrorBanner error={(models.error as Error)?.message||(experiments.error as Error)?.message||(result.error as Error)?.message||(run.error as Error)?.message}/><Card className="mt-5" title="Explanation method"><div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Model scope</span><Select aria-label="Explainability model scope" value={scope} onChange={e=>setScope(e.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + current experiment</option><option value="all">All registered models</option></Select></label><ModelSelect models={visibleModels} value={id} onChange={setId}/></div><div className="mt-4 grid gap-4 md:grid-cols-3"><label className="field"><span>Method</span><Select value={method} disabled={isQuantum(selectedModel?.model_type)} onChange={e=>setMethod(e.target.value)}><option value="permutation">Permutation</option><option value="shap">SHAP</option><option value="perturbation">Perturbation</option></Select></label><label className="field"><span>Samples</span><Input type="number" min="2" max="32" value={samples} onChange={e=>setSamples(Number(e.target.value))}/></label><label className="field"><span>Repeats</span><Input type="number" min="1" max="10" value={repeats} onChange={e=>setRepeats(Number(e.target.value))}/></label></div><Button className="mt-4" disabled={!id||run.isPending} onClick={()=>run.mutate()}><Play size={14}/>{run.isPending?'Calculating…':'Calculate explanation'}</Button></Card><div className="mt-5">{current?<Card title={current.result.title} description={current.result.scope}><InfluenceBars items={current.result.influence}/><JsonDisclosure label="Measured influence and limitations" value={current.result}/></Card>:<EmptyState title="No explanation yet">Select a completed model and request a bounded explanation.</EmptyState>}</div></div>
}

export function PredictionPage(){
 const {draft}=useDraft();
 const models=useQuery({queryKey:['models'],queryFn:qh.models});
 const experiments=useQuery({queryKey:['experiments'],queryFn:qh.experiments});
 const [scope,setScope]=useState<'active'|'all'>(draft.dataset_id?'active':'all');
 const visibleModels=contextModels(models.data,experiments.data,draft.dataset_id,scope);
 const [id,setId]=useState('');const selected=visibleModels.find(model=>model.id===id);const schema=useQuery({queryKey:['schema',id],queryFn:()=>qh.schema(id),enabled:Boolean(id)});const [values,setValues]=useState<Record<string,string>>({});const [low,setLow]=useState(.33);const [high,setHigh]=useState(.66);const [influence,setInfluence]=useState(true);const sample=useMutation({mutationFn:()=>qh.sample(id),onSuccess:data=>setValues(Object.fromEntries(Object.entries(data.features).map(([key,value])=>[key,value===null?'':String(value)])))});const pred=useMutation({mutationFn:()=>{const row=Object.fromEntries((schema.data?.features||[]).map(field=>[field.name,values[field.name]===undefined||values[field.name]===''?null:field.type==='number'?Number(values[field.name]):values[field.name]]));return qh.predict(id,{samples:[row],risk_thresholds:[low,high],include_influence:influence})}});
 useEffect(()=>{setValues({})},[id]);
 useEffect(()=>{if(!visibleModels.some(model=>model.id===id))setId('')},[scope,draft.dataset_id,models.data,experiments.data,id]);
 return <div><PageHeader eyebrow="04 / Predict" title="Research prediction" description="Apply an exact completed-model input schema to an anonymous research sample. The interface keeps the output explicitly non-clinical."/><StageNav current="/prediction"/><ErrorBanner error={(models.error as Error)?.message||(experiments.error as Error)?.message||(schema.error as Error)?.message||(sample.error as Error)?.message||(pred.error as Error)?.message}/><Card className="mt-5" title="Completed model">{selected?.details.experiment_kind==='precomputed_verified_demo'&&<Notice tone="blue">Verified precomputed research model. Integrity is revalidated by the backend before loading or prediction.</Notice>}<div className="grid gap-4 md:grid-cols-2"><label className="field"><span>Model scope</span><Select aria-label="Prediction model scope" value={scope} onChange={e=>setScope(e.target.value as 'active'|'all')}><option value="active" disabled={!draft.dataset_id}>Active dataset + current experiment</option><option value="all">All registered models</option></Select></label><ModelSelect models={visibleModels} value={id} onChange={setId}/></div>{schema.data&&<><div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={!id||sample.isPending} onClick={()=>sample.mutate()}>{sample.isPending?'Loading sample…':'Load one public benchmark sample'}</Button><Badge tone="amber">No patient data</Badge></div><div className="mt-4 grid gap-3 md:grid-cols-3">{schema.data.features.map(field=><label className="field" key={field.name}><span>{field.name}</span><Input type={field.type==='number'?'number':'text'} value={values[field.name]||''} onChange={e=>setValues(state=>({...state,[field.name]:e.target.value}))} placeholder="Missing / impute"/></label>)}</div></>}{sample.data&&<Notice tone="blue">Loaded: {sample.data.sample} · Source: {sample.data.source}</Notice>}<div className="mt-4 grid gap-4 md:grid-cols-3"><label className="field"><span>Low threshold</span><Input type="number" min=".01" max=".98" step=".01" value={low} onChange={e=>setLow(Number(e.target.value))}/></label><label className="field"><span>High threshold</span><Input type="number" min=".02" max=".99" step=".01" value={high} onChange={e=>setHigh(Number(e.target.value))}/></label><label className="flex items-center gap-2 pt-6 text-xs"><input type="checkbox" checked={influence} onChange={e=>setInfluence(e.target.checked)}/>Local feature influence</label></div><Button className="mt-4" disabled={!schema.data||pred.isPending||!(0<low&&low<high&&high<1)} onClick={()=>pred.mutate()}><Play size={14}/>{pred.isPending?'Calculating…':'Generate research prediction'}</Button></Card><div className="mt-5">{pred.data?<Card title="Model-generated result" description={pred.data.probability_status}><Notice tone="blue">Research operating point: {pred.data.decision_rule}. Source: {pred.data.threshold_source.replaceAll('_',' ')}. Not a clinically validated screening cutoff.</Notice>{pred.data.predictions.map(item=><div className="rounded-xl border p-4" key={item.sample}><div className="grid gap-4 md:grid-cols-3"><div><span className="metric-label">Predicted class</span><strong className="mt-1 block text-xl">{item.predicted_class}</strong></div><div><span className="metric-label">Probability</span><strong className="mt-1 block text-xl">{item.probability_positive===null?'Not available':metric(item.probability_positive)}</strong></div><div><span className="metric-label">Research category</span><strong className="mt-1 block text-xl">{item.research_risk_category||'Not assigned'}</strong></div></div></div>)}{pred.data.influence&&<InfluenceBars items={pred.data.influence}/>}<JsonDisclosure label="Decision rule and limitations" value={pred.data}/></Card>:<EmptyState title="No prediction calculated">Select a completed model and submit one anonymous sample.</EmptyState>}</div></div>
}

