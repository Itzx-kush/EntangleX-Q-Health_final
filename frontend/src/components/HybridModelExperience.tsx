import {Atom,ArrowRight,BrainCircuit,CheckCircle2,GitBranch,Layers3,LineChart,ShieldCheck,Sparkles} from 'lucide-react';
import {Link} from 'react-router-dom';
import {Badge,Card} from './ui';
import {MetricCard,Notice} from './Shared';
import type {Experiment,ModelRecord} from '../types/qhealth';

type HybridModelExperienceProps={
  model:ModelRecord;
  experiment:Experiment;
  mode:'live'|'verified';
  datasetName?:string;
  shapAvailable?:boolean;
};

function value(value:unknown,fallback='Not recorded'){
  if(value===null||value===undefined||value==='')return fallback;
  return String(value);
}

function finite(value:unknown):value is number{
  return typeof value==='number'&&Number.isFinite(value);
}

function Spec({label,value:content,mono=false}:{label:string;value:unknown;mono?:boolean}){
  return <div className="rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] px-3 py-2">
    <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">{label}</div>
    <div className={(mono?'mono ':'')+'mt-1 break-words text-xs font-semibold text-[#102A5C]'}>{value(content)}</div>
  </div>;
}

function FlowStage({
  eyebrow,
  title,
  description,
  tone='blue',
  icon,
  children,
}:{
  eyebrow:string;
  title:string;
  description:string;
  tone:'blue'|'violet'|'green';
  icon:React.ReactNode;
  children?:React.ReactNode;
}){
  const style=tone==='violet'
    ? 'border-[#6946D9]/25 bg-[#6946D9]/[0.045]'
    : tone==='green'
      ? 'border-[#159A70]/25 bg-[#159A70]/[0.035]'
      : 'border-[#1769E0]/20 bg-white';
  return <article className={'rounded-2xl border p-4 '+style}>
    <div className="flex items-start gap-3">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] text-[#102A5C]" aria-hidden="true">{icon}</div>
      <div className="min-w-0">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">{eyebrow}</div>
        <h3 className="mt-1 text-sm font-semibold text-[#102A5C]">{title}</h3>
        <p className="mt-1 text-xs leading-relaxed text-[#56657D]">{description}</p>
      </div>
    </div>
    {children&&<div className="mt-4">{children}</div>}
  </article>;
}

function Connector(){
  return <div className="flex items-center justify-center" aria-hidden="true">
    <ArrowRight size={15} className="hidden lg:block text-[#56657D]"/>
    <span className="h-4 w-px bg-[#D8E2EF] lg:hidden"/>
  </div>;
}

export function HybridModelExperience({
  model,
  experiment,
  mode,
  datasetName,
  shapAvailable,
}:HybridModelExperienceProps){
  if(model.model_type!=='hybrid_pennylane_torch')return null;

  const quantum=(model.details.quantum||{}) as Record<string,any>;
  const hybrid=experiment.config.hybrid;
  const pipeline=experiment.config.pipeline;
  const operating=(model.metrics.operating_point||model.details.operating_point||null) as Record<string,any>|null;
  const hidden=Array.isArray(quantum.configuration?.hidden_dimensions)
    ? quantum.configuration.hidden_dimensions
    : hybrid?.classical_hidden_dimensions||[];
  const expectationObservables=Array.isArray(quantum.expectation_observables)?quantum.expectation_observables:[];
  const selectedThreshold=operating?.selected_threshold;
  const thresholdStrategy=operating?.selection_strategy||experiment.config.threshold_strategy;
  const thresholdSource=operating?.threshold_source;
  const targetSensitivity=operating?.target_sensitivity??experiment.config.target_sensitivity;
  const shapKnown=shapAvailable===true||Boolean(quantum.explainability);
  const runtimeLabel=value(quantum.execution_kind);
  const deviceLabel=value(quantum.backend||hybrid?.backend);
  const qFramework=value(quantum.framework);
  const classicalFramework=value(quantum.classical_framework);
  const qParams=quantum.quantum_parameter_count;
  const totalParams=quantum.total_parameter_count;
  const featureMap=value(quantum.feature_map||hybrid?.feature_map);
  const activation=value(quantum.configuration?.activation||hybrid?.classical_activation);
  const optimizer=value(quantum.optimizer||hybrid?.optimizer);
  const learningRate=quantum.learning_rate??hybrid?.learning_rate;
  const epochs=quantum.epochs??hybrid?.epochs;
  const batchSize=quantum.batch_size??hybrid?.batch_size;
  const qubits=quantum.qubits??hybrid?.qubits;
  const layers=quantum.quantum_layers??hybrid?.quantum_layers;
  const representationDimension=pipeline?.pca_components;

  return <section className="mt-5" aria-label="PennyLane and PyTorch hybrid model detail">
    <Card
      className="border-[#6946D9]/20 bg-white"
      title="PennyLane + PyTorch Hybrid"
      description="Technical detail for the flagship hybrid quantum-classical model, using the existing model record and experiment configuration."
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="purple">HYBRID QUANTUM-CLASSICAL</Badge>
            <Badge tone="blue">{mode==='verified'?'VERIFIED / PRECOMPUTED EVIDENCE':'PERSISTED MODEL RECORD'}</Badge>
            <Badge tone="green">PennyLane + PyTorch</Badge>
          </div>
          <h2 className="mt-3 text-xl font-semibold text-[#102A5C]">{datasetName||'Hybrid model detail'}</h2>
          <p className="mt-1 max-w-4xl text-sm leading-relaxed text-[#56657D]">
            Classical feature preparation feeds a trainable PennyLane quantum transformation; the resulting quantum representation is passed to a PyTorch output head for the final positive-class probability.
          </p>
        </div>
        <div className="grid shrink-0 gap-2 sm:grid-cols-2">
          <Spec label="Quantum framework" value={qFramework}/>
          <Spec label="Classical framework" value={classicalFramework}/>
          <Spec label="Execution" value={runtimeLabel}/>
          <Spec label="Quantum device" value={deviceLabel} mono/>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="QUBITS" value={value(qubits)} detail="Logical qubits in configured hybrid circuit" icon={<Atom size={15}/>}/>
        <MetricCard label="QUANTUM LAYERS" value={value(layers)} detail="Trainable quantum layer count" icon={<BrainCircuit size={15}/>}/>
        <MetricCard label="REPRESENTATION" value={finite(representationDimension)?`${representationDimension}D`:'Not recorded'} detail="Post-PCA model representation"/>
        <MetricCard label="HARDWARE" value={quantum.real_hardware===false?'NOT USED':value(quantum.real_hardware)} detail="Execution context recorded by model metadata"/>
      </div>

      <Notice tone="blue">
        Why hybrid? The project combines classical feature preparation, a trainable PennyLane quantum transformation, and a classical {classicalFramework} output head. This is an architectural distinction, not a superiority claim.
      </Notice>

      <div className="mt-5 rounded-2xl border border-[#D8E2EF] bg-[#F7FAFD] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">IMPLEMENTED HYBRID FLOW</div>
            <h3 className="mt-1 text-sm font-semibold text-[#102A5C]">Classical → quantum → classical → research output</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            <Spec label="Feature encoding" value={featureMap}/>
            <Spec label="Expectation values" value={expectationObservables.length?expectationObservables.length+' recorded observables':'Not recorded'}/>
          </div>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr]">
          <FlowStage eyebrow="01 · CLASSICAL INPUT" title="Preprocessed feature representation" description="The existing experiment prepares the medical feature vector before quantum execution." tone="blue" icon={<Layers3 size={17}/>}>
            <div className="grid grid-cols-2 gap-2">
              <Spec label="Selection" value={pipeline.selection}/>
              <Spec label="Retained features" value={pipeline.k_features}/>
              <Spec label="PCA dimension" value={pipeline.pca_components}/>
              <Spec label="Angle scaling" value={pipeline.angle_scaling?'Enabled':'Disabled'}/>
            </div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="02 · QUANTUM ENCODING" title="PennyLane feature preparation" description="The reduced representation is encoded into the quantum circuit using the configured feature map." tone="violet" icon={<Atom size={17}/>}>
            <div className="grid gap-2">
              <Spec label="Framework" value={qFramework}/>
              <Spec label="Encoding" value={featureMap}/>
              <Spec label="Device" value={deviceLabel} mono/>
              <Spec label="Qubits" value={qubits}/>
            </div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="03 · TRAINABLE QUANTUM CIRCUIT" title="Quantum processing" description="The existing trainable circuit transforms the encoded vector and produces the recorded expectation-value representation." tone="violet" icon={<BrainCircuit size={17}/>}>
            <div className="grid grid-cols-2 gap-2">
              <Spec label="Layers" value={layers}/>
              <Spec label="Quantum parameters" value={qParams}/>
              <Spec label="Optimizer" value={optimizer}/>
              <Spec label="Parameters changed" value={quantum.quantum_parameters_changed===true?'Recorded: yes':'Not recorded'}/>
            </div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="04 · EXPECTATION VALUES" title="Quantum representation" description="Measured expectation values become the feature representation consumed by the classical output head." tone="violet" icon={<Sparkles size={17}/>}>
            <div className="grid gap-2">
              <Spec label="Observables" value={expectationObservables.length?expectationObservables.join(', '):'Not recorded'}/>
              <Spec label="Output width" value={value(qubits)}/>
              <Spec label="Noise / hardware" value={quantum.real_hardware===false?'Local simulation':'See execution metadata'}/>
            </div>
          </FlowStage>
        </div>

        <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
          <FlowStage eyebrow="05 · PYTORCH OUTPUT HEAD" title="Classical neural output" description="The quantum representation is consumed by the trainable PyTorch head for classification." tone="blue" icon={<GitBranch size={17}/>}>
            <div className="grid gap-2 sm:grid-cols-2">
              <Spec label="Framework" value={classicalFramework}/>
              <Spec label="Hidden dimensions" value={hidden.length?hidden.join(' → '):'Not recorded'}/>
              <Spec label="Activation" value={activation}/>
              <Spec label="Optimizer" value={optimizer}/>
            </div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="06 · PROBABILITY" title="Positive-class probability" description="The final hybrid output remains in probability space before the existing operating-point decision." tone="green" icon={<LineChart size={17}/>}>
            <div className="grid grid-cols-2 gap-2">
              <Spec label="Learning rate" value={learningRate}/>
              <Spec label="Epochs" value={epochs}/>
              <Spec label="Batch size" value={batchSize}/>
              <Spec label="Output" value="Positive-class probability"/>
            </div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="07 · OPERATING POINT" title="Sensitivity-first research decision" description="The existing threshold mechanism determines the research decision without changing benchmark methodology." tone="green" icon={<ShieldCheck size={17}/>}>
            <div className="grid grid-cols-2 gap-2">
              <Spec label="Strategy" value={thresholdStrategy}/>
              <Spec label="Target sensitivity" value={targetSensitivity}/>
              <Spec label="Selected threshold" value={selectedThreshold}/>
              <Spec label="Threshold source" value={thresholdSource}/>
            </div>
          </FlowStage>
        </div>

        <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto_1fr]">
          <FlowStage eyebrow="08 · RESEARCH PREDICTION" title="Prediction / risk stratification" description="The application exposes a research output and risk category, not a clinical diagnosis." tone="green" icon={<CheckCircle2 size={17}/>}>
            <div className="rounded-xl border border-[#159A70]/20 bg-[#159A70]/[0.045] px-3 py-3 text-xs font-semibold text-[#102A5C]">Existing prediction workflow → research output</div>
          </FlowStage>
          <Connector/>
          <FlowStage eyebrow="09 · EXPLAINABILITY" title="SHAP feature contributions" description={shapKnown?'SHAP availability is backed by hybrid metadata/evidence.':'The existing Explainability workflow can be used when persisted SHAP evidence is available.'} tone="blue" icon={<Sparkles size={17}/>}>
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={shapKnown?'green':'amber'}>{shapKnown?'SHAP AVAILABLE':'SHAP AVAILABILITY NOT RECORDED'}</Badge>
              <span className="text-[10px] text-[#56657D]">Final hybrid positive-class output</span>
            </div>
          </FlowStage>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <Spec label="Quantum optimizer" value={optimizer}/>
          <Spec label="Learning rate" value={learningRate}/>
          <Spec label="Epochs" value={epochs}/>
          <Spec label="Batch size" value={batchSize}/>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Link className="btn btn-outline" to="/quantum"><Atom size={14}/>Quantum evidence</Link>
        <Link className="btn btn-outline" to="/prediction"><LineChart size={14}/>Prediction Lab</Link>
        <Link className="btn btn-outline" to="/explainability"><Sparkles size={14}/>Explainability</Link>
        <Link className="btn btn-primary" to="/comparison"><ArrowRight size={14}/>Back to comparison</Link>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><CheckCircle2 size={14} className="text-[#159A70}"/> Research-only boundary</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Local quantum simulation. No real quantum hardware, clinical validation, or quantum-advantage claim is implied.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">TRAINING CONFIGURATION</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Optimizer, learning rate, epoch count, batch size and model dimensions are read from the existing experiment/model metadata.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">EXECUTION CONTEXT</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">{mode==='verified'?'Packaged verified evidence':'Persisted model execution state'} is kept distinct from current runtime availability.</p>
        </div>
      </div>
    </Card>
  </section>;
}
