import {useEffect,useRef,useState,type CSSProperties,type ReactNode} from 'react';

const glyphs='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789·/—';

export function DecryptedText({text,className=''}:{text:string;className?:string}){
  const [value,setValue]=useState(text);

  useEffect(()=>{
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(reduced){setValue(text);return}
    let frame=0;
    let iteration=0;
    let last=0;
    const tick=(time:number)=>{
      if(time-last<36){frame=requestAnimationFrame(tick);return}
      last=time;
      iteration+=.7;
      setValue(Array.from(text).map((character,index)=>{
        if(character===' '||index<iteration)return character;
        return glyphs[Math.floor((index*17+iteration*13)%glyphs.length)];
      }).join(''));
      if(iteration<text.length)frame=requestAnimationFrame(tick);
      else setValue(text);
    };
    frame=requestAnimationFrame(tick);
    return()=>cancelAnimationFrame(frame);
  },[text]);

  return <span className={`outer-rb-decrypted ${className}`} aria-label={text}>
    <span className="outer-rb-decrypted-measure" aria-hidden="true">{text}</span>
    <span className="outer-rb-decrypted-value" aria-hidden="true">{value}</span>
  </span>;
}

export function SplitReveal({text,className=''}:{text:string;className?:string}){
  return <span className={`outer-rb-split ${className}`} aria-label={text}>
    {text.split(' ').map((word,index)=><span aria-hidden="true" key={`${word}-${index}`} style={{'--word-index':index} as CSSProperties}>{word}</span>)}
  </span>;
}

export function OuterAurora(){
  return <div className="outer-rb-aurora" aria-hidden="true">
    <i className="outer-rb-aurora-ribbon ribbon-a"/>
    <i className="outer-rb-aurora-ribbon ribbon-b"/>
    <i className="outer-rb-aurora-ribbon ribbon-c"/>
    <span className="outer-rb-noise"/>
  </div>;
}

export function OuterMagnet({children,className=''}:{children:ReactNode;className?:string}){
  const ref=useRef<HTMLDivElement|null>(null);
  const frame=useRef(0);
  const current=useRef({x:0,y:0});
  const target=useRef({x:0,y:0});

  useEffect(()=>()=>cancelAnimationFrame(frame.current),[]);

  const animate=()=>{
    const node=ref.current;
    if(!node)return;
    current.current.x+=(target.current.x-current.current.x)*.18;
    current.current.y+=(target.current.y-current.current.y)*.18;
    node.style.setProperty('--magnet-x',`${current.current.x.toFixed(2)}px`);
    node.style.setProperty('--magnet-y',`${current.current.y.toFixed(2)}px`);
    if(Math.abs(target.current.x-current.current.x)>.05||Math.abs(target.current.y-current.current.y)>.05){
      frame.current=requestAnimationFrame(animate);
    }else frame.current=0;
  };
  const schedule=()=>{if(!frame.current)frame.current=requestAnimationFrame(animate)};
  const move=(event:React.PointerEvent<HTMLDivElement>)=>{
    if(event.pointerType==='touch'||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
    const rect=ref.current?.getBoundingClientRect();
    if(!rect)return;
    target.current.x=(event.clientX-rect.left-rect.width/2)*.09;
    target.current.y=(event.clientY-rect.top-rect.height/2)*.12;
    schedule();
  };
  const leave=()=>{target.current={x:0,y:0};schedule()};
  const spark=(event:React.PointerEvent<HTMLDivElement>)=>{
    const node=ref.current;
    if(!node)return;
    const rect=node.getBoundingClientRect();
    node.style.setProperty('--spark-x',`${event.clientX-rect.left}px`);
    node.style.setProperty('--spark-y',`${event.clientY-rect.top}px`);
    node.classList.remove('is-sparking');
    requestAnimationFrame(()=>node.classList.add('is-sparking'));
  };

  return <div ref={ref} className={`outer-rb-magnet ${className}`} onPointerMove={move} onPointerLeave={leave} onPointerDown={spark} onAnimationEnd={event=>{if(event.animationName==='outer-rb-spark')ref.current?.classList.remove('is-sparking')}}>{children}</div>;
}

export function OuterSpotlight({children,className=''}:{children:ReactNode;className?:string}){
  const ref=useRef<HTMLDivElement|null>(null);
  const move=(event:React.PointerEvent<HTMLDivElement>)=>{
    const rect=ref.current?.getBoundingClientRect();
    if(!rect||event.pointerType==='touch')return;
    ref.current?.style.setProperty('--spotlight-x',`${event.clientX-rect.left}px`);
    ref.current?.style.setProperty('--spotlight-y',`${event.clientY-rect.top}px`);
  };
  return <div ref={ref} className={`outer-rb-spotlight ${className}`} onPointerMove={move}>{children}</div>;
}

export function PixelTrail(){
  const hostRef=useRef<HTMLDivElement|null>(null);
  const frame=useRef(0);

  useEffect(()=>{
    const host=hostRef.current;
    if(!host)return;
    const dots=Array.from(host.querySelectorAll<HTMLElement>('i'));
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
    const coarse=window.matchMedia('(pointer: coarse)');
    let bounds=host.getBoundingClientRect();
    let active=false;
    const target={x:-40,y:-40};
    const positions=dots.map(()=>({x:-40,y:-40}));
    const measure=()=>{bounds=host.getBoundingClientRect()};
    const draw=()=>{
      positions.forEach((position,index)=>{
        const leader=index===0?target:positions[index-1];
        const ease=.28-index*.016;
        position.x+=(leader.x-position.x)*ease;
        position.y+=(leader.y-position.y)*ease;
        dots[index].style.transform=`translate3d(${position.x}px,${position.y}px,0) scale(${active?1:0})`;
      });
      frame.current=requestAnimationFrame(draw);
    };
    const move=(event:PointerEvent)=>{
      if(reduced.matches||coarse.matches||event.pointerType==='touch')return;
      target.x=event.clientX-bounds.left;
      target.y=event.clientY-bounds.top;
      active=target.x>=0&&target.x<=bounds.width&&target.y>=0&&target.y<=bounds.height;
      host.classList.toggle('is-active',active);
    };
    const leave=()=>{active=false;host.classList.remove('is-active')};
    const resize=new ResizeObserver(measure);
    resize.observe(host);
    window.addEventListener('pointermove',move,{passive:true});
    window.addEventListener('scroll',measure,{passive:true});
    document.addEventListener('mouseleave',leave);
    frame.current=requestAnimationFrame(draw);
    return()=>{
      cancelAnimationFrame(frame.current);
      resize.disconnect();
      window.removeEventListener('pointermove',move);
      window.removeEventListener('scroll',measure);
      document.removeEventListener('mouseleave',leave);
    };
  },[]);

  return <div ref={hostRef} className="outer-rb-pixel-trail" aria-hidden="true">{Array.from({length:8},(_,index)=><i key={index} style={{'--trail-index':index} as CSSProperties}/>)}</div>;
}