import type {ReactNode} from 'react';
import {Activity,Atom,BrainCircuit,CheckCircle2,Database,ExternalLink,FileText,FlaskConical,GitBranch,Layers3,Microscope,ShieldCheck,Sparkles,Workflow} from 'lucide-react';
import {Link} from 'react-router-dom';
import {Badge,Button,Card} from './ui';
import {Notice} from './Shared';
import {modelLabels} from '../utils/format';

type ResearchBasisExperienceProps={
  datasetName?:string;
  hybridDetailPath?:string;
};

type Category='Quantum ML'|'Hybrid QML'|'Healthcare QML'|'Explainability';

type Reference={
  category:Category;
  title:string;
  authors:string;
  year:string;
  venue:string;
  why:string;
  url:string;
  urlLabel:string;
};

const categoryTone:Record<Category,'purple'|'blue'|'amber'|'green'>={
  'Quantum ML':'purple',
  'Hybrid QML':'blue',
  'Healthcare QML':'amber',
  'Explainability':'green',
};

const categoryIcon:Record<Category,ReactNode>={
  'Quantum ML':<Atom size={14}/>,
  'Hybrid QML':<GitBranch size={14}/>,
  'Healthcare QML':<Activity size={14}/>,
  'Explainability':<Sparkles size={14}/>,
};

const references:Reference[]=[
  {
    category:'Quantum ML',
    title:'Quantum machine learning',
    authors:'Biamonte, J., Wittek, P., Pancotti, N., Rebentrost, P., Wiebe, N., & Lloyd, S.',
    year:'2017',venue:'Nature 549, 195–202',
    why:'Foundational review of quantum machine learning — motivation for investigating quantum approaches to learning tasks.',
    url:'https://www.nature.com/articles/nature23474',urlLabel:'Publisher (Nature)',
  },
  {
    category:'Quantum ML',
    title:'An introduction to quantum machine learning',
    authors:'Schuld, M., Sinayskiy, I., & Petruccione, F.',
    year:'2015',venue:'Contemporary Physics 56(2), 172–185',
    why:'Systematic overview of QML approaches and their technical foundations.',
    url:'https://doi.org/10.1080/00107514.2014.964942',urlLabel:'DOI',
  },
  {
    category:'Quantum ML',
    title:'Supervised learning with quantum-enhanced feature spaces',
    authors:'Havlíček, V., Córcoles, A.D., Temme, K., et al.',
    year:'2019',venue:'Nature 567, 209–212',
    why:'Introduces variational quantum classifiers and quantum feature spaces — the quantum classification concepts the platform’s quantum models build on.',
    url:'https://www.nature.com/articles/s41586-019-0980-2',urlLabel:'Publisher (Nature)',
  },
  {
    category:'Hybrid QML',
    title:'Quantum circuit learning',
    authors:'Mitarai, K., Negoro, M., Kitagawa, M., & Fujii, K.',
    year:'2018',venue:'Physical Review A 98, 032309',
    why:'Proposes a classical–quantum hybrid algorithm for near-term processors — the hybrid training pattern the platform follows.',
    url:'https://link.aps.org/doi/10.1103/PhysRevA.98.032309',urlLabel:'DOI',
  },
  {
    category:'Hybrid QML',
    title:'Circuit-centric quantum classifiers',
    authors:'Schuld, M., Bocharov, A., Svore, K.M., & Wiebe, N.',
    year:'2020',venue:'Physical Review A 101, 032308',
    why:'Formalizes circuit-centric quantum classifiers — directly relevant to the platform’s quantum classification models.',
    url:'https://link.aps.org/doi/10.1103/PhysRevA.101.032308',urlLabel:'DOI',
  },
  {
    category:'Hybrid QML',
    title:'Barren plateaus in quantum neural network training landscapes',
    authors:'McClean, J.R., Boixo, S., Smelyanskiy, V.N., Babbush, R., & Neven, H.',
    year:'2018',venue:'Nature Communications 9, 4812',
    why:'Characterizes training challenges in quantum neural networks — motivating controlled evaluation rather than assuming trainability.',
    url:'https://www.nature.com/articles/s41467-018-07090-4',urlLabel:'Publisher (Nature Communications)',
  },
  {
    category:'Healthcare QML',
    title:'The Potential of Quantum Computing and Machine Learning to Advance Clinical Research and Change the Practice of Medicine',
    authors:'Solenov, D., Brieler, J., & Scherrer, J.F.',
    year:'2018',venue:'Missouri Medicine 115(5), 463–467',
    why:'Healthcare-focused perspective on how quantum computing and ML could advance clinical research — motivates the biomedical QML research domain.',
    url:'https://pubmed.ncbi.nlm.nih.gov/30385997/',urlLabel:'PubMed',
  },
  {
    category:'Healthcare QML',
    title:'The state of quantum computing applications in health and medicine',
    authors:'Flöther, F.F.',
    year:'2023',venue:'arXiv:2301.09106 · also in Research Directions: Quantum Technologies (Cambridge)',
    why:'Reviews proof-of-concept quantum computing applications in health and medicine — establishes the healthcare QML research context.',
    url:'https://arxiv.org/abs/2301.09106',urlLabel:'arXiv',
  },
  {
    category:'Explainability',
    title:'A Unified Approach to Interpreting Model Predictions',
    authors:'Lundberg, S.M., & Lee, S.-I.',
    year:'2017',venue:'Advances in Neural Information Processing Systems 30 (NeurIPS 2017)',
    why:'Introduces SHAP, the feature-attribution method underpinning the platform’s model-level explainability.',
    url:'https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html',urlLabel:'Proceedings (NeurIPS)',
  },
];

function ThemeCard({category,description}:{category:Category;description:string}){
  return <div className="rounded-xl border border-[#D8E2EF] bg-white p-4">
    <div className="flex items-center gap-2">
      <span className="grid size-8 place-items-center rounded-lg border border-[#D8E2EF] bg-[#F7FAFD] text-[#102A5C]" aria-hidden="true">{categoryIcon[category]}</span>
      <Badge tone={categoryTone[category]}>{category}</Badge>
    </div>
    <p className="mt-2 text-xs leading-relaxed text-[#56657D]">{description}</p>
  </div>;
}

function ReferenceCard({reference}:{reference:Reference}){
  return <article className="flex flex-col rounded-2xl border border-[#D8E2EF] bg-white p-4">
    <div className="flex items-start justify-between gap-2">
      <Badge tone={categoryTone[reference.category]}>{reference.category}</Badge>
      <span className="shrink-0 text-[10px] font-semibold text-[#56657D]">{reference.year}</span>
    </div>
    <h3 className="mt-2 text-sm font-semibold leading-snug text-[#102A5C]">{reference.title}</h3>
    <div className="mt-1 flex items-center gap-1.5 text-[10px] text-[#56657D]"><FileText size={11} aria-hidden="true"/><span>{reference.authors}</span></div>
    <div className="mt-0.5 text-[10px] italic text-[#56657D]">{reference.venue}</div>
    <p className="mt-2 text-xs leading-relaxed text-[#56657D]"><span className="font-semibold text-[#102A5C]">Why it matters: </span>{reference.why}</p>
    <div className="mt-3 pt-3">
      <a className="btn btn-outline text-xs" href={reference.url} target="_blank" rel="noopener noreferrer">{reference.urlLabel}<ExternalLink size={13}/></a>
    </div>
  </article>;
}

function ClaimBlock({tone,title,items}:{tone:'blue'|'amber';title:string;items:string[]}){
  const style=tone==='blue'?'border-[#1769E0]/20 bg-[#1769E0]/[0.035]':'border-[#18B6C9]/25 bg-[#18B6C9]/[0.045]';
  return <div className={'rounded-2xl border p-4 '+style}>
    <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">{title}</div>
    <ul className="mt-2 space-y-1.5">
      {items.map(item=><li key={item} className="flex gap-2 text-xs leading-relaxed text-[#56657D]"><ShieldCheck size={13} className="mt-0.5 shrink-0 text-[#159A70]" aria-hidden="true"/><span>{item}</span></li>)}
    </ul>
  </div>;
}

export function ResearchBasisExperience({datasetName,hybridDetailPath}:ResearchBasisExperienceProps){
  const scrollTo=(id:string)=>document.getElementById(id)?.scrollIntoView({behavior:'smooth',block:'start'});

  const literatureSupports=[
    'Hybrid QML is an active research direction.',
    'Healthcare QML remains an emerging research area.',
    'Near-term quantum hardware constraints motivate hybrid and simulated workflows.',
    'Explainability is important for trustworthy ML workflows.',
    'Benchmarking against classical baselines is necessary to contextualize QML results.',
  ];
  const literatureDoesNotProve=[
    'The literature does not establish quantum advantage for the Early Stage Diabetes dataset.',
    'Simulation-based results do not establish clinical deployment readiness.',
    'A result on one disease/dataset does not generalize to all diseases.',
    'Published QML performance does not imply real-hardware superiority.',
  ];
  const researchToImplementation=[
    ['Hybrid QML',modelLabels.hybrid_pennylane_torch],
    ['Classical baselines',`${modelLabels.logistic_regression} / ${modelLabels.svm} / ${modelLabels.random_forest}`],
    ['Quantum models',`${modelLabels.vqc} / ${modelLabels.qsvc} / ${modelLabels.qnn}`],
    ['Explainability','SHAP pathway'],
    ['Evaluation','Controlled seven-model comparison'],
    ['Research data','Early Stage Diabetes flagship'],
    ['Evidence','Benchmark + robustness + provenance'],
  ];
  const establishedMethods=[
    'Logistic Regression','SVM','Random Forest',
    'VQC / QSVC / QNN methodologies','PennyLane','PyTorch',
    'SHAP','Standard evaluation metrics',
  ];
  const entangleXIntegration=[
    'Early Stage Diabetes flagship workflow',
    'PennyLane + PyTorch hybrid model implementation',
    'Seven-model controlled comparison',
    'Sensitivity-first evaluation',
    'Integrated research workflow',
    'Evidence / provenance packaging',
    'Judge-first verified demo experience',
  ];
  const futureWork=[
    'Real quantum hardware evaluation',
    'Larger / multi-site datasets',
    'External validation',
    'Broader disease coverage',
    'Prospective clinical evaluation',
    'Cost / performance analysis',
    'Noise-aware hardware experiments',
  ];

  return <section className="mt-5" aria-label="Research basis and references">
    <Card
      className="border-[#102A5C]/15 bg-white"
      title="RESEARCH BASIS & VERIFIED REFERENCES"
      description="Established methods → research challenge → EntangleX design response → implemented prototype → controlled evaluation → limitations & future work"
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="blue">SIH26139</Badge>
        <Badge tone="purple">{datasetName||'Early Stage Diabetes Risk Prediction'}</Badge>
        <Badge tone="green">VERIFIED SOURCES · CONTRIBUTION FRAMING</Badge>
      </div>

      <div className="mt-4 rounded-2xl border border-[#D8E2EF] bg-[#F7FAFD] p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#102A5C]"><Microscope size={15} className="text-[#102A5C]"/> RESEARCH BASIS</div>
        <p className="mt-2 max-w-4xl text-sm leading-relaxed text-[#102A5C]">EntangleX Q-Health builds on established work in quantum machine learning, hybrid quantum-classical models, biomedical ML, and model explainability. The contribution is the integration of these methods into a controlled, evidence-oriented research workflow — not the invention of the underlying methods.</p>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ThemeCard category="Quantum ML" description="Foundations and motivation for investigating quantum-enhanced representations."/>
        <ThemeCard category="Hybrid QML" description="Why combine classical processing with trainable quantum circuits."/>
        <ThemeCard category="Healthcare QML" description="Why biomedical disease-risk tasks are a relevant QML research domain."/>
        <ThemeCard category="Explainability" description="Why feature-level model explanation matters for trust."/>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">SELECTED REFERENCES</div>
        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {references.map(reference=><ReferenceCard key={reference.title} reference={reference}/>)}
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <ClaimBlock tone="blue" title="WHAT THE LITERATURE SUPPORTS" items={literatureSupports}/>
        <ClaimBlock tone="amber" title="WHAT THE LITERATURE DOES NOT PROVE" items={literatureDoesNotProve}/>
      </div>

      <div className="mt-5">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">FROM RESEARCH TO IMPLEMENTATION</div>
        <div className="table-wrap mt-3 overflow-x-auto">
          <table className="data-table min-w-[720px]">
            <thead><tr><th>Research basis</th><th>EntangleX implementation</th></tr></thead>
            <tbody>
              {researchToImplementation.map(([basis,implementation])=><tr key={basis}>
                <td><strong className="text-xs">{basis}</strong></td>
                <td className="text-xs muted">{implementation}</td>
              </tr>)}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">This table demonstrates design grounding, not proof of correctness — a cited paper does not validate the entire EntangleX implementation.</p>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-[#6946D9]/25 bg-[#6946D9]/[0.045] p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><Layers3 size={14} className="text-[#6946D9]"/> OUR CONTRIBUTION</div>
          <p className="mt-2 text-sm leading-relaxed text-[#102A5C]">Integration, implementation, controlled evaluation, and evidence-oriented presentation of a hybrid QML research workflow — combining classical baselines, quantum models, a PennyLane + PyTorch hybrid, seven-model comparison, sensitivity-first analysis, SHAP explanation, and evidence/provenance for the Early Stage Diabetes flagship.</p>
        </div>
        <div className="rounded-2xl border border-[#18B6C9]/25 bg-[#18B6C9]/[0.045] p-4">
          <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><Workflow size={14}/> ESTABLISHED vs OUR WORK</div>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            <div>
              <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">ESTABLISHED METHODS</div>
              <ul className="mt-1 space-y-1">{establishedMethods.map(item=><li key={item} className="text-[11px] leading-relaxed text-[#56657D]">{item}</li>)}</ul>
            </div>
            <div>
              <div className="text-[9px] font-semibold tracking-[0.12em] text-[#56657D]">ENTANGLEX INTEGRATION</div>
              <ul className="mt-1 space-y-1">{entangleXIntegration.map(item=><li key={item} className="text-[11px] leading-relaxed text-[#102A5C]">{item}</li>)}</ul>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-xl border border-[#159A70]/25 bg-[#159A70]/[0.035] p-4">
          <div className="text-[10px] font-semibold tracking-[0.14em] text-[#159A70]">WHAT IS OUR CONTRIBUTION?</div>
          <p className="mt-1.5 text-xs leading-relaxed text-[#102A5C]">Integration, implementation, controlled evaluation, and presentation of a hybrid QML research workflow.</p>
        </div>
        <div className="rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] p-4">
          <div className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">WHAT IS NOT OUR CLAIM?</div>
          <p className="mt-1.5 text-xs leading-relaxed text-[#56657D]">We do not claim to have invented QML, SHAP, PennyLane, PyTorch, quantum circuits, or quantum advantage.</p>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-[#D8E2EF] bg-white p-4">
        <div className="flex items-center gap-2 text-[10px] font-semibold tracking-[0.14em] text-[#56657D]"><CheckCircle2 size={14} className="text-[#159A70]"/> FUTURE WORK — NOT CURRENT CAPABILITIES</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {futureWork.map(item=><Badge key={item} tone="amber">{item}</Badge>)}
        </div>
        <div className="mt-3 grid gap-2 text-xs leading-relaxed text-[#56657D] sm:grid-cols-2">
          <div><span className="font-semibold text-[#102A5C]">Current implementation:</span> local quantum simulation, research prototype.</div>
          <div><span className="font-semibold text-[#102A5C]">Future direction:</span> hardware-backed evaluation and clinical validation (only with appropriate regulatory evidence).</div>
        </div>
        <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">Research prototype, not clinical validation, diagnosis, or treatment guidance. Hardware integration is not claimed as already available.</p>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={()=>scrollTo('hybrid-architecture')}><Layers3 size={14}/>View Hybrid Architecture</Button>
        <Button variant="outline" onClick={()=>scrollTo('why-hybrid')}><BrainCircuit size={14}/>Why Hybrid</Button>
        <Link className="btn btn-primary" to="/comparison"><FlaskConical size={14}/>View 7-Model Comparison</Link>
        <Link className="btn btn-outline" to="/explainability"><Sparkles size={14}/>View SHAP Evidence</Link>
        {hybridDetailPath&&<Link className="btn btn-outline" to={hybridDetailPath}><GitBranch size={14}/>Open hybrid model detail</Link>}
      </div>

      <div className="mt-4 flex items-start gap-2 rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] p-3">
        <Database size={14} className="mt-0.5 shrink-0 text-[#56657D]" aria-hidden="true"/>
        <p className="text-[11px] leading-relaxed text-[#56657D]">Evidence contribution: verified demo artifacts, benchmark evidence, robustness evidence, prediction evidence, preprocessing evidence, provenance, and integrity checks — reported as persisted evidence, not as reproducibility beyond what the package establishes.</p>
      </div>

      <Notice tone="green">Research prototype. Empirical benchmark evidence is reported transparently; no quantum advantage, clinical validation, or real quantum hardware is claimed. Reference metadata was verified before inclusion.</Notice>
    </Card>
  </section>;
}
