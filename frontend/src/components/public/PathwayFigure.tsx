import {useState} from 'react';

const branches = {
  classical: {label: 'Classical', caption: 'Tabular features → baseline estimator → held-out score'},
  quantum: {label: 'Quantum', caption: 'Encoded features → circuit readout → held-out score'},
} as const;

type Branch = keyof typeof branches;

// The two bundles trace the flow of information, not measured patient signals.
function tracePath(branch: Branch, index: number) {
  const direction = branch === 'classical' ? -1 : 1;
  const spread = index - 12;
  const y = 145 + direction * 64 + spread * 2;
  return `M 0 ${145 + spread * .85} C 64 ${145 + spread}, 86 ${145 - spread}, 120 145
    S 204 ${y + spread * 1.5}, 255 ${y} S 335 ${y - spread * 2}, 370 ${y}
    C 437 ${y + spread}, 441 145, 493 145 S 544 ${145 - spread}, 580 ${145 + spread * .8}`;
}

export function PathwayFigure() {
  const [branch, setBranch] = useState<Branch>('quantum');
  return <figure className="pathway-figure">
    <figcaption><span className="instrument-light"/> Research pathway</figcaption>
    <svg viewBox="0 0 580 288" role="img" aria-label="Biomedical features split into classical and quantum paths and rejoin at a shared benchmark">
      <g className="scope-grid" aria-hidden="true">
        {Array.from({length: 15}, (_, i) => <path key={i} d={`M${i * 42} 0v288`}/>)}
        {Array.from({length: 8}, (_, i) => <path key={i} d={`M0 ${i * 42}h580`}/>)}
      </g>
      {(Object.keys(branches) as Branch[]).map(key => <g key={key} className={`scope-traces ${key} ${branch === key ? 'is-selected' : ''}`}>
        {Array.from({length: 25}, (_, i) => <path key={i} d={tracePath(key, i)} />)}
        <path className="scope-pulse" key={branch} pathLength="100" d={tracePath(key, 12)}/>
      </g>)}
      <g className="scope-marks">
        <circle cx="120" cy="145" r="5"/><circle cx="493" cy="145" r="5"/>
        <text x="18" y="121">INPUT</text><text x="515" y="121">EVALUATE</text>
        <text x="244" y="36">CLASSICAL</text><text x="246" y="261">QUANTUM</text>
      </g>
    </svg>
    <div className="scope-footer">
      <div className="scope-controls" aria-label="Inspect a research path">
        {(Object.keys(branches) as Branch[]).map(key => <button key={key} type="button" aria-pressed={branch === key} onClick={() => setBranch(key)}>{branches[key].label}</button>)}
      </div>
      <p aria-live="polite">{branches[branch].caption}</p>
    </div>
  </figure>;
}
