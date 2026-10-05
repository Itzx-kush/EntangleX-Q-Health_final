import type {ReactNode} from 'react';
import {ArrowDown,ArrowRight,Atom,BrainCircuit,Database,GitBranch,Layers3,ShieldCheck,SlidersHorizontal,Sparkles,Workflow} from 'lucide-react';
import {Badge,Card} from './ui';
import type {AlignmentContract,Dataset,Experiment,ModelRecord,VerifiedEvidencePackage} from '../types/qhealth';

type ArchitectureProps={
  alignment?:AlignmentContract;
  dataset:Dataset;
  experiment:Experiment;
  models:ModelRecord[];
  evidence:VerifiedEvidencePackage['evidence'];
};

function Connector(){
  return <div className="flex items-center justify-center text-[#1769E0]" aria-hidden="true">
    <ArrowRight size={16} className="hidden md:block"/>
    <ArrowDown size={16} className="md:hidden"/>
  </div>;
}

function StageCard({
  eyebrow,
  title,
  description,
  children,
  tone='blue',
  icon,
}:{
  eyebrow:string;
  title:string;
  description:string;
  children?:ReactNode;
  tone?:'blue'|'violet'|'green'|'navy';
  icon:ReactNode;
}){
  const palette={
    blue:'border-[#1769E0]/20 bg-white',
    violet:'border-[#6946D9]/30 bg-[#6946D9]/[0.045]',
    green:'border-[#159A70]/25 bg-[#159A70]/[0.035]',
    navy:'border-[#102A5C]/15 bg-white',
  }[tone];
  return <article className={'rounded-2xl border p-4 shadow-[0_8px_24px_rgba(16,42,92,0.06)] '+palette}>
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

function Spec({label,value,mono=false}:{label:string;value:ReactNode;mono?:boolean}){
  return <div className="rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] px-3 py-2">
    <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">{label}</div>
    <div className={(mono?'mono ':'')+'mt-1 break-words text-xs font-semibold text-[#102A5C]'}>{value}</div>
  </div>;
}

function MiniFlow({items,tone='blue'}:{items:{title:string;detail:string}[];tone?:'blue'|'violet'|'green'}){
  const border=tone==='violet'?'border-[#6946D9]/25 bg-[#6946D9]/[0.055]':tone==='green'?'border-[#159A70]/25 bg-[#159A70]/[0.045]':'border-[#1769E0]/20 bg-[#1769E0]/[0.035]';
  return <div className="grid gap-2 md:grid-cols-3">
    {items.map((item,index)=><div key={item.title} className="flex items-center gap-2">
      <div className={'min-w-0 flex-1 rounded-xl border px-3 py-3 '+border}>
        <div className="text-xs font-semibold text-[#102A5C]">{item.title}</div>
        <div className="mt-1 text-[10px] leading-relaxed text-[#56657D]">{item.detail}</div>
      </div>
      {index<items.length-1&&<ArrowRight size={13} className="hidden shrink-0 text-[#56657D] md:block" aria-hidden="true"/>}
      {index<items.length-1&&<ArrowDown size={13} className="shrink-0 text-[#56657D] md:hidden" aria-hidden="true"/>}
    </div>)}
  </div>;
}

export function HybridArchitectureVisualization({alignment,dataset,experiment,models,evidence}:ArchitectureProps){
  const preprocessing=evidence.preprocessing.configuration;
  const pipeline=preprocessing.pipeline;
  const representation=(evidence.preprocessing.representation||{}) as Record<string,unknown>;
  const hybrid=models.find(model=>model.model_type==='hybrid_pennylane_torch');
  const quantum=(hybrid?.details.quantum||{}) as Record<string,any>;
  const operating=(hybrid?.metrics.operating_point||hybrid?.details.operating_point||null) as Record<string,any>|null;
  const hidden=Array.isArray(quantum.configuration?.hidden_dimensions)
    ? quantum.configuration.hidden_dimensions
    : Array.isArray(preprocessing.hybrid?.classical_hidden_dimensions)
      ? preprocessing.hybrid.classical_hidden_dimensions
      : [];
  const targetSensitivity=operating?.target_sensitivity??preprocessing.target_sensitivity;
  const threshold=operating?.selected_threshold??null;
  const thresholdSource=operating?.threshold_source||'OOF validation';
  const shapMethod=evidence.explainability.method||'SHAP';
  const hybridStatus=alignment?.flagship_architecture?.status||'IMPLEMENTED';

  return <section className="mt-5" aria-label="SIH hybrid quantum-classical architecture">
    <Card className="overflow-hidden border-[#102A5C]/10" title="Hybrid Quantum-Classical Architecture" description="Authoritative presentation of the implemented flagship Early Stage Diabetes pipeline. Values are read from the existing verified experiment metadata and alignment contract.">
      <div className="rounded-2xl border border-[#102A5C]/10 bg-[#F7FAFD] p-4 md:p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="purple">HYBRID QUANTUM-CLASSICAL MODEL</Badge>
              <Badge tone={hybridStatus==='IMPLEMENTED'?'green':'amber'}>{hybridStatus}</Badge>
              <Badge tone="blue">FLAGSHIP · SIH26139</Badge>
            </div>
            <h2 className="mt-3 text-xl font-semibold text-[#102A5C]">{dataset.name}</h2>
            <p className="mt-1 max-w-4xl text-sm leading-relaxed text-[#56657D]">Classical preprocessing + PennyLane quantum transformation + PyTorch classification, evaluated under the project's sensitivity-first research protocol.</p>
          </div>
          <div className="grid shrink-0 gap-2 sm:grid-cols-2">
            <Spec label="Quantum runtime" value={quantum.execution_kind||'local PennyLane quantum simulation'}/>
            <Spec label="Backend" value={<span className="mono">{quantum.backend||'default.qubit'}</span>}/>
          </div>
        </div>

        <div className="mt-5 grid gap-2 md:grid-cols-7" aria-label="Macro architecture flow">
          {[
            ['01','DATA','Structured diabetes data'],
            ['02','PREPROCESS','Validated transforms'],
            ['03','FEATURES','Selection + PCA'],
            ['04','QUANTUM','Angle encoding + circuit'],
            ['05','HYBRID','Quantum + PyTorch'],
            ['06','DECISION','Probability + threshold'],
            ['07','EXPLAIN','SHAP contributions'],
          ].map(([number,label,detail],index)=>(
            <div key={label} className="flex items-center gap-2">
              <div className="min-w-0 flex-1 rounded-xl border border-[#D8E2EF] bg-white px-3 py-3">
                <div className="text-[9px] font-semibold tracking-[0.14em] text-[#1769E0]">{number} · {label}</div>
                <div className="mt-1 text-[10px] leading-relaxed text-[#56657D]">{detail}</div>
              </div>
              {index<6&&<ArrowRight size={12} className="hidden shrink-0 text-[#56657D] xl:block" aria-hidden="true"/>}
            </div>
          ))}
        </div>

        <div className="mt-5 rounded-2xl border border-[#102A5C]/10 bg-white p-4 md:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">DETAILED IMPLEMENTED FLOW</div>
              <h3 className="mt-1 text-sm font-semibold text-[#102A5C]">Classical feature vector → quantum representation → classical decision head</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              <Spec label="Dataset target" value={dataset.provenance.target}/>
              <Spec label="Positive class" value={dataset.provenance.positive_label}/>
            </div>
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1.15fr_auto_1fr]">
            <StageCard eyebrow="01 · DATA SOURCE" title={dataset.name} description="Structured tabular risk data enters the controlled research pipeline." tone="navy" icon={<Database size={17}/>}>
              <div className="grid grid-cols-2 gap-2">
                <Spec label="Rows" value={dataset.provenance.row_count.toLocaleString()}/>
                <Spec label="Features" value={dataset.provenance.feature_count}/>
                <Spec label="Domain" value={dataset.provenance.domain}/>
                <Spec label="Integrity" value="Verified package identity"/>
              </div>
            </StageCard>

            <Connector/>

            <StageCard eyebrow="02–03 · CLASSICAL PIPELINE" title="Validation + feature preparation" description="The verified experiment reuses the project's configured preprocessing and shared representation." tone="blue" icon={<Workflow size={17}/>}>
              <MiniFlow items={[
                {title:'Validation',detail:'Target + provenance · duplicate policy: '+String(preprocessing.duplicate_policy||'as configured')},
                {title:'Preprocess',detail:String(pipeline.imputer||'configured')+' imputation → '+String(pipeline.scaler||'configured')+' scaling'},
                {title:'Reduce',detail:String(pipeline.selection||'configured')+' selection → PCA '+String(pipeline.pca_components??representation.pca_components??'configured')+'D → '+(pipeline.angle_scaling?'angle scaling':'configured transform')},
              ]}/>
            </StageCard>

            <Connector/>

            <StageCard eyebrow="04 · QUANTUM TRANSFORMATION" title="PennyLane trainable circuit" description="The reduced classical vector is angle-encoded into the executed local quantum simulator path." tone="violet" icon={<Atom size={17}/>}>
              <div className="rounded-xl border border-[#6946D9]/25 bg-[#6946D9]/[0.055] p-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><BrainCircuit size={15} className="text-[#6946D9]"/> Feature encoding</div>
                <p className="mt-1 text-[10px] text-[#56657D]">{String(quantum.feature_map||'angle')} encoding → trainable quantum layers → Pauli-Z expectation values</p>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Spec label="Qubits" value={quantum.qubits??preprocessing.hybrid?.qubits??representation.hybrid_qubits??'—'}/>
                <Spec label="Layers" value={quantum.quantum_layers??preprocessing.hybrid?.quantum_layers??'—'}/>
                <Spec label="Observables" value={Array.isArray(quantum.expectation_observables)?quantum.expectation_observables.length:'Pauli-Z per qubit'}/>
              </div>
              <div className="mt-3 rounded-xl border border-[#6946D9]/20 bg-white px-3 py-3 text-[10px] leading-relaxed text-[#56657D]">
                <strong className="text-[#102A5C]">Execution boundary:</strong> PennyLane <span className="mono">{String(quantum.backend||'default.qubit')}</span> · local simulation · no hardware execution.
              </div>
            </StageCard>

            <Connector/>

            <StageCard eyebrow="05 · CLASSICAL OUTPUT" title="PyTorch output head" description="Quantum expectation values feed a trainable classical classifier to produce the final probability." tone="blue" icon={<Layers3 size={17}/>}>
              <div className="grid gap-2">
                <Spec label="Hidden dimensions" value={hidden.length?hidden.join(' → '):'Configured in model metadata'}/>
                <Spec label="Activation" value={String(quantum.configuration?.activation||preprocessing.hybrid?.classical_activation||'configured activation')}/>
                <Spec label="Output" value="Linear score → sigmoid → positive-class probability"/>
              </div>
              <div className="mt-3 rounded-xl border border-[#1769E0]/20 bg-[#1769E0]/[0.035] px-3 py-3">
                <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">TRAINABLE HYBRID LOOP</div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-[#56657D]">
                  <span className="font-semibold text-[#102A5C]">Quantum parameters</span><ArrowRight size={11}/><span className="font-semibold text-[#102A5C]">Expectation values</span><ArrowRight size={11}/><span className="font-semibold text-[#102A5C]">{String(quantum.optimizer||preprocessing.hybrid?.optimizer||'configured optimizer')} updates weights</span>
                </div>
              </div>
            </StageCard>
          </div>

          <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
            <StageCard eyebrow="06 · DECISION LAYER" title="Positive-class probability" description="The final hybrid output stays in probability space before the platform's operating-point selection." tone="green" icon={<SlidersHorizontal size={17}/>}>
              <div className="grid grid-cols-2 gap-2">
                <Spec label="Threshold strategy" value={String(preprocessing.threshold_strategy||'target_sensitivity')}/>
                <Spec label="Target sensitivity" value={targetSensitivity??'Configured by evidence'}/>
                <Spec label="Selected threshold" value={threshold??'Locked at evaluation'}/>
                <Spec label="Threshold source" value={String(thresholdSource)}/>
              </div>
            </StageCard>
            <Connector/>
            <StageCard eyebrow="07 · RESEARCH DECISION" title="Prediction / risk stratification" description="The application exposes a research output and risk category, not a clinical diagnosis." tone="green" icon={<GitBranch size={17}/>}>
              <div className="rounded-xl border border-[#159A70]/20 bg-[#159A70]/[0.045] px-3 py-3 text-xs font-semibold text-[#102A5C]">Research prediction → risk category → decision support</div>
              <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">No clinical-validation, diagnosis, treatment, or quantum-advantage claim is made by this architecture.</p>
            </StageCard>
            <Connector/>
            <StageCard eyebrow="08 · EXPLAINABILITY" title="SHAP feature contributions" description="Post-hoc explanation is attached to the final hybrid positive-class output." tone="blue" icon={<Sparkles size={17}/>}>
              <div className="grid gap-2">
                <Spec label="Method" value={shapMethod}/>
                <Spec label="Explanation target" value="Final hybrid positive-class probability"/>
                <Spec label="Interpretation" value="Feature contribution toward/away from the positive class"/>
              </div>
            </StageCard>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Spec label="Shared representation dimension" value={representation.final_representation_dimension??pipeline.pca_components??'—'}/>
            <Spec label="Hybrid framework" value="PennyLane + PyTorch"/>
            <Spec label="Local simulation" value={String(quantum.backend||'default.qubit')}/>
            <Spec label="Scientific boundary" value="Research prototype · controlled evaluation"/>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><ShieldCheck size={14} className="text-[#159A70]"/> Source of truth</div>
            <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Dataset, experiment configuration, model metadata, and evidence are read from the existing verified package; alignment stages come from the backend alignment contract.</p>
          </div>
          <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Layers3 size={14} className="text-[#1769E0]"/> Coexisting quantum capabilities</div>
            <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">The broader project continues to expose Qiskit / Aer model capabilities. This visualization isolates the flagship PennyLane + PyTorch hybrid path.</p>
          </div>
          <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><ShieldCheck size={14} className="text-[#159A70]"/> Evidence boundary</div>
            <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">This is an architecture/evidence surface, not a claim of real quantum hardware execution, clinical validation, or quantum advantage.</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-[#D8E2EF] pt-4 text-[10px] text-[#56657D]">
          <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-[#1769E0]"/> Classical / orchestration</span>
          <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-[#6946D9]"/> Quantum execution</span>
          <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-[#159A70]"/> Decision / verified boundary</span>
          <span className="ml-auto inline-flex items-center gap-1"><ShieldCheck size={12}/> Responsive · keyboard-readable · color-independent labels</span>
        </div>
      </div>
    </Card>
  </section>;
}
