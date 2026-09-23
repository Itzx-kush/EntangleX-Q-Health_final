import {useEffect,useState} from 'react';

type IntroTheme='light'|'dark';

function resolveIntroTheme():IntroTheme{
  const stored=localStorage.getItem('qhealth-theme');
  if(stored==='dark')return 'dark';
  if(stored==='research')return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
}

export function LogoIntro(){
  const [visible,setVisible]=useState(true);
  const [exiting,setExiting]=useState(false);
  const [theme,setTheme]=useState<IntroTheme>(()=>resolveIntroTheme());

  useEffect(()=>{
    const updateTheme=()=>setTheme(resolveIntroTheme());
    updateTheme();
    window.addEventListener('storage',updateTheme);
    window.addEventListener('qhealth-settings-changed',updateTheme);

    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const exitDelay=reduced?80:1680;
    const removeDelay=reduced?360:2010;

    document.documentElement.classList.add('brand-intro-active');
    document.body.classList.add('brand-intro-active');

    const exitTimer=window.setTimeout(()=>setExiting(true),exitDelay);
    const removeTimer=window.setTimeout(()=>setVisible(false),removeDelay);

    return()=>{
      window.clearTimeout(exitTimer);
      window.clearTimeout(removeTimer);
      document.documentElement.classList.remove('brand-intro-active');
      document.body.classList.remove('brand-intro-active');
      window.removeEventListener('storage',updateTheme);
      window.removeEventListener('qhealth-settings-changed',updateTheme);
    };
  },[]);

  if(!visible)return null;

  return <div className={'brand-intro theme-'+theme+' '+(exiting?'is-exiting':'')} role="status" aria-label="Loading EntangleX Q-Health">
    <div className="brand-intro-vignette" aria-hidden="true"/>
    <div className="brand-intro-aura" aria-hidden="true"/>
    <div className="brand-intro-stage">
      <div className="brand-intro-orbit-orchestra" aria-hidden="true">
        <span className="intro-orbit intro-orbit-a"/>
        <span className="intro-orbit intro-orbit-b"/>
        <span className="intro-orbit intro-orbit-c"/>
        <i className="intro-node intro-node-a"/>
        <i className="intro-node intro-node-b"/>
        <i className="intro-node intro-node-c"/>
        <i className="intro-node intro-node-d"/>
        <i className="intro-node intro-node-e"/>
      </div>

      <div className="brand-intro-halo" aria-hidden="true"/>
      <div className="brand-intro-logo-wrap">
        <img
          className="brand-intro-logo"
          src={theme==='dark'?'/entanglex-logo-dark.svg':'/entanglex-logo-light.svg'}
          alt="EntangleX"
        />
        <span className="brand-intro-shine" aria-hidden="true"/>
      </div>

      <div className="brand-intro-subtitle">
        <span>Q-HEALTH</span>
        <span className="brand-intro-divider"/>
        <span>RESEARCH PLATFORM</span>
      </div>
    </div>
  </div>;
}
