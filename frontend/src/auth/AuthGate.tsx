import {useEffect, useRef, useState, type ReactNode} from 'react';
import {ArrowLeft, ArrowRight, Github, ShieldCheck} from 'lucide-react';
import {useLocation, useNavigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import {useGuestMigration} from './GuestMigrationProvider';
import {PublicExperience} from '../components/PublicExperience';
import {Brand} from '../components/Brand';
import {useAppearance} from '../lib/appearance';

function Welcome({destination, onBack}: {destination: string; onBack: () => void}) {
  const auth = useAuth();
  const {migration, continueGuestSession} = useGuestMigration();
  const [provider, setProvider] = useState<'google'|'github'|null>(null);
  const preserving = Boolean(migration && migration.status !== 'completed');
  const demo = destination === '/demo';
  const destinationName = destination.split('/').filter(Boolean).map(part => /^[a-f0-9-]{20,}$/i.test(part) ? 'record' : part.replaceAll('-', ' ')).join(' / ');
  const title = preserving ? 'Save your research' : demo ? 'Open the verified demo' : destinationName ? 'Open ' + destinationName : 'Enter your workspace';
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => { if (auth.error) setProvider(null); }, [auth.error]);
  async function signIn(next: 'google'|'github') {
    if (provider) return;
    auth.clearError();
    setProvider(next);
    await (next === 'google' ? auth.signInWithGoogle() : auth.signInWithGitHub());
  }
  return <main className="qx-access">
    <div className="qx-access-top"><Brand/><button className="qx-text-link" onClick={onBack}><ArrowLeft size={16}/> Back to public site</button></div>
    <section className="access-card" aria-labelledby="access-title">
      <p className="qx-kicker">{demo ? 'SIH 26139 · Verified package' : 'Research access'}</p>
      <h1 ref={heading} tabIndex={-1} id="access-title">{title}</h1>
      <p>{preserving ? 'Sign in to keep eligible activity from this guest session.' : demo ? 'Explore the Early Stage Diabetes experiment, its seven models and their recorded evidence.' : 'Explore the research tools as a guest, or sign in to keep your activity in a private workspace.'}</p>
      <button className="qx-button primary" disabled={Boolean(provider)} onClick={preserving ? continueGuestSession : auth.continueAsGuest}>{preserving ? 'Return to guest research' : demo ? 'Continue to demo as guest' : 'Continue as guest'}<ArrowRight size={16}/></button>
      <div className="access-divider">Account access</div>
      {(['google', 'github'] as const).map(id => <button key={id} className="qx-button secondary" disabled={Boolean(provider) || !auth.isConfigured} aria-busy={id === provider} onClick={() => void signIn(id)}>
        {id === 'github' ? <Github size={17}/> : <span className="google-letter" aria-hidden="true">G</span>}
        {id === provider ? 'Connecting…' : 'Continue with ' + (id === 'github' ? 'GitHub' : 'Google')}
      </button>)}
      {!auth.isConfigured && <p className="access-note">Account sign-in is unavailable here. Guest access is available.</p>}
      {auth.error && <p className="access-error" role="alert">{auth.error}</p>}
    </section>
    <p className="access-boundary"><ShieldCheck size={15}/> Academic research prototype · Not for clinical diagnosis</p>
  </main>;
}

export function AuthGate({children}: {children: ReactNode}) {
  const auth = useAuth();
  const {migration} = useGuestMigration();
  const location = useLocation();
  const navigate = useNavigate();
  const [access, setAccess] = useState(false);
  useAppearance(!auth.isGuest && !auth.isAuthenticated);
  useEffect(() => { if (auth.isAuthenticated || auth.isGuest) setAccess(false); }, [auth.isAuthenticated, auth.isGuest]);
  if (auth.loading) return <main className="access-loading" role="status"><Brand/>Restoring your research session…</main>;
  if (auth.isAuthenticated || auth.isGuest) return <>{children}</>;
  if (access || location.pathname !== '/' || auth.error || (migration?.status === 'pending' && !location.state?.publicHome)) return <Welcome destination={location.pathname} onBack={() => {
    auth.clearError(); setAccess(false); navigate('/', {replace: true, state: {publicHome:true}});
  }}/>;
  return <PublicExperience onRequestAccess={(destination = '/') => {
    if (destination !== location.pathname) navigate(destination);
    setAccess(true);
    window.scrollTo({top: 0, behavior: 'instant'});
  }}/>;
}
