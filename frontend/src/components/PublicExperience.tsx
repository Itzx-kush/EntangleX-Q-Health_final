import {useEffect,useState,type CSSProperties} from 'react';
import {ArrowDown,ArrowRight,ArrowUpRight,Atom,BrainCircuit,Database,Menu,ShieldCheck,X} from 'lucide-react';
import {InteractiveQuantumField} from './InteractiveQuantumField';
import {ParticleText} from './ParticleText';

type PublicExperienceProps={
  onRequestAccess:(destination?:string)=>void;
};

const researchSteps=[
  ['01','Research','Frame a reproducible biomedical research question.'],
  ['02','Evidence','Keep provenance, quality checks and limitations visible.'],
  ['03','Modeling','Evaluate classical, quantum and hybrid approaches.'],
  ['04','Evaluation','Compare measured outputs under shared conditions.'],
  ['05','Interpretation','Connect model behavior to bounded evidence.'],
] as const;

const pipelineSteps=[
  'Data',
  'Preprocessing',
  'Feature engineering',
  'Dimensionality reduction',
  'Modeling',
  'Evaluation',
] as const;

const platformFlow=[
  'Data',
  'Preprocess',
  'Feature engineering',
  'Hybrid modeling',
  'Evaluation',
  'Explainability',
  'Research decision support',
] as const;

export function PublicExperience({onRequestAccess}:PublicExperienceProps){
  const [menuOpen,setMenuOpen]=useState(false);

  useEffect(()=>{
    const elements=Array.from(document.querySelectorAll<HTMLElement>('[data-public-reveal]'));
    if(!('IntersectionObserver'in window)){
      elements.forEach(element=>element.classList.add('is-visible'));
      return;
    }
    const observer=new IntersectionObserver(entries=>{
      entries.forEach(entry=>{
        if(entry.isIntersecting){
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },{rootMargin:'0px 0px -10% 0px',threshold:.12});
    elements.forEach(element=>observer.observe(element));
    return()=>observer.disconnect();
  },[]);

  useEffect(()=>{
    if(!menuOpen)return;
    const close=(event:KeyboardEvent)=>{if(event.key==='Escape')setMenuOpen(false)};
    window.addEventListener('keydown',close);
    return()=>window.removeEventListener('keydown',close);
  },[menuOpen]);

  const requestAccess=(destination='/')=>{
    setMenuOpen(false);
    onRequestAccess(destination);
  };

  return <div className="public-experience">
    <div className="public-background" aria-hidden="true">
      <span className="public-glow public-glow-a"/>
      <span className="public-glow public-glow-b"/>
      <span className="public-background-node node-a"/>
      <span className="public-background-node node-b"/>
      <span className="public-background-node node-c"/>
    </div>

    <header className="public-header">
      <a className="public-brand" href="#top" aria-label="EntangleX Q-Health home" onClick={()=>setMenuOpen(false)}>
        <img src="/entanglex-logo-dark.svg" alt="EntangleX"/>
        <span>Q-HEALTH</span>
      </a>
      <nav className="public-nav" aria-label="Public navigation">
        <a href="#research">Research</a>
        <a href="#platform">Platform</a>
        <a href="#demonstration">Demonstration</a>
        <a href="#about">About</a>
      </nav>
      <button className="public-header-cta" type="button" onClick={()=>requestAccess('/')}>
        Sign in <ArrowUpRight size={14}/>
      </button>
      <button
        className="public-menu-toggle"
        type="button"
        aria-expanded={menuOpen}
        aria-controls="public-mobile-navigation"
        aria-label={menuOpen?'Close navigation':'Open navigation'}
        onClick={()=>setMenuOpen(value=>!value)}
      >
        {menuOpen?<X size={19}/>:<Menu size={19}/>}
      </button>
      {menuOpen&&<nav id="public-mobile-navigation" className="public-mobile-nav" aria-label="Mobile public navigation">
        <a href="#research" onClick={()=>setMenuOpen(false)}>Research</a>
        <a href="#platform" onClick={()=>setMenuOpen(false)}>Platform</a>
        <a href="#demonstration" onClick={()=>setMenuOpen(false)}>Demonstration</a>
        <a href="#about" onClick={()=>setMenuOpen(false)}>About</a>
        <button type="button" onClick={()=>requestAccess('/')}>Sign in <ArrowRight size={15}/></button>
      </nav>}
    </header>

    <main id="top">
      <section className="public-hero public-shell" aria-labelledby="public-hero-title">
        <InteractiveQuantumField/>
        <div className="public-hero-copy" data-public-reveal>
          <p className="public-eyebrow"><span>ENTANGLEX</span> Biomedical research platform</p>
          <ParticleText id="public-hero-title" text="Hybrid quantum–classical intelligence for biomedical research."/>
          <p className="public-hero-intro">A research prototype for moving from traceable biomedical data to measured model evidence, interpretation and reproducible experimentation.</p>
          <div className="public-hero-actions">
            <button className="public-button is-primary" type="button" onClick={()=>requestAccess('/')}>
              Explore the Research Workspace <ArrowRight size={16}/>
            </button>
            <button className="public-button is-secondary" type="button" onClick={()=>requestAccess('/')}>
              Sign in
            </button>
          </div>
          <p className="public-boundary"><ShieldCheck size={14}/> Research prototype · not for clinical diagnosis</p>
        </div>

        <div className="public-hero-system" data-public-reveal aria-label="Conceptual hybrid intelligence system">
          <div className="public-system-grid" aria-hidden="true"/>
          <div className="public-system-orbit orbit-one" aria-hidden="true"/>
          <div className="public-system-orbit orbit-two" aria-hidden="true"/>
          <div className="public-system-node system-node-a" aria-hidden="true"/>
          <div className="public-system-node system-node-b" aria-hidden="true"/>
          <div className="public-system-core">
            <img src="/entanglex-mark.svg" alt="" aria-hidden="true"/>
            <span>HYBRID CORE</span>
          </div>
          <div className="public-system-label label-classical"><span>CLASSICAL</span><strong>Measured baselines</strong></div>
          <div className="public-system-label label-quantum"><span>QUANTUM</span><strong>Simulator research</strong></div>
          <div className="public-system-caption"><span>Data</span><ArrowRight size={12}/><span>Evidence</span><ArrowRight size={12}/><span>Interpretation</span></div>
        </div>

        <a className="public-scroll-cue" href="#research"><span>Explore the research story</span><ArrowDown size={14}/></a>
      </section>

      <section id="research" className="public-section public-shell">
        <SectionHeading number="01" label="Research" title="Evidence before assertion." copy="EntangleX keeps the research pathway visible—from the question being studied to the evidence used for interpretation."/>
        <div className="public-research-sequence" data-public-reveal>
          {researchSteps.map(([number,title,copy])=><article key={number}>
            <span>{number}</span>
            <h3>{title}</h3>
            <p>{copy}</p>
          </article>)}
        </div>
      </section>

      <section id="platform" className="public-section public-shell">
        <SectionHeading number="02" label="Data" title="A traceable path from data to evaluation." copy="The public story mirrors the existing research workflow without reproducing any processing or calculation in the browser."/>
        <div className="public-pipeline" data-public-reveal>
          {pipelineSteps.map((step,index)=><div className="public-pipeline-step" key={step}>
            <span>{String(index+1).padStart(2,'0')}</span>
            <strong>{step}</strong>
            {index<pipelineSteps.length-1&&<ArrowRight aria-hidden="true"/>}
          </div>)}
        </div>
        <p className="public-section-note" data-public-reveal>All execution, transformation and scientific evidence remain inside the existing EntangleX research application.</p>
      </section>

      <section className="public-section public-shell">
        <SectionHeading number="03" label="Hybrid intelligence" title="Two model families. One controlled research workflow." copy="Classical and quantum approaches are evaluated as research methods under shared evidence boundaries—not as unsupported claims of advantage."/>
        <div className="public-hybrid-grid" data-public-reveal>
          <article className="public-model-panel">
            <div className="public-model-panel-head"><Database size={18}/><span>CLASSICAL ML</span></div>
            <h3>Established research baselines</h3>
            <div className="public-model-list"><span>Logistic Regression</span><span>SVM</span><span>Random Forest</span></div>
          </article>
          <div className="public-hybrid-bridge" aria-hidden="true">
            <span/>
            <strong>+</strong>
            <span/>
          </div>
          <article className="public-model-panel is-quantum">
            <div className="public-model-panel-head"><Atom size={18}/><span>QUANTUM ML</span></div>
            <h3>Simulator-based quantum research</h3>
            <div className="public-model-list"><span>VQC</span><span>QSVC</span><span>QNN</span><span>PennyLane + PyTorch Hybrid</span></div>
          </article>
        </div>
      </section>

      <section className="public-section public-shell">
        <SectionHeading number="04" label="Explainability" title="Prediction research connected to interpretable evidence." copy="EntangleX presents model influence with its method, scope and limitations so that interpretation remains bounded and scientifically responsible."/>
        <div className="public-explain-grid" data-public-reveal>
          <div className="public-evidence-map" aria-hidden="true">
            <span className="evidence-axis"/>
            <i style={{'--signal':'72%'} as CSSProperties}/><i style={{'--signal':'46%'} as CSSProperties}/><i style={{'--signal':'61%'} as CSSProperties}/><i style={{'--signal':'34%'} as CSSProperties}/><i style={{'--signal':'55%'} as CSSProperties}/>
          </div>
          <div className="public-evidence-cards">
            <article><BrainCircuit size={17}/><span><strong>Feature influence</strong><small>Measured model behavior, not biological causation</small></span></article>
            <article><ShieldCheck size={17}/><span><strong>Method context</strong><small>Explanation scope remains visible</small></span></article>
            <article><Atom size={17}/><span><strong>Research limitations</strong><small>Quantum and clinical boundaries stay explicit</small></span></article>
          </div>
        </div>
      </section>

      <section id="demonstration" className="public-section public-shell">
        <div className="public-demo" data-public-reveal>
          <div className="public-demo-copy">
            <p className="public-eyebrow"><span>05</span> Verified demonstration</p>
            <h2>Early Stage Diabetes Risk Prediction</h2>
            <p>Explore the existing flagship research package across provenance, preprocessing, controlled model comparison, robustness, quantum evidence, explainability and representative research predictions.</p>
            <div className="public-demo-tags"><span>Precomputed evidence</span><span>Research benchmark</span><span>Not clinical diagnosis</span></div>
            <button className="public-button is-primary" type="button" onClick={()=>requestAccess('/demo')}>
              Explore the Verified Demonstration <ArrowRight size={16}/>
            </button>
          </div>
          <div className="public-demo-art" aria-label="Verified demonstration research pathway">
            <span className="public-demo-index">SIH / 26139</span>
            <div className="public-demo-rings" aria-hidden="true"><i/><i/><i/></div>
            <div className="public-demo-mark"><img src="/entanglex-mark.svg" alt="" aria-hidden="true"/><span>VERIFIED<br/>RESEARCH<br/>PATHWAY</span></div>
          </div>
        </div>
      </section>

      <section className="public-section public-shell">
        <SectionHeading number="06" label="Platform flow" title="One connected research environment." copy="The public experience introduces the pathway. The existing workspace remains responsible for every real operation and measured output."/>
        <div className="public-platform-flow" data-public-reveal>
          {platformFlow.map((step,index)=><div key={step}>
            <span>{String(index+1).padStart(2,'0')}</span>
            <strong>{step}</strong>
            {index<platformFlow.length-1&&<ArrowRight aria-hidden="true"/>}
          </div>)}
        </div>
      </section>

      <section id="about" className="public-final public-shell" data-public-reveal>
        <div>
          <p className="public-eyebrow"><span>07</span> Enter the platform</p>
          <h2>Enter the EntangleX Research Workspace.</h2>
          <p>Explore the existing research environment, authenticated workspace features and verified workflows.</p>
        </div>
        <div className="public-final-actions">
          <button className="public-button is-primary" type="button" onClick={()=>requestAccess('/')}>Enter Workspace <ArrowRight size={16}/></button>
          <button className="public-button is-secondary" type="button" onClick={()=>requestAccess('/')}>Sign in</button>
        </div>
      </section>
    </main>

    <footer className="public-footer public-shell">
      <div className="public-brand"><img src="/entanglex-logo-dark.svg" alt="EntangleX"/><span>Q-HEALTH</span></div>
      <p>Hybrid quantum–classical biomedical research platform.</p>
      <p>Research prototype · no clinical diagnosis</p>
    </footer>
  </div>;
}

function SectionHeading({number,label,title,copy}:{number:string;label:string;title:string;copy:string}){
  return <div className="public-section-heading" data-public-reveal>
    <p className="public-eyebrow"><span>{number}</span> {label}</p>
    <div><h2>{title}</h2><p>{copy}</p></div>
  </div>;
}
