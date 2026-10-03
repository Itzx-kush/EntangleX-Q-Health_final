import {useEffect,type RefObject} from 'react';

/**
 * Motion-primitives-style pointer spring.
 *
 * The hook writes normalized motion values directly to the scene root so
 * pointer movement never re-renders the React tree. Descendants opt in with
 * scoped CSS and `data-motion-depth`.
 */
export function usePointerMotion<T extends HTMLElement>(rootRef:RefObject<T|null>){
  useEffect(()=>{
    const root=rootRef.current;
    if(!root)return;

    const reducedQuery=window.matchMedia('(prefers-reduced-motion: reduce)');
    const coarseQuery=window.matchMedia('(pointer: coarse)');
    let frame=0;
    let active=false;
    let targetX=0;
    let targetY=0;
    let currentX=0;
    let currentY=0;
    let energy=0;

    const write=()=>{
      const reduced=reducedQuery.matches;
      const easing=reduced?1:.075;
      currentX+=(targetX-currentX)*easing;
      currentY+=(targetY-currentY)*easing;
      energy+=((active&&!reduced?1:0)-energy)*(reduced?1:.09);
      root.style.setProperty('--motion-x',currentX.toFixed(4));
      root.style.setProperty('--motion-y',currentY.toFixed(4));
      root.style.setProperty('--motion-energy',energy.toFixed(4));
      if(!reduced&&(active||Math.abs(currentX)>.001||Math.abs(currentY)>.001||energy>.001)){
        frame=requestAnimationFrame(write);
      }else frame=0;
    };

    const schedule=()=>{
      if(!frame)frame=requestAnimationFrame(write);
    };
    const move=(event:PointerEvent)=>{
      if(reducedQuery.matches||coarseQuery.matches||event.pointerType==='touch')return;
      targetX=Math.max(-1,Math.min(1,(event.clientX/window.innerWidth-.5)*2));
      targetY=Math.max(-1,Math.min(1,(event.clientY/window.innerHeight-.5)*2));
      active=true;
      schedule();
    };
    const settle=()=>{
      active=false;
      targetX=0;
      targetY=0;
      schedule();
    };
    const motionChange=()=>{
      cancelAnimationFrame(frame);
      frame=0;
      if(reducedQuery.matches){
        currentX=0;
        currentY=0;
        energy=0;
        root.style.setProperty('--motion-x','0');
        root.style.setProperty('--motion-y','0');
        root.style.setProperty('--motion-energy','0');
      }else schedule();
    };

    root.style.setProperty('--motion-x','0');
    root.style.setProperty('--motion-y','0');
    root.style.setProperty('--motion-energy','0');
    window.addEventListener('pointermove',move,{passive:true});
    document.addEventListener('mouseleave',settle);
    window.addEventListener('blur',settle);
    reducedQuery.addEventListener('change',motionChange);
    coarseQuery.addEventListener('change',settle);

    return()=>{
      cancelAnimationFrame(frame);
      window.removeEventListener('pointermove',move);
      document.removeEventListener('mouseleave',settle);
      window.removeEventListener('blur',settle);
      reducedQuery.removeEventListener('change',motionChange);
      coarseQuery.removeEventListener('change',settle);
    };
  },[rootRef]);
}