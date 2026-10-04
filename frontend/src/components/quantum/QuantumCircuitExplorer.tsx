import {useEffect,useMemo,useState,type KeyboardEvent} from 'react';
import {ArrowLeft,ArrowRight,Info,Maximize2,Pause,Play,RotateCcw,ZoomIn,ZoomOut} from 'lucide-react';
import {Button,Badge} from '../ui';
import type {Circuit} from '../../types/qhealth';
import type {QuantumVisualizationCircuit,QuantumVisualizationFeatureMapping,QuantumVisualizationGate} from '../../types/quantumVisualization';

type CircuitSource=QuantumVisualizationCircuit|Circuit;
type Props={
  circuit:CircuitSource;
  sourceLabel?:string;
  selectedQubit?:number|null;
  selectedFeatureIndex?:number|null;
  featureMappings?:QuantumVisualizationFeatureMapping[];
  onSelectionChange?:(gate:QuantumVisualizationGate,position:number)=>void;
};

function gateSequence(circuit:CircuitSource):QuantumVisualizationGate[]{
  if('gate_sequence' in circuit)return [...circuit.gate_sequence].sort((left,right)=>left.gate_index-right.gate_index);
  return circuit.gates.map((gate,gateIndex)=>({
    gate_index:gateIndex,
    name:gate.name,
    gate_type:'not reported',
    qubits:gate.qubits,
    parameters:gate.parameters,
    control_qubits:[],
    target_qubits:[],
  }));
}

function displayGateName(name:string){return name.replaceAll('_',' ').toUpperCase();}

function gateMatchesFeature(gate:QuantumVisualizationGate,mapping?:QuantumVisualizationFeatureMapping){
  if(!mapping)return false;
  const token=mapping.parameter_name||'x['+mapping.feature_index+']';
  return gate.parameters.some(parameter=>parameter.includes(token)||parameter.includes('x['+mapping.feature_index+']'));
}

export function QuantumCircuitExplorer({
  circuit,
  sourceLabel='Backend circuit',
  selectedQubit=null,
  selectedFeatureIndex=null,
  featureMappings=[],
  onSelectionChange,
}:Props){
  const gates=useMemo(()=>gateSequence(circuit),[circuit]);
  const qubitCount=circuit.qubits??0;
  const [selectedIndex,setSelectedIndex]=useState(0);
  const [zoom,setZoom]=useState(1);
  const [playing,setPlaying]=useState(false);

  useEffect(()=>{
    setSelectedIndex(0);
    setZoom(1);
    setPlaying(false);
    if(gates[0])onSelectionChange?.(gates[0],0);
  },[circuit]);

  useEffect(()=>{
    if(!playing)return;
    if(selectedIndex>=gates.length-1){setPlaying(false);return;}
    const timer=window.setTimeout(()=>{
      const next=selectedIndex+1;
      setSelectedIndex(next);
      onSelectionChange?.(gates[next],next);
    },520);
    return ()=>window.clearTimeout(timer);
  },[playing,selectedIndex,gates]);

  if(!qubitCount||!gates.length){
    return <div className="ql-empty-state" role="status">Circuit structure is unavailable for this model.</div>;
  }

  const selectedPosition=Math.max(0,Math.min(gates.length-1,selectedIndex));
  const selectedGate=gates[selectedPosition];
  const detailed='gate_sequence' in circuit;
  const selectedMapping=featureMappings.find(mapping=>mapping.feature_index===selectedFeatureIndex);
  const left=78;
  const column=66;
  const width=Math.max(620,left+gates.length*column+40);
  const top=38;
  const row=54;
  const height=top+qubitCount*row+32;
  const scaledWidth=width*zoom;
  const scaledHeight=height*zoom;
  const yFor=(qubit:number)=>top+qubit*row;

  const selectPosition=(position:number)=>{
    const safe=Math.max(0,Math.min(gates.length-1,position));
    setSelectedIndex(safe);
    onSelectionChange?.(gates[safe],safe);
  };
  const activateFromKey=(event:KeyboardEvent<SVGGElement>,position:number)=>{
    if(event.key==='Enter'||event.key===' '){
      event.preventDefault();
      selectPosition(position);
    }
  };
  const step=(direction:-1|1)=>selectPosition(selectedPosition+direction);
  const zoomBy=(delta:number)=>setZoom(value=>Math.max(.75,Math.min(1.6,Number((value+delta).toFixed(2)))));
  const resetView=()=>{setZoom(1);selectPosition(0);setPlaying(false);};

  return <section className="ql-circuit-explorer" aria-label="Interactive backend circuit explorer">
    <div className="ql-circuit-toolbar">
      <div>
        <span className="ql-eyebrow">CIRCUIT STRUCTURE</span>
        <p>{sourceLabel} · operation order from backend</p>
      </div>
      <div className="ql-circuit-metrics">
        <Badge tone="purple">{qubitCount} qubits</Badge>
        <Badge tone="blue">{circuit.logical_depth??'Depth not reported'} depth</Badge>
        <Badge tone="blue">{circuit.parameter_count??'Parameters not reported'} parameters</Badge>
      </div>
    </div>

    <div className="ql-circuit-tools" aria-label="Circuit view controls">
      <div className="ql-control-group">
        <span className="ql-eyebrow">VIEW</span>
        <Button variant="outline" aria-label="Zoom out circuit" onClick={()=>zoomBy(-.1)} disabled={zoom<=.75}><ZoomOut size={14}/></Button>
        <span className="ql-zoom-readout" aria-live="polite">{Math.round(zoom*100)}%</span>
        <Button variant="outline" aria-label="Zoom in circuit" onClick={()=>zoomBy(.1)} disabled={zoom>=1.6}><ZoomIn size={14}/></Button>
        <Button variant="outline" aria-label="Fit circuit view" onClick={()=>setZoom(1)}><Maximize2 size={14}/><span className="ql-control-label">Fit</span></Button>
        <Button variant="outline" aria-label="Reset circuit view" onClick={resetView}><RotateCcw size={14}/><span className="ql-control-label">Reset</span></Button>
      </div>
      <span className="ql-pan-note">Wide circuits remain horizontally scrollable; zoom preserves gate readability.</span>
    </div>

    {detailed&&<div className="ql-circuit-architecture">
      {circuit.feature_map&&<span><small>Feature map</small><strong>{circuit.feature_map}</strong></span>}
      {circuit.ansatz&&<span><small>Ansatz</small><strong>{circuit.ansatz}</strong></span>}
      {circuit.entanglement_strategy&&<span><small>Entanglement strategy</small><strong>{circuit.entanglement_strategy}</strong></span>}
      {circuit.measurement_path&&<span><small>Measurement path</small><strong>{circuit.measurement_path}</strong></span>}
    </div>}

    <div className="ql-circuit-viewport" role="region" aria-label="Scrollable multi-qubit circuit" tabIndex={0}>
      <div className="ql-circuit-stage" style={{width:scaledWidth,height:scaledHeight}}>
        <svg
          className="ql-circuit-svg"
          width={scaledWidth}
          height={scaledHeight}
          viewBox={'0 0 '+width+' '+height}
          role="img"
          aria-label={'Backend-derived circuit with '+qubitCount+' qubit wires and '+gates.length+' ordered operations'}
        >
          <defs>
            <marker id="ql-gate-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6" className="ql-gate-arrowhead"/>
            </marker>
          </defs>
          {Array.from({length:qubitCount},(_,qubit)=>{
            const rowSelected=selectedQubit===qubit;
            return <g key={'wire-'+qubit}>
              <text x="12" y={yFor(qubit)+4} className={'ql-qubit-label '+(rowSelected?'is-selected':'')}>q[{qubit}]</text>
              <line x1={left-12} x2={width-18} y1={yFor(qubit)} y2={yFor(qubit)} className={'ql-qubit-wire '+(rowSelected?'is-selected':'')}/>
            </g>;
          })}
          {gates.map((gate,position)=>{
            const validQubits=gate.qubits.filter(qubit=>Number.isInteger(qubit)&&qubit>=0&&qubit<qubitCount);
            if(!validQubits.length)return null;
            const x=left+position*column+column/2;
            const active=position===selectedPosition;
            const qubitActive=selectedQubit!==null&&validQubits.includes(selectedQubit);
            const featureActive=gateMatchesFeature(gate,selectedMapping);
            const controls=detailed?gate.control_qubits.filter(qubit=>validQubits.includes(qubit)):[];
            const targets=detailed?gate.target_qubits.filter(qubit=>validQubits.includes(qubit)):[];
            const multi=validQubits.length>1;
            const upper=yFor(Math.min(...validQubits));
            const lower=yFor(Math.max(...validQubits));
            const boxY=multi?(upper+lower)/2:yFor(validQubits[0]);
            return <g
              key={gate.gate_index+'-'+gate.name+'-'+position}
              className={'ql-gate-mark'+(active?' is-selected':'')+(qubitActive?' is-qubit-highlight':'')+(featureActive?' is-feature-highlight':'')}
              role="button"
              tabIndex={active?0:-1}
              aria-label={'Operation '+(gate.gate_index+1)+': '+gate.name+', qubits '+(validQubits.join(', ')||'not reported')+(gate.parameters.length?', parameters '+gate.parameters.join(', '):'')}
              aria-pressed={active}
              onClick={()=>selectPosition(position)}
              onKeyDown={(event)=>activateFromKey(event,position)}
            >
              {multi&&<line x1={x} x2={x} y1={upper} y2={lower} className="ql-gate-connector"/>}
              {controls.length>0&&targets.length>0?<>
                {controls.map(qubit=><circle key={'control-'+qubit} cx={x} cy={yFor(qubit)} r="5" className="ql-gate-control"/>}
                {targets.map((qubit,targetIndex)=><g key={'target-'+qubit}>
                  <rect x={x-20} y={yFor(qubit)-13} width="40" height="26" rx="5" className="ql-gate-box"/>
                  <text x={x} y={yFor(qubit)+3} textAnchor="middle" className="ql-gate-name">{targetIndex===0?displayGateName(gate.name):'×'}</text>
                </g>)}
              </>:<g>
                <rect x={x-22} y={boxY-14} width="44" height="28" rx="6" className="ql-gate-box"/>
                <text x={x} y={boxY+3} textAnchor="middle" className="ql-gate-name">{displayGateName(gate.name)}</text>
              </g>}
              <title>{'#'+(gate.gate_index+1)+' · '+gate.name+(gate.parameters.length?' · '+gate.parameters.join(', '):'')}</title>
            </g>;
          })}
        </svg>
      </div>
    </div>

    <div className="ql-playback">
      <div className="ql-playback-label">
        <span className="ql-eyebrow">STRUCTURAL PLAYBACK</span>
        <div className="ql-playback-status"><Badge tone="amber">No state evolution</Badge><span>Step {selectedPosition+1} / {gates.length}</span></div>
      </div>
      <div className="ql-playback-controls">
        <Button variant="outline" aria-label="Previous operation" disabled={selectedPosition===0} onClick={()=>step(-1)}><ArrowLeft size={15}/></Button>
        <label className="ql-step-range">
          <span>Backend operation step</span>
          <input type="range" min={0} max={Math.max(0,gates.length-1)} value={selectedPosition} onChange={event=>selectPosition(Number(event.target.value))} aria-label="Select backend circuit operation"/>
        </label>
        <Button variant="outline" aria-label={playing?'Pause structural playback':'Play structural playback'} onClick={()=>setPlaying(value=>!value)}>{playing?<Pause size={15}/>:<Play size={15}/>}</Button>
        <Button variant="outline" aria-label="Next operation" disabled={selectedPosition>=gates.length-1} onClick={()=>step(1)}><ArrowRight size={15}/></Button>
      </div>
      <div className="ql-operation-timeline" role="list" aria-label="Backend operation timeline">
        {gates.map((gate,position)=><button key={'timeline-'+gate.gate_index+'-'+position} type="button" className={'ql-operation-node '+(position===selectedPosition?'is-active':'')} onClick={()=>selectPosition(position)} aria-label={'Select operation '+(position+1)+' '+gate.name}>
          <span>{String(position+1).padStart(2,'0')}</span><strong>{displayGateName(gate.name)}</strong>
        </button>)}
      </div>
      <p className="ql-playback-note"><Info size={14}/> This timeline follows the backend operation order. Per-gate circuit-layer indices are not inferred when the backend does not return them.</p>
    </div>

    <div className="ql-gate-inspector" aria-live="polite" aria-atomic="true">
      <div><span className="ql-eyebrow">SELECTED OPERATION</span><strong>{displayGateName(selectedGate.name)}</strong></div>
      <dl>
        <div><dt>Backend order</dt><dd>{selectedGate.gate_index+1}</dd></div>
        <div><dt>Qubits</dt><dd>{selectedGate.qubits.length?selectedGate.qubits.map(qubit=>'q['+qubit+']').join(', '):'Not reported'}</dd></div>
        <div><dt>Gate type</dt><dd>{selectedGate.gate_type}</dd></div>
        <div><dt>Parameters</dt><dd>{selectedGate.parameters.length?selectedGate.parameters.join(', '):'Not reported'}</dd></div>
        <div><dt>Controls</dt><dd>{selectedGate.control_qubits.length?selectedGate.control_qubits.map(qubit=>'q['+qubit+']').join(', '):'Not reported'}</dd></div>
        <div><dt>Targets</dt><dd>{selectedGate.target_qubits.length?selectedGate.target_qubits.map(qubit=>'q['+qubit+']').join(', '):'Not reported'}</dd></div>
        <div><dt>Feature link</dt><dd>{selectedMapping&&gateMatchesFeature(selectedGate,selectedMapping)?'Matches '+(selectedMapping.feature_name||'feature '+(selectedMapping.feature_index+1)):'Not returned'}</dd></div>
      </dl>
    </div>

    {circuit.gate_counts&&Object.keys(circuit.gate_counts).length>0&&<details className="ql-circuit-counts">
      <summary>Backend gate counts</summary>
      <div>{Object.entries(circuit.gate_counts).map(([name,count])=><span key={name}><strong>{name}</strong><small>{count}</small></span>)}</div>
    </details>}
    {detailed&&circuit.limitation&&<p className="ql-circuit-limitation">{circuit.limitation}</p>}
    {'text' in circuit&&<details className="ql-circuit-counts"><summary>Raw circuit text</summary><pre>{circuit.text}</pre></details>}
    {'circuit_text' in circuit&&circuit.circuit_text&&<details className="ql-circuit-counts"><summary>Raw circuit text</summary><pre>{circuit.circuit_text}</pre></details>}
  </section>;
}
