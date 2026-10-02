import {useEffect} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Atom,CheckCircle2,Database,FlaskConical,ShieldCheck,Sparkles} from 'lucide-react';
import {Badge,Button,Card} from './ui';
import {EmptyState,ErrorBanner,JsonDisclosure,Loading,MetricCard,Notice,PageHeader} from './Shared';
import {ProbabilityBand,PipelineFlow,StatusStrip,WorkbenchRail} from './TremorWorkbench';
import {TremorBarChart} from './TremorUI';
import {InfluenceBars,ValueBars} from './Charts';
import {StageNav} from '../pages/ResearchPagesCore';
import {metric,modelLabels,seconds} from '../utils/format';
import {useFlagshipData} from '../hooks/useVerifiedDemo';
import type {ModelKind,ModelRecord,VerifiedPredictionCase} from '../types/qhealth';

const family=(kind:ModelKind)=>kind==='hybrid_pennylane_torch'?'Hybrid':(['vqc','qsvc','qnn'] as string[]).includes(kind)?'Quantum':'Classical';
const toneFor=(kind:ModelKind)=>family(kind)==='Hybrid'?'purple':family(kind)==='Quantum'?'blue':'green';

function DemoBoundary({children}:{children:(data:NonNullable<ReturnType<typeof useFlagshipData>['payload']>)=>React.ReactNode}){
  const data=useFlagshipData(true);
  if(data.verified.isLoading)return <Loading/>;
  if(data.verified.error)return <><ErrorBanner error={(data.verified.error as Error).message}/><EmptyState title="Verified demo unavailable">The verified package could not be loaded. Continue with the normal dataset and training workflow.</EmptyState></>;
  if(!data.payload)return <EmptyState title="Verified demo unavailable">No validated precomputed artifact is available. Continue with the normal research workflow.</EmptyState>;
  return <>{children(data.payload)}</>;
}

export function VerifiedContextBar(){
  const {context,item,payload}=useFlagshipData(true);
  if(!context.active)return null;
  return <div className="verified-context-bar" role="status" aria-label="Active verified demonstration context">
    <div><span>ACTIVE DATASET</span><strong>{payload?.dataset.name||item?.name||'Loading…'}</strong></div>
    <div><span>EXPERIMENT</span><strong>Verified SIH Demonstration</strong></div>
    <div><span>MODE</span><strong>Precomputed / Verified</strong></div>
    <div><span>MODEL SET</span><strong>{payload?.models.length??item?.demo_readiness.model_ids.length??'—'} models</strong></div>
    <button onClick={context.deactivate}>Exit demo</button>
  </div>;
}

export function VerifiedDemoLanding(){
  const data=useFlagshipData();
  useEffect(()=>{
    if(data.available&&data.experimentId&&data.payload?.dataset.id)data.context.activate(data.experimentId,data.payload.dataset.id);
  },[data.available,data.experimentId,data.payload?.dataset.id]);
  if(data.library.isLoading||data.verified.isLoading)return <Loading/>;
  if(!data.available||!data.payload)return <div><PageHeader eyebrow="Featured SIH demonstration" title="Verified demo unavailable" description="The backend did not validate an instant research package. No placeholder scientific values are shown."/><ErrorBanner error={data.verified.error instanceof Error?data.verified.error.message:undefined}/><Link className="btn btn-primary" to="/datasets">Open normal research workflow</Link></div>;
  const {dataset,models,evidence,artifact_version}=data.payload;
  return <div className="tremor-dashboard">
    <PageHeader eyebrow="Featured SIH demonstration · verified precomputed result" title={dataset.name} description="Explore the complete controlled research record immediately—no upload, configuration, training, SHAP computation, or robustness rerun." actions={<Link className="btn btn-primary" to="/comparison">Explore model evidence <ArrowRight size={14}/></Link>}/>
    <StatusStrip items={[{label:'Package',value:'Verified demo',status:'good'},{label:'Computation',value:'Precomputed',status:'good'},{label:'Availability',value:'Ready instantly',status:'good'},{label:'Artifact',value:artifact_version,status:'neutral'}]}/>
    <WorkbenchRail items={[
      {label:'Samples',value:dataset.provenance.row_count.toLocaleString(),detail:'Packaged source rows',tone:'blue'},
      {label:'Features',value:dataset.provenance.feature_count,detail:dataset.provenance.target,tone:'purple'},
      {label:'Models',value:models.length,detail:'3 classical · 3 quantum · 1 hybrid',tone:'green'},
      {label:'Evidence',value:Object.keys(evidence).length,detail:'Validated evidence artifacts',tone:'amber'},
    ]}/>
    <Card className="mt-5" title="Instant research pathway" description="Every destination below reads the same validated dataset, experiment, model, and evidence identities.">
      <div className="demo-path-grid">{[
        ['Dataset','/datasets'],['Quality','/quality'],['Preprocessing','/preprocessing'],['Features / PCA','/features'],
        ['Model results','/training'],['Classical vs Quantum','/comparison'],['Hybrid model','/quantum'],
        ['Robustness','/robustness'],['Explainability','/explainability'],['Prediction','/prediction'],
      ].map(([label,to],index)=><Link to={to} key={to}><span>{String(index+1).padStart(2,'0')}</span><strong>{label}</strong><ArrowRight size={14}/></Link>)}</div>
    </Card>
    <div className="two-grid mt-5">
      <Card title="Controlled flagship model set" description="Statuses and identities come from the verified manifest.">
        <div className="space-y-2">{models.map(model=><div className="tremor-list-row" key={model.id}><Badge tone={toneFor(model.model_type)}>{family(model.model_type)}</Badge><strong className="ml-2 text-xs">{modelLabels[model.model_type]}</strong><span className="ml-auto"><Badge tone="green">{model.status}</Badge></span></div>)}</div>
      </Card>
      <Card title="Research boundaries" description="Measured evidence is descriptive, not a clinical or hardware claim.">
        <Notice tone="amber">Research benchmark only—not diagnosis, clinical validation, treatment guidance, or medical advice.</Notice>
        <div className="mt-4 space-y-2 text-xs muted"><p>Quantum execution: local simulation.</p><p>Quantum advantage claimed: No.</p><p>Dataset hash and every artifact hash are validated before readiness.</p></div>
      </Card>
    </div>
    <StageNav current="/demo"/>
  </div>;
}

export function VerifiedQuality(){
  return <DemoBoundary>{data=>{const d=data.dataset,q=d.quality,p=data.evidence.provenance.dataset;return <div>
    <PageHeader eyebrow="02 / Verified dataset evidence" title="Data quality & provenance" description="The packaged dataset state that produced the flagship experiment. No validation job is started."/>
    <StageNav current="/quality"/>
    <WorkbenchRail items={[{label:'Samples',value:p.row_count,detail:'Source rows',tone:'blue'},{label:'Features',value:p.feature_count,detail:p.target,tone:'purple'},{label:'Duplicates',value:q.duplicate_rows,detail:'Disclosed exact duplicates',tone:q.duplicate_rows?'amber':'green'},{label:'Missing cells',value:Object.values(q.missing_values).reduce((a,b)=>a+Number(b),0),detail:'Measured by backend',tone:'green'}]}/>
    <div className="two-grid mt-5"><Card title="Class distribution" description={`${p.positive_label} / ${p.negative_label}`}><ValueBars items={Object.entries(p.class_distribution).map(([name,value])=>({name,value}))}/></Card><Card title="Quality findings"><Notice tone={q.blockers.length?'amber':'green'}>{q.blockers.length?`${q.blockers.length} blocker(s) disclosed.`:'No blocking issue in the packaged quality record.'}</Notice><div className="mt-3 space-y-2">{q.blockers.map(x=><p className="text-xs text-red-700" key={x}>{x}</p>)}{q.warnings.map(x=><p className="text-xs text-amber-700" key={x}>{x}</p>)}</div></Card></div>
    <div className="two-grid mt-5"><Card title="Source & attribution"><dl className="demo-dl"><dt>Source</dt><dd>{p.source}</dd><dt>Attribution</dt><dd>{String(p.attribution||'—')}</dd><dt>License</dt><dd>{p.license||'—'}</dd><dt>Dataset SHA-256</dt><dd className="mono break-all">{data.dataset.sha256}</dd></dl></Card><Card title="Integrity detail"><JsonDisclosure label="Packaged quality record" value={q}/><JsonDisclosure label="Dataset provenance" value={p}/></Card></div>
  </div>}}</DemoBoundary>;
}

export function VerifiedPipeline({stage}:{stage:'preprocessing'|'features'|'pca'}){
  return <DemoBoundary>{data=>{const p=data.evidence.preprocessing,c=p.configuration.pipeline,r=p.representation as Record<string,any>,f=p.fitted_preprocessing as Record<string,any>;return <div>
    <PageHeader eyebrow="Verified research process" title={stage==='preprocessing'?'Preprocessing':stage==='features'?'Features & selection':'PCA & quantum representation'} description="Read-only configuration from the controlled flagship experiment; no preview or training request is made."/>
    <StageNav current={stage==='preprocessing'?'/preprocessing':stage==='features'?'/features':'/pca'}/>
    <PipelineFlow items={[{label:'Input',detail:`${r.raw_input_features?.length??data.dataset.provenance.feature_count} source features`,status:'complete'},{label:'Transform',detail:`${c.imputer} imputation · ${c.scaler} scaling`,status:'complete'},{label:'Select',detail:`${c.selection} · ${r.selected_feature_count??'—'} retained`,status:'complete'},{label:'Reduce',detail:`${c.pca_components??'No'} PCA components`,status:'complete'},{label:'Angles',detail:c.angle_scaling?'Angle scaling enabled':'Disabled',status:'complete'}]}/>
    <WorkbenchRail items={[{label:'Imputer',value:c.imputer,detail:'Missing-value policy',tone:'blue'},{label:'Scaler',value:c.scaler,detail:'Shared scaling',tone:'purple'},{label:'PCA',value:c.pca_components??'Off',detail:'Components',tone:'green'},{label:'Final dimension',value:r.final_representation_dimension??'—',detail:'Shared comparison space',tone:'amber'}]}/>
    <div className="two-grid mt-5"><Card title="Verified configuration"><dl className="demo-dl"><dt>Feature selection</dt><dd>{c.selection}</dd><dt>Maximum features</dt><dd>{c.k_features}</dd><dt>PCA components</dt><dd>{c.pca_components??'Disabled'}</dd><dt>PCA whitening</dt><dd>{c.pca_whiten?'Yes':'No'}</dd><dt>Angle scaling</dt><dd>{c.angle_scaling?'Enabled':'Disabled'}</dd><dt>Duplicate policy</dt><dd>{p.configuration.duplicate_policy}</dd><dt>Seed</dt><dd>{p.configuration.seed}</dd></dl></Card><Card title="Fitted pipeline evidence"><JsonDisclosure label="Fitted preprocessing" value={f}/><JsonDisclosure label="Shared representation" value={r}/><JsonDisclosure label="Controlled split" value={p.split}/></Card></div>
  </div>}}</DemoBoundary>;
}

export function VerifiedTraining(){
  return <DemoBoundary>{data=><div><PageHeader eyebrow="Verified result view · no live training" title="Flagship model set" description="Seven frozen, integrity-checked artifacts from one controlled experiment. Configuration controls and training actions are intentionally absent."/><StageNav current="/training"/><StatusStrip items={[{label:'Experiment',value:'Succeeded',status:'good'},{label:'Mode',value:'Precomputed',status:'good'},{label:'Models',value:String(data.models.length),status:'good'},{label:'Training request',value:'Not created',status:'neutral'}]}/><ModelTable models={data.models}/></div>}</DemoBoundary>;
}

function ModelTable({models}:{models:ModelRecord[]}){
  return <Card className="mt-5" title="Measured held-out results" description="Descriptive evidence only; no winner or quantum-advantage claim."><div className="table-wrap"><table className="data-table min-w-[980px]"><thead><tr><th>Family</th><th>Model</th><th>Status</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Training</th><th>Execution</th></tr></thead><tbody>{models.map(model=>{const m=model.metrics.test;const q=model.details.quantum as Record<string,any>|undefined;return <tr key={model.id}><td><Badge tone={toneFor(model.model_type)}>{family(model.model_type)}</Badge></td><td><strong>{modelLabels[model.model_type]}</strong></td><td><Badge tone="green">{model.status}</Badge></td><td>{metric(m?.accuracy)}</td><td>{metric(m?.precision)}</td><td>{metric(m?.recall)}</td><td>{metric(m?.f1)}</td><td>{metric(m?.roc_auc)}</td><td>{seconds(model.metrics.timing?.final_training_seconds)}</td><td>{q?.execution_kind||'Classical CPU execution'}</td></tr>})}</tbody></table></div></Card>;
}

export function VerifiedComparison(){
  return <DemoBoundary>{data=>{const rows=data.models.map(model=>({name:modelLabels[model.model_type],f1:Number(model.metrics.test?.f1??0)}));return <div><PageHeader eyebrow="Hero analytics · controlled seven-model comparison" title="Classical, quantum & hybrid evidence" description="All models share the packaged dataset identity, sample pool, split, preprocessing representation, seed, and threshold protocol."/><StageNav current="/comparison"/><WorkbenchRail items={[{label:'Models',value:data.models.length,detail:'One experiment',tone:'blue'},{label:'Classical',value:data.models.filter(m=>family(m.model_type)==='Classical').length,detail:'Measured artifacts',tone:'green'},{label:'Quantum',value:data.models.filter(m=>family(m.model_type)==='Quantum').length,detail:'Local simulation',tone:'purple'},{label:'Hybrid',value:data.models.filter(m=>family(m.model_type)==='Hybrid').length,detail:'PennyLane + PyTorch',tone:'amber'}]}/><div className="mt-5 tremor-grid-main"><ModelTable models={data.models}/><Card title="Measured F1 overview" description="Held-out F1 from persisted backend metrics."><TremorBarChart data={rows} category="name" value="f1" showGrid/></Card></div><Card className="mt-5" title="Benchmark conditions"><JsonDisclosure label="Controlled comparison contract" value={data.evidence.benchmark.comparison_contract}/><Notice tone="amber">The package records no quantum-advantage or real-hardware claim.</Notice></Card></div>}}</DemoBoundary>;
}

export function VerifiedQuantum(){
  return <DemoBoundary>{data=>{const quantum=data.models.filter(model=>family(model.model_type)!=='Classical');const hybrid=quantum.find(model=>model.model_type==='hybrid_pennylane_torch');const h=(hybrid?.details.quantum||{}) as Record<string,any>;const hc=data.evidence.preprocessing.configuration.hybrid;return <div><PageHeader eyebrow="Verified quantum workbench · precomputed" title="Qiskit models & flagship hybrid" description="Read-only simulator evidence from the packaged experiment. Opening this page does not execute Qiskit or PennyLane."/><StageNav current="/quantum"/><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 mt-5">{quantum.map(model=>{const q=(model.details.quantum||{}) as Record<string,any>;return <Card key={model.id} title={modelLabels[model.model_type]} description={model.model_type==='hybrid_pennylane_torch'?'PennyLane + PyTorch Hybrid':'Qiskit quantum model'}><Badge tone="green">Verified artifact</Badge><dl className="demo-dl mt-3"><dt>Backend</dt><dd>{q.backend||'statevector'}</dd><dt>Qubits</dt><dd>{q.qubits??data.evidence.preprocessing.configuration.quantum.qubits}</dd><dt>Execution</dt><dd>{q.execution_kind||'local simulation'}</dd><dt>Hardware</dt><dd>{q.real_hardware?'Reported':'No'}</dd><dt>ROC-AUC</dt><dd>{metric(model.metrics.test?.roc_auc)}</dd></dl></Card>})}</div><Card className="mt-5" title="PennyLane + PyTorch Hybrid architecture" description={data.evidence.explainability.output_path}><div className="hybrid-flow">{['Classical preprocessing','Feature representation','PennyLane quantum circuit','Expectation values','PyTorch output head','Positive-class probability'].map((x,i)=><div key={x}><span>{i+1}</span><strong>{x}</strong></div>)}</div><div className="grid gap-3 md:grid-cols-4 mt-5"><MetricCard label="QUBITS" value={h.qubits??hc.qubits}/><MetricCard label="QUANTUM LAYERS" value={h.quantum_layers??hc.quantum_layers}/><MetricCard label="OPTIMIZER" value={h.optimizer??hc.optimizer}/><MetricCard label="EPOCHS" value={h.epochs??hc.epochs}/></div><JsonDisclosure label="Verified hybrid configuration" value={{runtime:h,configuration:hc}}/></Card></div>}}</DemoBoundary>;
}

export function VerifiedRobustness(){
  return <DemoBoundary>{data=>{const results=data.evidence.robustness.results;return <div><PageHeader eyebrow="Precomputed verified research evidence" title="Robustness under controlled perturbation" description="Loaded directly from the package; no degradation experiment is running."/><StageNav current="/robustness"/><WorkbenchRail items={[{label:'Models',value:new Set(results.map(x=>x.model_id)).size,detail:'All flagship artifacts',tone:'blue'},{label:'Conditions',value:new Set(results.map(x=>x.condition)).size,detail:'Packaged perturbations',tone:'purple'},{label:'Records',value:results.length,detail:data.evidence.robustness.method,tone:'green'},{label:'Computation',value:'Precomputed',detail:'No POST request',tone:'amber'}]}/><Card className="mt-5" title="Observed degradation evidence"><div className="table-wrap"><table className="data-table min-w-[820px]"><thead><tr><th>Model</th><th>Condition</th><th>Baseline accuracy</th><th>Degraded accuracy</th><th>Δ accuracy</th><th>Δ ROC-AUC</th></tr></thead><tbody>{results.map((r,i)=><tr key={`${r.model_id}-${r.condition}-${i}`}><td>{modelLabels[r.model_type]}</td><td>{r.condition.replaceAll('_',' ')}</td><td>{metric(r.baseline.accuracy)}</td><td>{metric(r.degraded.accuracy)}</td><td>{metric(r.delta.accuracy,false)}</td><td>{metric(r.delta.roc_auc,false)}</td></tr>)}</tbody></table></div></Card><JsonDisclosure label="Complete packaged robustness evidence" value={results}/></div>}}</DemoBoundary>;
}

export function VerifiedExplainability(){
  return <DemoBoundary>{data=>{const x=data.evidence.explainability;const local=x.local;const positive=local.contributions.filter(c=>(c.contribution??0)>0);const negative=local.contributions.filter(c=>(c.contribution??0)<0);return <div><PageHeader eyebrow="PennyLane + PyTorch Hybrid · packaged SHAP" title="Why was this case flagged?" description="Local and global SHAP evidence for the genuine hybrid probability path; no explanation is computed in the browser or at request time."/><StageNav current="/explainability"/><div className="grid gap-5 lg:grid-cols-[.9fr_1.1fr] mt-5"><Card title={`Explained case · ${local.case_id}`} description={local.model_display_name}><ProbabilityBand probability={local.prediction_context.probability_positive} threshold={local.prediction_context.operating_threshold}/><div className="grid grid-cols-2 gap-3 mt-4"><MetricCard label="PREDICTED CLASS" value={local.prediction_context.predicted_class}/><MetricCard label="METHOD" value={x.method}/></div><Notice tone="amber">{local.limitations[0]}</Notice></Card><Card title="Top local contributions" description="Signed contribution to final positive-class probability."><InfluenceBars items={local.contributions}/></Card></div><div className="two-grid mt-5"><ContributionList title="Toward positive" items={positive}/><ContributionList title="Toward negative" items={negative}/></div><Card className="mt-5" title="Global SHAP summary" description="Mean absolute contribution across the packaged representative cases."><TremorBarChart data={x.global_summary.map(v=>({feature:v.feature,value:v.mean_absolute_shap}))} category="feature" value="value" height={340} showGrid/></Card><JsonDisclosure label="Complete verified SHAP evidence" value={x}/></div>}}</DemoBoundary>;
}

function ContributionList({title,items}:{title:string;items:{feature:string;contribution?:number;original_value?:unknown}[]}){
  return <Card title={title}>{items.length?<div>{items.map(item=><div className="tremor-list-row" key={item.feature}><div><strong className="text-xs">{item.feature}</strong><p className="text-[10px] muted">Value: {String(item.original_value??'—')}</p></div><strong className="mono ml-auto text-xs">{Number(item.contribution??0).toFixed(4)}</strong></div>)}</div>:<p className="text-xs muted">No contribution in this direction.</p>}</Card>;
}

export function VerifiedPrediction(){
  return <DemoBoundary>{data=><div><PageHeader eyebrow="Representative research cases · precomputed" title="Flagged & not-flagged examples" description="Deterministic packaged examples from the verified hybrid artifact—not real-time clinical diagnoses."/><StageNav current="/prediction"/><div className="two-grid mt-5">{data.evidence.predictions.cases.map(value=><PredictionCase key={value.case_id} value={value}/>)}</div><Notice tone="amber">These cases demonstrate model behavior on the public research dataset. They are not patient identities, diagnoses, or screening cutoffs.</Notice></div>}</DemoBoundary>;
}

function PredictionCase({value}:{value:VerifiedPredictionCase}){
  return <Card title={value.case_label==='flagged'?'Flagged case':'Not flagged case'} description={value.case_id}><div className="flex gap-2"><Badge tone={value.case_label==='flagged'?'amber':'green'}>{value.predicted_class}</Badge><Badge tone="purple">PennyLane + PyTorch Hybrid</Badge></div><ProbabilityBand probability={value.probability_positive} threshold={value.threshold}/><dl className="demo-dl mt-4"><dt>Probability</dt><dd>{metric(value.probability_positive)}</dd><dt>Threshold</dt><dd>{value.threshold.toFixed(4)}</dd><dt>Threshold source</dt><dd>{value.threshold_source.replaceAll('_',' ')}</dd></dl><JsonDisclosure label="Reproducible input context" value={value.input}/></Card>;
}