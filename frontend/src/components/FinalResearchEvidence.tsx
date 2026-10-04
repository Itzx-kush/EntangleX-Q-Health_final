import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {Download,FileCheck2,FileText,GitBranch,ShieldCheck} from 'lucide-react';
import {qh} from '../lib/api';
import {dateTime,metric,modelLabels,shortId} from '../utils/format';
import type {EvidenceInventoryEntry,ExperimentDetail,MetricName,ModelRecord,ResearchEvidencePackage} from '../types/qhealth';
import {Badge,Button,Card} from './ui';
import {JsonDisclosure,MetricCard,Notice,StatusBadge} from './Shared';

type Props={
  detail:ExperimentDetail;
  reportBusy:boolean;
  onReport:(format:'html'|'json')=>void;
  packagePanel:React.ReactNode;
};

type Family='Classical'|'Quantum'|'Hybrid';
const metricOrder:MetricName[]=['roc_auc','f1','accuracy','recall','sensitivity','specificity','precision'];
const coreCategories=['evaluation','calibration','threshold','robustness','quantum_diagnostics','controlled_comparison','model_cards','explainability'];

function finite(value:unknown):value is number{return typeof value==='number'&&Number.isFinite(value)}
function family(model:ModelRecord):Family{
  if(model.model_type==='hybrid_pennylane_torch')return 'Hybrid';
  return ['vqc','qsvc','qnn'].includes(model.model_type)?'Quantum':'Classical';
}
function metricLabel(value:MetricName){return value==='roc_auc'?'ROC-AUC':value.replaceAll('_',' ').toUpperCase()}
function display(value:unknown,fallback='Not recorded'){
  if(value===null||value===undefined||value==='')return fallback;
  return typeof value==='string'||typeof value==='number'?String(value):fallback;
}
function evidenceLabel(value:string){return value.replaceAll('_',' ').toUpperCase()}
function statusTone(value:string):'green'|'amber'|'red'|'blue'{
  const normalized=value.toLowerCase();
  if(normalized==='available'||normalized==='ready'||normalized==='complete')return 'green';
  if(normalized==='blocked'||normalized==='unavailable')return 'red';
  if(normalized.includes('not_')||normalized==='limited'||normalized==='incomplete'||normalized==='partial')return 'amber';
  return 'blue';
}
function fingerprint(value:string|null|undefined){return value?<span className="mono break-all text-[10px]" title={value}>{value}</span>:<span className="muted">Not recorded</span>}
function InventoryCard({name,entry}:{name:string;entry:EvidenceInventoryEntry}){
  return <div className="rounded-xl border p-3"><div className="flex items-center justify-between gap-2"><strong className="text-xs">{name.replaceAll('_',' ')}</strong><Badge tone={statusTone(entry.status)}>{evidenceLabel(entry.status)}</Badge></div><p className="mt-2 text-[11px] muted">{entry.record_count} persisted record{entry.record_count===1?'':'s'} · {entry.availability_reason||'No availability reason recorded'}</p></div>;
}

export function FinalResearchEvidence({detail,reportBusy,onReport,packagePanel}:Props){
  const {experiment,models}=detail;
  const id=experiment.id;
  const dataset=useQuery({queryKey:['dataset',experiment.dataset_id],queryFn:()=>qh.dataset(experiment.dataset_id),retry:false});
  const preflight=useQuery({queryKey:['evidence-package-preflight',id],queryFn:()=>qh.evidencePackagePreflight(id),retry:false});
  const evidencePackage=useQuery({queryKey:['evidence-package',id],queryFn:()=>qh.evidencePackage(id),retry:false});
  const lineage=useQuery({queryKey:['experiment-lineage',id,'3','both',true,true],queryFn:()=>qh.lineage(id,{depth:'3',direction:'both',include_artifacts:true,include_evidence:true}),retry:false});
  const audit=useQuery({queryKey:['experiment-audit',id,'all'],queryFn:()=>qh.experimentAudit(id,'all'),retry:false});
  const auditIntegrity=useQuery({queryKey:['audit-integrity',id],queryFn:()=>qh.auditIntegrity('experiment',id),retry:false});

  const manifest:ResearchEvidencePackage|undefined=evidencePackage.data||preflight.data?.manifest;
  const inventory=manifest?.evidence_inventory||preflight.data?.evidence_inventory||{};
  const inventoryEntries=Object.entries(inventory);
  const evidenceCounts=inventoryEntries.reduce((counts,[,entry])=>{
    if(entry.status==='available')counts.available+=1;
    else if(entry.status==='limited')counts.limited+=1;
    else counts.gaps+=1;
    return counts;
  },{available:0,limited:0,gaps:0});
  const criterion=metricOrder.find(name=>models.some(model=>finite(model.metrics.test?.[name])));
  const ranked=criterion?models.filter(model=>finite(model.metrics.test?.[criterion])).sort((a,b)=>(b.metrics.test?.[criterion] as number)-(a.metrics.test?.[criterion] as number)||modelLabels[a.model_type].localeCompare(modelLabels[b.model_type])):[];
  const leader=ranked[0];
  const leaderValue=criterion&&leader?leader.metrics.test?.[criterion]:undefined;
  const cv=criterion&&leader?leader.metrics.validation?.summary?.[criterion]:undefined;
  const familyCounts=models.reduce<Record<Family,number>>((counts,model)=>({...counts,[family(model)]:counts[family(model)]+1}),{Classical:0,Quantum:0,Hybrid:0});
  const packageStatus=evidencePackage.data?.package_status||preflight.data?.package_status||'INCOMPLETE';
  const packageSource=evidencePackage.data?'Persisted immutable package':'Current read-only preflight';
  const gaps=evidencePackage.data?.evidence_gaps||preflight.data?.missing_evidence||[];
  const limitations=[...new Set([...(manifest?.limitations||[]),...(lineage.data?.limitations||[])])];
  const lineageIssues=lineage.data?lineage.data.integrity.missing_references.length+lineage.data.integrity.orphaned_edges.length+lineage.data.integrity.invalid_edges.length+lineage.data.integrity.fingerprint_mismatches.length+lineage.data.integrity.cycles.length:0;
  const integrityValid=auditIntegrity.data?.valid??audit.data?.integrity_status==='VERIFIED';
  const reportSections=[
    ['Experiment and dataset identity',Boolean(experiment.id&&experiment.dataset_id)],
    ['Model results and final finding',Boolean(criterion&&leader)],
    ['Quantum computation evidence',familyCounts.Quantum+familyCounts.Hybrid>0],
    ['Evidence inventory and limitations',inventoryEntries.length>0],
    ['Traceability and lineage',Boolean(lineage.data)],
    ['Scientific audit',Boolean(audit.data)],
    ['Reproducibility configuration',Boolean(experiment.config)],
  ] as const;

  return <section className="mt-5 space-y-5" aria-label="Final research evidence">
    <Card title="Final Research Evidence" description="A traceable aggregation of persisted experiment outputs. It does not recalculate metrics, rerun studies, or alter the research record.">
      <div className="flex flex-wrap items-center gap-2"><StatusBadge value={experiment.status}/><Badge tone={experiment.summary.experiment_kind==='precomputed_verified_demo'?'blue':'green'}>{experiment.summary.experiment_kind==='precomputed_verified_demo'?'VERIFIED / PRECOMPUTED':'LIVE PERSISTED EVIDENCE'}</Badge><Badge tone={statusTone(packageStatus)}>PACKAGE {packageStatus}</Badge></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="DATASET" value={dataset.data?.name||shortId(experiment.dataset_id)} detail={dataset.data?.sha256?`SHA-256 ${dataset.data.sha256.slice(0,16)}…`:'Hash not available in this view'}/>
        <MetricCard label="SAMPLES / FEATURES" value={`${dataset.data?.provenance.row_count??'Not recorded'} / ${dataset.data?.provenance.feature_count??'Not recorded'}`} detail="Persisted dataset metadata"/>
        <MetricCard label="MODELS" value={models.length} detail={`${familyCounts.Classical} classical · ${familyCounts.Quantum} quantum · ${familyCounts.Hybrid} hybrid`}/>
        <MetricCard label="SEED · SPLIT · CV" value={`${display(experiment.config.seed)} · ${finite(experiment.config.test_size)?Math.round(experiment.config.test_size*100)+'%':'Not recorded'} · ${experiment.config.cv_folds?experiment.config.cv_folds+'-fold':'Not recorded'}`} detail="Persisted experiment configuration"/>
      </div>
      <div className="mt-4 grid gap-3 text-xs md:grid-cols-3"><div><span className="metric-label">EXPERIMENT</span><strong className="mono block break-all">{id}</strong></div><div><span className="metric-label">PIPELINE VERSION</span><strong className="mono block break-all">{experiment.pipeline_version_id||'Not recorded'}</strong></div><div><span className="metric-label">PROTOCOL VERSION</span><strong className="mono block break-all">{experiment.protocol_version_id||'Not recorded'}</strong></div></div>
    </Card>

    <div className="grid gap-5 lg:grid-cols-[1.25fr_.75fr]">
      <Card title="Final observed finding" description={criterion?`Highest persisted held-out ${metricLabel(criterion)} among models with that metric.`:'No supported held-out ranking metric is recorded.'}>
        {leader&&criterion&&finite(leaderValue)?<><div className="flex flex-wrap items-center gap-3"><h2 className="text-2xl font-semibold">{modelLabels[leader.model_type]}</h2><Badge tone="purple">{family(leader)}</Badge></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><MetricCard label={`HELD-OUT ${metricLabel(criterion)}`} value={metric(leaderValue)} detail="Ranking criterion"/><MetricCard label="CV MEAN ± SD" value={cv&&finite(cv.mean)?`${metric(cv.mean)}${finite(cv.std)?` ± ${metric(cv.std)}`:''}`:'Not recorded'} detail={cv?`${cv.valid_folds} valid folds`:'Validation summary unavailable'}/><MetricCard label="EVALUATED MODELS" value={models.length} detail="Persisted model records"/></div><Notice tone="blue">This is the leading observed result under the stated held-out metric. It does not establish clinical validity, causality, statistical significance, robustness, or quantum advantage.</Notice></>:<Notice tone="amber">No supported held-out metric is available, so this page does not claim a best model.</Notice>}
      </Card>
      <Card title="Evidence readiness" description={packageSource}>
        <div className="grid grid-cols-3 gap-2 text-center"><div className="rounded-lg border p-3"><strong className="block text-xl">{evidenceCounts.available}</strong><small className="muted">Available</small></div><div className="rounded-lg border p-3"><strong className="block text-xl">{evidenceCounts.limited}</strong><small className="muted">Limited</small></div><div className="rounded-lg border p-3"><strong className="block text-xl">{evidenceCounts.gaps}</strong><small className="muted">Gaps</small></div></div>
        {preflight.data&&!preflight.data.feasible&&<Notice tone="amber">Package creation is blocked until the recorded preflight blockers are resolved. Existing evidence remains inspectable.</Notice>}
        <div className="mt-3 text-xs"><span className="metric-label">CANDIDATE / PACKAGE FINGERPRINT</span>{fingerprint(evidencePackage.data?.package_fingerprint||preflight.data?.package_fingerprint_candidate)}</div>
      </Card>
    </div>

    <Card title="Authoritative evidence inventory" description="Availability comes from the backend evidence-package manifest or its read-only preflight; missing evidence is never represented as zero.">
      {inventoryEntries.length?<div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{inventoryEntries.map(([name,entry])=><InventoryCard key={name} name={name} entry={entry}/>)}</div>:<Notice tone="amber">The authoritative evidence inventory is not available for this record.</Notice>}
      {coreCategories.some(name=>inventory[name])&&<div className="mt-4 table-wrap"><table className="data-table"><thead><tr><th>Core evidence</th><th>Status</th><th>Records</th><th>Latest compatible evidence</th></tr></thead><tbody>{coreCategories.filter(name=>inventory[name]).map(name=><tr key={name}><td>{name.replaceAll('_',' ')}</td><td><Badge tone={statusTone(inventory[name].status)}>{evidenceLabel(inventory[name].status)}</Badge></td><td>{inventory[name].record_count}</td><td className="mono text-[10px]">{inventory[name].latest_compatible_evidence||'Not recorded'}</td></tr>)}</tbody></table></div>}
    </Card>

    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Traceability & lineage" description="Persisted relationships among dataset, configuration, execution, models, evidence, and artifacts.">
        {lineage.data?<><div className="flex flex-wrap gap-2"><StatusBadge value={lineage.data.status}/><Badge tone="blue">{lineage.data.summary.node_count} NODES</Badge><Badge tone="blue">{lineage.data.summary.edge_count} EDGES</Badge>{lineageIssues>0&&<Badge tone="amber">{lineageIssues} ISSUES</Badge>}</div><div className="mt-3"><span className="metric-label">LINEAGE FINGERPRINT</span>{fingerprint(lineage.data.lineage_fingerprint)}</div><p className="mt-3 text-xs muted">Captured layers: {[...new Set(lineage.data.nodes.map(node=>node.object_type.replaceAll('_',' ')))].slice(0,8).join(' · ')||'No related layers recorded'}.</p></>:<p className="text-sm muted">Lineage evidence is not available for this record.</p>}
      </Card>
      <Card title="Scientific audit" description="Chronological platform events and integrity status for this experiment.">
        {audit.data?<><div className="flex flex-wrap gap-2"><Badge tone={integrityValid?'green':'amber'}>{integrityValid?'INTEGRITY VERIFIED':'INTEGRITY WARNING'}</Badge><Badge tone="blue">{audit.data.total_events} EVENTS</Badge></div><p className="mt-3 text-xs muted">Categories: {audit.data.categories_present.join(', ')||'Not recorded'}</p>{audit.data.events.length>0&&<p className="mt-3 text-xs">Latest recorded event: <strong>{audit.data.events[0].event_type.replaceAll('_',' ')}</strong> · {dateTime(audit.data.events[0].occurred_at)}</p>}{auditIntegrity.data?.issues.length?<Notice tone="amber">{auditIntegrity.data.issues.length} audit integrity issue{auditIntegrity.data.issues.length===1?'':'s'} require review.</Notice>:null}</>:<p className="text-sm muted">Audit evidence is not available for this record.</p>}
      </Card>
    </div>

    <Card title="Fingerprints & integrity" description="Compact identifiers for verifying the dataset, configuration, package, protocol, pipeline, and evidence relationships.">
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {[['Dataset SHA-256',dataset.data?.sha256||manifest?.integrity.dataset_hash],['Configuration',manifest?.configuration_fingerprint||manifest?.experiment.configuration_fingerprint],['Package',evidencePackage.data?.package_fingerprint||preflight.data?.package_fingerprint_candidate],['Pipeline',manifest?.pipeline?.pipeline_fingerprint],['Protocol',manifest?.protocol?.protocol_fingerprint||experiment.protocol_fingerprint],['Lineage',lineage.data?.lineage_fingerprint]].map(([label,value])=><div className="rounded-xl border p-3" key={label}><span className="metric-label">{label}</span>{fingerprint(value)}</div>)}
      </div>
    </Card>

    <div className="grid gap-5 lg:grid-cols-2">
      <Card title="Evidence gaps & limitations" description="Explicit absence and scope boundaries are part of the final research record.">
        {gaps.length?<ul className="space-y-2 text-sm">{gaps.map((gap,index)=><li className="rounded-lg border p-3" key={`${gap.category}-${index}`}><div className="flex items-center justify-between gap-2"><strong>{gap.category.replaceAll('_',' ')}</strong><Badge tone={statusTone(gap.status)}>{evidenceLabel(gap.status)}</Badge></div><p className="mt-1 text-xs muted">{gap.reason}</p></li>)}</ul>:<p className="text-sm muted">No evidence gaps are recorded in the current manifest.</p>}
        {limitations.length>0&&<JsonDisclosure label="Inspect recorded limitations" value={limitations}/>} 
      </Card>
      <Card title="Research report preview" description="The report is assembled by the existing backend from persisted evidence; downloads do not trigger training or scientific recomputation.">
        <div className="space-y-2">{reportSections.map(([label,available])=><div className="flex items-center justify-between rounded-lg border p-3 text-sm" key={label}><span>{label}</span><Badge tone={available?'green':'amber'}>{available?'INCLUDED':'LIMITED'}</Badge></div>)}</div>
        <div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" disabled={reportBusy} onClick={()=>onReport('html')}><FileText size={13}/>Download HTML report</Button><Button variant="outline" disabled={reportBusy} onClick={()=>onReport('json')}><Download size={13}/>Download JSON report</Button></div>
      </Card>
    </div>

    <Card title="Final conclusion & reproducibility" description="A concise close-out statement anchored to this experiment's persisted record.">
      <div className="grid gap-5 lg:grid-cols-2"><div><div className="metric-label">CONCLUSION</div><p className="mt-2 text-sm">{leader&&criterion&&finite(leaderValue)?`${modelLabels[leader.model_type]} had the highest observed held-out ${metricLabel(criterion)} (${metric(leaderValue)}) among models with that persisted metric. ${gaps.length?`${gaps.length} evidence gap${gaps.length===1?' remains':'s remain'} recorded.`:'No evidence gaps are recorded in the current manifest.'}`:'The available record does not support a held-out model ranking.'}</p></div><div><div className="metric-label">REPRODUCIBILITY SNAPSHOT</div><p className="mt-2 text-sm">Dataset {shortId(experiment.dataset_id)} · seed {display(experiment.config.seed)} · {experiment.config.cv_folds?`${experiment.config.cv_folds}-fold CV`:'CV folds not recorded'} · pipeline {experiment.pipeline_version_id?shortId(experiment.pipeline_version_id):'not recorded'} · protocol {experiment.protocol_version_id?shortId(experiment.protocol_version_id):'not recorded'}.</p></div></div>
      <Notice tone="amber">Research use only. This evidence package and report do not establish diagnosis, treatment benefit, clinical validation, causality, statistical significance, generalization, or quantum advantage.</Notice>
    </Card>

    {packagePanel}

    <Card title="Final research actions" description="Download the authoritative outputs or continue into the existing evidence workbenches.">
      <div className="flex flex-wrap gap-2"><Button disabled={reportBusy} onClick={()=>onReport('html')}><FileCheck2 size={14}/>Final HTML report</Button><Button variant="outline" disabled={reportBusy} onClick={()=>onReport('json')}><Download size={14}/>Report JSON</Button><Link className="btn btn-outline" to="/comparison">Diagnostics</Link><Link className="btn btn-outline" to="/explainability">Explainability</Link><Link className="btn btn-outline" to="/prediction">Prediction</Link><Link className="btn btn-outline" to="/robustness">Robustness</Link><Link className="btn btn-outline" to="/quantum">Quantum evidence</Link><Link className="btn btn-outline" to={`/experiments/${id}`}><GitBranch size={13}/>Lineage & audit</Link></div>
      <div className="mt-4 flex items-center gap-2 text-xs muted"><ShieldCheck size={14}/>All summaries above are deterministic presentations of persisted evidence and existing backend projections.</div>
    </Card>
  </section>;
}
