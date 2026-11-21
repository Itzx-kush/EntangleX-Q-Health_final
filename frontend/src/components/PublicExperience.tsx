import {ArrowRight, Database, Layers3, ScanLine} from 'lucide-react';
import {PublicHeader} from './public/PublicHeader';
import {PublicHero} from './public/PublicHero';
import {PublicGuidedProcess} from './public/PublicGuidedProcess';
import {PublicResearchDemonstration} from './public/PublicResearchDemonstration';
import {Brand} from './Brand';
import '../styles/public-experience.css';

export function PublicExperience({onRequestAccess}: {onRequestAccess: (destination?: string) => void}) {
  return <div className="qx-public" id="top">
    <a className="qx-skip" href="#main-content">Skip to content</a>
    <PublicHeader onRequestAccess={onRequestAccess}/>
    <main id="main-content">
      <PublicHero onRequestAccess={onRequestAccess}/>
      <section className="benchmark-band" id="demonstration" aria-label="Verified demonstration">
        <div className="qx-wrap benchmark-line">
          <div><p className="qx-kicker">Featured benchmark</p><h2>Early Stage Diabetes Risk Prediction</h2></div>
          <dl><div><dt>Source records</dt><dd>520</dd></div><div><dt>Features</dt><dd>16</dd></div><div><dt>Model artifacts</dt><dd>7</dd></div></dl>
          <button className="qx-text-link" onClick={() => onRequestAccess('/demo')}>Inspect package <ArrowRight size={16}/></button>
        </div>
      </section>
      <PublicResearchDemonstration/>
      <PublicGuidedProcess/>
      <section id="technical-stack" className="qx-section qx-wrap">
        <p className="qx-kicker">Architecture</p><h2>Inside the benchmark</h2>
        <div className="research-notes">
          <article><Database/><h3>Traceable data</h3><p>Dataset versions, fingerprints and fitted transformations connect every evaluation to its inputs.</p></article>
          <article><Layers3/><h3>Model families</h3><p>Compare classical baselines, quantum classifiers and the hybrid PennyLane–PyTorch model on the same experiment.</p></article>
          <article><ScanLine/><h3>Reproducible evidence</h3><p>Inspect held-out scores, robustness results, feature contributions and the limits of each result.</p></article>
        </div>
      </section>
    </main>
    <footer id="about" className="qx-public-footer"><div className="qx-wrap"><Brand/><p>SIH 2026 · PS 26139<br/>Research prototype for computational experiments. Not for clinical diagnosis.</p><button className="qx-text-link" onClick={() => onRequestAccess('/')}>Enter workspace <ArrowRight size={16}/></button></div></footer>
  </div>;
}
