import {useEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';

export function Reveal({children,className='',delay=0}:{children:ReactNode;className?:string;delay?:number}){
 const ref=useRef<HTMLDivElement>(null);
 const [visible,setVisible]=useState(false);
 useEffect(()=>{
  const el=ref.current;if(!el)return;
  const obs=new IntersectionObserver(([entry])=>{if(entry.isIntersecting){setVisible(true);obs.disconnect();}},{threshold:.08});
  obs.observe(el);return()=>obs.disconnect();
 },[]);
 return <div ref={ref} className={`rb-reveal ${visible?'is-visible':''} ${className}`} style={{'--rb-delay':`${delay}ms`} as CSSProperties}>{children}</div>;
}

export function BlurText({children,className='',delay=0}:{children:ReactNode;className?:string;delay?:number}){
 return <span className={`rb-blur-text ${className}`} style={{animationDelay:`${delay}ms`}}>{children}</span>;
}

export function SpotlightCard({children,className='',spotlightColor='rgba(25,118,210,.16)'}:{children:ReactNode;className?:string;spotlightColor?:string}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const el=ref.current;if(!el)return;
  const onMove=(e:PointerEvent)=>{const r=el.getBoundingClientRect();el.style.setProperty('--spotlight-x',`${e.clientX-r.left}px`);el.style.setProperty('--spotlight-y',`${e.clientY-r.top}px`);};
  el.addEventListener('pointermove',onMove);return()=>el.removeEventListener('pointermove',onMove);
 },[]);
 return <div ref={ref} className={`rb-spotlight ${className}`} style={{'--spotlight-color':spotlightColor} as CSSProperties}>{children}</div>;
}

export function BorderGlow({children,className=''}:{children:ReactNode;className?:string}){
 return <div className={`rb-border-glow ${className}`}><div className='rb-border-glow-inner'>{children}</div></div>;
}

export function Magnet({children,className='',strength=5}:{children:ReactNode;className?:string;strength?:number}){
 const ref=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const el=ref.current;if(!el)return;
  const onMove=(e:PointerEvent)=>{const r=el.getBoundingClientRect();const x=(e.clientX-(r.left+r.width/2))/r.width;const y=(e.clientY-(r.top+r.height/2))/r.height;el.style.transform=`translate3d(${x*strength}px,${y*strength}px,0)`;};
  const reset=()=>{el.style.transform='translate3d(0,0,0)'};
  el.addEventListener('pointermove',onMove);el.addEventListener('pointerleave',reset);
  return()=>{el.removeEventListener('pointermove',onMove);el.removeEventListener('pointerleave',reset);};
 },[strength]);
 return <div ref={ref} className={className} style={{transition:'transform .22s cubic-bezier(.22,1,.36,1)'}}>{children}</div>;
}

export function CountUp({to,duration=850,prefix='',suffix=''}:{to:number;duration?:number;prefix?:string;suffix?:string}){
 const [value,setValue]=useState(0);
 useEffect(()=>{let raf=0;const start=performance.now();const tick=(now:number)=>{const p=Math.min(1,(now-start)/duration);const eased=1-Math.pow(1-p,3);setValue(Math.round(to*eased));if(p<1)raf=requestAnimationFrame(tick);};raf=requestAnimationFrame(tick);return()=>cancelAnimationFrame(raf);},[to,duration]);
 return <>{prefix}{value.toLocaleString()}{suffix}</>;
}

export function ClickSpark({children,className=''}:{children:ReactNode;className?:string}){
 const ref=useRef<HTMLDivElement>(null);
 const onClick=(e:React.MouseEvent<HTMLDivElement>)=>{const host=ref.current;if(!host)return;const r=host.getBoundingClientRect();const spark=document.createElement('span');spark.className='rb-click-spark';spark.style.left=`${e.clientX-r.left}px`;spark.style.top=`${e.clientY-r.top}px`;host.appendChild(spark);window.setTimeout(()=>spark.remove(),500);};
 return <div ref={ref} onClick={onClick} className={`rb-click-spark-host ${className}`}>{children}</div>;
}