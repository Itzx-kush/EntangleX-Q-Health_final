import {useEffect,useMemo,useState} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Atom,BarChart3,Brain,Database,FileText,GitBranch,ShieldAlert} from 'lucide-react';
import {Badge,Card,Select} from './ui';
import {EmptyState,JsonDisclosure,MetricCard,Notice,StatusBadge} from './Shared';
import {InfluenceBars} from './Charts';
import {ProbabilityBand} from './TremorWorkbench';
import {dateTime,metric,modelLabels,shortId,isHybridModel,isQiskitQuantumModel} from '../utils/format';
import type {Dataset,Experiment,Explanation,HybridLocalExplanation,Influence,ModelRecord,VerifiedEvidencePackage} from '../types/qhealth';

type VerifiedExplanation=VerifiedEvidencePackage['evidence']['explainability'];
type Availability='AVAILABLE'|'LIMITED'|'NOT AVAILABLE'|'NOT APPLICABLE'|'NOT RECORDED';
type Props={
 model?:ModelRecord;
 models:ModelRecord[];
 experiment?:Experiment;
 dataset?:Dataset;
 records?:Explanation[];
 verified?:VerifiedExplanation;
 mode:'live'|'verified';
 onModelChange?:(modelId:string)=>void;
};

function finite(value:unknown):value is number{return typeof value==='number'&&Number.isFinite(value)}
function family(model?:ModelRecord){if(!model)return 'Not recorded';if(isHybridModel(model.model_type))return 'Hybrid';if(isQiskitQuantumModel(model.model_type))return 'Quantum';return 'Classical'}
function methodLabel(value:string|undefined){if(!value)return 'Not recorded';if(value.toLowerCase()==='shap')return 'SHAP';if(value.toLowerCase()==='permutation')return 'Permutation importance';if(value.toLowerCase()==='perturbation')return 'Feature perturbation / sensitivity';return value}
function stateTone(state:Availability):'green'|'blue'|'amber'|'red'{return state==='AVAILABLE'?'green':state==='LIMITED'?'blue':state==='NOT APPLICABLE'?'amber':state==='NOT RECORDED'?'amber':'red'}
function score(item:Influence){return finite(item.contribution)?item.contribution:finite(item.signed_mean)?item.signed_mean:undefined}
function magnitude(item:Influence){return finite(item.magnitude)?item.magnitude:finite(item.absolute_contribution)?item.absolute_contribution:undefined}
function direction(item:Influence){const value=score(item);return item.direction||(value===undefined?'neutral':value>0?'toward_positive':value<0?'toward_negative':'neutral')}
function ranked(items:Influence[]){return [...items].filter(item=>magnitude(item)!==undefined).sort((a,b)=>(magnitude(b)??-Infinity)-(magnitude(a)??-Infinity)||a.feature.localeCompare(b.feature))}
function valueText(value:unknown){return value===null||value===undefined||value===''?'Not recorded':String(value)}
function ContributionList({title,items}:{title:string;items:Influence[]}){
 return <Card title={title} description="Signed contribution to this specific research model output.">{items.length?<div className="space-y-2">{items.map(item=>{const value=score(item);return <div className="rounded-lg border p-3" key={item.feature}><div className="flex items-center justify-between gap-3"><div><strong className="text-sm">{item.feature}</strong><small className="block muted">Original input: {valueText(item.original_value)}</small></div><strong className={direction(item)==='toward_positive'?'text-red-600':'text-blue-600'}>{value===undefined?'Not recorded':`${value>=0?'+':''}${value.toFixed(4)}`}</strong></div>{item.interpretation&&<p className="mt-1 text-xs muted">{item.interpretation}</p>}</div>})}</div>:<p className="text-xs muted">No persisted contribution in this direction.</p>}</Card>;
}

export function ExplainabilityResearchLab({model,models,experiment,dataset,records=[],verified,mode,onModelChange}:Props){
 const [recordId,setRecordId]=useState(records[0]?.id||'');
 useEffect(()=>{if(!records.some(record=>record.id===recordId))setRecordId(records[0]?.id||'')},[records,recordId]);
 const record=records.find(item=>item.id===recordId)||records[0];
 const globalItems=useMemo(()=>verified?verified.global_summary.map(item=>({feature:item.feature,magnitude:item.mean_absolute_shap,signed_mean:item.mean_signed_shap,direction:item.mean_signed_shap>0?'toward_positive':item.mean_signed_shap<0?'toward_negative':'neutral'} as Influence)):record?.result.influence||[],[verified,record]);
 const globalRanked=useMemo(()=>ranked(globalItems),[globalItems]);
 const local=verified?.local as (HybridLocalExplanation&{case_id?:string})|undefined;
 const localRanked=useMemo(()=>ranked(local?.contributions||[]),[local]);
 const positive=localRanked.filter(item=>direction(item)==='toward_positive');
 const negative=localRanked.filter(item=>direction(item)==='toward_negative');
 const explanationMethod=verified?.method||record?.result.method_display||record?.method;
 const limitations=verified?local?.limitations||[]:record?.result.limitations||[];
 const globalState:Availability=globalRanked.length?'AVAILABLE':model?'NOT AVAILABLE':'NOT RECORDED';
 const localState:Availability=local?.contributions?.length?'AVAILABLE':mode==='verified'?'NOT AVAILABLE':'NOT RECORDED';
 const overallState:Availability=globalState==='AVAILABLE'&&localState==='AVAILABLE'?'AVAILABLE':globalState==='AVAILABLE'?'LIMITED':model?'NOT AVAILABLE':'NOT RECORDED';
 const details=(model?.details||{}) as Record<string,unknown>;
 const quantum=(model?.details.quantum||{}) as Record<string,unknown>;
 const modelArtifactId=details.model_artifact_id||details.artifact_id;
 const configurationFingerprint=details.configuration_fingerprint||(record?.result.configuration_fingerprint as string|undefined);
 const explanationCount=verified?local?.explained_case_count:record?.result.explained_case_count??record?.result.sample_count;
 const source=mode==='verified'?'Packaged / verified explanation evidence':record?'Persisted experiment explanation':'No explanation record selected';
 const topGlobal=globalRanked[0];const topPositive=positive[0];const topNegative=negative[0];
 const narrative:string[]=[];
 if(topGlobal)narrative.push(`${topGlobal.feature} had the largest persisted global ${methodLabel(explanationMethod)} magnitude in this explanation record.`);
 if(topPositive)narrative.push(`For the selected research case, ${topPositive.feature} contributed most strongly toward the positive-class model output among the displayed positive contributions.`);
 if(topNegative)narrative.push(`For the selected research case, ${topNegative.feature} contributed most strongly toward the negative-class model output among the displayed negative contributions.`);
 if(mode==='live'&&record)narrative.push(`The global explanation summarizes ${record.result.explained_case_count??record.result.sample_count} bounded held-out research cases; it is not an exhaustive explanation of every dataset row.`);
 const inputProfile=local?.contributions?.filter((item,index,all)=>all.findIndex(other=>other.feature===item.feature)===index)||[];

 return <div className="space-y-5">
  <Card title="Explainability overview" description="Traceable post-training explanation evidence for a frozen model.">
   <div className="grid gap-3 md:grid-cols-[minmax(240px,.8fr)_minmax(0,2fr)]">
    <label className="field"><span>Model explanation</span><Select aria-label="Explainability model" value={model?.id||''} disabled={!onModelChange} onChange={event=>onModelChange?.(event.target.value)}><option value="">Select model</option>{models.map(item=><option key={item.id} value={item.id}>{modelLabels[item.model_type]} · {item.status}</option>)}</Select></label>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><MetricCard label="MODEL" value={model?modelLabels[model.model_type]:'Not selected'} detail={family(model)}/><MetricCard label="METHOD" value={methodLabel(explanationMethod)} detail={verified?'Packaged method':'Persisted record method'}/><MetricCard label="STATUS" value={<Badge tone={stateTone(overallState)}>{overallState}</Badge>} detail={source}/><MetricCard label="EXPLAINED CASES" value={explanationCount??'Not recorded'} detail={local?'Representative local case':record?.result.scope||'Scope not recorded'}/></div>
   </div>
   <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><div className="rounded-lg border p-3"><span className="metric-label">EXPERIMENT</span><strong className="mt-1 block text-sm">{experiment?shortId(experiment.id):model?shortId(model.experiment_id):'Not recorded'}</strong></div><div className="rounded-lg border p-3"><span className="metric-label">DATASET</span><strong className="mt-1 block text-sm">{dataset?.name||(model?shortId(model.dataset_id):'Not recorded')}</strong></div><div className="rounded-lg border p-3"><span className="metric-label">EVIDENCE SOURCE</span><strong className="mt-1 block text-sm">{source}</strong></div><div className="rounded-lg border p-3"><span className="metric-label">TIMESTAMP</span><strong className="mt-1 block text-sm">{record?.created_at?dateTime(record.created_at):'Not recorded'}</strong></div></div>
   {limitations[0]&&<div className="mt-4"><Notice tone="amber">{limitations[0]}</Notice></div>}
  </Card>

  <Card title="Explanation availability" description="Global and local evidence are reported separately; unavailable evidence is never replaced with another model's explanation.">
   <div className="grid gap-3 md:grid-cols-3"><div className="rounded-xl border p-4"><div className="flex items-center justify-between gap-2"><strong>Global explanation</strong><Badge tone={stateTone(globalState)}>{globalState}</Badge></div><p className="mt-2 text-xs muted">What features tend to influence this model across the bounded explanation cases.</p></div><div className="rounded-xl border p-4"><div className="flex items-center justify-between gap-2"><strong>Local explanation</strong><Badge tone={stateTone(localState)}>{localState}</Badge></div><p className="mt-2 text-xs muted">What contributed to one specific persisted research model output.</p></div><div className="rounded-xl border p-4"><div className="flex items-center justify-between gap-2"><strong>Evidence quality</strong><Badge tone={stateTone(overallState)}>{overallState}</Badge></div><p className="mt-2 text-xs muted">{mode==='verified'?'Packaged representative evidence; no computation is run.':'Persisted records only; generation remains an explicit user action.'}</p></div></div>
  </Card>

  {mode==='live'&&records.length>1&&<Card title="Persisted explanation records" description="Choose an existing method-specific record; scores from different methods are not combined."><label className="field max-w-xl"><span>Explanation record</span><Select aria-label="Explanation record" value={record?.id||''} onChange={event=>setRecordId(event.target.value)}>{records.map(item=><option key={item.id} value={item.id}>{methodLabel(item.result.method_display||item.method)} · {dateTime(item.created_at)}</option>)}</Select></label></Card>}

  {globalState==='AVAILABLE'?<Card title="Global feature influence" description="Ranked persisted magnitudes across the bounded explanation dataset; this is model behavior, not medical importance.">
   <div className="mb-3 flex flex-wrap items-center gap-2"><Badge tone="purple">GLOBAL / DATASET-LEVEL</Badge><Badge tone="blue">METHOD: {methodLabel(explanationMethod)}</Badge><span className="text-xs muted">{record?.result.units||'Mean absolute contribution magnitude from packaged evidence'}</span></div>
   <div className="tremor-grid-main"><InfluenceBars items={globalRanked}/><div className="table-wrap overflow-x-auto"><table className="data-table"><thead><tr><th>Rank</th><th>Feature</th><th>Magnitude</th><th>Available direction</th></tr></thead><tbody>{globalRanked.map((item,index)=><tr key={item.feature}><td>{index+1}</td><td><strong>{item.feature}</strong></td><td>{magnitude(item)?.toFixed(6)??'Not recorded'}</td><td>{score(item)===undefined?'Not recorded':`${score(item)!>=0?'+':''}${score(item)!.toFixed(6)} · ${direction(item).replaceAll('_',' ')}`}</td></tr>)}</tbody></table></div></div>
  </Card>:<EmptyState title="Global explainability evidence is not available for this model">Select another model with a persisted explanation or use the explicit generation workflow below.</EmptyState>}

  <div className="grid gap-5 lg:grid-cols-2">
   <Card title="Global explanation" description="What tends to matter across the bounded explanation dataset.">{globalState==='AVAILABLE'?<><Badge tone="blue">{globalRanked.length} ranked features</Badge><div className="mt-4 space-y-2">{globalRanked.slice(0,8).map((item,index)=><div className="flex items-center gap-3 rounded-lg border p-3" key={item.feature}><span className="grid h-7 w-7 place-items-center rounded-full bg-primary/10 text-xs font-bold">{index+1}</span><strong className="flex-1 text-sm">{item.feature}</strong><span className="mono text-xs">{magnitude(item)?.toFixed(4)}</span></div>)}</div></>:<p className="text-sm muted">Not available.</p>}</Card>
   <Card title="Local research case" description="What contributed to this specific persisted model output.">{local?<><div className="flex flex-wrap items-center gap-2"><Badge tone="purple">LOCAL / CASE-LEVEL</Badge><Badge tone="blue">{local.case_id||'Case ID not recorded'}</Badge></div><div className="mt-4"><ProbabilityBand probability={local.prediction_context.probability_positive} threshold={local.prediction_context.operating_threshold} label="Positive-class model probability"/></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><MetricCard label="PREDICTED CLASS" value={local.prediction_context.predicted_class}/><MetricCard label="RESEARCH THRESHOLD" value={local.prediction_context.operating_threshold.toFixed(4)} detail={local.prediction_context.threshold_source.replaceAll('_',' ')}/><MetricCard label="DECISION SCORE" value="Not recorded"/><MetricCard label="METHOD" value={local.method_display}/></div></>:<Notice tone="amber">Local explanation evidence is not recorded for this model. Open Prediction for the existing explicit local-output workflow; no local explanation is generated automatically here.</Notice>}</Card>
  </div>

  {local&&<><Card title="Explained input profile" description="Original input values intentionally persisted with the representative explanation case."><div className="table-wrap overflow-x-auto"><table className="data-table"><thead><tr><th>Feature</th><th>Original input value</th></tr></thead><tbody>{inputProfile.map(item=><tr key={item.feature}><td><strong>{item.feature}</strong></td><td>{valueText(item.original_value)}</td></tr>)}</tbody></table></div></Card><div className="two-grid"><ContributionList title="Toward positive" items={positive}/><ContributionList title="Toward negative" items={negative}/></div></>}

  {model&&(isHybridModel(model.model_type)||isQiskitQuantumModel(model.model_type))&&<Card title="Quantum / hybrid explanation context" description="Execution and explanation metadata are reported without causal or quantum-advantage claims."><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><MetricCard label="MODEL" value={modelLabels[model.model_type]} detail={family(model)}/><MetricCard label="FRAMEWORK" value={valueText(quantum.framework)} detail={valueText(quantum.classical_framework)}/><MetricCard label="EXECUTION" value={valueText(quantum.execution_kind)} detail={quantum.real_hardware?'Hardware reported by evidence':'Simulation / hardware not reported'}/><MetricCard label="EXPLANATION" value={methodLabel(explanationMethod)} detail={record?.result.output_semantics||local?.output_semantics||'Output semantics not recorded'}/></div><Notice tone="amber">Quantum or hybrid feature influence describes frozen model behavior under the selected method. It does not prove quantum causality, biological mechanism, or quantum advantage.</Notice></Card>}

  <Card title="What the explanation shows" description="Machine-derived statements from the visible persisted explanation evidence."><ul className="space-y-3">{narrative.length?narrative.map((item,index)=><li className="flex gap-3 text-sm" key={index}><Brain size={16} className="mt-0.5 shrink-0 text-primary"/><span>{item}</span></li>):<li className="text-sm muted">Insufficient persisted explanation evidence for a factual narrative.</li>}</ul></Card>

  <div className="tremor-grid-main">
   <Card title="Explanation context" description="Compact identifiers and provenance for reproducibility."><div className="grid gap-2 text-xs">{[
    ['Experiment ID',experiment?.id||model?.experiment_id],['Model ID',model?.id],['Dataset ID',dataset?.id||model?.dataset_id],['Dataset hash',dataset?.sha256],['Model artifact ID',modelArtifactId as string|undefined],['Explanation record ID',record?.id],['Run ID',record?.run_id],['Configuration fingerprint',configurationFingerprint],['Method',methodLabel(explanationMethod)],['Created',record?.created_at?dateTime(record.created_at):undefined],['Evidence status',overallState]
   ].map(([key,value])=><div className="flex flex-wrap justify-between gap-3 border-b py-2 last:border-0" key={String(key)}><span className="muted">{String(key)}</span><strong className="mono break-all text-right">{value?String(value):'Not recorded'}</strong></div>)}</div>{record&&<JsonDisclosure label="Explanation request and bounded source context" value={{request:record.result.request,scope:record.result.scope,background_source:record.result.background_source,background_sample_count:record.result.background_sample_count,explained_case_count:record.result.explained_case_count,elapsed_seconds:record.result.elapsed_seconds}}/>}</Card>
   <Card title="Explanation limitations" description="Post-hoc evidence is model-derived and non-clinical."><ul className="space-y-2 text-sm">{limitations.map((item,index)=><li className="flex gap-2" key={index}><ShieldAlert className="mt-0.5 shrink-0 text-amber-600" size={15}/><span>{item}</span></li>)}</ul><div className="mt-4"><Notice tone="amber">Feature contribution reflects model behavior under the selected explanation method; it does not establish medical causation, clinical validation, diagnosis, or biological mechanism.</Notice></div></Card>
  </div>

  <Card title="Continue the research investigation" description="Move from explanation evidence to the existing related research workbenches."><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[
   ['/comparison','Research Results Center',BarChart3],['/comparison','Diagnostic Evidence',Brain],['/prediction','Prediction',ArrowRight],['/robustness','Robustness',ShieldAlert],['/quantum','Quantum Evidence',Atom],['/experiments/'+(experiment?.id||model?.experiment_id||''),'Evidence Package',FileText],['/experiments/'+(experiment?.id||model?.experiment_id||''),'Experiment Lineage',GitBranch],['/datasets','Dataset Evidence',Database]
  ].map(([path,copy,Icon])=><Link className="group flex items-center gap-3 rounded-xl border p-4 hover:bg-primary/5" to={String(path)} key={String(copy)}><Icon size={16} className="text-primary"/><strong className="flex-1 text-xs">{String(copy)}</strong><ArrowRight size={13} className="muted group-hover:text-primary"/></Link>)}</div></Card>
 </div>;
}
