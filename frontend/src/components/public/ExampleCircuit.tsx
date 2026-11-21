import type {PreviewKind, RegisterWidth} from './previewPresets';

// Each column is one layer of independent gates or one ordered controlled-X.
export function ExampleCircuit({kind, width}: {kind: Exclude<PreviewKind,'classical-baseline'>; width:RegisterWidth}) {
  const wires = Array.from({length:width}, (_, i)=>i);
  type Column = string | {control:number; target:number};
  const ring = wires.map(control=>({control,target:(control+1)%width}));
  const columns: Column[] = kind==='quantum-kernel'?['H','Rz(x)','Rz(−z)','H']:['Ry','Rot',...ring,'Rot',...ring];
  const y=(wire:number)=>23+29*wire;
  const span=55+columns.length*46;
  return <figure className="example-circuit"><figcaption>Example circuit <span>{width} wires</span></figcaption>
    <div className="example-circuit-scroll" tabIndex={0} role="region" aria-label="Scrollable example circuit"><svg viewBox={'0 0 '+span+' '+(width*29+16)} style={{minWidth:span*.8}} role="img" aria-label={kind+' circuit on '+width+' qubits'}>
      {wires.map(wire=><g key={wire}><text x="2" y={y(wire)+4}>{'q'+wire}</text><line x1="24" x2={span-3} y1={y(wire)} y2={y(wire)}/></g>)}
      {columns.map((gate,i)=>{const x=52+i*46;return <g key={i}>{typeof gate==='string'?wires.map(wire=><g key={wire}>
        <rect x={x-18} y={y(wire)-10} width="36" height="20" rx="4"/><text x={x} y={y(wire)+3} textAnchor="middle">{gate}</text>
      </g>):<g><line x1={x} x2={x} y1={y(gate.control)} y2={y(gate.target)}/><circle className="control" cx={x} cy={y(gate.control)} r="3.8"/>
        <circle cx={x} cy={y(gate.target)} r="7"/><path d={'M'+(x-5)+' '+y(gate.target)+'h10 M'+x+' '+(y(gate.target)-5)+'v10'}/></g>}</g>})}
    </svg></div>
  </figure>;
}
