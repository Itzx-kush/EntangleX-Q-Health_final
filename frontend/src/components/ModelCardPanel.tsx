import {useQuery} from '@tanstack/react-query';
import {qh} from '../lib/api';
import type {ModelCardEvidenceStatus,ModelRecord} from '../types/qhealth';
import {Badge,Card} from './ui';
import {ErrorBanner,JsonDisclosure,Loading,Notice,StatusBadge} from './Shared';

const sections=[
  ['Evaluation','evaluation'],['Multi-seed','multi_seed_evidence'],['Calibration','calibration'],
  ['Threshold','threshold'],['Robustness','robustness'],['External validation','external_validation'],
  ['Distribution shift','distribution_shift'],['Group validation','group_validation'],['Quantum / provider','quantum'],
] as const;

function EvidenceState({value}:{value:ModelCardEvidenceStatus}){
  const tone=value==='available'?'blue':value==='not_applicable'?'green':'amber';
  return <Badge tone={tone}>{value.replaceAll('_',' ').toUpperCase()}</Badge>;
}

export function ModelCardPanel({model}:{model:ModelRecord}){
  const result=useQuery({queryKey:['model-card',model.id],queryFn:()=>qh.modelCard(model.id),enabled:model.status==='ready',staleTime:30000});
  if(model.status!=='ready')return <Notice tone="amber">Model Card unavailable until this model has a persisted terminal research record.</Notice>;
  if(result.isLoading)return <Card className="mt-4" title="Model Card" description="Loading canonical evidence…"><Loading/></Card>;
  if(result.error||!result.data)return <Card className="mt-4" title="Model Card" description="The canonical card could not be loaded."><ErrorBanner error={(result.error as Error)?.message}/></Card>;
  const card=result.data;
  return <Card className="mt-4" title="Model Card" description={`${card.schema_version} · deterministic research evidence`}>
    <div className="flex flex-wrap items-center gap-2"><StatusBadge value={card.card_status}/><Badge tone="blue">RESEARCH EVALUATION ONLY</Badge><span className="mono text-[10px] muted">{card.card_id}</span></div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{sections.map(([label,key])=><div className="rounded-xl border p-3" key={key}><div className="metric-label">{label}</div><div className="mt-2"><EvidenceState value={card[key].status as ModelCardEvidenceStatus}/></div></div>)}</div>
    <div className="mt-4 grid gap-4 lg:grid-cols-2">
      <div><div className="metric-label">MODEL / TASK / DATA</div><JsonDisclosure label="Inspect documented identity and scope" value={{model_identity:card.model_identity,task:card.task,data:card.data}}/></div>
      <div><div className="metric-label">TRAINING / MODEL DETAILS</div><JsonDisclosure label="Inspect persisted configuration" value={{training:card.training,model:card.model}}/></div>
      <div><div className="metric-label">REPRODUCIBILITY</div><JsonDisclosure label="Inspect provenance evidence" value={{provenance:card.provenance,reproducibility:card.reproducibility,artifact:card.artifact}}/></div>
      <div><div className="metric-label">LIMITATIONS / EVIDENCE GAPS</div><JsonDisclosure label={`${card.limitations.length} limitations · ${card.evidence_gaps.length} gaps`} value={{limitations:card.limitations,evidence_gaps:card.evidence_gaps}}/></div>
    </div>
    <JsonDisclosure label="Open complete canonical Model Card" value={card}/>
    <Notice tone="amber">This card documents persisted evidence. It does not establish clinical validity, deployment readiness, population generalization, or quantum advantage.</Notice>
  </Card>;
}