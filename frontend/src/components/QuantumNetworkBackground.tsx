import {useEffect,useRef} from 'react';

type NetworkNode={
  nx:number;
  ny:number;
  x:number;
  y:number;
  vx:number;
  vy:number;
  phase:number;
  speed:number;
  drift:number;
  depth:number;
  radius:number;
  cyan:boolean;
};

type NetworkEdge={a:number;b:number;alpha:number;tracer:boolean;offset:number};

const TAU=Math.PI*2;

function seededRandom(seed:number){
  let value=seed>>>0;
  return()=>{
    value=(value*1664525+1013904223)>>>0;
    return value/4294967296;
  };
}

function smoothFalloff(value:number){
  const clamped=Math.max(0,Math.min(1,value));
  return clamped*clamped*(3-2*clamped);
}

export function QuantumNetworkBackground(){
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
    let frameId=0;
    let lastTime=performance.now();
    let nodes:NetworkNode[]=[];
    let edges:NetworkEdge[]=[];
    const pointer={x:-1000,y:-1000,active:false,energy:0};

    const buildNetwork=()=>{
      const random=seededRandom(20261003);
      const count=width<620?28:width<1050?46:72;
      nodes=Array.from({length:count},(_,index)=>{
        const depth=index%5===0?.36:index%3===0?.64:1;
        const nx=.025+random()*.95;
        const ny=.035+random()*.93;
        return{
          nx,ny,
          x:nx*width,
          y:ny*height,
          vx:0,vy:0,
          phase:random()*TAU,
          speed:.0001+random()*.00019,
          drift:1.5+random()*4.5,
          depth,
          radius:(.6+random()*1.15)*(.72+depth*.28),
          cyan:random()>.82,
        };
      });

      edges=[];
      nodes.forEach((node,index)=>{
        const limit=width<620?150:width<1050?205:250;
        const nearest=nodes
          .map((other,otherIndex)=>({
            index:otherIndex,
            distance:Math.hypot((node.nx-other.nx)*width,(node.ny-other.ny)*height),
          }))
          .filter(candidate=>candidate.index>index&&candidate.distance<limit)
          .sort((a,b)=>a.distance-b.distance)
          .slice(0,node.depth<.5?1:2);
        nearest.forEach(candidate=>edges.push({
          a:index,
          b:candidate.index,
          alpha:.035+(1-candidate.distance/limit)*.09,
          tracer:random()>.88,
          offset:random(),
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
      buildNetwork();
    };

    const draw=(time:number)=>{
      const elapsed=Math.min(34,time-lastTime);
      lastTime=time;
      const step=elapsed/16.667;
      context.clearRect(0,0,width,height);
      pointer.energy+=((pointer.active?1:0)-pointer.energy)*Math.min(1,.095*step);
      const influenceRadius=coarse?95:Math.min(180,Math.max(130,width*.12));

      nodes.forEach(node=>{
        const ambientX=Math.cos(time*node.speed+node.phase)*node.drift*node.depth;
        const ambientY=Math.sin(time*node.speed*.79+node.phase)*node.drift*.72*node.depth;
        const parallaxX=pointer.active?(pointer.x-width/2)/width*3.5*(1-node.depth):0;
        const parallaxY=pointer.active?(pointer.y-height/2)/height*2.5*(1-node.depth):0;
        const baseX=node.nx*width+ambientX+parallaxX;
        const baseY=node.ny*height+ambientY+parallaxY;

        if(!reduced&&pointer.energy>.001){
          const dx=node.x-pointer.x;
          const dy=node.y-pointer.y;
          const distance=Math.max(1,Math.hypot(dx,dy));
          if(distance<influenceRadius){
            const influence=smoothFalloff(1-distance/influenceRadius);
            const force=influence*influence*(.56+node.depth*.72)*pointer.energy*step;
            node.vx+=dx/distance*force;
            node.vy+=dy/distance*force;
          }
        }

        const spring=reduced?.06:.021;
        node.vx+=(baseX-node.x)*spring*step;
        node.vy+=(baseY-node.y)*spring*step;
        const damping=Math.pow(reduced?.7:.875,step);
        node.vx*=damping;
        node.vy*=damping;
        node.x+=node.vx*step;
        node.y+=node.vy*step;
      });

      edges.forEach(edge=>{
        const first=nodes[edge.a];
        const second=nodes[edge.b];
        const distance=Math.hypot(first.x-second.x,first.y-second.y);
        const fade=Math.max(0,1-distance/(width<620?205:330));
        if(fade<=0)return;
        const pulse=reduced?1:.78+Math.sin(time*.00042+edge.offset*TAU)*.22;
        context.beginPath();
        context.moveTo(first.x,first.y);
        context.lineTo(second.x,second.y);
        context.lineWidth=.55+(first.depth+second.depth)*.08;
        context.strokeStyle=`rgba(142,132,218,${edge.alpha*fade*pulse})`;
        context.stroke();

        if(!reduced&&edge.tracer){
          const progress=(time*.000035+edge.offset)%1;
          const x=first.x+(second.x-first.x)*progress;
          const y=first.y+(second.y-first.y)*progress;
          context.beginPath();
          context.arc(x,y,1.15,0,TAU);
          context.fillStyle='rgba(200,191,255,.38)';
          context.fill();
        }
      });

      nodes.forEach(node=>{
        const color=node.cyan?'103,185,207':'157,137,255';
        const alpha=.24+node.depth*.48;
        if(node.depth>.6){
          const glow=context.createRadialGradient(node.x,node.y,0,node.x,node.y,node.radius+6);
          glow.addColorStop(0,`rgba(${color},${alpha*.24})`);
          glow.addColorStop(1,`rgba(${color},0)`);
          context.fillStyle=glow;
          context.fillRect(node.x-7,node.y-7,14,14);
        }
        context.beginPath();
        context.arc(node.x,node.y,node.radius,0,TAU);
        context.fillStyle=`rgba(${color},${alpha})`;
        context.fill();
      });

      if(!reduced&&pointer.energy>.02){
        const radius=72*pointer.energy;
        const glow=context.createRadialGradient(pointer.x,pointer.y,0,pointer.x,pointer.y,radius);
        glow.addColorStop(0,'rgba(148,126,255,.045)');
        glow.addColorStop(1,'rgba(100,82,190,0)');
        context.fillStyle=glow;
        context.fillRect(pointer.x-radius,pointer.y-radius,radius*2,radius*2);
      }

      if(!reduced)frameId=requestAnimationFrame(draw);
    };

    const renderStatic=()=>{
      nodes.forEach(node=>{
        node.x=node.nx*width;
        node.y=node.ny*height;
        node.vx=0;
        node.vy=0;
      });
      draw(performance.now());
    };

    const onPointerMove=(event:PointerEvent)=>{
      if(reduced||event.pointerType==='touch')return;
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
      cancelAnimationFrame(frameId);
      if(reduced)renderStatic();
      else{
        lastTime=performance.now();
        frameId=requestAnimationFrame(draw);
      }
    };
    const onCoarseChange=()=>{coarse=coarseQuery.matches;buildNetwork()};

    const resizeObserver=new ResizeObserver(measure);
    resizeObserver.observe(canvas);
    window.addEventListener('resize',measure,{passive:true});
    window.addEventListener('pointermove',onPointerMove,{passive:true});
    window.addEventListener('pointerdown',onPointerDown,{passive:true});
    window.addEventListener('pointerup',releasePointer,{passive:true});
    window.addEventListener('pointercancel',releasePointer,{passive:true});
    document.addEventListener('mouseleave',releasePointer);
    reducedQuery.addEventListener('change',onMotionChange);
    coarseQuery.addEventListener('change',onCoarseChange);
    measure();
    if(reduced)renderStatic();
    else frameId=requestAnimationFrame(draw);

    return()=>{
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      window.removeEventListener('resize',measure);
      window.removeEventListener('pointermove',onPointerMove);
      window.removeEventListener('pointerdown',onPointerDown);
      window.removeEventListener('pointerup',releasePointer);
      window.removeEventListener('pointercancel',releasePointer);
      document.removeEventListener('mouseleave',releasePointer);
      reducedQuery.removeEventListener('change',onMotionChange);
      coarseQuery.removeEventListener('change',onCoarseChange);
    };
  },[]);

  return <canvas ref={canvasRef} className="auth-quantum-network" aria-hidden="true"/>;
}
