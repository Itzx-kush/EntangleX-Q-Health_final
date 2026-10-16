import {useEffect, useRef, useState, type CSSProperties} from 'react';
import {ArrowRight, ArrowUpRight, Atom, BrainCircuit, Database, ShieldCheck, Sparkles} from 'lucide-react';
import {InteractiveQuantumField} from './InteractiveQuantumField';
import {usePointerMotion} from './motion/usePointerMotion';
import {BorderGlow, GlareHover, OuterAurora, OuterMagnet, OuterSpotlight, ShinyText} from './reactbits';
import {PublicHeader} from './public/PublicHeader';
import {PublicHero} from './public/PublicHero';
import {PublicGuidedProcess} from './public/PublicGuidedProcess';
import {PublicResearchDemonstration} from './public/PublicResearchDemonstration';

interface PublicExperienceProps {
  onRequestAccess: (destination?: string) => void;
  exiting?: boolean;
}

export function PublicExperience({onRequestAccess, exiting = false}: PublicExperienceProps) {
  const sceneRef = useRef<HTMLDivElement | null>(null);
  usePointerMotion(sceneRef);

  // Reveal Observer with Progressive Enhancement and Reduced-Motion Resilience
  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>('[data-public-reveal]'));
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    // Baseline fallback: if reduced motion is requested or IntersectionObserver unsupported, reveal immediately
    if (!('IntersectionObserver' in window) || motionQuery.matches) {
      elements.forEach(element => element.classList.add('is-visible'));
      return;
    }

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      {rootMargin: '0px 0px -8% 0px', threshold: 0.05}
    );

    elements.forEach(element => observer.observe(element));

    const handleMotionChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        elements.forEach(element => element.classList.add('is-visible'));
      }
    };
    motionQuery.addEventListener('change', handleMotionChange);

    return () => {
      observer.disconnect();
      motionQuery.removeEventListener('change', handleMotionChange);
    };
  }, []);

  // Scroll progress indicator
  useEffect(() => {
    const root = sceneRef.current;
    if (!root) return;
    let frame = 0;
    const updateProgress = () => {
      const documentHeight = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const progress = Math.max(0, Math.min(1, window.scrollY / documentHeight));
      root.style.setProperty('--public-scroll-progress', progress.toFixed(4));
      frame = 0;
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(updateProgress);
    };
    updateProgress();
    window.addEventListener('scroll', onScroll, {passive: true});
    window.addEventListener('resize', onScroll, {passive: true});
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  const requestAccess = (destination = '/') => {
    onRequestAccess(destination);
  };

  return (
    <div ref={sceneRef} className={'public-experience ' + (exiting ? 'is-exiting' : '')}>
      {/* Scroll indicator & Ambient Background */}
      <div className="public-scroll-progress" aria-hidden="true">
        <i />
      </div>
      <div className="public-background" aria-hidden="true">
        <OuterAurora />
        <span className="public-glow public-glow-a" data-motion-depth="back" />
        <span className="public-glow public-glow-b" data-motion-depth="back" />
        <span className="public-background-vignette" />
        <InteractiveQuantumField />
      </div>

      {/* Refined Public Header */}
      <PublicHeader onRequestAccess={requestAccess} />

      <main id="top">
        {/* Section 1: Hero (Centered, Above-the-fold, Dot-Matrix Display) */}
        <PublicHero onRequestAccess={requestAccess} />

        {/* Section 2: Guided Research Process (Dual-Theme Warm Canvas with Sticky Stepper) */}
        <PublicGuidedProcess />

        {/* Section 3: Interactive Research Demonstration (Functional Workbench replacing abstract art) */}
        <PublicResearchDemonstration />

        {/* Section 4: Controlled Hybrid Architecture & Evidence */}
        <section id="technical-stack" className="public-section public-shell">
          <div className="public-section-heading" data-public-reveal>
            <p className="public-eyebrow">
              <span>04 // ARCHITECTURE</span> Hybrid Intelligence
            </p>
            <div>
              <h2>Two Model Families. One Controlled Research Workflow.</h2>
              <p>
                Classical baselines and variational quantum circuits are benchmarked under identical
                cross-validation partitions, ensuring that every comparative advantage is backed by
                measurable empirical evidence rather than theoretical assumptions.
              </p>
            </div>
          </div>

          <div className="public-hybrid-grid" data-public-reveal>
            <OuterSpotlight className="public-model-spotlight">
              <GlareHover>
                <article className="public-model-panel">
                  <div className="public-model-panel-head">
                    <Database size={18} />
                    <span>CLASSICAL ML BASELINES</span>
                  </div>
                  <h3>Standardized Empirical Baselines</h3>
                  <p className="public-panel-desc">
                    Established tabular and ensemble methods providing standard baseline performance
                    on normalized clinical records.
                  </p>
                  <div className="public-model-list">
                    <span>Logistic Regression</span>
                    <span>Support Vector Machine</span>
                    <span>Random Forest (100 Trees)</span>
                    <span>XGBoost Gradient Boosting</span>
                  </div>
                </article>
              </GlareHover>
            </OuterSpotlight>

            <div className="public-hybrid-bridge" aria-hidden="true">
              <span />
              <strong>+</strong>
              <span />
            </div>

            <OuterSpotlight className="public-model-spotlight">
              <GlareHover>
                <article className="public-model-panel is-quantum">
                  <div className="public-model-panel-head">
                    <Atom size={18} />
                    <span>QUANTUM ML RESEARCH</span>
                  </div>
                  <h3>Simulator-Based Variational Circuits</h3>
                  <p className="public-panel-desc">
                    Parameterized quantum statevector simulations evaluated for non-linear Hilbert
                    space separability and feature correlation.
                  </p>
                  <div className="public-model-list">
                    <span>Variational Quantum Classifier (VQC)</span>
                    <span>Quantum Support Vector (QSVC)</span>
                    <span>Fidelity Kernel Estimation</span>
                    <span>PennyLane + PyTorch Hybrid</span>
                  </div>
                </article>
              </GlareHover>
            </OuterSpotlight>
          </div>
        </section>

        {/* Section 5: Verified Demonstration (Flagship SIH-26139 Package) */}
        <section id="demonstration" className="public-section public-shell">
          <OuterSpotlight className="public-demo-spotlight">
            <div className="public-demo" data-public-reveal>
              <div className="public-demo-copy">
                <p className="public-eyebrow">
                  <span>05 // VERIFIED DEMO</span> Flagship Research Package
                </p>
                <h2>Early Stage Diabetes Risk Prediction</h2>
                <p>
                  Explore the full 11-stage research package covering clinical ingestion,
                  preprocessing, 5-fold stratified cross-validation, 7-model comparison, noise
                  robustness sweeps, and SHAP explainability.
                </p>
                <div className="public-demo-tags">
                  <span>SIH-26139 Benchmark</span>
                  <span>520 Patient Records</span>
                  <span>Precomputed Artifacts</span>
                  <span>Bounded Scientific Evidence</span>
                </div>
                <OuterMagnet>
                  <button
                    className="public-button is-primary"
                    type="button"
                    onClick={() => requestAccess('/demo')}
                  >
                    <span>Launch Verified Demonstration</span>
                    <ArrowRight size={16} />
                  </button>
                </OuterMagnet>
              </div>

              <div className="public-demo-art" aria-label="Verified demonstration research pathway">
                <span className="public-demo-index">SIH / 26139</span>
                <div className="public-demo-rings" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </div>
                <div className="public-demo-mark">
                  <img src="/entanglex-mark.svg" alt="" aria-hidden="true" />
                  <span>
                    VERIFIED
                    <br />
                    RESEARCH
                    <br />
                    PACKAGE
                  </span>
                </div>
              </div>
            </div>
          </OuterSpotlight>
        </section>

        {/* Section 6: Access Gateway & Pre-Footer CTA */}
        <section id="about" className="public-final public-shell" data-public-reveal>
          <div className="public-final-copy">
            <BorderGlow className="public-final-access-badge">
              <span>RESEARCH ACCESS / OPEN REPRODUCIBILITY</span>
            </BorderGlow>
            <p className="public-eyebrow">
              <span>06 // ACCESS</span> Enter the Platform
            </p>
            <h2>Accelerate Your Hybrid Research Workflow.</h2>
            <p>
              Directly access the EntangleX interactive workspace, browse the simulator catalog, or
              inspect complete reproducible research reports.
            </p>
          </div>
          <div className="public-final-actions">
            <OuterMagnet>
              <button
                className="public-button is-primary"
                type="button"
                onClick={() => requestAccess('/')}
              >
                <span>Enter Research Workspace</span>
                <ArrowRight size={16} />
              </button>
            </OuterMagnet>
            <OuterMagnet>
              <button
                className="public-button is-secondary"
                type="button"
                onClick={() => requestAccess('/')}
              >
                <span>Sign in</span>
              </button>
            </OuterMagnet>
          </div>
        </section>
      </main>

      {/* Refined Technical Footer */}
      <footer className="public-footer public-shell">
        <div className="public-footer-top">
          <div className="public-brand">
            <img src="/entanglex-logo-dark.svg" alt="EntangleX" />
            <span className="public-brand-name">Q-HEALTH</span>
          </div>
          <p className="public-footer-mission">
            Hybrid classical-quantum intelligence platform designed for biomedical machine learning,
            transparent feature attribution, and reproducible research validation.
          </p>
        </div>

        <div className="public-footer-bottom">
          <p>© 2026 EntangleX Q-Health · Smart India Hackathon (SIH 2026 · PS 26139)</p>
          <p className="public-footer-disclaimer">
            Academic Research Prototype · Computational Simulations Only · Not Intended for Clinical Diagnosis
          </p>
        </div>
      </footer>
    </div>
  );
}
