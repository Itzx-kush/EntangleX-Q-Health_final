import type {ReactNode} from 'react';
import {ArrowRight,Atom,BrainCircuit,CheckCircle2,FlaskConical,GitBranch,Layers3,ShieldCheck,Sparkles,Workflow} from 'lucide-react';
import {Link} from 'react-router-dom';
import {Badge,Button,Card} from './ui';
import {Notice} from './Shared';
import {modelLabels} from '../utils/format';

type WhyHybridExperienceProps={
  datasetName?:string;
  hybridDetailPath?:string;
};

type FamilyTone='blue'|'purple'|'amber';

function FamilyCard({
  family,
  tone,
  heading,
  body,
  models,
}:{
  family:'Classical'|'Quantum'|'Hybrid';
  tone:FamilyTone;
  heading:string;
  body:string[];
  models:string[];
}){
  const palette={
    blue:'border-[#1769E0]/20 bg-white',
    purple:'border-[#6946D9]/25 bg-[#6946D9]/[0.045]',
    amber:'border-[#18B6C9]/25 bg-[#18B6C9]/[0.045]',
  }[tone];
  const accent={
    blue:'text-[#1769E0]',
    purple:'text-[#6946D9]',
    amber:'text-[#18B6C9]',
  }[tone];
  return <article className={'rounded-2xl border p-4 '+palette}>
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">{family} MODEL FAMILY</div>
        <h3 className={'mt-1 text-sm font-semibold '+accent}>{family.charAt(0)+family.slice(1).toLowerCase()}</h3>
        <p className="mt-1 text-xs leading-relaxed text-[#56657D]">{heading}</p>
      </div>
      <Badge tone={tone}>{family.toUpperCase()}</Badge>
    </div>
    <ul className="mt-3 space-y-1.5">
      {body.map(item=><li key={item} className="flex gap-2 text-[11px] leading-relaxed text-[#56657D]"><CheckCircle2 size={13} className={'mt-0.5 shrink-0 '+accent} aria-hidden="true"/><span>{item}</span></li>)}
    </ul>
    <div className="mt-3 rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] px-3 py-2">
      <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">ROLE IN ENTANGLEX</div>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {models.map(label=><Badge key={label} tone={tone==='amber'?'blue':tone}>{label}</Badge>)}
      </div>
    </div>
  </article>;
}

function AnswerBlock({eyebrow,children,tone='blue'}:{eyebrow:string;children:ReactNode;tone?:'blue'|'violet'|'green'}){
  const border=tone==='violet'?'border-[#6946D9]/25 bg-[#6946D9]/[0.04]':tone==='green'?'border-[#159A70]/25 bg-[#159A70]/[0.035]':'border-[#1769E0]/20 bg-white';
  return <div className={'rounded-xl border p-4 '+border}>
    <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">{eyebrow}</div>
    <p className="mt-1.5 text-xs leading-relaxed text-[#102A5C]">{children}</p>
  </div>;
}

function FlowStep({label,detail,tone='blue'}:{label:string;detail:string;tone?:'blue'|'violet'|'green'}){
  const border=tone==='violet'?'border-[#6946D9]/25 bg-[#6946D9]/[0.045]':tone==='green'?'border-[#159A70]/25 bg-[#159A70]/[0.035]':'border-[#1769E0]/20 bg-white';
  return <div className={'min-w-0 flex-1 rounded-xl border px-3 py-3 '+border}>
    <div className="text-[10px] font-semibold tracking-[0.06em] text-[#102A5C]">{label}</div>
    <div className="mt-1 text-[10px] leading-relaxed text-[#56657D]">{detail}</div>
  </div>;
}

export function WhyHybridExperience({datasetName,hybridDetailPath}:WhyHybridExperienceProps){
  const scrollToArchitecture=()=>{
    document.getElementById('hybrid-architecture')?.scrollIntoView({behavior:'smooth',block:'start'});
  };

  const flowSteps=[
    {label:'CLASSICAL DATA',detail:'Structured tabular risk data',tone:'blue' as const},
    {label:'CLASSICAL PREPROCESSING',detail:'Cleaning, scaling, feature selection, dimensionality reduction',tone:'blue' as const},
    {label:'QUANTUM TRANSFORMATION',detail:'Trainable PennyLane circuit',tone:'violet' as const},
    {label:'QUANTUM REPRESENTATION',detail:'Expectation-value feature representation',tone:'violet' as const},
    {label:'CLASSICAL OUTPUT HEAD',detail:'PyTorch classifier produces the probability',tone:'blue' as const},
    {label:'PREDICTION',detail:'Research risk output + SHAP explanation',tone:'green' as const},
  ];

  const matrixRows=[
    ['Classical preprocessing','Prepare reliable input','Standard structured-data workflow'],
    ['Feature reduction','Match model constraints','Controlled shared representation'],
    ['Quantum layer','Learn quantum representation','Research component under evaluation'],
    ['PyTorch head','Produce final output','Classical classification stage'],
    ['SHAP','Explain prediction','Model interpretability at the output level'],
  ];

  return <section className="mt-5" aria-label="Why hybrid quantum-classical explanation">
    <Card
      className="border-[#18B6C9]/20 bg-white"
      title="WHY HYBRID?"
      description="Classical reliability + quantum representation research"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="blue">SIH26139</Badge>
        <Badge tone="purple">{datasetName||'Early Stage Diabetes Risk Prediction'}</Badge>
        <Badge tone="green">EMPIRICALLY EVALUATED · NOT ASSUMED</Badge>
      </div>

      <div className="mt-4 rounded-2xl border border-[#6946D9]/25 bg-[#6946D9]/[0.045] p-4">
        <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><FlaskConical size={14} className="text-[#6946D9]"/> RESEARCH HYPOTHESIS</div>
        <p className="mt-2 max-w-4xl text-sm font-medium leading-relaxed text-[#102A5C]">Can a trainable quantum representation integrated into a classical ML pipeline provide useful predictive behavior for early-stage disease-risk classification under a controlled benchmark?</p>
        <div className="mt-3 rounded-xl border border-[#D8E2EF] bg-white px-3 py-2">
          <span className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">HOW WE TEST IT</span>
          <span className="ml-2 text-xs text-[#56657D]">Compare classical, quantum, and hybrid models under the existing controlled evaluation framework. This is a hypothesis, not a pre-stated conclusion.</span>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <FamilyCard
          family="Classical"
          tone="blue"
          heading="The established baseline and controlled reference for tabular ML workflows."
          body={[
            'Provides directly interpretable benchmark context',
            'Covers robust, widely understood classification workflows',
            'Remains the controlled reference against which hybrid behavior is measured',
          ]}
          models={[modelLabels.logistic_regression,modelLabels.svm,modelLabels.random_forest]}
        />
        <FamilyCard
          family="Quantum"
          tone="purple"
          heading="A research direction for alternative feature representations and classification behavior."
          body={[
            'Investigates quantum feature representations',
            'Examines quantum classification behavior under controlled evaluation',
            'Kept deliberately isolated as a research variable',
          ]}
          models={[modelLabels.vqc,modelLabels.qsvc,modelLabels.qnn]}
        />
        <FamilyCard
          family="Hybrid"
          tone="amber"
          heading="Combines established classical processing with a trainable quantum transformation."
          body={[
            'Classical preprocessing is retained end-to-end',
            'PennyLane circuit learns the quantum representation',
            'PyTorch output head keeps classification practical, with existing SHAP explainability',
          ]}
          models={[modelLabels.hybrid_pennylane_torch]}
        />
      </div>

      <Notice tone="blue">Classical baselines are not competitors to hide. They are essential controls that make any observed hybrid behavior interpretable.</Notice>

      <div className="mt-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">WHY THIS STRUCTURE? · COMPACT HYBRID FLOW</div>
          <Badge tone="green">RATIONALE · COMPANION TO THE ARCHITECTURE</Badge>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-3 xl:grid-cols-6" aria-label="Compact hybrid reasoning flow">
          {flowSteps.map((step,index)=><div key={step.label} className="flex items-center gap-2">
            <FlowStep label={step.label} detail={step.detail} tone={step.tone}/>
            {index<flowSteps.length-1&&<ArrowRight size={13} className="hidden shrink-0 text-[#56657D] xl:block" aria-hidden="true"/>}
          </div>)}
        </div>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">WHY THIS ARCHITECTURE? · LAYER-BY-LAYER</div>
        <div className="table-wrap mt-3 overflow-x-auto">
          <table className="data-table min-w-[760px]">
            <thead><tr><th>Layer</th><th>Purpose</th><th>Why it exists</th></tr></thead>
            <tbody>
              {matrixRows.map(([layer,purpose,rationale])=><tr key={layer}>
                <td><strong className="text-xs">{layer}</strong></td>
                <td className="text-xs">{purpose}</td>
                <td className="text-xs muted">{rationale}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <AnswerBlock eyebrow="WHY NOT CLASSICAL ONLY?" tone="blue">Classical ML provides strong, established baselines and is retained. The platform therefore does not assume that quantum processing is necessary, and classical methods remain the controlled reference.</AnswerBlock>
        <AnswerBlock eyebrow="WHY QUANTUM?" tone="violet">Quantum circuits are investigated as trainable feature transformations within a controlled evaluation framework — not presented as a guaranteed replacement for classical ML.</AnswerBlock>
        <AnswerBlock eyebrow="WHY HYBRID?" tone="violet"><span className="font-semibold">Classical data processing + trainable quantum transformation + classical prediction.</span> This preserves established classical workflows while allowing quantum subcomponents to be evaluated in isolation.</AnswerBlock>
        <AnswerBlock eyebrow="WHAT DOES ENTANGLEX ACTUALLY TEST?" tone="green">Whether the hybrid approach provides useful <span className="font-semibold">empirical model behavior</span> under the same research evaluation context — measuring the hypothesis instead of assuming the conclusion.</AnswerBlock>
      </div>

      <div className="mt-5 rounded-2xl border border-[#159A70]/25 bg-[#159A70]/[0.035] p-4">
        <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#159A70]"><ShieldCheck size={14}/> WHAT WE DO NOT CLAIM</div>
        <ul className="mt-3 grid gap-2 sm:grid-cols-2">
          {[
            'No assumed quantum advantage',
            'No real quantum hardware execution',
            'No clinical validation',
            'No claim that hybrid always outperforms classical ML',
            'No claim that simulation equals noiseless real-world deployment',
            'No universal statement beyond the benchmark observation',
          ].map(item=><li key={item} className="flex gap-2 text-xs leading-relaxed text-[#56657D]"><ShieldCheck size={13} className="mt-0.5 shrink-0 text-[#159A70]" aria-hidden="true"/><span>{item}</span></li>)}
        </ul>
        <p className="mt-3 text-xs leading-relaxed text-[#56657D]">Empirical performance is evaluated against classical and quantum baselines under a controlled benchmark. Preferred language is “measured”, “evaluated”, and “compared” — not “proves” or “guarantees”.</p>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><GitBranch size={14} className="text-[#1769E0]"/> Hybrid model → output</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">The platform does not stop at prediction; it exposes the existing SHAP explanation pathway on the final hybrid output.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Layers3 size={14} className="text-[#6946D9]"/> Classical stays</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">The input is real-world structured data, so cleaning, scaling, selection, reduction, output and evaluation remain necessary.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Atom size={14} className="text-[#18B6C9]"/> Quantum as a research component</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Quantum execution runs on local simulators and is intentionally isolated as a research variable inside the pipeline.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Workflow size={14} className="text-[#159A70]"/> Engineering rationale</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Hybrid design preserves established preprocessing, reuses standard ML evaluation, and keeps comparison against classical baselines possible.</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Link className="btn btn-primary" to="/comparison"><FlaskConical size={14}/>View 7-Model Comparison</Link>
        <Button variant="outline" onClick={scrollToArchitecture}><Layers3 size={14}/>See Hybrid Architecture</Button>
        {hybridDetailPath&&<Link className="btn btn-outline" to={hybridDetailPath}><BrainCircuit size={14}/>Open hybrid model detail</Link>}
        <Link className="btn btn-outline" to="/explainability"><Sparkles size={14}/>Explainability</Link>
      </div>
    </Card>
  </section>;
}
