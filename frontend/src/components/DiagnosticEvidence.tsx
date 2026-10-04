import {useEffect,useMemo,useState} from 'react';
import {Activity,CheckCircle2,Clock3,FlaskConical,Info,ShieldAlert,XCircle} from 'lucide-react';
import {Badge,Card,Select} from './ui';
import {JsonDisclosure,MetricCard,Notice,StatusBadge} from './Shared';
import {CalibrationChart,RocChart,ThresholdTradeoffChart} from './Charts';
import {metric,modelLabels,seconds} from '../utils/format';
import type {Experiment,MetricName,ModelRecord} from '../types/qhealth';

const metrics:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];
const primaryOrder:MetricName[]=['roc_auc','f1','accuracy','recall','sensitivity','specificity','precision'];
type EvidenceState='AVAILABLE'|'LIMITED'|'NOT AVAILABLE'|'NOT YET EVALUATED'|'NOT APPLICABLE';

function finite(value:unknown):value is number{return typeof value==='number'&&Number.isFinite(value)}
function label(name:MetricName){return name==='roc_auc'?'ROC-AUC':name.replaceAll('_',' ').toUpperCase()}
function evidenceTone(state:EvidenceState):'green'|'blue'|'amber'|'red'{return state==='AVAILABLE'?'green':state==='LIMITED'?'blue':state==='NOT APPLICABLE'?'amber':state==='NOT YET EVALUATED'?'amber':'red'}
function EvidenceStatus({state}:{state:EvidenceState}){
 const Icon=state==='AVAILABLE'?CheckCircle2:state==='LIMITED'?Info:state==='NOT APPLICABLE'||state==='NOT YET EVALUATED'?ShieldAlert:XCircle;
 return <Badge tone={evidenceTone(state)}><Icon size={11}/>{state}</Badge>;
}
function hasMetrics(model:ModelRecord){return Boolean(model.metrics.test&&metrics.some(name=>finite(model.metrics.test?.[name])))}
function primaryMetric(model:ModelRecord){return primaryOrder.find(name=>finite(model.metrics.test?.[name])||finite(model.metrics.validation?.summary?.[name]?.mean))}
function count(value:number|null|undefined){return finite(value)?String(value):'Not recorded'}
function calibrationState(model:ModelRecord,experiment:Experiment):EvidenceState{
 const calibration=model.metrics.calibration;
 if(calibration?.method==='not_available')return 'NOT APPLICABLE';
 if(calibration?.method==='none'&&(finite(calibration.brier_score)||calibration.reliability_curve))return 'LIMITED';
 if(calibration?.method&&calibration.method!=='none')return finite(calibration.brier_score)||calibration.reliability_curve?'AVAILABLE':'LIMITED';
 return experiment.config?.calibration==='none'?'NOT YET EVALUATED':'NOT AVAILABLE';
}
function runtimeState(model:ModelRecord):EvidenceState{
 const timing=model.metrics.timing;
 if(!timing)return 'NOT AVAILABLE';
 const values=[timing.final_training_seconds,timing.cv_total_seconds,timing.test_inference_seconds,timing.test_inference_seconds_per_sample];
 const available=values.filter(finite).length;
 return available===values.length?'AVAILABLE':available?'LIMITED':'NOT AVAILABLE';
}
function EvidenceItem({label:copy,state,detail}:{label:string;state:EvidenceState;detail:string}){
 return <div className="rounded-lg border p-3"><div className="flex items-start justify-between gap-2"><strong className="text-xs">{copy}</strong><EvidenceStatus state={state}/></div><p className="mt-2 text-[10px] muted">{detail}</p></div>;
}

export function DiagnosticEvidence({experiment,models,mode,limitations=[]}:{experiment:Experiment;models:ModelRecord[];mode:'live'|'verified';limitations?:string[]}){
 const initial=models.find(model=>hasMetrics(model))?.id||models[0]?.id||'';
 const [modelId,setModelId]=useState(initial);
 useEffect(()=>{if(!models.some(model=>model.id===modelId))setModelId(models.find(model=>hasMetrics(model))?.id||models[0]?.id||'')},[models,modelId]);
 const model=models.find(item=>item.id===modelId)||models[0];
 const diagnostic=useMemo(()=>{
  if(!model)return null;
  const test=model.metrics.test;
  const validation=model.metrics.validation;
  const operating=model.metrics.operating_point;
  const calibration=model.metrics.calibration||{};
  const primary=primaryMetric(model);
  const primarySummary=primary?validation?.summary?.[primary]:undefined;
  const confusionAvailable=Boolean(test?.confusion_matrix?.length===2&&test.confusion_matrix.every(row=>row.length===2));
  const rocAvailable=Boolean(test?.roc_curve?.fpr?.length&&test.roc_curve.fpr.length===test.roc_curve.tpr.length);
  const cvState:EvidenceState=validation?.folds?.length?'AVAILABLE':validation?.summary&&Object.values(validation.summary).some(value=>finite(value?.mean))?'LIMITED':'NOT AVAILABLE';
  const operatingState:EvidenceState=operating?(operating.threshold_feasible?'AVAILABLE':'LIMITED'):'NOT YET EVALUATED';
  const thresholdState:EvidenceState=operating?.curve?.length?'AVAILABLE':operating?'LIMITED':'NOT YET EVALUATED';
  const calibrationEvidenceState=calibrationState(model,experiment);
  return {test,validation,operating,calibration,primary,primarySummary,confusionAvailable,rocAvailable,cvState,operatingState,thresholdState,calibrationEvidenceState};
 },[model,experiment]);
 if(!model||!diagnostic)return <Card title="Diagnostic Evidence"><p className="text-sm muted">No persisted model records are available for diagnostic inspection.</p></Card>;
 const {test,validation,operating,calibration,primary,primarySummary,confusionAvailable,rocAvailable,cvState,operatingState,thresholdState,calibrationEvidenceState}=diagnostic;
 const findings:string[]=[];
 if(primary&&finite(test?.[primary])){
  let text=`${modelLabels[model.model_type]} recorded a held-out ${label(primary)} of ${metric(test?.[primary])}`;
  if(finite(primarySummary?.mean))text+=` with a cross-validation mean of ${metric(primarySummary?.mean)}${finite(primarySummary?.std)?` ± ${metric(primarySummary?.std)}`:''}`;
  findings.push(text+'.');
 }
 if(operating?.validation_metrics&&finite(operating.validation_metrics.sensitivity)&&finite(operating.validation_metrics.specificity))findings.push(`The persisted research operating point produced observed validation sensitivity of ${metric(operating.validation_metrics.sensitivity)} and specificity of ${metric(operating.validation_metrics.specificity)}.`);
 if(calibration?.method==='none'||experiment.config?.calibration==='none')findings.push('Calibration was not performed; any displayed probability diagnostics describe uncalibrated research outputs.');
 if(test&&finite(test.false_positive)&&finite(test.false_negative))findings.push(`The held-out confusion matrix contains ${test.false_positive} false positives and ${test.false_negative} false negatives.`);
 const gaps:string[]=[];
 if(!confusionAvailable)gaps.push('Held-out confusion matrix was not recorded.');
 if(!rocAvailable)gaps.push('A valid persisted ROC curve is unavailable for the selected model.');
 if(cvState!=='AVAILABLE')gaps.push(cvState==='LIMITED'?'Validation summary exists, but fold-level values are not recorded.':'Cross-validation evidence is unavailable.');
 if(!operating)gaps.push('Operating-point evidence was not evaluated or not persisted.');
 if(!operating?.curve?.length)gaps.push('Threshold trade-off coordinates are unavailable.');
 if(calibrationEvidenceState==='NOT AVAILABLE'||calibrationEvidenceState==='NOT YET EVALUATED')gaps.push('Calibration evidence was not evaluated or not persisted.');

 return <section className="space-y-5" aria-label="Diagnostic and statistical research evidence">
  <Card title="Diagnostic Evidence" description={`${mode==='verified'?'Verified precomputed':'Live persisted'} evidence availability for the selected model. Viewing or switching models does not execute scientific computation.`}>
   <div className="mb-4 grid gap-3 md:grid-cols-[minmax(240px,.8fr)_minmax(0,2fr)]"><label className="field"><span>Model diagnostic selector</span><Select aria-label="Model diagnostic selector" value={model.id} onChange={event=>setModelId(event.target.value)}>{models.map(item=><option key={item.id} value={item.id}>{modelLabels[item.model_type]} · {item.status}</option>)}</Select></label><div className="rounded-lg border p-3"><div className="flex flex-wrap items-center gap-2"><strong>{modelLabels[model.model_type]}</strong><StatusBadge value={model.status}/><Badge tone={mode==='verified'?'purple':'blue'}>{mode==='verified'?'PRECOMPUTED / VERIFIED':'PERSISTED LIVE RESULT'}</Badge></div><p className="mt-2 text-xs muted">Selected model evidence updates locally from the already loaded model records.</p></div></div>
   <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
    <EvidenceItem label="Held-out metrics" state={hasMetrics(model)?'AVAILABLE':'NOT AVAILABLE'} detail="Final held-out/test record"/>
    <EvidenceItem label="Cross-validation" state={cvState} detail={validation?.std_definition||'Fold evidence not recorded'}/>
    <EvidenceItem label="Confusion matrix" state={confusionAvailable?'AVAILABLE':'NOT AVAILABLE'} detail="Persisted held-out classification counts"/>
    <EvidenceItem label="ROC curve" state={rocAvailable?'AVAILABLE':'NOT AVAILABLE'} detail="Persisted held-out FPR/TPR coordinates"/>
    <EvidenceItem label="Operating-point analysis" state={operatingState} detail={operating?.threshold_source||'No threshold source recorded'}/>
    <EvidenceItem label="Threshold trade-off" state={thresholdState} detail={operating?.curve?.length?`${operating.curve.length} persisted validation points`:'Curve not recorded'}/>
    <EvidenceItem label="Calibration" state={calibrationEvidenceState} detail={calibration?.method==='none'?'Not performed; uncalibrated diagnostics only':calibration?.method||'Method not recorded'}/>
    <EvidenceItem label="Runtime measurements" state={runtimeState(model)} detail="Observed on this execution environment"/>
   </div>
  </Card>

  <div className="tremor-grid-main">
   <Card title="Held-out confusion matrix" description="Persisted observed rows × predicted columns for the selected model.">
    {confusionAvailable&&test?<><div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-center text-xs"><div/><div className="metric-label">Predicted negative</div><div className="metric-label">Predicted positive</div><div className="flex items-center text-left metric-label">Observed negative</div><div className="rounded-xl border bg-emerald-500/5 p-5"><span className="metric-label">TRUE NEGATIVE</span><strong className="mt-2 block text-2xl">{count(test.true_negative)}</strong></div><div className="rounded-xl border bg-amber-500/5 p-5"><span className="metric-label">FALSE POSITIVE</span><strong className="mt-2 block text-2xl">{count(test.false_positive)}</strong></div><div className="flex items-center text-left metric-label">Observed positive</div><div className="rounded-xl border bg-red-500/5 p-5"><span className="metric-label">FALSE NEGATIVE</span><strong className="mt-2 block text-2xl">{count(test.false_negative)}</strong></div><div className="rounded-xl border bg-emerald-500/5 p-5"><span className="metric-label">TRUE POSITIVE</span><strong className="mt-2 block text-2xl">{count(test.true_positive)}</strong></div></div><div className="mt-4 grid gap-3 sm:grid-cols-4"><MetricCard label="HELD-OUT SAMPLES" value={count(test.sample_count)}/><MetricCard label="SENSITIVITY / RECALL" value={metric(test.sensitivity)}/><MetricCard label="SPECIFICITY" value={metric(test.specificity)}/><MetricCard label="PRECISION" value={metric(test.precision)}/><MetricCard label="ACCURACY" value={metric(test.accuracy)}/><MetricCard label="F1" value={metric(test.f1)}/></div></>:<Notice tone="amber">Evidence not recorded. No confusion-matrix values are reconstructed from other metrics.</Notice>}
   </Card>
   <Card title="Cross-validation stability" description={primary?`${experiment.config?.cv_folds||primarySummary?.valid_folds||'Configured'}-fold validation · ${label(primary)}`:'No supported primary validation metric is available.'}>
    {primary&&primarySummary?<><div className="grid gap-3 sm:grid-cols-3"><MetricCard label="CV MEAN" value={metric(primarySummary.mean)}/><MetricCard label="OBSERVED CV VARIABILITY" value={finite(primarySummary.std)?`± ${metric(primarySummary.std)}`:'Not recorded'}/><MetricCard label="VALID FOLDS" value={primarySummary.valid_folds}/></div>{validation?.folds?.length?<div className="table-wrap mt-4"><table className="data-table"><thead><tr><th>Fold</th><th>{label(primary)}</th></tr></thead><tbody>{validation.folds.map((fold,index)=><tr key={index}><td>Fold {index+1}</td><td>{metric(fold[primary])}</td></tr>)}</tbody></table></div>:<p className="mt-4 text-xs muted">Fold-level values were not recorded; only the persisted summary is available.</p>}<p className="mt-3 text-[10px] muted">{validation?.std_definition||'Standard-deviation definition not recorded. No confidence interval or significance claim is inferred.'}</p></>:<Notice tone="amber">Cross-validation evidence is not available for the selected model.</Notice>}
   </Card>
  </div>

  <Card title="Validation / cross-validation vs held-out test" description="The validation evidence used during model assessment is kept separate from the final held-out result.">
   <div className="table-wrap overflow-x-auto"><table className="data-table"><thead><tr><th>Metric</th><th>CV mean</th><th>CV SD</th><th>Valid folds</th><th>Held-out test</th></tr></thead><tbody>{metrics.map(name=>{const summary=validation?.summary?.[name];return <tr key={name}><td>{label(name)}</td><td>{metric(summary?.mean)}</td><td>{metric(summary?.std)}</td><td>{summary?.valid_folds??'Not recorded'}</td><td>{metric(test?.[name])}</td></tr>})}</tbody></table></div>
  </Card>

  <Card title="Held-out ROC behavior" description="Actual persisted test-set coordinates for evaluated models; models without valid ROC evidence are omitted."><RocChart models={models}/><div className="mt-3 text-xs muted">Excluded: {models.filter(item=>!item.metrics.test?.roc_curve?.fpr?.length||item.metrics.test.roc_curve.fpr.length!==item.metrics.test.roc_curve.tpr.length).map(item=>modelLabels[item.model_type]).join(', ')||'None'}.</div></Card>

  <div className="tremor-grid-main">
   <Card title="Research operating point" description="How the persisted validation-derived threshold was selected.">
    {operating?<><div className="grid gap-3 sm:grid-cols-2"><MetricCard label="SELECTION STRATEGY" value={operating.selection_strategy.replaceAll('_',' ')}/><MetricCard label="SELECTED THRESHOLD" value={operating.selected_threshold===null?'Not feasible':operating.selected_threshold.toFixed(4)}/><MetricCard label="THRESHOLD SOURCE" value={operating.threshold_source||'Not recorded'}/><MetricCard label="FEASIBILITY" value={operating.threshold_feasible?'Feasible':'Not feasible'}/><MetricCard label="TARGET SENSITIVITY" value={metric(operating.target_sensitivity)}/><MetricCard label="OOF SAMPLES / CV FOLDS" value={`${operating.number_of_oof_samples??'Not recorded'} / ${operating.cv_fold_count??'Not recorded'}`}/><MetricCard label="VALIDATION SENSITIVITY" value={metric(operating.validation_metrics?.sensitivity)}/><MetricCard label="VALIDATION SPECIFICITY" value={metric(operating.validation_metrics?.specificity)}/></div>{operating.holdout_metrics&&<div className="mt-4"><div className="metric-label mb-2">HELD-OUT METRICS AT THE FROZEN OPERATING POINT</div><div className="grid gap-3 sm:grid-cols-3">{metrics.filter(name=>finite(operating.holdout_metrics?.[name])).map(name=><MetricCard key={name} label={label(name)} value={metric(operating.holdout_metrics?.[name])}/>)}</div></div>}{!operating.threshold_feasible&&<div className="mt-4"><Notice tone="amber">{operating.infeasible_reason||'The configured target was not feasible in persisted validation evidence.'}</Notice></div>}</>:<Notice tone="amber">Operating-point evidence was not evaluated or not recorded for this model.</Notice>}
   </Card>
   <Card title="Threshold trade-off" description="Persisted out-of-fold validation sensitivity, specificity, precision, recall, and F1 across research thresholds.">{operating?<ThresholdTradeoffChart operatingPoint={operating}/>:<Notice tone="amber">Threshold curve not evaluated.</Notice>}</Card>
  </div>

  <div className="tremor-grid-main">
   <Card title="Calibration evidence" description="Probability diagnostics remain distinct from clinical calibration.">
    <div className="grid gap-3 sm:grid-cols-3"><MetricCard label="CALIBRATION" value={calibration?.method==='none'?'Not performed':calibration?.method||'Not recorded'}/><MetricCard label="EVIDENCE STATUS" value={<EvidenceStatus state={calibrationEvidenceState}/>}/><MetricCard label="BRIER SCORE" value={finite(calibration?.brier_score)?calibration.brier_score.toFixed(4):'Not recorded'}/></div><div className="mt-4"><CalibrationChart calibration={calibration}/></div><p className="mt-3 text-xs muted">{calibration?.interpretation||'No persisted calibration interpretation is available.'}</p><p className="mt-2 text-[10px] muted">Separate calibration study status: not recorded in this model result.</p>
   </Card>
   <Card title="Observed runtime" description="Observed runtime on this execution environment; not a general infrastructure benchmark.">
    <div className="grid gap-3 sm:grid-cols-2"><MetricCard label="FINAL TRAINING" value={seconds(model.metrics.timing?.final_training_seconds)}/><MetricCard label="TOTAL CV" value={seconds(model.metrics.timing?.cv_total_seconds)}/><MetricCard label="MEAN CV FOLD" value="Not recorded separately"/><MetricCard label="HELD-OUT INFERENCE" value={seconds(model.metrics.timing?.test_inference_seconds)}/><MetricCard label="INFERENCE / SAMPLE" value={seconds(model.metrics.timing?.test_inference_seconds_per_sample)}/><MetricCard label="EXECUTION" value={String((model.details.quantum as Record<string,unknown>|undefined)?.execution_kind||'Classical / not separately recorded')}/></div>{model.metrics.timing?.cv_fold_seconds?.length?<JsonDisclosure label="Persisted per-fold runtime values" value={model.metrics.timing.cv_fold_seconds.map((value,index)=>({fold:index+1,seconds:value}))}/>:null}
   </Card>
  </div>

  <div className="tremor-grid-main">
   <Card title="Diagnostic findings" description="Machine-derived statements from the selected model's visible persisted evidence."><ul className="space-y-3">{findings.length?findings.map((finding,index)=><li className="flex gap-3 text-sm" key={index}><Activity className="mt-0.5 shrink-0 text-primary" size={16}/><span>{finding}</span></li>):<li className="text-sm muted">Insufficient persisted evidence for diagnostic findings.</li>}</ul></Card>
   <Card title="Limitations / evidence gaps" description="Missing evidence remains explicit and is never converted to zero."><ul className="space-y-2 text-sm">{[...gaps,...limitations].map((item,index)=><li className="flex gap-2" key={`${item}-${index}`}><ShieldAlert className="mt-0.5 shrink-0 text-amber-600" size={15}/><span>{item}</span></li>)}</ul>{!gaps.length&&!limitations.length&&<p className="text-sm muted">No additional evidence gaps were recorded in this view.</p>}<div className="mt-4 flex items-center gap-2 text-[10px] muted"><Clock3 size={13}/>All conclusions are limited to this observed experiment and evaluated dataset.</div></Card>
  </div>
 </section>;
}
