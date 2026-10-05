import type {ReactNode} from 'react';
import {ArrowDown,ArrowRight,Atom,BrainCircuit,CheckCircle2,Database,FlaskConical,GitBranch,Layers3,Microscope,Scale,Search,ShieldCheck,Sparkles,Workflow} from 'lucide-react';
import {Link} from 'react-router-dom';
import {Badge,Button,Card} from './ui';
import {Notice} from './Shared';
import {modelLabels} from '../utils/format';

type ResearchGapSolutionExperienceProps={
  datasetName?:string;
  hybridDetailPath?:string;
};

function GapCard({index,title,body}:{index:string;title:string;body:string}){
  return <article className="rounded-xl border border-[#102A5C]/15 bg-white p-4">
    <div className="flex items-start gap-3">
      <span className="grid size-8 shrink-0 place-items-center rounded-lg border border-[#D8E2EF] bg-[#F7FAFD] text-[11px] font-bold text-[#102A5C]" aria-hidden="true">{index}</span>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-[#102A5C]">{title}</h3>
        <p className="mt-1 text-xs leading-relaxed text-[#56657D]">{body}</p>
      </div>
    </div>
  </article>;
}

function StageColumn({tone,label,children}:{tone:'navy'|'neutral'|'blue'|'green';label:string;children:ReactNode}){
  const style={
    navy:'border-[#102A5C]/20 bg-white',
    neutral:'border-[#D8E2EF] bg-[#F7FAFD]',
    blue:'border-[#1769E0]/20 bg-[#1769E0]/[0.035]',
    green:'border-[#159A70]/25 bg-[#159A70]/[0.035]',
  }[tone];
  return <div className={'rounded-xl border p-4 '+style}>
    <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">{label}</div>
    <p className="mt-1.5 text-xs leading-relaxed text-[#102A5C]">{children}</p>
  </div>;
}

function FlowNode({label,tone}:{label:string;tone:'navy'|'blue'|'violet'|'green'}){
  const style={
    navy:'border-[#102A5C]/20 bg-white',
    blue:'border-[#1769E0]/20 bg-white',
    violet:'border-[#6946D9]/25 bg-[#6946D9]/[0.045]',
    green:'border-[#159A70]/25 bg-[#159A70]/[0.035]',
  }[tone];
  return <div className={'min-w-0 flex-1 rounded-xl border px-3 py-3 '+style}>
    <div className="text-[10px] font-semibold tracking-[0.06em] text-[#102A5C]">{label}</div>
  </div>;
}

export function ResearchGapSolutionExperience({datasetName,hybridDetailPath}:ResearchGapSolutionExperienceProps){
  const scrollTo=(id:string)=>document.getElementById(id)?.scrollIntoView({behavior:'smooth',block:'start'});

  const gapBullets=[
    'Hybrid QML is hard to evaluate meaningfully without baselines',
    'Quantum results need classical controls',
    'Prediction alone lacks interpretability and reproducible evidence',
  ];
  const solutionStack=[
    'Hybrid QML — PennyLane + PyTorch',
    '7-model controlled comparison',
    'Sensitivity-first evaluation',
    'SHAP explainability',
    'Robustness evidence',
    'Provenance / reproducibility',
  ];
  const researchFlow=[
    {label:'RESEARCH GAP',tone:'navy' as const},
    {label:'HYPOTHESIS',tone:'navy' as const},
    {label:'HYBRID IMPLEMENTATION',tone:'violet' as const},
    {label:'CONTROLLED COMPARISON',tone:'blue' as const},
    {label:'EXPLAINABILITY',tone:'blue' as const},
    {label:'EVIDENCE',tone:'green' as const},
    {label:'RESEARCH INSIGHT',tone:'green' as const},
  ];
  const capabilityRows=[
    ['Classical reference','3 classical baselines',`${modelLabels.logistic_regression} · ${modelLabels.svm} · ${modelLabels.random_forest}`],
    ['Quantum comparison','3 quantum models',`${modelLabels.vqc} · ${modelLabels.qsvc} · ${modelLabels.qnn}`],
    ['Hybrid QML','PennyLane + PyTorch Hybrid',modelLabels.hybrid_pennylane_torch],
    ['Controlled evaluation','7-model benchmark','One shared research comparison framework'],
    ['Decision operating point','Sensitivity-first strategy','Existing evaluation strategy'],
    ['Explainability','SHAP pathway','Feature contributions at the model-output level'],
    ['Robustness','Existing evidence','Packaged robustness evidence'],
    ['Reproducibility','Provenance + integrity','Existing metadata and integrity mechanisms'],
    ['Demonstration','Verified flagship workflow','Early Stage Diabetes Risk Prediction'],
  ];

  return <section className="mt-5" aria-label="Research gap to our solution explanation">
    <Card
      className="border-[#102A5C]/15 bg-white"
      title="RESEARCH GAP → OUR SOLUTION"
      description="SIH26139 · Hybrid Quantum Machine Learning Platform for Early Disease Detection"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="blue">SIH26139</Badge>
        <Badge tone="purple">{datasetName||'Early Stage Diabetes Risk Prediction'}</Badge>
        <Badge tone="green">RESEARCH PLATFORM CONTRIBUTION</Badge>
      </div>

      <div className="mt-4 rounded-2xl border border-[#D8E2EF] bg-[#F7FAFD] p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Microscope size={15} className="text-[#102A5C]"/> SIH26139 · WHY THIS PLATFORM MATTERS</div>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#102A5C]">Early disease detection with hybrid QML requires more than a quantum circuit. It requires a controlled ML research workflow around the quantum component: data → preprocessing → hybrid modeling → comparison → evidence → prediction → explainability.</p>
      </div>

      <div className="mt-5 grid gap-3">
        <div className="rounded-2xl border border-[#102A5C]/15 bg-white p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><Search size={14} className="text-[#102A5C]"/> RESEARCH GAP</div>
          <ul className="mt-2 space-y-1.5">
            {gapBullets.map(item=><li key={item} className="flex gap-2 text-xs leading-relaxed text-[#56657D]"><CheckCircle2 size={13} className="mt-0.5 shrink-0 text-[#56657D]" aria-hidden="true"/><span>{item}</span></li>)}
          </ul>
        </div>
        <div className="flex justify-center" aria-hidden="true"><ArrowDown size={16} className="text-[#56657D]"/></div>
        <div className="rounded-2xl border border-[#1769E0]/20 bg-[#1769E0]/[0.035] p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#1769E0]"><Layers3 size={14}/> OUR SOLUTION — ENTANGLEX Q-HEALTH</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {solutionStack.map(item=><Badge key={item} tone="blue">{item}</Badge>)}
          </div>
        </div>
      </div>

      <Notice tone="blue">Our design goal: move beyond a standalone quantum demonstration toward an evidence-oriented hybrid ML platform. The value is the complete research workflow, not simply “we use quantum”.</Notice>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <GapCard index="GAP 1" title="Hybrid QML is difficult to evaluate meaningfully" body="Medical QML research often combines classical and quantum components, so EntangleX treats hybrid QML as a research architecture to be evaluated against meaningful baselines rather than assumed to be superior."/>
        <GapCard index="GAP 2" title="Quantum models need classical controls" body="A quantum result is not meaningful without classical comparison. The platform runs Logistic Regression, SVM, and Random Forest alongside VQC, QSVC, QNN, and the PennyLane + PyTorch hybrid."/>
        <GapCard index="GAP 3" title="Prediction alone is insufficient" body="A research-oriented medical prototype also needs sensitivity-first evaluation, SHAP explainability, robustness evidence, and provenance/integrity — not just a class label."/>
        <GapCard index="GAP 4" title="Hybrid architecture should be explainable at the output level" body="The hybrid prediction pathway is paired with the existing SHAP workflow. This explains the model through feature contributions, not by claiming gate-level interpretability."/>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">GAP → SOLUTION · FOUR-STAGE VIEW</div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StageColumn tone="navy" label="GAP">Hybrid QML needs stronger integration with controlled benchmarking, interpretability, and reproducible evaluation.</StageColumn>
          <StageColumn tone="neutral" label="EXISTING APPROACH">Conventional workflows often stop at a quantum circuit inserted into a classifier, or at classical baselines without a unified research workflow.</StageColumn>
          <StageColumn tone="blue" label="ENTANGLEX SOLUTION">One integrated research workflow: hybrid QML, seven-model comparison, sensitivity-first evaluation, SHAP, and evidence/provenance.</StageColumn>
          <StageColumn tone="green" label="EVIDENCE">The prototype demonstrates the verified Early Stage Diabetes flagship and its packaged benchmark, robustness, prediction, and SHAP evidence.</StageColumn>
        </div>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">WHAT WE ADD</div>
        <div className="table-wrap mt-3 overflow-x-auto">
          <table className="data-table min-w-[760px]">
            <thead><tr><th>Research need</th><th>EntangleX capability</th><th>Implementation</th></tr></thead>
            <tbody>
              {capabilityRows.map(([need,capability,implementation])=><tr key={need}>
                <td><strong className="text-xs">{need}</strong></td>
                <td className="text-xs">{capability}</td>
                <td className="text-xs muted">{implementation}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-[#6946D9]/25 bg-[#6946D9]/[0.045] p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><GitBranch size={14} className="text-[#6946D9]"/> OUR CONTRIBUTION</div>
          <p className="mt-2 text-sm leading-relaxed text-[#102A5C]">An integrated research workflow that combines hybrid QML, controlled cross-family benchmarking, model-level explainability, sensitivity-aware evaluation, and evidence/provenance within a single disease-focused prototype.</p>
          <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">A contribution statement, not a universal novelty claim.</p>
        </div>
        <div className="rounded-2xl border border-[#D8E2EF] bg-[#F7FAFD] p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><Workflow size={14}/> BUILT ON ESTABLISHED METHODS</div>
          <p className="mt-2 text-xs leading-relaxed text-[#56657D]">Classical ML, Qiskit-based quantum models, PennyLane, PyTorch, SHAP, and standard statistical/ML metrics.</p>
          <p className="mt-2 text-xs font-semibold leading-relaxed text-[#102A5C]">Our contribution is the integration, workflow, and evaluation design.</p>
        </div>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">RESEARCH-TO-PRODUCT FLOW</div>
        <div className="mt-3 grid gap-2 md:grid-cols-4 xl:grid-cols-7" aria-label="Research gap to insight flow">
          {researchFlow.map((node,index)=><div key={node.label} className="flex items-center gap-2">
            <FlowNode label={node.label} tone={node.tone}/>
            {index<researchFlow.length-1&&<ArrowRight size={13} className="hidden shrink-0 text-[#56657D] xl:block" aria-hidden="true"/>}
          </div>)}
        </div>
      </div>

      <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Scale size={14} className="text-[#1769E0]"/> Differentiation from classical-only</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">Classical-only systems provide strong established baselines. EntangleX extends them with a research path for quantum evaluation, hybrid modeling, and controlled cross-family comparison.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Atom size={14} className="text-[#6946D9]"/> Differentiation from a quantum demo</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">A generic quantum demo shows input → circuit → output. EntangleX adds data, quality, preprocessing, comparison, evaluation, prediction, explainability, robustness, and provenance.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-white p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><ShieldCheck size={14} className="text-[#159A70]"/> Beyond the quantum component</div>
          <p className="mt-1 text-[10px] leading-relaxed text-[#56657D]">The value is the complete research workflow: hybrid model + fair baseline comparison + evaluation + explainability + evidence + reproducibility.</p>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={()=>scrollTo('hybrid-architecture')}><Layers3 size={14}/>View Hybrid Architecture</Button>
        <Button variant="outline" onClick={()=>scrollTo('why-hybrid')}><BrainCircuit size={14}/>Why Hybrid</Button>
        <Link className="btn btn-primary" to="/comparison"><FlaskConical size={14}/>View Controlled Comparison</Link>
        <Link className="btn btn-outline" to="/explainability"><Sparkles size={14}/>Explainability</Link>
        {hybridDetailPath&&<Link className="btn btn-outline" to={hybridDetailPath}><GitBranch size={14}/>Open hybrid model detail</Link>}
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] p-3">
        <Database size={14} className="mt-0.5 shrink-0 text-[#56657D]" aria-hidden="true"/>
        <p className="text-[11px] leading-relaxed text-[#56657D]">Evidence contribution: verified demo artifacts, benchmark evidence, robustness evidence, prediction evidence, preprocessing evidence, provenance, and integrity checks — reported as persisted evidence, not as reproducibility beyond what the package establishes.</p>
      </div>

      <Notice tone="green">Research prototype. Empirical benchmark evidence is reported transparently; no clinical validation, clinical diagnosis, real quantum hardware, or quantum advantage is claimed.</Notice>
    </Card>
  </section>;
}
