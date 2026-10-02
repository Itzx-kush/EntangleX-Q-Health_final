import {useEffect,useLayoutEffect,useRef,useState,type ReactNode} from 'react';
import {ArrowLeft,ArrowRight,Atom,FlaskConical,Github,ShieldCheck,TriangleAlert} from 'lucide-react';
import {useNavigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import {useGuestMigration} from './GuestMigrationProvider';
import {LogoIntro} from '../components/LogoIntro';
import {PublicExperience} from '../components/PublicExperience';
import {QuantumNetworkBackground} from '../components/QuantumNetworkBackground';
import './auth.css';

function applyStoredTheme(){
  const stored=localStorage.getItem('qhealth-theme')||'research';
  const dark=stored==='dark'||(stored==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark',dark);
  document.documentElement.dataset.theme=dark?'dark':'research';
}

function GoogleMark(){
  return <svg className="auth-google-mark" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.54h3.24c1.9-1.75 2.98-4.32 2.98-7.41Z"/>
    <path fill="#34A853" d="M12 22c2.7 0 4.98-.9 6.63-2.36l-3.24-2.54c-.9.6-2.05.96-3.39.96-2.61 0-4.83-1.77-5.62-4.14H3.04v2.62A10 10 0 0 0 12 22Z"/>
    <path fill="#FBBC05" d="M6.38 13.92A6.01 6.01 0 0 1 6.07 12c0-.67.11-1.32.31-1.92V7.46H3.04A10 10 0 0 0 2 12c0 1.61.39 3.14 1.04 4.54l3.34-2.62Z"/>
    <path fill="#EA4335" d="M12 5.94c1.47 0 2.79.5 3.82 1.5l2.88-2.88A9.65 9.65 0 0 0 12 2a10 10 0 0 0-8.96 5.46l3.34 2.62C7.17 7.71 9.39 5.94 12 5.94Z"/>
  </svg>;
}

function AuthLoading(){
  return <main className="auth-loading" aria-live="polite" aria-busy="true">
    <div className="auth-loading-grid" aria-hidden="true"/>
    <div className="auth-loading-lockup">
      <img src="/entanglex-mark.svg" alt="" aria-hidden="true"/>
      <div>
        <strong>ENTANGLEX Q-HEALTH</strong>
        <span>Restoring your research session…</span>
      </div>
    </div>
  </main>;
}

function AccessTransition({guest}:{guest:boolean}){
  return <div className={'auth-access-transition '+(guest?'is-guest':'is-authenticated')} role="status" aria-live="polite" aria-busy="true">
    <div className="auth-convergence" aria-hidden="true">{Array.from({length:16},(_,index)=><i key={index}/>)}</div>
    <div className="auth-transition-mark"><img src="/entanglex-mark.svg" alt="" aria-hidden="true"/><span/></div>
    <span>{guest?'GUEST RESEARCH SESSION':'AUTHENTICATED WORKSPACE'}</span>
    <h2>{guest?'Entering research workspace…':'Workspace ready'}</h2>
    <p>{guest?'Preparing the existing research prototype.':'Restoring your research environment…'}</p>
    <div className="auth-transition-lockup"><img src="/entanglex-logo-dark.svg" alt="EntangleX"/><b>Q-HEALTH</b></div>
    <div className="auth-transition-line" aria-hidden="true"><i/></div>
  </div>;
}

function Welcome({onBack,onOAuthStart}:{onBack:()=>void;onOAuthStart:(provider:'google'|'github')=>void}){
  const {continueAsGuest,error,clearError,isConfigured,signInWithGoogle,signInWithGitHub}=useAuth();
  const {migration,continueGuestSession}=useGuestMigration();
  const preservingGuestWork=Boolean(migration&&migration.status!=='completed');
  const [authenticating,setAuthenticating]=useState<'google'|'github'|null>(null);
  const [enteringGuest,setEnteringGuest]=useState(false);
  const guestTimer=useRef<number|null>(null);

  useEffect(()=>{
    if(error)setAuthenticating(null);
  },[error]);
  useEffect(()=>()=>{if(guestTimer.current!==null)window.clearTimeout(guestTimer.current)},[]);

  const beginOAuth=async(provider:'google'|'github')=>{
    if(authenticating)return;
    setAuthenticating(provider);
    onOAuthStart(provider);
    await (provider==='google'?signInWithGoogle():signInWithGitHub());
  };

  const beginGuest=()=>{
    if(enteringGuest)return;
    setEnteringGuest(true);
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    guestTimer.current=window.setTimeout(()=>{
      if(preservingGuestWork)continueGuestSession();
      else continueAsGuest();
    },reduced?80:520);
  };

  return <main className="auth-entry">
    <QuantumNetworkBackground/>
    <div className="auth-atmosphere" aria-hidden="true">
      <div className="auth-grid"/>
      <span className="auth-depth-glow auth-depth-glow-a"/>
      <span className="auth-depth-glow auth-depth-glow-b"/>
      <span className="auth-depth-vignette"/>
    </div>

    <section className="auth-brand" aria-labelledby="auth-title">
      <button className="auth-back" type="button" onClick={onBack}><ArrowLeft size={14}/> Back to public experience</button>
      <div className="auth-brand-lockup">
        <img src="/entanglex-logo-dark.svg" alt="EntangleX"/>
        <span>Q-HEALTH</span>
      </div>
      <p className="auth-eyebrow">Research access</p>
      <h1 id="auth-title">Enter your research workspace.</h1>
      <p className="auth-intro">Continue with your account or enter as a guest. The existing datasets, experiments and verified research workflows remain ready.</p>

      <div className="auth-capabilities" aria-label="Platform capabilities">
        <div><FlaskConical size={17}/><span><strong>Evidence-led workflows</strong><small>Datasets, models and explainability remain connected.</small></span></div>
        <div><Atom size={17}/><span><strong>Classical + quantum research</strong><small>One controlled environment for existing model workflows.</small></span></div>
      </div>
      <p className="auth-boundary"><ShieldCheck size={14}/> Research prototype · not for clinical diagnosis</p>
    </section>

    <section className="auth-panel" aria-label="Choose how to continue">
      <div className="auth-panel-index" aria-hidden="true"><span>ACCESS</span><strong>03</strong></div>
      <div className="auth-panel-heading">
        <span className="auth-step">ENTANGLEX Q-HEALTH</span>
        <h2>{preservingGuestWork?'Save this research to your workspace':'Enter your research workspace'}</h2>
        <p>{preservingGuestWork?'Your current guest session will remain available during sign-in.':'Choose how you would like to continue.'}</p>
      </div>

      <div className="auth-oauth-actions">
        <button className="auth-oauth-button" type="button" disabled={Boolean(authenticating)||enteringGuest} aria-busy={authenticating==='google'} onClick={()=>void beginOAuth('google')}>
          <GoogleMark/>
          <span>{authenticating==='google'?'Connecting to Google…':'Continue with Google'}</span>
          {authenticating==='google'?<i className="auth-button-progress" aria-hidden="true"/>:<ArrowRight size={17} aria-hidden="true"/>}
        </button>
        <button className="auth-oauth-button" type="button" disabled={Boolean(authenticating)||enteringGuest} aria-busy={authenticating==='github'} onClick={()=>void beginOAuth('github')}>
          <Github className="auth-github-mark" aria-hidden="true"/>
          <span>{authenticating==='github'?'Connecting to GitHub…':'Continue with GitHub'}</span>
          {authenticating==='github'?<i className="auth-button-progress" aria-hidden="true"/>:<ArrowRight size={17} aria-hidden="true"/>}
        </button>
      </div>
      <p className="auth-action-copy">{preservingGuestWork?'Continue with Google or GitHub to add eligible research metadata to My Research.':'Sign in to keep research activity in your private workspace.'}</p>

      <div className="auth-divider"><span>or</span></div>

      <button className="auth-guest-button" type="button" disabled={Boolean(authenticating)||enteringGuest} aria-busy={enteringGuest} onClick={beginGuest}>
        <span>{enteringGuest?'Entering research workspace…':preservingGuestWork?'Return to guest research':'Continue as Guest'}</span>
        {!enteringGuest&&<ArrowRight size={16} aria-hidden="true"/>}
      </button>
      <p className="auth-action-copy">{preservingGuestWork?'Nothing will be removed from this guest session.':'Explore the research prototype without signing in.'}</p>

      {!isConfigured&&!error&&<div className="auth-notice" role="status">
        <TriangleAlert size={16} aria-hidden="true"/>
        <span>Account sign-in is not configured here yet. Guest access remains available.</span>
      </div>}
      {error&&<div className="auth-error" role="alert">
        <TriangleAlert size={17} aria-hidden="true"/>
        <div><strong>Sign-in unavailable</strong><p>{error}</p><button type="button" onClick={clearError}>Dismiss</button></div>
      </div>}

      <p className="auth-footnote">Secure account access · guest exploration remains available</p>
    </section>
    {enteringGuest&&<AccessTransition guest/>}
  </main>;
}

export function AuthGate({children}:{children:ReactNode}){
  const {loading,isAuthenticated,isGuest,error}=useAuth();
  const navigate=useNavigate();
  const [showAccess,setShowAccess]=useState(false);
  const [workspaceReady,setWorkspaceReady]=useState(false);
  const [accessKind,setAccessKind]=useState<'google'|'github'|'guest'|null>(null);

  useLayoutEffect(()=>{
    applyStoredTheme();
    const sync=()=>applyStoredTheme();
    window.addEventListener('qhealth-settings-changed',sync);
    return()=>window.removeEventListener('qhealth-settings-changed',sync);
  },[]);
  useEffect(()=>{
    if(error)setShowAccess(true);
  },[error]);
  useEffect(()=>{
    if(!isAuthenticated&&!isGuest){
      setWorkspaceReady(false);
      return;
    }
    if(isGuest)setAccessKind(current=>current||'guest');
    const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const delay=reduced?140:accessKind==='guest'||isGuest?900:2450;
    const timer=window.setTimeout(()=>setWorkspaceReady(true),delay);
    return()=>window.clearTimeout(timer);
  },[isAuthenticated,isGuest,accessKind]);

  if(loading)return <AuthLoading/>;
  const intro=<LogoIntro/>;

  if(!isAuthenticated&&!isGuest){
    const requestAccess=(destination='/')=>{
      if(destination!==window.location.pathname)navigate(destination);
      setShowAccess(true);
      window.scrollTo({top:0,behavior:'auto'});
    };
    const backToPublic=()=>{
      if(window.location.pathname!=='/')navigate('/');
      setShowAccess(false);
      setAccessKind(null);
      window.scrollTo({top:0,behavior:'auto'});
    };
    return <>{intro}{showAccess?<Welcome onBack={backToPublic} onOAuthStart={setAccessKind}/>:<PublicExperience onRequestAccess={requestAccess}/>}</>;
  }

  const guestAccess=accessKind==='guest'||isGuest;
  return <>{intro}<div className={'workspace-reveal-shell '+(workspaceReady?'is-ready ':'')+(guestAccess?'is-guest':'is-authenticated')}>{children}</div>{!workspaceReady&&<AccessTransition guest={guestAccess}/>}</>;
}
