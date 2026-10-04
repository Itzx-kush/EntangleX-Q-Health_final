import type {ReactNode} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Atom,BarChart3,Brain,FileText,GitBranch,LineChart,Microscope,ShieldCheck} from 'lucide-react';
import {Badge,Card} from './ui';
import {JsonDisclosure,MetricCard,Notice,StatusBadge} from './Shared';
import {DiagnosticEvidence} from './DiagnosticEvidence';
import {metric,modelLabels,seconds,shortId} from '../utils/format';
import type {Comparison,Dataset,Experiment,MetricName,ModelRecord} from '../types/qhealth';

const metricOrder:MetricName[]=['roc_auc','f1','accuracy','recall','sensitivity','specificity','precision'];
const comparisonMetrics:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];

type ResultsCenterProps={
  experiment:Experiment;
  dataset?:Dataset;
  models:ModelRecord[];
  comparison?:Pick<Comparison,'split'|'controlled_protocol'|'comparison_fingerprint'|'limitations'>;
  mode:'live'|'verified';
};

type RankedModel={model:ModelRecord;value:number;rank:number;tied:boolean};
type Family='Classical'|'Quantum'|'Hybrid';

function family(model:ModelRecord):Family{
  if(model.model_type==='hybrid_pennylane_torch')return 'Hybrid';
  if(['vqc','qsvc','qnn'].includes(model.model_type))return 'Quantum';
  return 'Classical';
}
function tone(value:Family):'blue'|'purple'|'amber'{return value==='Classical'?'blue':value==='Quantum'?'purple':'amber'}
function finite(value:unknown):value is number{return typeof value==='number'&&Number.isFinite(value)}
function valueText(value:unknown,fallback='Not recorded'){
  if(value===null||value===undefined||value==='')return fallback;
  if(typeof value==='boolean')return value?'Enabled':'Disabled';
  if(typeof value==='number'||typeof value==='string')return String(value);
  return fallback;
}
function primaryMetric(models:ModelRecord[]):MetricName|undefined{
  return metricOrder.find(name=>models.some(model=>finite(model.metrics.test?.[name])));
}
function metricLabel(name:MetricName){return name==='roc_auc'?'ROC-AUC':name.replaceAll('_',' ').toUpperCase()}
function rankModels(models:ModelRecord[],criterion:MetricName|undefined):{ranked:RankedModel[];unranked:ModelRecord[]}{
  if(!criterion)return {ranked:[],unranked:models};
  const withValue=models.filter(model=>finite(model.metrics.test?.[criterion])).map(model=>({model,value:model.metrics.test?.[criterion] as number}));
  withValue.sort((a,b)=>b.value-a.value||modelLabels[a.model.model_type].localeCompare(modelLabels[b.model.model_type])||a.model.id.localeCompare(b.model.id));
  const ranked=withValue.map((entry,index)=>{
    const previous=withValue[index-1];
    const rank=previous&&previous.value===entry.value?(index>0?withValue.slice(0,index).findIndex(item=>item.value===entry.value)+1:index+1):index+1;
    return {...entry,rank,tied:withValue.some((other,otherIndex)=>otherIndex!==index&&other.value===entry.value)};
  });
  return {ranked,unranked:models.filter(model=>!finite(model.metrics.test?.[criterion]))};
}
function bestForFamily(ranked:RankedModel[],value:Family){return ranked.find(item=>family(item.model)===value)}
function detailsRecord(model:ModelRecord){return model.details as Record<string,unknown>}
function execution(model:ModelRecord){
  const quantum=detailsRecord(model).quantum as Record<string,unknown>|undefined;
  return valueText(quantum?.execution_kind,family(model)==='Classical'?'Classical execution':'Not recorded');
}
function field(record:Record<string,unknown>|undefined,...keys:string[]){
  for(const key of keys){const value=record?.[key];if(value!==undefined&&value!==null&&value!=='')return value}
  return undefined;
}
function SummaryItem({label,value,detail}:{label:string;value:ReactNode;detail?:string}){
  return <div className="rounded-lg border p-3"><div className="metric-label">{label}</div><div className="mt-1 text-sm font-semibold">{value}</div>{detail&&<div className="mt-1 text-[10px] muted">{detail}</div>}</div>;
}

export function ResearchResultsCenter({experiment,dataset,models,comparison,mode}:ResultsCenterProps){
  const criterion=primaryMetric(models);
  const {ranked,unranked}=rankModels(models,criterion);
  const leader=ranked[0];
  const leaderSummary=criterion&&leader?.model.metrics.validation?.summary?.[criterion];
  const config=experiment.config;
  const pipeline=config.pipeline||({} as typeof config.pipeline);
  const quantum=config.quantum||({} as typeof config.quantum);
  const split=comparison?.split as Record<string,unknown>|undefined;
  const summary=experiment.summary||{};
  const families:Family[]=['Classical','Quantum','Hybrid'];
  const familyCounts=Object.fromEntries(families.map(value=>[value,models.filter(model=>family(model)===value).length])) as Record<Family,number>;
  const bestClassical=bestForFamily(ranked,'Classical');
  const bestQuantum=bestForFamily(ranked,'Quantum');
  const bestHybrid=bestForFamily(ranked,'Hybrid');
  const quantumComparator=bestQuantum||bestHybrid;
  const observedDifference=quantumComparator&&bestClassical?quantumComparator.value-bestClassical.value:null;
  const samples=field(summary,'sample_count','evaluated_row_count','row_count','samples')??dataset?.provenance.row_count;
  const features=dataset?.provenance.feature_count??field(summary,'feature_count','selected_feature_count','features');
  const pca=pipeline.pca_components;
  const findings:string[]=[];
  if(leader&&criterion)findings.push(`${modelLabels[leader.model.model_type]} achieved the highest observed held-out ${metricLabel(criterion)} among models with that persisted metric${leader.tied?' (tied at the leading value)':''}.`);
  if(leaderSummary&&finite(leaderSummary.mean)&&finite(leaderSummary.std))findings.push(`The leading model's cross-validation ${metricLabel(criterion as MetricName)} was ${metric(leaderSummary.mean)} ± ${metric(leaderSummary.std)} across ${leaderSummary.valid_folds} valid folds.`);
  findings.push(`${models.length} persisted model artifact${models.length===1?' was':'s were'} evaluated: ${familyCounts.Classical} classical, ${familyCounts.Quantum} quantum, and ${familyCounts.Hybrid} hybrid.`);
  if(criterion&&observedDifference!==null&&quantumComparator&&bestClassical)findings.push(`${modelLabels[quantumComparator.model.model_type]} showed an observed ${metricLabel(criterion)} difference of ${observedDifference>=0?'+':''}${observedDifference.toFixed(3)} versus the strongest classical result under this experiment.`);
  const quantumExecutions=[...new Set(models.filter(model=>family(model)!=='Classical').map(execution).filter(value=>value!=='Not recorded'))];
  if(quantumExecutions.length)findings.push(`Persisted quantum execution evidence reports: ${quantumExecutions.join(', ')}.`);

  return <div className="space-y-5">
    <Card title="Experiment summary" description="The tested dataset, persisted setup, and evaluated artifact set at a glance.">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryItem label="EXPERIMENT" value={experiment.name||`Experiment ${shortId(experiment.id)}`} detail={experiment.id}/>
        <SummaryItem label="DATASET" value={dataset?.name||shortId(experiment.dataset_id)} detail={dataset?.sha256?`SHA-256 ${dataset.sha256}`:'Dataset hash not recorded in this view'}/>
        <SummaryItem label="SAMPLES / FEATURES" value={`${valueText(samples)} / ${valueText(features)}`} detail="Persisted dataset evidence"/>
        <SummaryItem label="STATUS" value={<StatusBadge value={experiment.status}/>} detail={mode==='verified'?'Verified precomputed evidence':'Live persisted experiment'}/>
        <SummaryItem label="MODELS" value={models.length} detail={`${familyCounts.Classical} classical · ${familyCounts.Quantum} quantum · ${familyCounts.Hybrid} hybrid`}/>
        <SummaryItem label="CONTROLLED COMPARISON" value={comparison?.controlled_protocol?.status||'Not recorded'} detail={comparison?.controlled_protocol?.protocol_fingerprint||'No persisted controlled protocol in this view'}/>
        <SummaryItem label="PIPELINE / PROTOCOL" value={experiment.pipeline_version_id?shortId(experiment.pipeline_version_id):'Not recorded'} detail={experiment.protocol_version_id?`Protocol ${shortId(experiment.protocol_version_id)}`:'Protocol identity not recorded'}/>
        <SummaryItem label="SEED · SPLIT · CV" value={`${valueText(config.seed)} · ${finite(config.test_size)?Math.round(config.test_size*100)+'%':'Not recorded'} · ${config.cv_folds?config.cv_folds+'-fold':'Not recorded'}`} detail="Training configuration"/>
      </div>
    </Card>

    <Card title="Primary Research Outcome" description="The leading observed result under one explicit held-out ranking criterion.">
      {leader&&criterion?<div className="tremor-grid-main">
        <div className="rounded-xl border bg-primary/5 p-5">
          <div className="metric-label">BEST OBSERVED MODEL{leader.tied?' · TIED':''}</div>
          <div className="mt-2 flex flex-wrap items-center gap-3"><h2 className="text-2xl font-semibold">{modelLabels[leader.model.model_type]}</h2><Badge tone={tone(family(leader.model))}>{family(leader.model)}</Badge></div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label={metricLabel(criterion)} value={metric(leader.value)} detail="Held-out test result"/>
            <MetricCard label="CV" value={leaderSummary&&finite(leaderSummary.mean)?`${metric(leaderSummary.mean)}${finite(leaderSummary.std)?` ± ${metric(leaderSummary.std)}`:''}`:'Not recorded'} detail={leaderSummary?`${leaderSummary.valid_folds} valid folds`:'Validation summary unavailable'}/>
            <MetricCard label="EVALUATION" value="Held-out test set" detail={`Ranked by ${metricLabel(criterion)}`}/>
            <MetricCard label="TEST INFERENCE" value={seconds(leader.model.metrics.timing?.test_inference_seconds)} detail="Persisted runtime"/>
          </div>
        </div>
        <div className="rounded-xl border p-5"><div className="metric-label">INTERPRETATION BOUNDARY</div><p className="mt-3 text-sm muted">“Best” means the highest persisted held-out {metricLabel(criterion)} among models where that metric is available. It does not establish clinical validity, causality, statistical significance, robustness, or quantum advantage.</p>{leader.tied&&<div className="mt-3"><Notice tone="amber">The leading value is tied. No unique winner is claimed.</Notice></div>}</div>
      </div>:<Notice tone="amber">No supported held-out primary metric is persisted for these model records, so no best model or ranking is claimed.</Notice>}
    </Card>

    <Card title="Validation, holdout, and runtime" description="Model comparison matrix with held-out performance, cross-validation stability, and runtime evidence kept visibly distinct.">
      <div className="table-wrap overflow-x-auto"><table className="data-table min-w-[1450px]"><thead><tr><th>Family</th><th>Model</th><th>Status</th>{comparisonMetrics.map(name=><th key={name}>{metricLabel(name)} · test</th>)}<th>{criterion?`${metricLabel(criterion)} · CV mean`:'Primary CV mean'}</th><th>CV SD</th><th>Valid folds</th><th>Final training</th><th>CV runtime</th><th>Test inference</th></tr></thead><tbody>{models.map(model=>{const validation=criterion?model.metrics.validation?.summary?.[criterion]:undefined;return <tr key={model.id}><td><Badge tone={tone(family(model))}>{family(model)}</Badge></td><td><strong>{modelLabels[model.model_type]}</strong></td><td><StatusBadge value={model.status}/></td>{comparisonMetrics.map(name=><td className="numeric" key={name}>{metric(model.metrics.test?.[name])}</td>)}<td className="numeric">{metric(validation?.mean)}</td><td className="numeric">{metric(validation?.std)}</td><td className="numeric">{validation?.valid_folds??'Not recorded'}</td><td className="numeric">{seconds(model.metrics.timing?.final_training_seconds)}</td><td className="numeric">{seconds(model.metrics.timing?.cv_total_seconds)}</td><td className="numeric">{seconds(model.metrics.timing?.test_inference_seconds)}</td></tr>})}</tbody></table></div>
    </Card>

    <div className="tremor-grid-main">
      <Card title="Model ranking" description={criterion?`RANKING CRITERION: Held-out ${metricLabel(criterion)}`:'No common ranking criterion available'}>
        {ranked.length?<ol className="space-y-2">{ranked.map(item=><li className="flex items-center gap-3 rounded-lg border p-3" key={item.model.id}><span className="grid h-8 w-8 place-items-center rounded-full bg-primary/10 text-sm font-bold">{item.rank}</span><div className="min-w-0 flex-1"><strong>{modelLabels[item.model.model_type]}</strong><div className="text-[10px] muted">{family(item.model)} · {item.tied?'tied value':'persisted held-out evidence'}</div></div><span className="mono text-sm font-semibold">{metric(item.value)}</span></li>)}</ol>:<p className="text-sm muted">Ranking is unavailable because no supported held-out metric was recorded.</p>}
        {unranked.length>0&&<div className="mt-4 text-xs muted"><strong>Not ranked:</strong> {unranked.map(item=>modelLabels[item.model_type]).join(', ')} — {criterion?`${metricLabel(criterion)} not recorded`:'no supported metric recorded'}.</div>}
      </Card>
      <Card title="Research findings" description="Deterministic statements derived only from the evidence visible on this page."><ul className="space-y-3">{findings.map((finding,index)=><li className="flex gap-3 text-sm" key={index}><ShieldCheck className="mt-0.5 shrink-0 text-emerald-600" size={16}/><span>{finding}</span></li>)}</ul></Card>
    </div>

    <DiagnosticEvidence experiment={experiment} models={models} mode={mode} limitations={comparison?.limitations||[]}/>

    <Card title="Classical vs quantum vs hybrid" description={criterion?`Best observed held-out ${metricLabel(criterion)} within each model family.`:'Family counts are available; a common result metric is not.'}>
      <div className="grid gap-3 md:grid-cols-3">{families.map(value=>{const best=bestForFamily(ranked,value);return <div className="rounded-xl border p-4" key={value}><div className="flex items-center justify-between"><Badge tone={tone(value)}>{value.toUpperCase()}</Badge><span className="text-xs muted">{familyCounts[value]} model{familyCounts[value]===1?'':'s'}</span></div><h3 className="mt-3 font-semibold">{best?modelLabels[best.model.model_type]:'No comparable result'}</h3><div className="mt-1 text-xl font-semibold">{best?metric(best.value):'Not available'}</div><div className="mt-1 text-[10px] muted">{criterion?`Held-out ${metricLabel(criterion)}`:'Primary metric unavailable'}</div></div>})}</div>
      {criterion&&observedDifference!==null&&quantumComparator&&bestClassical&&<div className="mt-4"><Notice tone="blue"><strong>Observed {metricLabel(criterion)} difference:</strong> {modelLabels[quantumComparator.model.model_type]} vs best classical = {observedDifference>=0?'+':''}{observedDifference.toFixed(3)}. This is a descriptive result under this experiment, not an advantage claim.</Notice></div>}
    </Card>

    {leader&&criterion&&<Card title="Variability / stability summary" description="Persisted cross-validation evidence for the leading held-out result."><div className="grid gap-3 sm:grid-cols-3"><MetricCard label="CV MEAN" value={metric(leaderSummary?.mean)} detail={metricLabel(criterion)}/><MetricCard label="CV SD" value={metric(leaderSummary?.std)} detail="Persisted fold variability"/><MetricCard label="VALID FOLDS" value={leaderSummary?.valid_folds??'Not recorded'} detail={config.cv_folds?`${config.cv_folds}-fold configured`:`Fold count not recorded`}/></div>{leader.model.metrics.validation?.folds?.length?<JsonDisclosure label="Inspect persisted fold-level values" value={leader.model.metrics.validation.folds.map((fold,index)=>({fold:index+1,[criterion]:fold[criterion]}))}/>:<p className="mt-3 text-xs muted">Fold-level values were not recorded in this result.</p>}</Card>}

    <Card title="Experiment conditions" description="A readable snapshot of persisted configuration; no condition is described as matched unless the backend records it.">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryItem label="DATASET" value={dataset?.name||shortId(experiment.dataset_id)} detail={dataset?.sha256||'Hash not recorded'}/>
        <SummaryItem label="REPRESENTATION" value={config.features?.length?`${config.features.length} selected features`:'Feature count not recorded'} detail={`Selection: ${valueText(pipeline.selection)}`}/>
        <SummaryItem label="PREPROCESSING" value={`${valueText(pipeline.imputer)} imputation · ${valueText(pipeline.scaler)} scaling`} detail={`Outliers: ${valueText(pipeline.outlier_strategy)}`}/>
        <SummaryItem label="PCA / DIMENSIONALITY" value={pca===null?'Disabled':pca===undefined?'Not recorded':`${pca} components`} detail={pipeline.pca_whiten===undefined?'Whitening not recorded':pipeline.pca_whiten?'Whitening enabled':'Whitening disabled'}/>
        <SummaryItem label="SPLIT" value={valueText(field(split,'test_size','holdout_fraction'),finite(config.test_size)?`${Math.round(config.test_size*100)}% held out`:'Not recorded')} detail={valueText(field(split,'strategy','method'),'Configuration value')}/>
        <SummaryItem label="CV / SEED" value={`${config.cv_folds?config.cv_folds+'-fold':'Not recorded'} · ${valueText(config.seed)}`} detail="Persisted training configuration"/>
        <SummaryItem label="THRESHOLD" value={config.threshold_strategy?config.threshold_strategy.replaceAll('_',' '):'Not recorded'} detail={config.threshold_strategy==='fixed'?`Threshold ${valueText(config.probability_threshold)}`:config.threshold_strategy==='target_sensitivity'?`Target sensitivity ${valueText(config.target_sensitivity)}`:'Threshold strategy unavailable'}/>
        <SummaryItem label="CALIBRATION" value={valueText(config.calibration)} detail={config.calibration==='none'?'Not configured':config.calibration_folds?`${config.calibration_folds} folds`:'Calibration folds not recorded'}/>
        <SummaryItem label="QUANTUM EXECUTION" value={quantum.execution_mode||quantum.backend||'Not recorded'} detail={quantum.provider_id||'Provider not recorded'}/>
      </div>
      <JsonDisclosure label="Complete persisted conditions and provenance" value={{experiment_id:experiment.id,dataset_hash:dataset?.sha256,config,split,comparison_fingerprint:comparison?.comparison_fingerprint,limitations:comparison?.limitations}}/>
    </Card>

    <Card title="Investigate deeper evidence" description="Start with this result, then continue into the existing evidence workbenches.">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ['/comparison','Diagnostics / comparison',BarChart3],['/explainability','Explainability',Brain],['/prediction','Prediction',LineChart],['/robustness','Robustness',ShieldCheck],['/quantum','Quantum evidence',Atom],['/experiments/'+experiment.id,'Experiment lineage',GitBranch],['/experiments/'+experiment.id,'Evidence package',Microscope],['/experiments/'+experiment.id,'Research report',FileText]
        ].map(([path,label,Icon])=><Link className="group flex items-center gap-3 rounded-xl border p-4 transition-colors hover:bg-primary/5" to={String(path)} key={String(label)}><Icon size={17} className="text-primary"/><span className="flex-1 text-sm font-semibold">{String(label)}</span><ArrowRight size={14} className="muted group-hover:text-primary"/></Link>)}
      </div>
    </Card>

    <Notice tone="amber">Research-only output. These observed model results are not diagnoses, clinical predictions, treatment recommendations, or evidence of quantum advantage.</Notice>
  </div>;
}
