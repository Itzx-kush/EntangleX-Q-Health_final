import {Database,FlaskConical,ShieldCheck} from 'lucide-react';
import {Badge,Card} from './ui';
import {JsonDisclosure,MetricCard,Notice} from './Shared';
import {metric,modelLabels} from '../utils/format';
import type {AlignmentContract,Dataset,Experiment,ModelKind,ModelRecord,VerifiedEvidencePackage} from '../types/qhealth';

type Props={
  dataset:Dataset;
  experiment:Experiment;
  models:ModelRecord[];
  evidence:VerifiedEvidencePackage['evidence'];
  comparisonContract:Record<string,unknown>;
  alignment?:AlignmentContract;
};

type Family='Classical'|'Quantum'|'Hybrid';

const orderedKinds:ModelKind[]=[
  'logistic_regression',
  'svm',
  'random_forest',
  'vqc',
  'qsvc',
  'qnn',
  'hybrid_pennylane_torch',
];

function family(kind:ModelKind):Family{
  if(kind==='hybrid_pennylane_torch')return 'Hybrid';
  if(kind==='vqc'||kind==='qsvc'||kind==='qnn')return 'Quantum';
  return 'Classical';
}

function tone(value:Family):'blue'|'purple'|'amber'{
  return value==='Classical'?'blue':value==='Quantum'?'purple':'amber';
}

function finite(value:unknown):value is number{
  return typeof value==='number'&&Number.isFinite(value);
}

function textValue(value:unknown,fallback='Not recorded'){
  if(value===null||value===undefined||value==='')return fallback;
  return typeof value==='string'||typeof value==='number'||typeof value==='boolean'?String(value):fallback;
}

function capabilityFor(alignment:AlignmentContract|undefined,kind:ModelKind){
  return alignment?.models.find(item=>item.model_id===kind);
}

function frameworkFor(model:ModelRecord,alignment:AlignmentContract|undefined){
  const capability=capabilityFor(alignment,model.model_type);
  const quantum=model.details.quantum;
  if(family(model.model_type)==='Classical'){
    return capability?.classical_framework||quantum?.classical_framework||'Not recorded';
  }
  return capability?.quantum_framework||quantum?.framework||'Not recorded';
}

function executionFor(model:ModelRecord,alignment:AlignmentContract|undefined){
  const capability=capabilityFor(alignment,model.model_type);
  const quantum=model.details.quantum;
  return capability?.execution||quantum?.execution_kind||'Not recorded';
}

function evidenceStatus(present:boolean){
  return present?'Available':'Not recorded';
}

function readRecord(record:Record<string,unknown>|undefined,key:string){
  return record?.[key];
}

export function ControlledSevenModelComparison({
  dataset,
  experiment,
  models,
  evidence,
  comparisonContract,
  alignment,
}:Props){
  const benchmarkIds=new Set(evidence.benchmark.model_ids||[]);
  const explainabilityIds=new Set(evidence.explainability.model_ids||[]);
  const robustnessIds=new Set((evidence.robustness.results||[]).map(item=>item.model_id));
  const orderedModels=orderedKinds
    .map(kind=>models.find(model=>model.model_type===kind))
    .filter((model):model is ModelRecord=>Boolean(model));

  const representation=(comparisonContract.representation||{}) as Record<string,unknown>;
  const selection=(readRecord(representation,'feature_selection')||{}) as Record<string,unknown>;
  const testSize=finite(comparisonContract.test_size)?comparisonContract.test_size:experiment.config.test_size;
  const targetSensitivity=finite(comparisonContract.target_sensitivity)
    ? comparisonContract.target_sensitivity
    : experiment.config.target_sensitivity;
  const thresholdStrategy=textValue(
    comparisonContract.threshold_strategy||experiment.config.threshold_strategy,
  );
  const controlledClaim=evidence.benchmark.claims?.quantum_advantage===false&&evidence.benchmark.claims?.real_quantum_hardware===false;

  const families=[
    {name:'Classical baselines' as const,kinds:orderedKinds.slice(0,3)},
    {name:'Quantum models' as const,kinds:orderedKinds.slice(3,6)},
    {name:'Hybrid model' as const,kinds:orderedKinds.slice(6)},
  ];

  return <div className="space-y-5">
    <Card
      className="border-primary/20 bg-primary/[0.025]"
      title="SIH26139 — EARLY STAGE DIABETES CONTROLLED MODEL COMPARISON"
      description="Seven classical, quantum, and hybrid model implementations are evaluated under the verified research benchmark."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="MODEL SET"
          value={orderedModels.length}
          detail="Verified benchmark model artifacts"
          icon={<FlaskConical size={15}/>}
        />
        <MetricCard
          label="DATASET"
          value={dataset.name}
          detail={dataset.sha256 ? `SHA-256 ${dataset.sha256}` : 'Dataset hash not recorded'}
          icon={<Database size={15}/>}
        />
        <MetricCard
          label="EVALUATED ROWS"
          value={textValue(comparisonContract.evaluated_row_count)}
          detail={`Source rows: ${textValue(comparisonContract.source_row_count,dataset.provenance.row_count.toString())}`}
        />
        <MetricCard
          label="OPERATING STRATEGY"
          value={thresholdStrategy==='target_sensitivity'?'Sensitivity-first':thresholdStrategy}
          detail={finite(targetSensitivity)?`Target sensitivity ${metric(targetSensitivity)}`:'Target sensitivity not recorded'}
          icon={<ShieldCheck size={15}/>}
        />
      </div>
      <Notice tone="blue">
        This is a controlled empirical research comparison. Performance differences are reported from packaged evidence; the platform does not assume quantum or hybrid superiority.
      </Notice>
    </Card>

    <Card
      title="Comparison protocol"
      description="The judge-facing controls below are read from the verified benchmark contract and persisted experiment configuration."
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border p-4"><div className="metric-label">FLAGSHIP DATASET</div><strong className="mt-1 block text-sm">{dataset.name}</strong><span className="mt-1 block text-[10px] muted">{dataset.provenance.target} · {dataset.provenance.positive_label} / {dataset.provenance.negative_label}</span></div>
        <div className="rounded-xl border p-4"><div className="metric-label">COMMON REPRESENTATION</div><strong className="mt-1 block text-sm">{textValue(representation.final_representation_dimension)} dimensions</strong><span className="mt-1 block text-[10px] muted">{textValue(selection.method)} selection · {textValue(selection.k_features)} retained</span></div>
        <div className="rounded-xl border p-4"><div className="metric-label">SPLIT / CV</div><strong className="mt-1 block text-sm">{finite(testSize)?`${Math.round(testSize*100)}% holdout`:'Not recorded'} · {textValue(comparisonContract.cv_folds,experiment.config.cv_folds.toString())}-fold</strong><span className="mt-1 block text-[10px] muted">Seed {textValue(comparisonContract.seed,experiment.config.seed.toString())}</span></div>
        <div className="rounded-xl border p-4"><div className="metric-label">THRESHOLD PROTOCOL</div><strong className="mt-1 block text-sm">{thresholdStrategy==='target_sensitivity'?'Target sensitivity':'Configured strategy'}</strong><span className="mt-1 block text-[10px] muted">{finite(targetSensitivity)?`Target ${metric(targetSensitivity)} · OOF-selected where recorded`:'Target not recorded'}</span></div>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <MetricCard label="BENCHMARK EVIDENCE" value={evidence.benchmark.model_ids.length===orderedModels.length?'Complete model-set coverage':'Partial coverage'} detail={`${evidence.benchmark.model_ids.length} benchmark-linked models`}/>
        <MetricCard label="ROBUSTNESS EVIDENCE" value={robustnessIds.size} detail="Packaged model-linked records"/>
        <MetricCard label="EXPLAINABILITY" value={evidence.explainability.model_ids.length} detail="Packaged explainability-linked models"/>
      </div>
      {controlledClaim
        ? <Notice tone="green">Evidence claims explicitly record no quantum-advantage claim and no real-quantum-hardware execution.</Notice>
        : <Notice tone="amber">Scientific-claim flags are not fully available in the packaged evidence view.</Notice>}
    </Card>

    <Card
      title="Seven-model comparison matrix"
      description="Exact persisted held-out metrics plus evidence availability. Missing measurements remain visibly unavailable."
    >
      <div className="table-wrap overflow-x-auto">
        <table className="data-table min-w-[1500px]">
          <thead>
            <tr>
              <th>Family</th>
              <th>Model</th>
              <th>Framework</th>
              <th>Quantum layer</th>
              <th>Accuracy</th>
              <th>Sensitivity</th>
              <th>Specificity</th>
              <th>F1</th>
              <th>ROC-AUC</th>
              <th>Explainability</th>
              <th>Robustness</th>
              <th>Benchmark</th>
            </tr>
          </thead>
          <tbody>
            {orderedModels.map(model=>{
              const fam=family(model.model_type);
              const metrics=model.metrics.test;
              const framework=frameworkFor(model,alignment);
              const execution=executionFor(model,alignment);
              return <tr key={model.id}>
                <td><Badge tone={tone(fam)}>{fam}</Badge></td>
                <td><strong>{modelLabels[model.model_type]}</strong><div className="text-[10px] muted">{execution}</div></td>
                <td className="text-xs">{framework}</td>
                <td>{fam==='Classical'?'No':'Yes'}</td>
                <td className="numeric">{metric(metrics?.accuracy)}</td>
                <td className="numeric">{metric(metrics?.sensitivity??metrics?.recall)}</td>
                <td className="numeric">{metric(metrics?.specificity)}</td>
                <td className="numeric">{metric(metrics?.f1)}</td>
                <td className="numeric">{metric(metrics?.roc_auc,false)}</td>
                <td><Badge tone={explainabilityIds.has(model.id)?'green':'amber'}>{evidenceStatus(explainabilityIds.has(model.id))}</Badge></td>
                <td><Badge tone={robustnessIds.has(model.id)?'green':'amber'}>{evidenceStatus(robustnessIds.has(model.id))}</Badge></td>
                <td><Badge tone={benchmarkIds.has(model.id)?'green':'amber'}>{evidenceStatus(benchmarkIds.has(model.id))}</Badge></td>
              </tr>;
            })}
          </tbody>
        </table>
      </div>
    </Card>

    <div className="grid gap-5 lg:grid-cols-3">
      {families.map(group=>{
        const groupModels=group.kinds.map(kind=>orderedModels.find(model=>model.model_type===kind)).filter((model):model is ModelRecord=>Boolean(model));
        return <Card key={group.name} title={group.name} description={`${groupModels.length} model${groupModels.length===1?'':'s'} in the verified set.`}>
          <div className="space-y-2">
            {groupModels.map(model=><div key={model.id} className="flex items-center gap-2 rounded-lg border p-3"><Badge tone={tone(family(model.model_type))}>{family(model.model_type).toUpperCase()}</Badge><strong className="min-w-0 flex-1 text-xs">{modelLabels[model.model_type]}</strong><span className="text-[10px] muted">{frameworkFor(model,alignment)}</span></div>)}
          </div>
        </Card>;
      })}
    </div>

    <Card title="How to read this comparison" description="Scientific interpretation boundary">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border p-4"><div className="metric-label">WHAT IS BEING COMPARED?</div><p className="mt-2 text-sm">Seven existing model implementations: three classical baselines, three quantum models, and one PennyLane + PyTorch hybrid.</p></div>
        <div className="rounded-xl border p-4"><div className="metric-label">WHAT DOES IT SHOW?</div><p className="mt-2 text-sm">Empirical differences in persisted held-out performance, stability, execution, and available research evidence.</p></div>
        <div className="rounded-xl border p-4"><div className="metric-label">WHAT DOES IT NOT PROVE?</div><p className="mt-2 text-sm">It does not establish quantum advantage, clinical validation, or suitability for clinical deployment.</p></div>
      </div>
      <JsonDisclosure
        label="Inspect verified comparison contract"
        value={{comparison_contract:comparisonContract,claims:evidence.benchmark.claims,benchmark_model_ids:evidence.benchmark.model_ids,experiment_id:experiment.id,dataset_id:dataset.id}}
      />
    </Card>
  </div>;
}
