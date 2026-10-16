import {ArrowDown, ArrowRight, ShieldCheck, Sparkles} from 'lucide-react';

interface PublicHeroProps {
  onRequestAccess: (destination?: string) => void;
}

export function PublicHero({onRequestAccess}: PublicHeroProps) {
  const handleScrollCue = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById('guided-process');
    if (target) {
      target.scrollIntoView({behavior: 'smooth'});
    }
  };

  return (
    <section className="public-hero public-shell" aria-labelledby="public-hero-title">
      <div className="public-hero-container">
        {/* Eyebrow badge */}
        <div className="public-hero-eyebrow" data-public-reveal>
          <span className="public-eyebrow-pill">
            <Sparkles size={11} className="public-eyebrow-icon" />
            <span className="public-eyebrow-code">ENTANGLEX // Q-HEALTH</span>
          </span>
          <span className="public-eyebrow-separator">/</span>
          <span className="public-eyebrow-text">Biomedical ML Research Platform</span>
        </div>

        {/* Centered Headline with Dot-Matrix Accent */}
        <h1 id="public-hero-title" className="public-hero-headline" data-public-reveal>
          The Hybrid{' '}
          <span className="public-quantum-matrix" aria-label="Quantum">
            <span className="public-matrix-text">Quantum</span>
            <span className="public-matrix-dots" aria-hidden="true" />
          </span>{' '}
          Intelligence Platform
        </h1>

        {/* Readable supporting copy */}
        <p className="public-hero-subhead" data-public-reveal>
          Accelerate biomedical discovery through traceable data pipelines, controlled classical
          baselines, and variational quantum circuits evaluated under identical scientific
          boundaries.
        </p>

        {/* Prominent CTA buttons above the 850px fold */}
        <div className="public-hero-actions" data-public-reveal>
          <button
            className="public-button is-primary public-hero-btn-primary"
            type="button"
            onClick={() => onRequestAccess('/')}
          >
            <span>Explore Research Workspace</span>
            <ArrowRight size={15} />
          </button>
          <button
            className="public-button is-secondary public-hero-btn-secondary"
            type="button"
            onClick={() => onRequestAccess('/')}
          >
            <span>Sign In / Guest Access</span>
          </button>
        </div>

        {/* Bounded Research Note */}
        <div className="public-hero-boundary" data-public-reveal>
          <ShieldCheck size={13} className="public-boundary-icon" />
          <span>SIH-26139 Research Prototype · Simulated & Empirical Benchmarks · Not for Clinical Diagnosis</span>
        </div>

        {/* Scroll Cue */}
        <a
          href="#guided-process"
          id="hero-scroll-cue"
          className="public-scroll-cue"
          onClick={handleScrollCue}
          data-public-reveal
        >
          <span>Explore the research pathway</span>
          <ArrowDown size={14} />
        </a>
      </div>
    </section>
  );
}
