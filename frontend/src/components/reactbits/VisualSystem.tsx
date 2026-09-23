import {useEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';

export function AmbientBackground(){return <div className="rb-ambient" aria-hidden="true"><div className="rb-aurora rb-aurora-a"/><div className="rb-aurora rb-aurora-b"/><div className="rb-grid"/><div className="rb-particles">{Array.from({length:18},(_,i)=><i key={i} style={{'--i':i} as CSSProperties}/>)}</div></div>}

export function Reveal({children,className='',delay=0}:{children:ReactNode;className?:string;delay?:number}){return <div className={`rb-reveal ${className}`} style={{'--rb-delay':`${delay}ms`} as CSSProperties}>{children}</div>}
export function AnimatedSection({children,className='',delay=0}:{children:ReactNode;className?:string;delay?:number}){return <Reveal className={`rb-section ${className}`} delay={delay}>{children}</Reveal>}

export function BlurText({children,className=''}:{children:ReactNode;className?:string}){return <span className={`rb-blur-text ${className}`}>{children}</span>}
export function GradientText({children,className=''}:{children:ReactNode;className?:string}){return <span className={`rb-gradient-text ${className}`}>{children}</span>}
export function ShinyText({children,className=''}:{children:ReactNode;className?:string}){return <span className={`rb-shiny-text ${className}`}>{children}</span>}

export function CountUp({value}:{value:ReactNode}){const [shown,setShown]=useState(value);const ref=useRef<HTMLSpanElement>(null);useEffect(()=>{const text=String(value);const n=Number(text.replace(/,/g,''));if(!Number.isFinite(n)){setShown(value);return}const reduce=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;if(reduce){setShown(value);return}let frame=0;const start=performance.now();const tick=(now:number)=>{const p=Math.min(1,(now-start)/650);setShown(Math.round(n*p).toLocaleString());if(p<1)frame=requestAnimationFrame(tick)};frame=requestAnimationFrame(tick);return()=>cancelAnimationFrame(frame)},[value]);return <span ref={ref} className="rb-count">{shown}</span>}

export function SpotlightPanel({children,className='',tone='blue'}:{children:ReactNode;className?:string;tone?:'blue'|'teal'|'violet'}){const ref=useRef<HTMLDivElement>(null);return <div ref={ref} className={`rb-spotlight rb-tone-${tone} ${className}`} onPointerMove={e=>{const r=ref.current?.getBoundingClientRect();if(r)ref.current?.style.setProperty('--rb-x',`${e.clientX-r.left}px`);if(r)ref.current?.style.setProperty('--rb-y',`${e.clientY-r.top}px`)}}>{children}</div>}
export function GlowCard({children,className=''}:{children:ReactNode;className?:string}){return <div className={`rb-glow-card ${className}`}>{children}</div>}
export function BorderGlow({children,className=''}:{children:ReactNode;className?:string}){return <div className={`rb-border-glow ${className}`}>{children}</div>}
export function GlareHover({children,className=''}:{children:ReactNode;className?:string}){return <div className={`rb-glare ${className}`}>{children}</div>}
export function HoverLift({children,className=''}:{children:ReactNode;className?:string}){return <div className={`rb-hover-lift ${className}`}>{children}</div>}

export function Magnet({children,className=''}:{children:ReactNode;className?:string}){const ref=useRef<HTMLDivElement>(null);return <div ref={ref} className={`rb-magnet ${className}`} onPointerMove={e=>{const node=ref.current;const r=node?.getBoundingClientRect();if(r&&node)node.style.transform=`translate(${(e.clientX-r.left-r.width/2)*.08}px, ${(e.clientY-r.top-r.height/2)*.08}px)`}} onPointerLeave={()=>{if(ref.current)ref.current.style.transform=''}}>{children}</div>}
export function ClickSpark({children,className=''}:{children:ReactNode;className?:string}){const [active,setActive]=useState(false);return <div className={`rb-click-spark ${active?'is-clicked':''} ${className}`} onPointerDown={()=>{setActive(false);requestAnimationFrame(()=>setActive(true))} } onAnimationEnd={()=>setActive(false)}>{children}</div>}

export function AnimatedMetric({label,value,detail,icon}:{label:string;value:ReactNode;detail?:string;icon?:ReactNode}){return <GlowCard className="rb-metric"><div className="rb-metric-top"><span className="metric-label">{label}</span>{icon&&<span className="rb-metric-icon">{icon}</span>}</div><strong className="metric-value"><CountUp value={value}/></strong>{detail&&<span className="metric-detail">{detail}</span>}</GlowCard>}
export function QuantumVisual(){return <div className="rb-quantum-visual" aria-hidden="true"><div className="rb-q-ring rb-q-ring-a"/><div className="rb-q-ring rb-q-ring-b"/><div className="rb-q-core"/><i/><i/><i/><i/></div>}
