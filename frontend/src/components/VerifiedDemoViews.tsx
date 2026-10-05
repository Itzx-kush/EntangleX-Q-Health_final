import {useEffect} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Atom,CheckCircle2,Database,FlaskConical,ShieldCheck,Sparkles} from 'lucide-react';
import {Badge,Button,Card} from './ui';
import {EmptyState,ErrorBanner,JsonDisclosure,Loading,MetricCard,Notice,PageHeader} from './Shared';
import {ProbabilityBand,PipelineFlow,StatusStrip,WorkbenchRail} from './TremorWorkbench';
import {TremorBarChart} from './TremorUI';
import {InfluenceBars,MetricBars,RocChart,ThresholdTradeoffChart,ValueBars} from './Charts';
import {StageNav} from '../pages/ResearchPagesCore';
import {metric,modelLabels,seconds} from '../utils/format';
import {useFlagshipData} from '../hooks/useVerifiedDemo';
import {ResearchResultsCenter} from './ResearchResultsCenter';
import {ExplainabilityResearchLab} from './ExplainabilityResearchLab';
import {ResearchPredictionLab} from './ResearchPredictionLab';
import {RobustnessEvidenceLab} from './RobustnessEvidenceLab';
import {QuantumEvidenceLab} from './QuantumEvidenceLab';
import {HybridArchitectureVisualization} from './HybridArchitectureVisualization';
import type {MetricName,ModelKind,ModelRecord,VerifiedPredictionCase} from '../types/qhealth';

const family=(kind:ModelKind)=>kind==='hybrid_pennylane_torch'?'Hybrid':(['vqc','qsvc','qnn'] as string[]).includes(kind)?'Quantum':'Classical';
const toneFor=(kind:ModelKind)=>family(kind)==='Hybrid'?'purple':family(kind)==='Quantum'?'blue':'green';

function EvidenceStrip({source='Verified artifact package',scope='Early Stage Diabetes',limitation='Research benchmark only'}:{source?:string;scope?:string;limitation?:string}){
  return <div className="evidence-provenance-strip" role="note" aria-label="Evidence provenance">
    <div><span>Source</span><strong>{source}</strong></div>
    <div><span>Status</span><strong><i className="evidence-status-dot" aria-hidden="true"/>Precomputed / verified</strong></div>
    <div><span>Scope</span><strong>{scope}</strong></div>
    <div><span>Limitation</span><strong>{limitation}</strong></div>
  </div>;
}

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

export function VerifiedDemoLanding({current='/demo'}:{current?:string}){
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
    <HybridArchitectureVisualization alignment={data.alignment.data} dataset={dataset} experiment={data.payload.experiment} models={models} evidence={evidence}/>
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
    <StageNav current={current}/>
  </div>;
}

export function VerifiedQuality(){
  return <DemoBoundary>{data=>{const d=data.dataset,q=d.quality,p=data.evidence.provenance.dataset;return <div>
    <PageHeader eyebrow="02 / Verified dataset evidence" title="Data quality & provenance" description="The packaged dataset state that produced the flagship experiment. No validation job is started."/>
    <EvidenceStrip source="Packaged dataset + provenance record" scope={d.name}/>
    <StageNav current="/quality"/>
    <WorkbenchRail items={[{label:'Samples',value:p.row_count,detail:'Source rows',tone:'blue'},{label:'Features',value:p.feature_count,detail:p.target,tone:'purple'},{label:'Duplicates',value:q.duplicate_rows,detail:'Disclosed exact duplicates',tone:q.duplicate_rows?'amber':'green'},{label:'Missing cells',value:Object.values(q.missing_values).reduce((a,b)=>a+Number(b),0),detail:'Measured by backend',tone:'green'}]}/>
    <div className="two-grid mt-5"><Card title="Class distribution" description={`${p.positive_label} / ${p.negative_label}`}><ValueBars items={Object.entries(p.class_distribution).map(([name,value])=>({name,value}))}/></Card><Card title="Quality findings"><Notice tone={q.blockers.length?'amber':'green'}>{q.blockers.length?`${q.blockers.length} blocker(s) disclosed.`:'No blocking issue in the packaged quality record.'}</Notice><div className="mt-3 space-y-2">{q.blockers.map(x=><p className="text-xs text-red-700" key={x}>{x}</p>)}{q.warnings.map(x=><p className="text-xs text-amber-700" key={x}>{x}</p>)}</div></Card></div>
    <div className="two-grid mt-5"><Card title="Source & attribution"><dl className="demo-dl"><dt>Source</dt><dd>{p.source}</dd><dt>Attribution</dt><dd>{String(p.attribution||'—')}</dd><dt>License</dt><dd>{p.license||'—'}</dd><dt>Dataset SHA-256</dt><dd className="mono break-all">{data.dataset.sha256}</dd></dl></Card><Card title="Integrity detail"><JsonDisclosure label="Packaged quality record" value={q}/><JsonDisclosure label="Dataset provenance" value={p}/></Card></div>
  </div>}}</DemoBoundary>;
}

export function VerifiedPipeline({stage}:{stage:'preprocessing'|'features'|'pca'}){
  return <DemoBoundary>{data=>{const p=data.evidence.preprocessing,c=p.configuration.pipeline,r=p.representation as Record<string,any>,f=p.fitted_preprocessing as Record<string,any>;return <div>
    <PageHeader eyebrow="Verified research process" title={stage==='preprocessing'?'Preprocessing':stage==='features'?'Features & selection':'PCA & quantum representation'} description="Read-only configuration from the controlled flagship experiment; no preview or training request is made."/>
    <EvidenceStrip source="Flagship experiment configuration" scope={data.dataset.name}/>
    <StageNav current={stage==='preprocessing'?'/preprocessing':stage==='features'?'/features':'/pca'}/>
    <PipelineFlow items={[{label:'Input',detail:`${r.raw_input_features?.length??data.dataset.provenance.feature_count} source features`,status:'complete'},{label:'Transform',detail:`${c.imputer} imputation · ${c.scaler} scaling`,status:'complete'},{label:'Select',detail:`${c.selection} · ${r.selected_feature_count??'—'} retained`,status:'complete'},{label:'Reduce',detail:`${c.pca_components??'No'} PCA components`,status:'complete'},{label:'Angles',detail:c.angle_scaling?'Angle scaling enabled':'Disabled',status:'complete'}]}/>
    <WorkbenchRail items={[{label:'Imputer',value:c.imputer,detail:'Missing-value policy',tone:'blue'},{label:'Scaler',value:c.scaler,detail:'Shared scaling',tone:'purple'},{label:'PCA',value:c.pca_components??'Off',detail:'Components',tone:'green'},{label:'Final dimension',value:r.final_representation_dimension??'—',detail:'Shared comparison space',tone:'amber'}]}/>
    <div className="two-grid mt-5"><Card title="Verified configuration"><dl className="demo-dl"><dt>Feature selection</dt><dd>{c.selection}</dd><dt>Maximum features</dt><dd>{c.k_features}</dd><dt>PCA components</dt><dd>{c.pca_components??'Disabled'}</dd><dt>PCA whitening</dt><dd>{c.pca_whiten?'Yes':'No'}</dd><dt>Angle scaling</dt><dd>{c.angle_scaling?'Enabled':'Disabled'}</dd><dt>Duplicate policy</dt><dd>{p.configuration.duplicate_policy}</dd><dt>Seed</dt><dd>{p.configuration.seed}</dd></dl></Card><Card title="Fitted pipeline evidence"><JsonDisclosure label="Fitted preprocessing" value={f}/><JsonDisclosure label="Shared representation" value={r}/><JsonDisclosure label="Controlled split" value={p.split}/></Card></div>
  </div>}}</DemoBoundary>;
}

export function VerifiedTraining(){
  return <DemoBoundary>{data=><div><PageHeader eyebrow="Verified result view · no live training" title="Flagship model set" description="Seven frozen, integrity-checked artifacts from one controlled experiment. Configuration controls and training actions are intentionally absent."/><EvidenceStrip source="Verified model artifacts" scope={data.dataset.name}/><StageNav current="/training"/><StatusStrip items={[{label:'Experiment',value:'Succeeded',status:'good'},{label:'Mode',value:'Precomputed',status:'good'},{label:'Models',value:String(data.models.length),status:'good'},{label:'Training request',value:'Not created',status:'neutral'}]}/><ModelTable models={data.models}/></div>}</DemoBoundary>;
}

function ModelTable({models}:{models:ModelRecord[]}){
  return <Card className="mt-5" title="Measured held-out results" description="Descriptive evidence only; no winner or quantum-advantage claim."><div className="table-wrap"><table className="data-table min-w-[980px]"><thead><tr><th>Family</th><th>Model</th><th>Status</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>Training</th><th>Execution</th></tr></thead><tbody>{models.map(model=>{const m=model.metrics.test;const q=model.details.quantum as Record<string,any>|undefined;return <tr key={model.id}><td><Badge tone={toneFor(model.model_type)}>{family(model.model_type)}</Badge></td><td><strong>{modelLabels[model.model_type]}</strong></td><td><Badge tone="green">{model.status}</Badge></td><td>{metric(m?.accuracy)}</td><td>{metric(m?.precision)}</td><td>{metric(m?.recall)}</td><td>{metric(m?.f1)}</td><td>{metric(m?.roc_auc)}</td><td>{seconds(model.metrics.timing?.final_training_seconds)}</td><td>{q?.execution_kind||'Classical CPU execution'}</td></tr>})}</tbody></table></div></Card>;
}

export function VerifiedComparison(){
  return <DemoBoundary>{data=>{
    const benchmarkModels=(data.evidence.benchmark.models||[]) as Array<Record<string,any>>;
    const benchmarkById=new Map(benchmarkModels.map(model=>[String(model.model_id),model]));
    const models=data.models.map(model=>{
      const evidence=benchmarkById.get(model.id);
      const evidenceMetrics=(evidence?.metrics||{}) as Record<string,any>;
      return {...model,metrics:{
        ...model.metrics,
        training:model.metrics.training||evidenceMetrics.training,
        test:model.metrics.test?.roc_curve?.fpr?.length?model.metrics.test:{...(model.metrics.test||{}),...(evidenceMetrics.test||{})},
        validation:model.metrics.validation||evidenceMetrics.validation,
        timing:model.metrics.timing||evidenceMetrics.timing,
        calibration:model.metrics.calibration||evidenceMetrics.calibration,
        operating_point:model.metrics.operating_point||evidence?.operating_point||evidenceMetrics.operating_point
      }} as ModelRecord;
    });
    const preprocessing=data.evidence.preprocessing;
    const comparison={
      split:preprocessing.split,
      controlled_protocol:null,
      comparison_fingerprint:data.manifest_sha256,
      limitations:['Verified precomputed package; no live computation is executed.','The package records no quantum-advantage or real-hardware claim.']
    };
    return <div>
      <PageHeader eyebrow="Verified result view · no live computation" title="Research Results Center" description="A complete, read-only interpretation of the packaged experiment, its measured model evidence, variability, conditions, and next investigation paths."/>
      <EvidenceStrip source="Controlled benchmark record" scope={`${models.length} models · one verified experiment`}/>
      <StageNav current="/comparison"/>
      <div className="mt-5"><ResearchResultsCenter experiment={{...data.experiment,summary:{...data.experiment.summary,sample_count:(data.evidence.benchmark.comparison_contract as Record<string,unknown>).evaluated_row_count}}} dataset={data.dataset} models={models} comparison={comparison} mode="verified"/></div>
    </div>;
  }}</DemoBoundary>;
}

export function VerifiedQuantum(){
  return <DemoBoundary>{data=>{const quantum=data.models.filter(model=>family(model.model_type)!=='Classical');return <div><PageHeader eyebrow="Verified quantum evidence · precomputed" title="Quantum Evidence Lab" description="Read-only execution, configuration, runtime, and circuit evidence from packaged quantum and hybrid artifacts. Opening this page does not execute Qiskit or PennyLane."/><EvidenceStrip source="Validated simulator artifacts" scope={`${quantum.length} quantum / hybrid models`} limitation="Simulation · no hardware or advantage claim"/><StageNav current="/quantum"/><div className="mt-5"><QuantumEvidenceLab mode="verified" models={data.models} experiment={data.experiment} dataset={data.dataset}/></div></div>}}</DemoBoundary>;
}

export function VerifiedRobustness(){
  return <DemoBoundary>{data=>{const results=data.evidence.robustness.results;return <div><PageHeader eyebrow="Verified robustness evidence · precomputed" title="Robustness Evidence Lab" description="Read-only baseline, degraded, scenario, model, and limitation evidence from the packaged experiment; no perturbation study runs when this page opens."/><EvidenceStrip source="Packaged robustness lab" scope={`${results.length} measured records`} limitation="Evaluated scenarios only · no generalization claim"/><StageNav current="/robustness"/><WorkbenchRail items={[{label:'Models',value:new Set(results.map(x=>x.model_id)).size,detail:'Packaged model artifacts',tone:'blue'},{label:'Conditions',value:new Set(results.map(x=>x.condition)).size,detail:'Packaged perturbations',tone:'purple'},{label:'Records',value:results.length,detail:data.evidence.robustness.method,tone:'green'},{label:'Computation',value:'Precomputed',detail:'No study execution',tone:'amber'}]}/><div className="mt-5"><RobustnessEvidenceLab mode="verified" experiment={data.experiment} dataset={data.dataset} models={data.models} verifiedRecords={results} method={data.evidence.robustness.method}/></div></div>}}</DemoBoundary>;
}

export function VerifiedExplainability(){
  return <DemoBoundary>{data=>{
    const evidence=data.evidence.explainability;
    const model=data.models.find(item=>item.id===evidence.model_id)||data.models.find(item=>item.model_type==='hybrid_pennylane_torch');
    return <div>
      <PageHeader eyebrow="Verified explainability · packaged evidence" title="Explainability Research Lab" description="Global and representative local SHAP evidence for the frozen hybrid output; no explanation is computed in the browser or at request time."/>
      <EvidenceStrip source="Packaged hybrid SHAP record" scope={evidence.local.case_id} limitation="Post-hoc research explanation · not diagnosis"/>
      <StageNav current="/explainability"/>
      <div className="mt-5"><ExplainabilityResearchLab model={model} models={model?[model]:[]} experiment={data.experiment} dataset={data.dataset} verified={evidence} mode="verified"/></div>
    </div>;
  }}</DemoBoundary>;
}

export function VerifiedPrediction(){
  return <DemoBoundary>{data=>{
    const evidence=data.evidence.predictions;
    const model=data.models.find(item=>item.id===evidence.model_id);
    return <div>
      <PageHeader eyebrow="Verified / precomputed representative cases" title="Research Prediction Lab" description="Traceable packaged research inputs and hybrid outputs from the verified experiment; no live prediction is executed."/>
      <EvidenceStrip source="Packaged prediction evidence" scope={`${evidence.cases.length} representative cases`} limitation="Research model output · not diagnosis"/>
      <StageNav current="/prediction"/>
      <div className="mt-5"><ResearchPredictionLab mode="verified" model={model} models={data.models} experiment={data.experiment} dataset={data.dataset} verifiedCases={evidence.cases}/></div>
    </div>;
  }}</DemoBoundary>;
}
