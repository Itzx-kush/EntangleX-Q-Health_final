import {ArrowRight, Play} from 'lucide-react';
import {PathwayFigure} from './PathwayFigure';

export function PublicHero({onRequestAccess}: {onRequestAccess: (path: string) => void}) {
  return <section className="qx-hero qx-wrap" aria-labelledby="public-hero-title">
    <div className="qx-hero-copy">
      <p className="qx-kicker"><span/> Biomedical machine learning</p>
      <h1 id="public-hero-title">One dataset.<br/><em>Two paths.</em></h1>
      <p className="qx-lede">Compare classical and quantum models on the same biomedical benchmark. Follow the evidence from raw features to held-out results.</p>
      <div className="qx-actions">
        <button className="qx-button primary" onClick={() => onRequestAccess('/demo')}>Open verified SIH demo <ArrowRight size={17}/></button>
        <a className="qx-button secondary" href="#interactive-demo"><Play size={15}/> Try interactive preview</a>
      </div>
    </div>
    <PathwayFigure/>
  </section>;
}
