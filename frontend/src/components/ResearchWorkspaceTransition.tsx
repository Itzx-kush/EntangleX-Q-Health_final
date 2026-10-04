import {useEffect,useLayoutEffect,useRef,type CSSProperties} from 'react';
import gsap from 'gsap';
import './ResearchWorkspaceTransition.css';

const particles=Array.from({length:18},(_,index)=>{
  const angle=(index/18)*Math.PI*2;
  const radiusX=24+(index%4)*7;
  const radiusY=18+(index%3)*8;
  return {
    x:String((Math.cos(angle)*radiusX).toFixed(2))+'vw',
    y:String((Math.sin(angle)*radiusY).toFixed(2))+'vh',
  };
});

const networkNodes=[
  {left:'12%',top:'31%'},{left:'19%',top:'61%'},{left:'29%',top:'21%'},{left:'33%',top:'74%'},
  {left:'67%',top:'24%'},{left:'75%',top:'66%'},{left:'86%',top:'35%'},{left:'81%',top:'79%'},
  {left:'8%',top:'76%'},{left:'90%',top:'57%'},{left:'42%',top:'16%'},{left:'58%',top:'82%'},
];

const pipelineStages=['DATA','PREPROCESS','FEATURE SPACE','MODELING','EVIDENCE'];

type Props={guest:boolean;onComplete:()=>void};

export function ResearchWorkspaceTransition({guest,onComplete}:Props){
  const rootRef=useRef<HTMLDivElement|null>(null);
  const onCompleteRef=useRef(onComplete);

  useEffect(()=>{onCompleteRef.current=onComplete},[onComplete]);

  useLayoutEffect(()=>{
    const root=rootRef.current;
    if(!root)return;
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const ctx=gsap.context(()=>{
      const timeline=gsap.timeline({
        defaults:{overwrite:'auto'},
        onComplete:()=>onCompleteRef.current(),
      });
      const paths=Array.from(root.querySelectorAll<SVGPathElement>('.rwt-path'));
      const particleNodes=Array.from(root.querySelectorAll<HTMLElement>('.rwt-particle'));

      paths.forEach(path=>{
        const length=path.getTotalLength();
        gsap.set(path,{strokeDasharray:length,strokeDashoffset:length});
      });

      gsap.set(root,{opacity:1});
      gsap.set('.rwt-copy,.rwt-pipeline,.rwt-core,.rwt-network,.rwt-signal',{opacity:0});
      gsap.set('.rwt-core',{scale:.82});
      gsap.set('.rwt-core-ring',{scale:.68,opacity:0});
      gsap.set('.rwt-feature-trace',{scaleX:0,transformOrigin:'50% 50%',opacity:0});
      gsap.set('.rwt-network-node',{scale:.4,opacity:0});
      gsap.set('.rwt-path-label',{opacity:0,y:8});
      gsap.set('.rwt-particle',{scale:.35,opacity:0});

      if(reduced){
        timeline
          .to('.rwt-field',{opacity:1,duration:.06})
          .to('.rwt-core',{opacity:1,scale:1,duration:.12},'<')
          .to('.rwt-core-ring',{scale:1,opacity:1,duration:.16},'<')
          .to('.rwt-copy,.rwt-pipeline',{opacity:1,y:0,duration:.14,stagger:.015})
          .to(root,{opacity:0,duration:.12,ease:'power1.in',delay:.08});
        return;
      }

      timeline
        .to('.rwt-field',{opacity:1,duration:.18,ease:'power2.out'})
        .to('.rwt-particle',{scale:1,opacity:.48,duration:.22,stagger:{each:.012,from:'edges'},ease:'power2.out'},'-=.08')
        .to(particleNodes,{x:0,y:0,scale:.46,opacity:0,duration:.54,stagger:{each:.014,from:'edges'},ease:'power3.in'},'-=.06')
        .to('.rwt-network',{opacity:1,duration:.22},'-=.28')
        .to('.rwt-network-node',{scale:1,opacity:.52,duration:.32,stagger:{each:.018,from:'random'},ease:'back.out(2)'},'-=.16')
        .to('.rwt-copy',{opacity:1,y:0,duration:.3,ease:'power3.out'},'-=.3')
        .to('.rwt-core',{opacity:1,scale:1,duration:.48,ease:'expo.out'},'-=.22')
        .to('.rwt-core-ring',{scale:1,opacity:1,duration:.5,stagger:.05,ease:'expo.out'},'-=.42')
        .to('.rwt-feature-trace',{scaleX:1,opacity:1,duration:.34,stagger:.05,ease:'power3.out'},'-=.28')
        .to(paths,{strokeDashoffset:0,duration:.5,stagger:.07,ease:'power2.inOut'},'-=.36')
        .to('.rwt-path-label',{opacity:1,y:0,duration:.24,stagger:.06,ease:'power2.out'},'-=.24')
        .to('.rwt-pipeline',{opacity:1,y:0,duration:.3,ease:'power3.out'},'-=.18')
        .to('.rwt-pipeline-step',{opacity:1,y:0,duration:.26,stagger:.06,ease:'power3.out'},'-=.18')
        .to('.rwt-copy',{opacity:0,y:-8,duration:.22,ease:'power2.in'},'+=.12')
        .to('.rwt-pipeline,.rwt-path-label,.rwt-network',{opacity:0,duration:.22,ease:'power2.in'},'-=.14')
        .to('.rwt-core-ring',{scale:1.06,opacity:.24,duration:.22,ease:'power2.in'},'-=.1')
        .to('.rwt-core',{scale:1.02,opacity:0,duration:.26,ease:'power2.in'},'-=.16')
        .to(root,{opacity:0,duration:.18,ease:'power2.in'},'-=.12');
    },rootRef);

    return()=>ctx.revert();
  },[]);

  return <div ref={rootRef} className={'research-workspace-transition '+(guest?'is-guest':'is-authenticated')} role="status" aria-live="polite" aria-busy="true">
    <div className="rwt-field" aria-hidden="true">
      <div className="rwt-grid"/>
      <div className="rwt-grid-glow"/>
      <div className="rwt-horizon"/>
      <div className="rwt-particle-field">
        {particles.map((particle,index)=><i key={index} className="rwt-particle" style={{'--rwt-x':particle.x,'--rwt-y':particle.y} as CSSProperties}/>)}
      </div>
    </div>
    <div className="rwt-network" aria-hidden="true">
      {networkNodes.map((node,index)=><i key={index} className="rwt-network-node" style={{left:node.left,top:node.top}}/>)}
      <span className="rwt-network-line line-a"/><span className="rwt-network-line line-b"/><span className="rwt-network-line line-c"/>
      <span className="rwt-network-line line-d"/><span className="rwt-network-line line-e"/><span className="rwt-network-line line-f"/>
    </div>
    <svg className="rwt-path-map" viewBox="0 0 1000 1000" preserveAspectRatio="none" aria-hidden="true">
      <path className="rwt-path rwt-path-classical" d="M500 500 C430 470 340 428 185 346"/>
      <path className="rwt-path rwt-path-quantum" d="M500 500 C570 530 675 594 835 704"/>
      <path className="rwt-path rwt-path-evidence" d="M500 500 C505 585 500 690 500 846"/>
    </svg>
    <div className="rwt-path-label rwt-label-classical" aria-hidden="true">CLASSICAL COMPUTATION</div>
    <div className="rwt-path-label rwt-label-quantum" aria-hidden="true">QUANTUM COMPUTATION</div>
    <div className="rwt-core" aria-hidden="true">
      <span className="rwt-core-aura"/><span className="rwt-core-ring ring-a"/><span className="rwt-core-ring ring-b"/><span className="rwt-core-ring ring-c"/>
      <div className="rwt-core-mark"><img src="/entanglex-mark.svg" alt=""/></div><span className="rwt-core-pulse"/>
    </div>
    <div className="rwt-signal" aria-hidden="true">
      <span className="rwt-feature-trace trace-a"/><span className="rwt-feature-trace trace-b"/><span className="rwt-feature-trace trace-c"/><span className="rwt-feature-trace trace-d"/>
    </div>
    <div className="rwt-copy">
      <span className="rwt-eyebrow">{guest?'GUEST ACCESS CONFIRMED':'ACCESS CONFIRMED'}</span>
      <h2>Entering the research environment.</h2>
      <p>Preparing the existing EntangleX research workspace.</p>
    </div>
    <div className="rwt-pipeline">
      {pipelineStages.map(stage=><div className="rwt-pipeline-step" key={stage}><span className="rwt-pipeline-dot"/><span>{stage}</span></div>)}
    </div>
  </div>;
}