import type {CSSProperties} from 'react';

const nodes = [
  {x: 78, y: 64, r: 3.1, delay: '0ms'}, {x: 156, y: 42, r: 2.3, delay: '180ms'},
  {x: 236, y: 82, r: 3.5, delay: '360ms'}, {x: 306, y: 52, r: 2.5, delay: '540ms'},
  {x: 360, y: 128, r: 3, delay: '720ms'}, {x: 258, y: 160, r: 2.1, delay: '900ms'},
  {x: 126, y: 144, r: 2.8, delay: '1080ms'},
];
const links = [[78, 64, 156, 42], [156, 42, 236, 82], [236, 82, 306, 52], [236, 82, 360, 128], [360, 128, 258, 160], [258, 160, 126, 144], [126, 144, 78, 64], [156, 42, 126, 144]];

/** Restrained scientific geometry. It is decorative and does not represent computation. */
export function QuantumField({className = '', label = 'Decorative quantum-inspired research geometry'}: {className?: string; label?: string}) {
  return <svg className={`quantum-field ${className}`.trim()} viewBox="0 0 440 205" role="img" aria-label={label} focusable="false">
    <g className="quantum-field-grid" aria-hidden="true"><path d="M0 178H440"/><path d="M42 0V205"/><path d="M398 0V205"/></g>
    <g className="quantum-field-links" aria-hidden="true">{links.map(([x1, y1, x2, y2], index) => <line key={`${x1}-${y1}-${x2}-${y2}`} x1={x1} y1={y1} x2={x2} y2={y2} style={{'--line-delay': `${index * 90}ms`} as CSSProperties}/>)}</g>
    <g className="quantum-field-orbits" aria-hidden="true"><ellipse cx="220" cy="103" rx="182" ry="74"/><ellipse cx="220" cy="103" rx="118" ry="54" transform="rotate(-24 220 103)"/></g>
    <g className="quantum-field-nodes" aria-hidden="true">{nodes.map(node => <circle key={`${node.x}-${node.y}`} cx={node.x} cy={node.y} r={node.r} style={{'--node-delay': node.delay} as CSSProperties}/>)}</g>
    <circle className="quantum-field-pulse" cx="236" cy="82" r="8" aria-hidden="true"/>
  </svg>;
}
