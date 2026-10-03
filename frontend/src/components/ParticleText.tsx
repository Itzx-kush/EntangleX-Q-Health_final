import {useEffect,useRef} from 'react';

type Point={ox:number;oy:number;x:number;y:number;vx:number;vy:number;a:number};

export function ParticleText({text,id}:{text:string;id:string}){
  const hostRef=useRef<HTMLDivElement|null>(null);
  const textRef=useRef<HTMLHeadingElement|null>(null);
  const canvasRef=useRef<HTMLCanvasElement|null>(null);

  useEffect(()=>{
    const host=hostRef.current;
    const heading=textRef.current;
    const canvas=canvasRef.current;
    if(!host||!heading||!canvas)return;
    const context=canvas.getContext('2d');
    if(!context)return;
    const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
    const coarse=window.matchMedia('(pointer: coarse)');
    let points:Point[]=[];
    let width=1;
    let height=1;
    let left=0;
    let top=0;
    let frame=0;
    let last=performance.now();
    const pointer={x:-999,y:-999,active:false,energy:0};

    const build=()=>{
      host.classList.remove('is-particle-ready');
      const rect=heading.getBoundingClientRect();
      left=rect.left;
      top=rect.top;
      width=Math.max(1,Math.round(rect.width));
      height=Math.max(1,Math.round(rect.height));
      if(motion.matches||coarse.matches||width<520){
        points=[];
        context.clearRect(0,0,canvas.width,canvas.height);
        return;
      }
      const ratio=Math.min(devicePixelRatio||1,1.5);
      canvas.width=Math.round(width*ratio);
      canvas.height=Math.round(height*ratio);
      canvas.style.width=`${width}px`;
      canvas.style.height=`${height}px`;
      context.setTransform(ratio,0,0,ratio,0,0);

      const style=getComputedStyle(heading);
      const font=`${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      const fontSize=parseFloat(style.fontSize);
      const lineHeight=parseFloat(style.lineHeight)||fontSize*.96;
      const off=document.createElement('canvas');
      off.width=width;
      off.height=height;
      const offContext=off.getContext('2d');
      if(!offContext)return;
      offContext.font=font;
      offContext.textBaseline='top';
      offContext.fillStyle='#fff';
      const words=text.split(' ');
      const lines:string[]=[];
      let line='';
      words.forEach(word=>{
        const candidate=line?`${line} ${word}`:word;
        if(line&&offContext.measureText(candidate).width>width){
          lines.push(line);
          line=word;
        }else line=candidate;
      });
      if(line)lines.push(line);
      const blockHeight=lines.length*lineHeight;
      const startY=Math.max(0,(height-blockHeight)/2);
      lines.forEach((value,index)=>offContext.fillText(value,0,startY+index*lineHeight));
      const data=offContext.getImageData(0,0,width,height).data;
      const sample=width>1100?4:5;
      points=[];
      for(let y=0;y<height;y+=sample){
        for(let x=0;x<width;x+=sample){
          const alpha=data[(y*width+x)*4+3];
          if(alpha>110)points.push({ox:x,oy:y,x,y,vx:0,vy:0,a:alpha/255});
        }
      }
      if(points.length>13000)points=points.filter((_,index)=>index%2===0);
      host.classList.add('is-particle-ready');
    };

    const draw=(time:number)=>{
      const step=Math.min(2,(time-last)/16.667);
      last=time;
      context.clearRect(0,0,width,height);
      pointer.energy+=((pointer.active?1:0)-pointer.energy)*Math.min(1,.11*step);
      host.style.setProperty('--particle-x',`${pointer.x}px`);
      host.style.setProperty('--particle-y',`${pointer.y}px`);
      host.style.setProperty('--particle-energy',pointer.energy.toFixed(3));
      points.forEach(point=>{
        if(pointer.active){
          const dx=point.x-pointer.x;
          const dy=point.y-pointer.y;
          const distance=Math.max(1,Math.hypot(dx,dy));
          const radius=105;
          if(distance<radius){
            const influence=1-distance/radius;
            const force=influence*influence*1.7*pointer.energy*step;
            point.vx+=dx/distance*force;
            point.vy+=dy/distance*force;
          }
        }
        point.vx+=(point.ox-point.x)*.055*step;
        point.vy+=(point.oy-point.y)*.055*step;
        const damping=Math.pow(.82,step);
        point.vx*=damping;
        point.vy*=damping;
        point.x+=point.vx*step;
        point.y+=point.vy*step;
        context.fillStyle=`rgba(244,242,248,${point.a})`;
        context.fillRect(point.x,point.y,2,2);
      });
      frame=requestAnimationFrame(draw);
    };
    const move=(event:PointerEvent)=>{
      pointer.x=event.clientX-left;
      pointer.y=event.clientY-top;
      pointer.active=pointer.x>-110&&pointer.x<width+110&&pointer.y>-110&&pointer.y<height+110;
    };
    const leave=()=>{pointer.active=false};
    const resize=new ResizeObserver(build);
    resize.observe(heading);
    window.addEventListener('pointermove',move,{passive:true});
    document.addEventListener('mouseleave',leave);
    motion.addEventListener('change',build);
    coarse.addEventListener('change',build);
    build();
    frame=requestAnimationFrame(draw);
    return()=>{
      cancelAnimationFrame(frame);
      resize.disconnect();
      window.removeEventListener('pointermove',move);
      document.removeEventListener('mouseleave',leave);
      motion.removeEventListener('change',build);
      coarse.removeEventListener('change',build);
    };
  },[text]);

  return <div className="particle-text" ref={hostRef}>
    <h1 id={id} ref={textRef}>{text}</h1>
    <canvas ref={canvasRef} aria-hidden="true"/>
  </div>;
}
