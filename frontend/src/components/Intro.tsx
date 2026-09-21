import {useCallback, useEffect, useState} from 'react';
import type {ReactNode} from 'react';
import {QuantumField} from './QuantumField';

export const INTRO_STORAGE_KEY = 'qhealth-intro-seen-v1';
const INTRO_DURATION = 1680;

function readIntroSeen() { try { return localStorage.getItem(INTRO_STORAGE_KEY) === 'true'; } catch { return false; } }
/** Future Settings can call this without introducing a backend dependency. */
export function replayIntro() { try { localStorage.removeItem(INTRO_STORAGE_KEY); } catch { /* Persistence may be disabled. */ } }

export function IntroExperience({onComplete}: {onComplete: () => void}) {
  const [isReducedMotion, setIsReducedMotion] = useState(false);
  const complete = useCallback(() => { onComplete(); }, [onComplete]);
  useEffect(() => {
    const media = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    const update = () => setIsReducedMotion(media?.matches ?? false);
    update(); media?.addEventListener?.('change', update);
    const timer = window.setTimeout(complete, media?.matches ? 550 : INTRO_DURATION);
    return () => { window.clearTimeout(timer); media?.removeEventListener?.('change', update); };
  }, [complete]);
  return <section className={`intro-screen ${isReducedMotion ? 'intro-reduced' : ''}`} aria-label="EntangleX Q-Health introduction">
    <div className="intro-ambient intro-ambient-one" aria-hidden="true"/><div className="intro-ambient intro-ambient-two" aria-hidden="true"/>
    <div className="intro-frame">
      <div className="intro-mark" aria-hidden="true"><span/><span/><span/><span/></div><QuantumField className="intro-field" />
      <div className="intro-copy"><p className="intro-kicker">ENTANGLEX / RESEARCH SYSTEM</p><h1>Q-HEALTH</h1><p className="intro-subtitle">Hybrid Quantum–Classical Biomedical Research Platform</p></div>
      <div className="intro-meta"><span>SCIENTIFIC VALIDITY FIRST</span><span className="intro-meta-rule"/><span>LOCAL RESEARCH WORKSPACE</span></div>
      <button className="intro-skip" onClick={complete}>Enter workspace <span aria-hidden="true">↗</span></button>
    </div>
  </section>;
}

export function IntroGate({children}: {children: ReactNode}) {
  const [showIntro, setShowIntro] = useState(() => !readIntroSeen());
  const complete = useCallback(() => { try { localStorage.setItem(INTRO_STORAGE_KEY, 'true'); } catch { /* The app remains usable without persistence. */ } setShowIntro(false); }, []);
  return showIntro ? <IntroExperience onComplete={complete}/> : <>{children}</>;
}
