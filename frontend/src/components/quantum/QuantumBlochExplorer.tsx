import {useRef,useState,type PointerEvent} from 'react';
import {Minus,Plus,RotateCcw} from 'lucide-react';
import {Button,Badge} from '../ui';
import type {QuantumVisualizationBlochQubit} from '../../types/quantumVisualization';

type Props={
  qubits:QuantumVisualizationBlochQubit[];
  selectedQubit?:number|null;
  onSelectQubit?:(index:number)=>void;
};

function project3d(x:number,y:number,z:number,yaw:number,pitch:number,scale:number){
  const yr=yaw*Math.PI/180;
  const pr=pitch*Math.PI/180;
  const x1=x*Math.cos(yr)-z*Math.sin(yr);
  const z1=x*Math.sin(yr)+z*Math.cos(yr);
  const y1=y*Math.cos(pr)-z1*Math.sin(pr);
  return {
    x:50+x1*34*scale,
    y:50-y1*34*scale,
    depth:z1*Math.cos(pr)+y*Math.sin(pr),
  };
}

export function QuantumBlochExplorer({qubits,selectedQubit,onSelectQubit}:Props){
  const available=qubits.filter(qubit=>Number.isFinite(qubit.x)&&Number.isFinite(qubit.y)&&Number.isFinite(qubit.z));
  const [internal,setInternal]=useState(selectedQubit??available[0]?.qubit_index??0);
  const [mode,setMode]=useState<'projection3d'|'fallback2d'>('projection3d');
  const [yaw,setYaw]=useState(-24);
  const [pitch,setPitch]=useState(18);
  const [zoom,setZoom]=useState(1);
  const dragRef=useRef<{x:number;y:number}|null>(null);
  const activeId=selectedQubit??internal;
  const active=available.find(qubit=>qubit.qubit_index===activeId)||available[0];

  if(!active){
    return <div className="ql-view-empty">Reduced-state Bloch vectors were not returned by the backend.</div>;
  }

  const select=(index:number)=>{
    setInternal(index);
    onSelectQubit?.(index);
  };
  const projection=project3d(active.x,active.y,active.z,yaw,pitch,zoom);
  const radius=Math.max(.25,Math.min(1,Math.sqrt(active.x**2+active.y**2+active.z**2)));

  const pointerDown=(event:PointerEvent<SVGSVGElement>)=>{
    dragRef.current={x:event.clientX,y:event.clientY};
    event.currentTarget.setPointerCapture(event.pointerId);
  };
  const pointerMove=(event:PointerEvent<SVGSVGElement>)=>{
    if(!dragRef.current)return;
    const dx=event.clientX-dragRef.current.x;
    const dy=event.clientY-dragRef.current.y;
    dragRef.current={x:event.clientX,y:event.clientY};
    setYaw(value=>value+dx*.65);
    setPitch(value=>Math.max(-75,Math.min(75,value-dy*.5)));
  };
  const pointerUp=(event:PointerEvent<SVGSVGElement>)=>{
    dragRef.current=null;
    try{event.currentTarget.releasePointerCapture(event.pointerId);}catch{}
  };

  const pointX=mode==='projection3d'?projection.x:50+Math.max(-1,Math.min(1,active.x))*34;
  const pointY=mode==='projection3d'?projection.y:50-Math.max(-1,Math.min(1,active.z))*34;

  return <section className="ql-bloch-explorer" aria-label="Interactive Bloch qubit explorer">
    <div className="ql-bloch-header">
      <div>
        <span className="ql-eyebrow">QUBIT / BLOCH SPACE</span>
        <p>Interactive 3D coordinate projection from backend-reported x, y, z values. Drag the sphere to rotate.</p>
      </div>
      <div className="ql-bloch-toolbar">
        <div className="ql-bloch-modes" role="tablist" aria-label="Bloch representation mode">
          <button type="button" role="tab" aria-selected={mode==='projection3d'} className={mode==='projection3d'?'is-active':''} onClick={()=>setMode('projection3d')}>3D projection</button>
          <button type="button" role="tab" aria-selected={mode==='fallback2d'} className={mode==='fallback2d'?'is-active':''} onClick={()=>setMode('fallback2d')}>2D fallback</button>
        </div>
        <Button variant="outline" aria-label="Zoom Bloch view out" onClick={()=>setZoom(value=>Math.max(.75,value-.1))}><Minus size={13}/></Button>
        <Button variant="outline" aria-label="Zoom Bloch view in" onClick={()=>setZoom(value=>Math.min(1.45,value+.1))}><Plus size={13}/></Button>
        <Button variant="outline" aria-label="Reset Bloch view" onClick={()=>{setYaw(-24);setPitch(18);setZoom(1);}}><RotateCcw size={13}/></Button>
      </div>
    </div>

    <div className="ql-bloch-qubit-picker" role="tablist" aria-label="Available qubits">
      {available.map(qubit=><button
        key={qubit.qubit_index}
        type="button"
        role="tab"
        aria-selected={active.qubit_index===qubit.qubit_index}
        className={active.qubit_index===qubit.qubit_index?'is-active':''}
        onClick={()=>select(qubit.qubit_index)}
      >
        q[{qubit.qubit_index}]<span>{qubit.purity.toFixed(3)} purity</span>
      </button>)}
    </div>

    <div className="ql-bloch-stage">
      <div className="ql-bloch-active-label">
        <Badge tone="purple">Qubit q[{active.qubit_index}]</Badge>
        <span>x {active.x.toFixed(3)} · y {active.y.toFixed(3)} · z {active.z.toFixed(3)}</span>
      </div>
      <svg
        viewBox="0 0 100 100"
        role="img"
        aria-label={'Bloch projection for qubit '+active.qubit_index+': x '+active.x.toFixed(3)+', y '+active.y.toFixed(3)+', z '+active.z.toFixed(3)}
        onPointerDown={pointerDown}
        onPointerMove={pointerMove}
        onPointerUp={pointerUp}
        onPointerCancel={pointerUp}
      >
        <defs>
          <radialGradient id="ql-bloch-surface" cx="38%" cy="32%">
            <stop offset="0%" className="ql-bloch-grad-a"/>
            <stop offset="100%" className="ql-bloch-grad-b"/>
          </radialGradient>
        </defs>
        <circle cx="50" cy="50" r="34" className="ql-bloch-ring ql-bloch-surface" fill="url(#ql-bloch-surface)"/>
        {mode==='projection3d'?<>
          <ellipse cx="50" cy="50" rx="34" ry="12" className="ql-bloch-latitude"/>
          <ellipse cx="50" cy="50" rx="14" ry="34" className="ql-bloch-longitude" transform="rotate(-24 50 50)"/>
          <ellipse cx="50" cy="50" rx="31" ry="9" className="ql-bloch-latitude is-back"/>
          <line x1="16" x2="84" y1="50" y2="50" className="ql-bloch-axis"/>
          <line x1="50" x2="50" y1="16" y2="84" className="ql-bloch-axis"/>
          <line x1="24" x2="76" y1="72" y2="28" className="ql-bloch-depth-axis"/>
        </>:<>
          <line x1="14" x2="86" y1="50" y2="50" className="ql-bloch-axis"/>
          <line x1="50" x2="50" y1="14" y2="86" className="ql-bloch-axis"/>
        </>}
        <text x="17" y="55" className="ql-bloch-mark">−X</text>
        <text x="80" y="55" className="ql-bloch-mark">+X</text>
        <text x="53" y="16" className="ql-bloch-mark">+Z</text>
        <text x="53" y="88" className="ql-bloch-mark">−Z</text>
        {mode==='projection3d'&&<text x="74" y="25" className="ql-bloch-mark">+Y</text>}
        <line x1="50" y1="50" x2={pointX} y2={pointY} className="ql-bloch-vector"/>
        <circle cx={pointX} cy={pointY} r={3+radius*1.7} className="ql-bloch-point"/>
      </svg>
      <p className="ql-bloch-note">
        Backend-reported purity {active.purity.toFixed(4)}. {active.state_representation_status.replaceAll('_',' ')}.
        The 2D x/z projection remains available as a fallback.
      </p>
    </div>

    <dl className="ql-bloch-values">
      <div><dt>X</dt><dd>{active.x.toFixed(4)}</dd></div>
      <div><dt>Y</dt><dd>{active.y.toFixed(4)}</dd></div>
      <div><dt>Z</dt><dd>{active.z.toFixed(4)}</dd></div>
      <div><dt>Purity</dt><dd>{active.purity.toFixed(4)}</dd></div>
      {active.polar_angle!==null&&<div><dt>Polar θ</dt><dd>{active.polar_angle.toFixed(4)}</dd></div>}
      {active.azimuth!==null&&<div><dt>Azimuth φ</dt><dd>{active.azimuth.toFixed(4)}</dd></div>}
    </dl>
  </section>;
}
