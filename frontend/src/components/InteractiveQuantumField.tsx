import {useEffect,useRef} from 'react';

type Node={
  nx:number;
  ny:number;
  x:number;
  y:number;
  vx:number;
  vy:number;
  phase:number;
  depth:number;
  radius:number;
  cyan:boolean;
};

type Link={
  a:number;
  b:number;
  alpha:number;
  tracer:boolean;
  phase:number;
};

type Particle={
  x:number;
  y:number;
  depth:number;
  phase:number;
  speed:number;
  radius:number;
};

const TAU=Math.PI*2;
const VIOLET=[155,135,255] as const;
const CYAN=[113,190,210] as const;

const clamp=(value:number,min=0,max=1)=>Math.max(min,Math.min(max,value));
const smooth=(value:number)=>{
  const t=clamp(value);
  return t*t*(3-2*t);
};
const mix=(a:readonly number[],b:readonly number[],t:number)=>[
  a[0]+(b[0]-a[0])*t,
  a[1]+(b[1]-a[1])*t,
  a[2]+(b[2]-a[2])*t,
];
const rgba=(rgb:readonly number[],alpha:number)=>'rgba('+Math.round(rgb[0])+','+Math.round(rgb[1])+','+Math.round(rgb[2])+','+alpha+')';

function seededRandom(seed:number){
  let value=seed>>>0;
  return()=>{
    value=(value*1664525+1013904223)>>>0;
    return value/4294967296;
  };
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
    let animationFrame=0;
    let lastTime=performance.now();
    let pageVisible=!document.hidden;
    let scrollProgress=0;
    let nodes:Node[]=[];
    let links:Link[]=[];
    let particles:Particle[]=[];

    const pointer={
      x:-1000,
      y:-1000,
      active:false,
      energy:0,
      releaseTimer:0 as number
    };

    const buildField=()=>{
      const random=seededRandom(26139);
      const nodeCount=width<640?22:width<1024?34:52;
      const particleCount=width<640?28:width<1024?48:78;

      nodes=Array.from({length:nodeCount},(_,index)=>{
        const cluster=index%5;
        const nx=clamp((cluster*.15)+.08+random()*.36+(index%2?random()*.1:0),.035,.965);
        const ny=clamp(.07+random()*.86,.055,.945);
        return{
          nx,
          ny,
          x:nx*width,
          y:ny*height,
          vx:0,
          vy:0,
          phase:random()*TAU,
          depth:.45+random()*.8,
          radius:.65+random()*1.25,
          cyan:random()>.76,
        };
      });

      links=[];
      nodes.forEach((node,index)=>{
        const candidates=nodes
          .map((other,otherIndex)=>({
            index:otherIndex,
            distance:Math.hypot((node.nx-other.nx)*width,(node.ny-other.ny)*height)
          }))
          .filter(candidate=>candidate.index>index&&candidate.distance<Math.min(300,width*.3))
          .sort((a,b)=>a.distance-b.distance)
          .slice(0,2);
        candidates.forEach(candidate=>{
          links.push({
            a:index,
            b:candidate.index,
            alpha:.035+(.11*(1-candidate.distance/Math.min(300,width*.3))),
            tracer:(index+candidate.index)%3!==0,
            phase:random()*TAU
          });
        });
      });

      particles=Array.from({length:particleCount},()=>{
        const depth=random();
        return{
          x:random()*width,
          y:random()*height,
          depth,
          phase:random()*TAU,
          speed:.035+random()*.09,
          radius:.35+(1-depth)*.65
        };
      });
    };

    const measure=()=>{
      const nextWidth=Math.max(1,Math.round(window.innerWidth));
      const nextHeight=Math.max(1,Math.round(window.innerHeight));
      if(nextWidth===width&&nextHeight===height)return;
      width=nextWidth;
      height=nextHeight;
      const dpr=Math.min(window.devicePixelRatio||1,1.5);
      canvas.width=Math.round(width*dpr);
      canvas.height=Math.round(height*dpr);
      canvas.style.width=width+'px';
      canvas.style.height=height+'px';
      context.setTransform(dpr,0,0,dpr,0,0);
      buildField();
    };

    const updateScroll=()=>{
      const maxScroll=Math.max(1,document.documentElement.scrollHeight-window.innerHeight);
      scrollProgress=clamp(window.scrollY/maxScroll);
    };

    const drawAtmosphere=(time:number)=>{
      const heroState=1-smooth(scrollProgress/.28);
      const quantumState=smooth((scrollProgress-.42)/.26);
      const evidenceState=smooth((scrollProgress-.63)/.25);
      const accessState=smooth((scrollProgress-.84)/.16);
      const driftX=Math.sin(time*.00008)*width*.08;
      const driftY=Math.cos(time*.000065)*height*.055;

      const broad=context.createRadialGradient(width*.6+driftX,height*.18+driftY,0,width*.6+driftX,height*.18+driftY,Math.max(width,height)*.72);
      broad.addColorStop(0,rgba(VIOLET,.09+heroState*.06));
      broad.addColorStop(.5,rgba(CYAN,.025+quantumState*.045));
      broad.addColorStop(1,'rgba(7,7,10,0)');
      context.fillStyle=broad;
      context.fillRect(0,0,width,height);

      const lower=context.createRadialGradient(width*(.18+accessState*.6),height*(.7-.13*evidenceState),0,width*.35,height*.65,Math.max(width,height)*.65);
      lower.addColorStop(0,rgba(CYAN,.025+evidenceState*.04));
      lower.addColorStop(.72,'rgba(7,7,10,0)');
      context.fillStyle=lower;
      context.fillRect(0,0,width,height);

      if(pointer.energy>.001&&!reduced){
        const glow=context.createRadialGradient(pointer.x,pointer.y,0,pointer.x,pointer.y,Math.min(width,height)*.28);
        glow.addColorStop(0,rgba(VIOLET,.055*pointer.energy));
        glow.addColorStop(.35,rgba(CYAN,.018*pointer.energy));
        glow.addColorStop(1,'rgba(7,7,10,0)');
        context.fillStyle=glow;
        context.fillRect(0,0,width,height);
      }
    };

    const drawResearchGrid=(time:number)=>{
      const baseAlpha=.022+(1-scrollProgress)*.018;
      const spacing=coarse?96:78;
      const drift=(time*.006*(.25+.45*(1-scrollProgress)))%spacing;

      context.lineWidth=.5;
      context.strokeStyle=rgba(VIOLET,baseAlpha);
      context.beginPath();
      for(let x=-spacing+drift;x<width+spacing;x+=spacing){
        context.moveTo(x,0);
        context.lineTo(x+width*.035,height);
      }
      context.stroke();

      context.strokeStyle=rgba(CYAN,baseAlpha*.7);
      context.beginPath();
      for(let y=-spacing+drift*.62;y<height+spacing;y+=spacing){
        context.moveTo(0,y);
        context.lineTo(width,y+height*.02);
      }
      context.stroke();

      const gridPulse=(Math.sin(time*.00035)+1)*.5;
      context.fillStyle=rgba(VIOLET,.025+gridPulse*.02);
      for(let y=spacing*.55;y<height;y+=spacing*1.5){
        for(let x=spacing*.75;x<width;x+=spacing*1.5){
          const dx=x-pointer.x;
          const dy=y-pointer.y;
          const distance=Math.hypot(dx,dy);
          const local=!reduced&&pointer.active?Math.max(0,1-distance/170):0;
          context.beginPath();
          context.arc(x,y,.65+local*1.2,0,TAU);
          context.fill();
        }
      }
    };

    const drawFloatingLines=(time:number)=>{
      const heroState=1-smooth(scrollProgress/.32);
      const structuredState=smooth((scrollProgress-.18)/.45);
      const alpha=.035+structuredState*.018+heroState*.012;
      const lineCount=coarse?3:4;

      for(let line=0;line<lineCount;line++){
        const normalized=line/(Math.max(1,lineCount-1));
        const yBase=height*(.16+normalized*.28)+Math.sin(line*1.7)*height*.035;
        const phase=time*.00013*(.55+normalized*.18)+line*1.63;
        context.beginPath();
        for(let x=0;x<=width+24;x+=14){
          const u=x/width;
          const wave1=Math.sin(u*TAU*(1.05+normalized*.4)+phase)*height*(.008+.006*structuredState);
          const wave2=Math.sin(u*TAU*.42-phase*.72)*height*.012;
          const y=yBase+wave1+wave2;
          if(x===0)context.moveTo(x,y);
          else context.lineTo(x,y);
        }
        const color=mix(VIOLET,CYAN,normalized*.65);
        context.strokeStyle=rgba(color,alpha);
        context.lineWidth=.8;
        context.stroke();
      }
    };

    const drawNetwork=(time:number)=>{
      const modelingState=smooth((scrollProgress-.18)/.4);
      const quantumState=smooth((scrollProgress-.42)/.25);
      const evidenceState=smooth((scrollProgress-.63)/.22);
      const accessState=smooth((scrollProgress-.84)/.16);
      const convergence=accessState*.18;

      nodes.forEach(node=>{
        const ambientX=Math.cos(time*.00016+node.phase)*node.depth*3.2;
        const ambientY=Math.sin(time*.00013+node.phase*.82)*node.depth*3.5;
        let targetX=node.nx*width+ambientX;
        let targetY=node.ny*height+ambientY;

        targetX+=(width*.5-targetX)*convergence;
        targetY+=(height*.5-targetY)*convergence;

        if(!reduced&&pointer.active){
          const dx=targetX-pointer.x;
          const dy=targetY-pointer.y;
          const distance=Math.max(1,Math.hypot(dx,dy));
          if(distance<180){
            const force=Math.pow(1-distance/180,2)*(.55+pointer.energy*.75);
            targetX+=dx/distance*force*24;
            targetY+=dy/distance*force*24;
          }
        }

        node.vx+=(targetX-node.x)*.018;
        node.vy+=(targetY-node.y)*.018;
        const damping=Math.pow(reduced?.76:.86,1);
        node.vx*=damping;
        node.vy*=damping;
        node.x+=node.vx;
        node.y+=node.vy;
      });

      links.forEach(link=>{
        const a=nodes[link.a];
        const b=nodes[link.b];
        const distance=Math.hypot(a.x-b.x,a.y-b.y);
        const fade=clamp(1-distance/340);
        if(fade<=0)return;

        const branchBoost=link.tracer?modelingState*.8:.15*quantumState;
        const selected=evidenceState>.45?.55+evidenceState*.45:1;
        const alpha=(link.alpha+branchBoost*.045)*fade*selected;
        context.beginPath();
        context.moveTo(a.x,a.y);
        context.lineTo(b.x,b.y);
        context.strokeStyle=rgba(link.tracer?VIOLET:CYAN,alpha);
        context.lineWidth=.6+quantumState*.25;
        context.stroke();

        if(!reduced&&link.tracer){
          const tracer=(time*.000055*(.55+quantumState*.9)+link.phase/TAU)%1;
          const tx=a.x+(b.x-a.x)*tracer;
          const ty=a.y+(b.y-a.y)*tracer;
          const radius=1.05+quantumState*.65;
          const tracerEnergy=tracer<.5?tracer*2:(1-tracer)*2;
          context.beginPath();
          context.arc(tx,ty,radius,0,TAU);
          context.fillStyle=rgba(mix(VIOLET,CYAN,.35),.2+.35*tracerEnergy);
          context.fill();
        }
      });

      nodes.forEach((node,index)=>{
        const local=!reduced&&pointer.active?Math.max(0,1-Math.hypot(node.x-pointer.x,node.y-pointer.y)/150):0;
        const breathing=.72+.28*((Math.sin(time*.0008+node.phase)+1)*.5);
        const base=node.cyan?CYAN:VIOLET;
        const stateBoost=.25+modelingState*.18+quantumState*.2+evidenceState*.18;
        const radius=node.radius+local*1.25+quantumState*.35;

        context.beginPath();
        context.arc(node.x,node.y,radius+2.6,0,TAU);
        context.fillStyle=rgba(base,(.03+local*.08)*breathing);
        context.fill();

        context.beginPath();
        context.arc(node.x,node.y,radius,0,TAU);
        context.fillStyle=rgba(base,(.18+stateBoost+local*.3)*breathing);
        context.fill();

        if(index%7===0&&stateBoost>.45){
          context.beginPath();
          context.arc(node.x,node.y,radius+5+Math.sin(time*.001+index)*1.5,0,TAU);
          context.strokeStyle=rgba(base,.055+local*.06);
          context.lineWidth=.5;
          context.stroke();
        }
      });
    };

    const drawParticles=(time:number)=>{
      particles.forEach((particle,index)=>{
        if(!reduced){
          const travel=time*.00015*particle.speed*(1+particle.depth);
          particle.x+=Math.cos(particle.phase+travel)*.028*(.4+particle.depth);
          particle.y+=Math.sin(particle.phase*.7+travel)*.02*(.4+particle.depth);
          if(particle.x<-20)particle.x=width+20;
          if(particle.x>width+20)particle.x=-20;
          if(particle.y<-20)particle.y=height+20;
          if(particle.y>height+20)particle.y=-20;
        }
        const depthAlpha=.03+(1-particle.depth)*.07;
        const local=!reduced&&pointer.active?Math.max(0,1-Math.hypot(particle.x-pointer.x,particle.y-pointer.y)/140):0;
        const rgb=index%4===0?CYAN:VIOLET;
        context.beginPath();
        context.arc(particle.x,particle.y,particle.radius+local*.55,0,TAU);
        context.fillStyle=rgba(rgb,depthAlpha+local*.08);
        context.fill();
      });
    };

    const drawOrbits=(time:number)=>{
      const heroState=1-smooth(scrollProgress/.34);
      const x=width*.73;
      const y=height*.37;
      const scale=Math.min(width,height);
      if(heroState<=.01)return;

      context.save();
      context.translate(x,y);
      context.rotate(-.12+Math.sin(time*.00008)*.06);
      context.strokeStyle=rgba(VIOLET,.075*heroState);
      context.lineWidth=.7;
      context.beginPath();
      context.ellipse(0,0,scale*.29,scale*.1,0,0,TAU);
      context.stroke();
      context.strokeStyle=rgba(CYAN,.06*heroState);
      context.beginPath();
      context.ellipse(0,0,scale*.24,scale*.085,.46,0,TAU);
      context.stroke();
      context.restore();
    };

    const drawEnergyPulse=(time:number)=>{
      if(reduced)return;
      const pulseAmount=(Math.sin(time*.00042)+1)*.5;
      const phase=(time*.00009)%1;
      const focusProgress=smooth((scrollProgress-.52)/.35);
      const x=width*(.32+.38*scrollProgress);
      const y=height*(.32+.16*Math.sin(scrollProgress*TAU));
      const radius=30+pulseAmount*44+focusProgress*22;

      context.beginPath();
      context.arc(x,y,radius,0,TAU);
      context.strokeStyle=rgba(mix(VIOLET,CYAN,.55),(.02+.045*focusProgress)*pulseAmount);
      context.lineWidth=1;
      context.stroke();

      if(pointer.energy>.02){
        const pointerRadius=18+pointer.energy*48;
        context.beginPath();
        context.arc(pointer.x,pointer.y,pointerRadius,0,TAU);
        context.strokeStyle=rgba(VIOLET,.06*pointer.energy);
        context.lineWidth=1;
        context.stroke();
      }

      if(phase<.32){
        const spread=phase/.32;
        context.beginPath();
        context.arc(x,y,10+spread*90,0,TAU);
        context.strokeStyle=rgba(CYAN,(1-spread)*.055);
        context.stroke();
      }
    };

    const renderStatic=()=>{
      context.clearRect(0,0,width,height);
      drawAtmosphere(0);
      drawResearchGrid(0);
      drawFloatingLines(0);
      drawNetwork(0);
      drawParticles(0);
      drawOrbits(0);
    };

    const draw=(time:number)=>{
      if(!pageVisible)return;
      const elapsed=Math.min(40,time-lastTime);
      lastTime=time;
      pointer.energy+=((pointer.active?1:0)-pointer.energy)*Math.min(1,.08*(elapsed/16.667));
      context.clearRect(0,0,width,height);
      updateScroll();
      drawAtmosphere(time);
      drawResearchGrid(time);
      drawFloatingLines(time);
      drawNetwork(time);
      drawParticles(time);
      drawOrbits(time);
      drawEnergyPulse(time);
      if(!reduced)animationFrame=requestAnimationFrame(draw);
    };

    const updatePointer=(clientX:number,clientY:number,active:boolean)=>{
      pointer.x=clientX;
      pointer.y=clientY;
      pointer.active=active;
    };

    const onPointerMove=(event:PointerEvent)=>{
      if(reduced||coarse||event.pointerType==='touch')return;
      updatePointer(event.clientX,event.clientY,true);
    };
    const onPointerDown=(event:PointerEvent)=>{
      if(reduced)return;
      updatePointer(event.clientX,event.clientY,true);
      if(pointer.releaseTimer)window.clearTimeout(pointer.releaseTimer);
      pointer.releaseTimer=window.setTimeout(()=>{
        pointer.active=false;
        pointer.releaseTimer=0;
      },900);
    };
    const settle=()=>{
      pointer.active=false;
      if(pointer.releaseTimer){window.clearTimeout(pointer.releaseTimer);pointer.releaseTimer=0;}
    };
    const onScroll=()=>updateScroll();
    const onVisibility=()=>{
      pageVisible=!document.hidden;
      cancelAnimationFrame(animationFrame);
      animationFrame=0;
      if(!pageVisible)return;
      lastTime=performance.now();
      if(reduced)renderStatic();
      else animationFrame=requestAnimationFrame(draw);
    };
    const onMotionChange=()=>{
      reduced=reducedQuery.matches;
      cancelAnimationFrame(animationFrame);
      animationFrame=0;
      if(reduced)renderStatic();
      else{
        lastTime=performance.now();
        animationFrame=requestAnimationFrame(draw);
      }
    };
    const onCoarseChange=()=>{
      coarse=coarseQuery.matches;
      buildField();
    };

    const resizeObserver=new ResizeObserver(measure);
    resizeObserver.observe(document.documentElement);
    window.addEventListener('resize',measure,{passive:true});
    window.addEventListener('scroll',onScroll,{passive:true});
    window.addEventListener('pointermove',onPointerMove,{passive:true});
    window.addEventListener('pointerdown',onPointerDown,{passive:true});
    window.addEventListener('pointerup',settle,{passive:true});
    window.addEventListener('pointercancel',settle,{passive:true});
    window.addEventListener('blur',settle);
    document.addEventListener('visibilitychange',onVisibility);
    reducedQuery.addEventListener('change',onMotionChange);
    coarseQuery.addEventListener('change',onCoarseChange);

    measure();
    updateScroll();
    if(reduced)renderStatic();
    else animationFrame=requestAnimationFrame(draw);

    return()=>{
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      window.removeEventListener('resize',measure);
      window.removeEventListener('scroll',onScroll);
      window.removeEventListener('pointermove',onPointerMove);
      window.removeEventListener('pointerdown',onPointerDown);
      window.removeEventListener('pointerup',settle);
      window.removeEventListener('pointercancel',settle);
      window.removeEventListener('blur',settle);
      document.removeEventListener('visibilitychange',onVisibility);
      reducedQuery.removeEventListener('change',onMotionChange);
      coarseQuery.removeEventListener('change',onCoarseChange);
      if(pointer.releaseTimer)window.clearTimeout(pointer.releaseTimer);
    };
  },[]);

  return <canvas ref={canvasRef} className="public-quantum-field" aria-hidden="true"/>;
}
