import {useEffect,useState} from 'react';

export function LogoIntro(){
  const [visible,setVisible]=useState(true);
  const [exiting,setExiting]=useState(false);

  useEffect(()=>{
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const exitDelay=reduced?40:1580;
    const removeDelay=reduced?500:1900;
    document.documentElement.classList.add('brand-intro-active');
    document.body.classList.add('brand-intro-active');
    const exitTimer=window.setTimeout(()=>setExiting(true),exitDelay);
    const removeTimer=window.setTimeout(()=>setVisible(false),removeDelay);
    return()=>{
      window.clearTimeout(exitTimer);
      window.clearTimeout(removeTimer);
      document.documentElement.classList.remove('brand-intro-active');
      document.body.classList.remove('brand-intro-active');
    };
  },[]);

  if(!visible)return null;

  return <div className={'brand-intro '+(exiting?'is-exiting':'')} role="status" aria-label="Loading EntangleX Q-Health">
    <div className="brand-intro-stage">
      <span className="brand-intro-orbit brand-intro-orbit-a" aria-hidden="true"/>
      <span className="brand-intro-orbit brand-intro-orbit-b" aria-hidden="true"/>
      <span className="brand-intro-particle brand-intro-particle-a" aria-hidden="true"/>
      <span className="brand-intro-particle brand-intro-particle-b" aria-hidden="true"/>
      <span className="brand-intro-particle brand-intro-particle-c" aria-hidden="true"/>
      <div className="brand-intro-logo">
        <picture>
          <source media="(prefers-color-scheme: dark)" srcSet="/entanglex-logo-dark.svg"/>
          <img src="/entanglex-logo-light.svg" alt="EntangleX"/>
        </picture>
      </div>
      <span className="brand-intro-caption">Q-HEALTH RESEARCH PLATFORM</span>
    </div>
  </div>;
}