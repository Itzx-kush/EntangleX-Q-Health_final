import {useEffect,useState} from 'react';

export function LogoIntro(){
  const [visible,setVisible]=useState(true);
  const [exiting,setExiting]=useState(false);

  useEffect(()=>{
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const exitDelay=reduced?80:1680;
    const removeDelay=reduced?220:2080;

    document.documentElement.classList.add('brand-intro-active');
    document.body.classList.add('brand-intro-active');

    const releaseScrollLock=()=>{
      document.documentElement.classList.remove('brand-intro-active');
      document.body.classList.remove('brand-intro-active');
    };

    const exitTimer=window.setTimeout(()=>setExiting(true),exitDelay);
    const removeTimer=window.setTimeout(()=>{
      releaseScrollLock();
      setVisible(false);
    },removeDelay);

    return()=>{
      window.clearTimeout(exitTimer);
      window.clearTimeout(removeTimer);
      releaseScrollLock();
    };
  },[]);

  if(!visible)return null;

  return <div className={'brand-intro '+(exiting?'is-exiting':'')} role="status" aria-label="EntangleX Q-Health opening">
    <div className="brand-intro-grid" aria-hidden="true"/>
    <div className="brand-intro-vignette" aria-hidden="true"/>
    <div className="brand-intro-aura" aria-hidden="true"/>

    <div className="brand-intro-network" aria-hidden="true">
      <span className="intro-connection connection-a"/>
      <span className="intro-connection connection-b"/>
      <span className="intro-connection connection-c"/>
      <span className="intro-connection connection-d"/>
      <i className="intro-node intro-node-a"/>
      <i className="intro-node intro-node-b"/>
      <i className="intro-node intro-node-c"/>
      <i className="intro-node intro-node-d"/>
      <i className="intro-node intro-node-e"/>
      <i className="intro-node intro-node-f"/>
      <i className="intro-node intro-node-g"/>
      <i className="intro-tracer intro-tracer-a"/>
      <i className="intro-tracer intro-tracer-b"/>
    </div>

    <div className="brand-intro-stage">
      <div className="brand-intro-kicker" aria-hidden="true">
        <span/>
        <strong>HYBRID RESEARCH SYSTEM</strong>
        <span/>
      </div>

      <div className="brand-intro-halo" aria-hidden="true"/>
      <div className="brand-intro-logo-wrap">
        <img
          className="brand-intro-logo"
          src="/entanglex-logo-dark.svg"
          alt="EntangleX"
        />
        <span className="brand-intro-shine" aria-hidden="true"/>
      </div>

      <div className="brand-intro-identity">
        <span className="brand-intro-product">Q-HEALTH</span>
        <span className="brand-intro-divider" aria-hidden="true"/>
        <span className="brand-intro-description">Hybrid quantum–classical biomedical research</span>
      </div>

      <div className="brand-intro-accent" aria-hidden="true"><span/></div>
    </div>
  </div>;
}
