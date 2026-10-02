import {useLayoutEffect,type ReactNode} from 'react';
import {ArrowRight,FlaskConical,ShieldCheck,TriangleAlert} from 'lucide-react';
import {useAuth} from './AuthProvider';
import {useGuestMigration} from './GuestMigrationProvider';
import {LogoIntro} from '../components/LogoIntro';
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
    <img src="/entanglex-mark.svg" alt="" aria-hidden="true"/>
    <div>
      <strong>ENTANGLEX Q-HEALTH</strong>
      <span>Restoring your research session…</span>
    </div>
  </main>;
}

function Welcome(){
  const {continueAsGuest,error,clearError,isConfigured,signInWithGoogle}=useAuth();
  const {migration,continueGuestSession}=useGuestMigration();
  const preservingGuestWork=Boolean(migration&&migration.status!=='completed');

  return <main className="auth-entry">
    <div className="auth-grid" aria-hidden="true"/>
    <div className="auth-orbit auth-orbit-one" aria-hidden="true"/>
    <div className="auth-orbit auth-orbit-two" aria-hidden="true"/>

    <section className="auth-brand" aria-labelledby="auth-title">
      <div className="auth-brand-lockup">
        <img src="/entanglex-logo-light.svg" alt="EntangleX"/>
        <span>Q-HEALTH</span>
      </div>
      <p className="auth-eyebrow">Hybrid intelligence for biomedical research</p>
      <h1 id="auth-title">A rigorous workspace for quantum–classical health research.</h1>
      <p className="auth-intro">Move from verified datasets to reproducible model evidence in one focused research environment.</p>

      <div className="auth-capabilities" aria-label="Platform capabilities">
        <div><FlaskConical size={17}/><span><strong>Evidence-led workflows</strong><small>Datasets, models and explainability remain connected.</small></span></div>
        <div><ShieldCheck size={17}/><span><strong>Research-first safeguards</strong><small>Transparent methods without clinical overclaiming.</small></span></div>
      </div>
    </section>

    <section className="auth-panel" aria-label="Choose how to continue">
      <div className="auth-panel-heading">
        <span className="auth-step">RESEARCH ACCESS</span>
        <h2>{preservingGuestWork?'Save this research to your workspace':'Enter your workspace'}</h2>
        <p>{preservingGuestWork?'Your current guest session will remain available during sign-in.':'Choose the experience that fits this session.'}</p>
      </div>

      <button className="auth-google-button" type="button" onClick={signInWithGoogle}>
        <GoogleMark/>
        <span>Continue with Google</span>
        <ArrowRight size={17} aria-hidden="true"/>
      </button>
      <p className="auth-action-copy">{preservingGuestWork?'Continue with Google to add eligible research metadata to My Research.':'Sign in to keep research activity in your private workspace.'}</p>

      <div className="auth-divider"><span>or</span></div>

      <button className="auth-guest-button" type="button" onClick={preservingGuestWork?continueGuestSession:continueAsGuest}>
        {preservingGuestWork?'Return to guest research':'Continue without signing in'}
      </button>
      <p className="auth-action-copy">{preservingGuestWork?'Nothing will be removed from this guest session.':'Explore the current research prototype with the existing anonymous workflow.'}</p>

      {!isConfigured&&!error&&<div className="auth-notice" role="status">
        <TriangleAlert size={16} aria-hidden="true"/>
        <span>Google sign-in is not configured here yet. Guest access remains available.</span>
      </div>}
      {error&&<div className="auth-error" role="alert">
        <TriangleAlert size={17} aria-hidden="true"/>
        <div><strong>Sign-in unavailable</strong><p>{error}</p><button type="button" onClick={clearError}>Dismiss</button></div>
      </div>}

      <p className="auth-footnote">Research prototype · not for clinical diagnosis</p>
    </section>
  </main>;
}

export function AuthGate({children}:{children:ReactNode}){
  const {loading,isAuthenticated,isGuest}=useAuth();
  useLayoutEffect(()=>{
    applyStoredTheme();
    const sync=()=>applyStoredTheme();
    window.addEventListener('qhealth-settings-changed',sync);
    return()=>window.removeEventListener('qhealth-settings-changed',sync);
  },[]);
  if(loading)return <AuthLoading/>;
  if(!isAuthenticated&&!isGuest)return <Welcome/>;
  return <><LogoIntro/>{children}</>;
}
