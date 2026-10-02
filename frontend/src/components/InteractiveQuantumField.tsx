import {useEffect,useRef} from 'react';

type Particle={
  nx:number;
  ny:number;
  x:number;
  y:number;
  vx:number;
  vy:number;
  phase:number;
  speed:number;
  drift:number;
  radius:number;
  cyan:boolean;
};

type Link={a:number;b:number;alpha:number};

const TAU=Math.PI*2;

function seededRandom(seed:number){
  let value=seed>>>0;
  return()=>{
    value=(value*1664525+1013904223)>>>0;
    return value/4294967296;
  };
}

function smoothstep(value:number){
  const clamped=Math.max(0,Math.min(1,value));
  return clamped*clamped*(3-2*clamped);
}

export function InteractiveQuantumField(){
  const canvasRef=useRef<HTMLCanvasElement|null>(null);

  useEffect(()=>{
    const canvas=canvasRef.current;
    if(!canvas)return;
    const context=canvas.getContext('2d',{alpha:true});
    if(!context)return;

    const reducedQuery=window.matchMedia('(prefers-reduced-motion: reduce)');
    const coarseQuery=window.matchMedia('(pointer: coarse)');
    let reduced=reducedQuery.matches;
    let coarse=coarseQuery.matches;
    let width=1;
    let height=1;
    let left=0;
    let top=0;
    let animationFrame=0;
    let lastTime=performance.now();
    let particles:Particle[]=[];
    let links:Link[]=[];
    const pointer={x:-1000,y:-1000,active:false,energy:0};

    const buildField=()=>{
      const random=seededRandom(26139);
      const count=width<640?30:width<1024?46:68;
      const brandCluster=Math.min(16,Math.floor(count*.27));
      particles=Array.from({length:count},(_,index)=>{
        const clustered=index<brandCluster;
        const nx=clustered?.08+random()*.5:.025+random()*.95;
        const ny=clustered?.2+random()*.55:.04+random()*.9;
        return{
          nx,ny,
          x:nx*width,
          y:ny*height,
          vx:0,vy:0,
          phase:random()*TAU,
          speed:.00018+random()*.00024,
          drift:1.4+random()*3.8,
          radius:random()>.82?1.8:.65+random()*.7,
          cyan:random()>.78,
        };
      });

      links=[];
      particles.forEach((particle,index)=>{
        const candidates=particles
          .map((other,otherIndex)=>({
            index:otherIndex,
            distance:Math.hypot((particle.nx-other.nx)*width,(particle.ny-other.ny)*height),
          }))
          .filter(candidate=>candidate.index>index&&candidate.distance<Math.min(240,width*.23))
          .sort((a,b)=>a.distance-b.distance)
          .slice(0,2);
        candidates.forEach(candidate=>links.push({
          a:index,
          b:candidate.index,
          alpha:.045+(1-candidate.distance/260)*.075,
        }));
      });
    };

    const measure=()=>{
      const rect=canvas.getBoundingClientRect();
      left=rect.left;
      top=rect.top;
      const nextWidth=Math.max(1,Math.round(rect.width));
      const nextHeight=Math.max(1,Math.round(rect.height));
      if(nextWidth===width&&nextHeight===height)return;
      width=nextWidth;
      height=nextHeight;
      const dpr=Math.min(window.devicePixelRatio||1,2);
      canvas.width=Math.round(width*dpr);
      canvas.height=Math.round(height*dpr);
      context.setTransform(dpr,0,0,dpr,0,0);
      buildField();
    };

    const draw=(time:number)=>{
      const elapsed=Math.min(32,time-lastTime);
      lastTime=time;
      const frame=elapsed/16.667;
      context.clearRect(0,0,width,height);

      const influenceRadius=coarse?105:Math.min(190,Math.max(138,width*.145));
      pointer.energy+=((pointer.active?1:0)-pointer.energy)*Math.min(1,.11*frame);

      particles.forEach(particle=>{
        const ambientX=Math.cos(time*particle.speed+particle.phase)*particle.drift;
        const ambientY=Math.sin(time*particle.speed*.82+particle.phase)*particle.drift*.72;
        const baseX=particle.nx*width+ambientX;
        const baseY=particle.ny*height+ambientY;

        if(!reduced&&pointer.energy>.001){
          const dx=particle.x-pointer.x;
          const dy=particle.y-pointer.y;
          const distance=Math.max(1,Math.hypot(dx,dy));
          if(distance<influenceRadius){
            const falloff=smoothstep(1-distance/influenceRadius);
            const force=falloff*falloff*(coarse?1.05:1.42)*pointer.energy*frame;
            particle.vx+=dx/distance*force;
            particle.vy+=dy/distance*force;
          }
        }

        const spring=reduced?.055:.024;
        particle.vx+=(baseX-particle.x)*spring*frame;
        particle.vy+=(baseY-particle.y)*spring*frame;
        const damping=Math.pow(reduced?.72:.865,frame);
        particle.vx*=damping;
        particle.vy*=damping;
        particle.x+=particle.vx*frame;
        particle.y+=particle.vy*frame;
      });

      links.forEach(link=>{
        const first=particles[link.a];
        const second=particles[link.b];
        const distance=Math.hypot(first.x-second.x,first.y-second.y);
        const fade=Math.max(0,1-distance/310);
        if(fade<=0)return;
        context.beginPath();
        context.moveTo(first.x,first.y);
        context.lineTo(second.x,second.y);
        context.strokeStyle=`rgba(157,139,255,${link.alpha*fade})`;
        context.lineWidth=.65;
        context.stroke();
      });

      particles.forEach(particle=>{
        const glow=particle.radius>1.5?7:4;
        context.beginPath();
        context.arc(particle.x,particle.y,particle.radius+glow,0,TAU);
        const gradient=context.createRadialGradient(
          particle.x,particle.y,0,particle.x,particle.y,particle.radius+glow,
        );
        const color=particle.cyan?'113,190,210':'155,135,255';
        gradient.addColorStop(0,`rgba(${color},.2)`);
        gradient.addColorStop(1,`rgba(${color},0)`);
        context.fillStyle=gradient;
        context.fill();
        context.beginPath();
        context.arc(particle.x,particle.y,particle.radius,0,TAU);
        context.fillStyle=particle.cyan?'rgba(133,207,224,.72)':'rgba(181,166,255,.72)';
        context.fill();
      });

      if(!reduced&&pointer.energy>.015){
        const radius=78*pointer.energy;
        const glow=context.createRadialGradient(pointer.x,pointer.y,0,pointer.x,pointer.y,radius);
        glow.addColorStop(0,'rgba(151,126,255,.055)');
        glow.addColorStop(.45,'rgba(112,95,220,.025)');
        glow.addColorStop(1,'rgba(112,95,220,0)');
        context.fillStyle=glow;
        context.fillRect(pointer.x-radius,pointer.y-radius,radius*2,radius*2);
      }

      if(!reduced)animationFrame=requestAnimationFrame(draw);
    };

    const renderStatic=()=>{
      particles.forEach(particle=>{
        particle.x=particle.nx*width;
        particle.y=particle.ny*height;
        particle.vx=0;
        particle.vy=0;
      });
      draw(performance.now());
    };

    const onPointerMove=(event:PointerEvent)=>{
      if(reduced||(!coarse&&event.pointerType!=='mouse'&&event.pointerType!=='pen'))return;
      const x=event.clientX-left;
      const y=event.clientY-top;
      pointer.x=x;
      pointer.y=y;
      pointer.active=x>=0&&x<=width&&y>=0&&y<=height;
    };
    const onPointerDown=(event:PointerEvent)=>{
      if(reduced||event.pointerType==='mouse')return;
      pointer.x=event.clientX-left;
      pointer.y=event.clientY-top;
      pointer.active=true;
    };
    const releasePointer=()=>{pointer.active=false};
    const onMotionChange=()=>{
      reduced=reducedQuery.matches;
      cancelAnimationFrame(animationFrame);
      if(reduced)renderStatic();
      else{
        lastTime=performance.now();
        animationFrame=requestAnimationFrame(draw);
      }
    };
    const onCoarseChange=()=>{coarse=coarseQuery.matches;buildField()};

    const resizeObserver=new ResizeObserver(measure);
    resizeObserver.observe(canvas);
    window.addEventListener('resize',measure,{passive:true});
    window.addEventListener('scroll',measure,{passive:true});
    window.addEventListener('pointermove',onPointerMove,{passive:true});
    window.addEventListener('pointerdown',onPointerDown,{passive:true});
    window.addEventListener('pointerup',releasePointer,{passive:true});
    window.addEventListener('pointercancel',releasePointer,{passive:true});
    document.addEventListener('mouseleave',releasePointer);
    reducedQuery.addEventListener('change',onMotionChange);
    coarseQuery.addEventListener('change',onCoarseChange);
    measure();
    if(reduced)renderStatic();
    else animationFrame=requestAnimationFrame(draw);

    return()=>{
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      window.removeEventListener('resize',measure);
      window.removeEventListener('scroll',measure);
      window.removeEventListener('pointermove',onPointerMove);
      window.removeEventListener('pointerdown',onPointerDown);
      window.removeEventListener('pointerup',releasePointer);
      window.removeEventListener('pointercancel',releasePointer);
      document.removeEventListener('mouseleave',releasePointer);
      reducedQuery.removeEventListener('change',onMotionChange);
      coarseQuery.removeEventListener('change',onCoarseChange);
    };
  },[]);

  return <canvas ref={canvasRef} className="public-quantum-field" aria-hidden="true"/>;
          }
