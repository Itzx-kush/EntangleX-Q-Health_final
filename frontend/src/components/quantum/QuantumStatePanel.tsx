import {useEffect,useState} from 'react';
import {AlertCircle,AlertTriangle,Atom,CheckCircle2,HelpCircle,Info,Loader2,Play,Radio,RotateCcw,SlidersHorizontal} from 'lucide-react';
import {Badge,Button,Card} from '../ui';
import {QuantumBlochExplorer} from './QuantumBlochExplorer';
import type {QuantumVisualizationContract,QuantumVisualizationModelType} from '../../types/quantumVisualization';

type View='probability'|'amplitude'|'phase'|'bloch'|'measurement';
const viewLabels:Record<View,string>={probability:'Probability',amplitude:'Amplitude',phase:'Phase',bloch:'Bloch',measurement:'Measurements'};

type ProbSortMode='probability'|'index';
type AmpSortMode='magnitude'|'index';
type PhaseSortMode='phase'|'index';

export interface QuantumStatePanelProps {
  contract:QuantumVisualizationContract|null;
  unavailableReason?:string;
  selectedQubit?:number|null;
  onQubitSelect?:(index:number)=>void;
  modelType?:QuantumVisualizationModelType;
  qubitCount?:number;
  encodedVector?:number[];
  onEncodedVectorChange?:(vector:number[])=>void;
  onSimulate?:()=>void;
  isSimulating?:boolean;
  simulationError?:string|null;
  isStale?:boolean;
  backendId?:string;
}

function unavailableCopy(status:string){
  if(status==='STRUCTURE_ONLY')return 'Structural preview only. No quantum state was simulated for this context.';
  if(status==='INSUFFICIENT_REPRESENTATION')return 'An encoded representation is not available for this dataset context.';
  if(status==='NOT_APPLICABLE')return 'This state view does not apply to the selected model or simulator.';
  return 'State visualization is not available for the current configuration.';
}

function formatPercent(value:number):string{
  if(!Number.isFinite(value))return '0.00%';
  if(value===0)return '0.00%';
  const pct=value*100;
  if(pct<0.01&&pct>0)return '< 0.01%';
  return pct.toFixed(2)+'%';
}

function formatDecimal(value:number):string{
  if(!Number.isFinite(value))return '0.0000';
  if(value===0)return '0.0000';
  if(value<0.0001&&value>0)return value.toExponential(2);
  return value.toFixed(4);
}

function formatComplex(real:number,imag:number):string{
  const r=Number(real);
  const i=Number(imag);
  const rStr=r.toFixed(4);
  const iAbs=Math.abs(i).toFixed(4);
  const sign=i<0?'−':'+';
  return `${rStr} ${sign} ${iAbs}i`;
}

function ProbabilityView({
  contract,
  selectedBasisState,
  onSelectBasis,
}:{
  contract:QuantumVisualizationContract;
  selectedBasisState:string|null;
  onSelectBasis:(value:string)=>void;
}){
  const [sortMode,setSortMode]=useState<ProbSortMode>('probability');
  const basis=contract.state.basis_states||[];
  const probabilities=contract.state.normalized_probability||[];
  const totalStates=basis.length;

  if(!basis.length||!probabilities.length)return <p className="ql-view-empty">Normalized probability output was not returned by the backend.</p>;

  const sumProbability=probabilities.reduce((acc,p)=>acc+(Number(p)||0),0);
  const isNormalized=Math.abs(sumProbability-1.0)<1e-3;
  const isExact=contract.state.simulator==='qiskit_local'||contract.state.backend_id==='statevector';

  const rows=basis.map((state,index)=>({
    state,
    probability:Number(probabilities[index]),
    index,
  }))
    .filter(item=>Number.isFinite(item.probability))
    .sort((a,b)=>sortMode==='probability'?b.probability-a.probability:a.index-b.index)
    .slice(0,32);

  const selectedItem=rows.find(r=>r.state===selectedBasisState)||null;

  return <div className="ql-state-view-stack">
    <div className="ql-state-view-header">
      <div className="ql-meta-pills">
        <span className="ql-pill"><small>TOTAL STATES</small><strong>{totalStates}</strong></span>
        <span className="ql-pill"><small>SUM (∑P)</small><strong>{sumProbability.toFixed(4)}</strong> <Badge tone={isNormalized?'green':'amber'}>{isNormalized?'Normalized (100%)':'Non-normal'}</Badge></span>
        <span className="ql-pill"><small>SIMULATION TYPE</small><strong>{isExact?'Exact Statevector Probabilities':`Aer Finite-Shot Frequencies (${contract.state.shots||'N/A'} shots)`}</strong></span>
      </div>
      <div className="ql-sort-controls" role="group" aria-label="Sort probabilities">
        <span className="ql-sort-label">Sort:</span>
        <button type="button" className={`ql-sort-btn ${sortMode==='probability'?'is-active':''}`} onClick={()=>setSortMode('probability')}>Probability ↓</button>
        <button type="button" className={`ql-sort-btn ${sortMode==='index'?'is-active':''}`} onClick={()=>setSortMode('index')}>Basis index ↑</button>
      </div>
    </div>

    {totalStates>rows.length&&<p className="ql-bounded-note">Showing the top 32 basis states by {sortMode==='probability'?'normalized probability':'index'}. {totalStates} states were returned by the backend.</p>}

    <div className="ql-probability-list" role="list" aria-label="Backend probability distribution">
      {rows.map(item=><button
        type="button"
        className={'ql-probability-row '+(selectedBasisState===item.state?'is-selected':'')}
        role="listitem"
        key={item.state}
        onClick={()=>onSelectBasis(item.state)}
        aria-pressed={selectedBasisState===item.state}
      >
        <span className="ql-mono">{'|'+item.state+'⟩'}</span>
        <span className="ql-probability-track" aria-hidden="true"><i style={{width:Math.max(0,Math.min(100,item.probability*100))+'%'}}/></span>
        <strong>{formatPercent(item.probability)}</strong>
        <span className="ql-prob-decimal">{formatDecimal(item.probability)}</span>
      </button>)}
    </div>

    {selectedItem&&<div className="ql-selected-inspector" role="region" aria-label="Selected basis state details">
      <div className="ql-inspector-subhead">
        <span className="ql-mono">Selected state: |{selectedItem.state}⟩ (Basis #{selectedItem.index})</span>
        <Badge tone="purple">Probability: {(selectedItem.probability*100).toFixed(2)}%</Badge>
      </div>
      <div className="ql-inspector-details">
        <div><small>Basis Index</small><strong>#{selectedItem.index}</strong></div>
        <div><small>Binary Bitstring</small><strong className="ql-mono">{selectedItem.state}</strong></div>
        <div><small>Exact Probability</small><strong className="ql-mono">{selectedItem.probability.toFixed(6)}</strong></div>
        {contract.state.amplitude_magnitude&&<div><small>Amplitude Magnitude |α|</small><strong className="ql-mono">{Number(contract.state.amplitude_magnitude[selectedItem.index]).toFixed(4)}</strong></div>}
      </div>
    </div>}
  </div>;
}

function AmplitudeView({
  contract,
  selectedBasisState,
  onSelectBasis,
}:{
  contract:QuantumVisualizationContract;
  selectedBasisState:string|null;
  onSelectBasis:(value:string)=>void;
}){
  const [sortMode,setSortMode]=useState<AmpSortMode>('magnitude');
  const state=contract.state;
  const basis=state.basis_states;
  const real=state.amplitude_real;
  const imaginary=state.amplitude_imaginary;
  const magnitude=state.amplitude_magnitude;

  if(!basis||!real||!imaginary||!magnitude||!basis.length)return <p className="ql-view-empty">Statevector amplitudes were not returned by the backend.</p>;

  const rows=basis.map((label,index)=>({
    label,
    index,
    magnitude:Number(magnitude[index]),
    real:Number(real[index]),
    imaginary:Number(imaginary[index]),
  }))
    .filter(item=>Number.isFinite(item.magnitude))
    .sort((a,b)=>sortMode==='magnitude'?b.magnitude-a.magnitude:a.index-b.index)
    .slice(0,32);

  return <div className="ql-state-view-stack" role="list" aria-label="Simulator statevector amplitudes">
    <div className="ql-state-view-header">
      <div className="ql-math-callout-sm">
        <span className="ql-math-formula">α = a + bi = |α|e^(iφ) · P = |α|² = a² + b²</span>
      </div>
      <div className="ql-sort-controls" role="group" aria-label="Sort amplitudes">
        <span className="ql-sort-label">Sort:</span>
        <button type="button" className={`ql-sort-btn ${sortMode==='magnitude'?'is-active':''}`} onClick={()=>setSortMode('magnitude')}>Magnitude ↓</button>
        <button type="button" className={`ql-sort-btn ${sortMode==='index'?'is-active':''}`} onClick={()=>setSortMode('index')}>Basis index ↑</button>
      </div>
    </div>

    {basis.length>rows.length&&<p className="ql-bounded-note">Showing the top 32 basis states by amplitude magnitude to keep large statevectors readable.</p>}

    <div className="ql-amplitude-list">
      {rows.map(item=><button
        type="button"
        className={'ql-amplitude-row '+(selectedBasisState===item.label?'is-selected':'')}
        role="listitem"
        key={item.label}
        onClick={()=>onSelectBasis(item.label)}
        aria-pressed={selectedBasisState===item.label}
      >
        <span className="ql-mono">{'|'+item.label+'⟩'}</span>
        <span className="ql-amplitude-track" aria-hidden="true"><i style={{width:Math.max(0,Math.min(100,item.magnitude*100))+'%'}}/></span>
        <code>{Number(real[item.index]).toFixed(4)} {Number(imaginary[item.index])<0?'−':'+'} {Math.abs(Number(imaginary[item.index])).toFixed(4)}i</code>
        <small>|a| {item.magnitude.toFixed(4)}</small>
      </button>)}
    </div>
  </div>;
}

function PhaseView({
  contract,
  selectedBasisState,
  onSelectBasis,
}:{
  contract:QuantumVisualizationContract;
  selectedBasisState:string|null;
  onSelectBasis:(value:string)=>void;
}){
  const [sortMode,setSortMode]=useState<PhaseSortMode>('phase');
  const basis=contract.state.basis_states;
  const phase=contract.state.phase;
  const magnitude=contract.state.amplitude_magnitude;

  if(!basis||!phase||!basis.length)return <p className="ql-view-empty">Phase values were not returned by the backend.</p>;

  const rows=basis.map((label,index)=>({
    label,
    index,
    value:phase[index],
    magnitude:magnitude?Number(magnitude[index]):null,
  }))
    .sort((left,right)=>{
      if(sortMode==='index')return left.index-right.index;
      const lv=left.value===null||left.value===undefined?Number.NEGATIVE_INFINITY:left.value;
      const rv=right.value===null||right.value===undefined?Number.NEGATIVE_INFINITY:right.value;
      return rv-lv;
    })
    .slice(0,32);

  return <div className="ql-state-view-stack" role="list" aria-label="Statevector phase in radians">
    <div className="ql-state-view-header">
      <div className="ql-meta-pills">
        <span className="ql-pill"><small>RANGE</small><strong>−π to +π (−180° to +180°)</strong></span>
        <span className="ql-pill"><small>ZERO AMPLITUDE</small><strong>Phase is undefined for |α| = 0</strong></span>
      </div>
      <div className="ql-sort-controls" role="group" aria-label="Sort phases">
        <span className="ql-sort-label">Sort:</span>
        <button type="button" className={`ql-sort-btn ${sortMode==='phase'?'is-active':''}`} onClick={()=>setSortMode('phase')}>Phase ↓</button>
        <button type="button" className={`ql-sort-btn ${sortMode==='index'?'is-active':''}`} onClick={()=>setSortMode('index')}>Basis index ↑</button>
      </div>
    </div>

    {basis.length>rows.length&&<p className="ql-bounded-note">Showing the first 32 returned phase entries for bounded rendering.</p>}

    <div className="ql-phase-list">
      {rows.map(item=>{
        const radians=item.value;
        const position=radians===null||radians===undefined?null:Math.max(0,Math.min(100,((radians+Math.PI)/(2*Math.PI))*100));
        const degrees=radians===null||radians===undefined?null:(radians*180)/Math.PI;

        return <button
          type="button"
          className={'ql-phase-row '+(selectedBasisState===item.label?'is-selected':'')}
          role="listitem"
          key={item.label}
          onClick={()=>onSelectBasis(item.label)}
          aria-pressed={selectedBasisState===item.label}
        >
          <span className="ql-mono">{'|'+item.label+'⟩'}</span>
          <span className="ql-phase-track" aria-hidden="true">
            {position!==null&&<i style={{left:position+'%'}}/>}
          </span>
          <span className="ql-phase-readout">
            <strong className="ql-mono">{radians===null||radians===undefined?'Undefined':radians.toFixed(3)+' rad'}</strong>
            <small className="ql-phase-deg">{degrees===null?'(|α| = 0)':`${degrees.toFixed(1)}°`}</small>
          </span>
        </button>;
      })}
      <div className="ql-phase-scale">
        <span>−π (−180°)</span>
        <span>−π/2</span>
        <span>0 (0°)</span>
        <span>+π/2</span>
        <span>+π (+180°)</span>
      </div>
    </div>
  </div>;
}

function MeasurementView({
  contract,
  selectedBasisState,
  onSelectBasis,
}:{
  contract:QuantumVisualizationContract;
  selectedBasisState:string|null;
  onSelectBasis:(value:string)=>void;
}){
  const counts=contract.measurement.counts||contract.state.measurement_counts;
  const shotCount=contract.measurement.shots??contract.state.shots;

  if(!counts||!Object.keys(counts).length){
    return <div className="ql-measurement-notice">
      <div className="ql-measurement-empty-box">
        <Radio size={20}/>
        <div>
          <strong>Exact Statevector Simulation (No Stochastic Counts)</strong>
          <p>The statevector simulator computes analytical wavefunctions and exact computational-basis probabilities directly, without finite-shot sampling. To view exact probabilities, see the <strong>Probability</strong> tab. To generate finite-sample measurement shot histograms, configure the simulator backend to <code>aer</code> with shots (e.g. 1024 or 4096).</p>
        </div>
      </div>
    </div>;
  }

  const rows=Object.entries(counts).filter(([,count])=>Number.isFinite(count)&&count>=0).sort((left,right)=>right[1]-left[1]).slice(0,32);
  const maximum=Math.max(1,...rows.map(([,count])=>count));
  const totalReturned=Object.values(counts).reduce((sum,count)=>sum+count,0);

  return <div className="ql-measurement-list" role="list" aria-label="Backend simulator measurement counts">
    {Object.keys(counts).length>rows.length&&<p className="ql-bounded-note">Showing the top 32 measured basis states by count.</p>}
    <p>Returned shot counts{shotCount!==null&&shotCount!==undefined?' · '+shotCount+' shots':''}. Counts are simulator outputs, not hardware measurements.</p>
    {rows.map(([basis,count])=>{
      const fraction=totalReturned>0?(count/totalReturned)*100:0;
      return <button
        type="button"
        className={'ql-measurement-row '+(selectedBasisState===basis?'is-selected':'')}
        role="listitem"
        key={basis}
        onClick={()=>onSelectBasis(basis)}
        aria-pressed={selectedBasisState===basis}
      >
        <span className="ql-mono">{'|'+basis+'⟩'}</span>
        <span className="ql-measurement-track" aria-hidden="true"><i style={{width:count/maximum*100+'%'}}/></span>
        <div className="ql-measurement-counts-col">
          <strong>{count.toLocaleString()}</strong>
          <small>{fraction.toFixed(1)}%</small>
        </div>
      </button>;
    })}
    <small>{totalReturned.toLocaleString()} total returned counts.</small>
  </div>;
}

function BlochView({
  contract,
  selectedQubit,
  onSelectQubit,
}:{
  contract:QuantumVisualizationContract;
  selectedQubit:number|null;
  onSelectQubit:(index:number)=>void;
}){
  const qubits=contract.bloch.qubits;
  if(!qubits?.length){
    return <div className="ql-view-empty">
      <p>Reduced-state Bloch vectors were not returned by the backend.</p>
      {contract.state.simulator==='qiskit_aer'&&<p className="mt-1 text-xs text-muted-foreground">Bloch coordinates require statevector simulation to extract phase and single-qubit density matrices. Finite-shot Aer measurement counts alone do not determine Bloch coordinates. Switch backend to statevector to inspect Bloch spheres.</p>}
    </div>;
  }

  return <div className="ql-bloch-view-container">
    <div className="ql-reduced-explanation-banner">
      <HelpCircle size={15}/>
      <div>
        <strong>Single-Qubit Reduced Density Matrices</strong>
        <p>Each Bloch vector represents the partial trace ρ_i = Tr_\i(|ψ⟩⟨ψ|) of the multi-qubit state. Pure unentangled product states lie on the sphere surface (|r| = 1, purity = 1.0). Entangled states produce mixed single-qubit states strictly inside the sphere (|r| &lt; 1, purity &lt; 1.0).</p>
      </div>
    </div>
    <QuantumBlochExplorer qubits={qubits} selectedQubit={selectedQubit} onSelectQubit={onSelectQubit}/>
  </div>;
}

export function QuantumStatePanel({
  contract,
  unavailableReason,
  selectedQubit=null,
  onQubitSelect,
  modelType='vqc',
  qubitCount=2,
  encodedVector,
  onEncodedVectorChange,
  onSimulate,
  isSimulating=false,
  simulationError=null,
  isStale=false,
  backendId='statevector',
}:QuantumStatePanelProps){
  const [requestedView,setRequestedView]=useState<View>('probability');
  const [selectedBasisState,setSelectedBasisState]=useState<string|null>(null);

  useEffect(()=>{
    setRequestedView('probability');
    setSelectedBasisState(null);
  },[contract]);

  const selectQubit=(index:number)=>onQubitSelect?.(index);

  const isHybrid=modelType==='hybrid_pennylane_torch';
  const isQubitLimitExceeded=qubitCount>6;
  const canSimulate=!isHybrid&&!isQubitLimitExceeded&&Boolean(onSimulate);

  const effectiveVector=encodedVector&&encodedVector.length===qubitCount
    ? encodedVector
    : Array(qubitCount).fill(0.5);

  const handleVectorChange=(index:number,value:number)=>{
    const next=[...effectiveVector];
    next[index]=value;
    onEncodedVectorChange?.(next);
  };

  const applyPreset=(presetValue:number)=>{
    onEncodedVectorChange?.(Array(qubitCount).fill(presetValue));
  };

  if(!contract){
    return <Card title="Quantum state" description="State and measurement views appear only when supplied by the backend.">
      <div className="ql-state-unavailable">
        <Info size={17}/>
        <span>{unavailableReason||'Load a backend preview to inspect reported state availability. Preview does not execute a simulation.'}</span>
      </div>
    </Card>;
  }

  const state=contract.state;
  const isSimulated=state.status==='AVAILABLE'||state.status==='SIMULATION_AVAILABLE';
  const availableViews:View[]=[];

  if(isSimulated){
    const basisCount=state.basis_states?.length||0;
    if(basisCount>0&&state.normalized_probability?.length===basisCount)availableViews.push('probability');
    if(basisCount>0&&state.amplitude_real?.length===basisCount&&state.amplitude_imaginary?.length===basisCount&&state.amplitude_magnitude?.length===basisCount)availableViews.push('amplitude');
    if(basisCount>0&&state.phase?.length===basisCount)availableViews.push('phase');
    if(contract.bloch.status==='AVAILABLE'&&contract.bloch.qubits?.length)availableViews.push('bloch');
    if(contract.measurement.status==='AVAILABLE')availableViews.push('measurement');
  }

  const activeView=availableViews.includes(requestedView)?requestedView:availableViews[0];

  return <div className="ql-state-stack">
    {/* Interactive Simulation Controls Bar */}
    <Card title="Circuit simulation" description="Execute local simulation on the configured backend to compute statevector amplitudes, basis probabilities, phases, and reduced Bloch coordinates.">
      <div className="ql-simulation-workbench">
        {isStale&&<div className="ql-stale-banner" role="alert">
          <AlertTriangle size={15}/>
          <span>Circuit configuration changed since last simulation. Results below reflect the previous circuit state.</span>
          {canSimulate&&<Button variant="outline" onClick={onSimulate} disabled={isSimulating}>
            <RotateCcw size={13}/> Re-simulate
          </Button>}
        </div>}

        {simulationError&&<div className="ql-sim-error-banner" role="alert">
          <AlertCircle size={15}/>
          <span>Simulation error: {simulationError}</span>
          {canSimulate&&<Button variant="outline" onClick={onSimulate} disabled={isSimulating}>
            Retry
          </Button>}
        </div>}

        {isHybrid?<div className="ql-sim-unsupported-note">
          <Info size={15}/>
          <span>Simulation is available for pure quantum circuits (VQC, QSVC, QNN). PennyLane + PyTorch hybrid circuits require fitted weights from a completed Model Lab training job.</span>
        </div>:isQubitLimitExceeded?<div className="ql-sim-unsupported-note">
          <AlertTriangle size={15}/>
          <span>Simulation is bounded to ≤ 6 qubits (maximum 64 amplitudes) for responsive browser exploration. Current configuration has {qubitCount} qubits. Reduce qubit count to run simulation.</span>
        </div>:<div className="ql-sim-controls-grid">
          <div className="ql-vector-section">
            <div className="ql-vector-heading">
              <span className="ql-eyebrow">INPUT FEATURE VECTOR (ENCODING STAGE)</span>
              <div className="ql-vector-presets">
                <button type="button" className="ql-preset-btn" onClick={()=>applyPreset(0.0)}>Zeros (0.0)</button>
                <button type="button" className="ql-preset-btn" onClick={()=>applyPreset(0.5)}>Uniform (0.5)</button>
                <button type="button" className="ql-preset-btn" onClick={()=>applyPreset(Math.PI/2)}>π/2 (Superposition)</button>
                <button type="button" className="ql-preset-btn" onClick={()=>applyPreset(Math.PI)}>π (Inverted)</button>
              </div>
            </div>
            <div className="ql-vector-inputs" role="group" aria-label="Input vector feature parameters">
              {effectiveVector.map((val,idx)=><label key={idx} className="ql-vector-field">
                <span>x[{idx}]</span>
                <input
                  type="number"
                  step="0.05"
                  min="-6.28"
                  max="6.28"
                  value={Number(val.toFixed(3))}
                  onChange={e=>{
                    const num=parseFloat(e.target.value);
                    if(Number.isFinite(num))handleVectorChange(idx,num);
                  }}
                  disabled={isSimulating}
                  aria-label={`Feature input x[${idx}]`}
                />
              </label>)}
            </div>
          </div>

          <div className="ql-sim-action-box">
            <div className="ql-sim-backend-pill">
              <small>TARGET ENGINE</small>
              <strong>{backendId==='aer'?'Qiskit Aer Simulator':'Qiskit Statevector'}</strong>
            </div>
            <Button
              variant="primary"
              className="ql-sim-submit-btn"
              onClick={onSimulate}
              disabled={isSimulating||!canSimulate}
            >
              {isSimulating?<><Loader2 className="animate-spin" size={14}/> Simulating circuit…</>:<><Play size={14}/> {isSimulated?'Re-simulate circuit':'Simulate circuit'}</>}
            </Button>
          </div>
        </div>}
      </div>
    </Card>

    {/* Quantum State Output Card */}
    <Card title="Quantum state" description="Only simulator-returned values are plotted. No encoded values or state are inferred in the browser.">
      <div className="ql-state-status" aria-live="polite">
        <Badge tone={state.status==='AVAILABLE'?'green':state.status==='STRUCTURE_ONLY'?'amber':'blue'}>{state.status.replaceAll('_',' ')}</Badge>
        {state.execution_source&&<span>{state.execution_source} · {state.simulator||'simulator not specified'} · {state.backend_id||'backend not specified'}</span>}
        {isSimulated&&contract.state.normalized_probability&&<Badge tone="purple">∑P = {contract.state.normalized_probability.reduce((s,p)=>s+(Number(p)||0),0).toFixed(4)}</Badge>}
      </div>

      {availableViews.length?<>
        <div className="ql-state-tabs" role="tablist" aria-label="Available quantum state views">
          {availableViews.map((view)=><button
            type="button"
            role="tab"
            id={'ql-state-tab-'+view}
            aria-controls="ql-state-panel"
            aria-selected={activeView===view}
            tabIndex={activeView===view?0:-1}
            className={activeView===view?'is-active':''}
            onClick={()=>setRequestedView(view)}
            onKeyDown={event=>{
              if(event.key==='ArrowRight'||event.key==='ArrowLeft'){
                event.preventDefault();
                const step=event.key==='ArrowRight'?1:-1;
                const current=availableViews.indexOf(view);
                const next=availableViews[(current+step+availableViews.length)%availableViews.length];
                setRequestedView(next);
                document.getElementById('ql-state-tab-'+next)?.focus();
              }
            }}
            key={view}
          >{viewLabels[view]}</button>)}
        </div>
        <div className="ql-state-view" id="ql-state-panel" role="tabpanel" aria-labelledby={'ql-state-tab-'+activeView}>
          {activeView==='probability'&&<ProbabilityView contract={contract} selectedBasisState={selectedBasisState} onSelectBasis={setSelectedBasisState}/>}
          {activeView==='amplitude'&&<AmplitudeView contract={contract} selectedBasisState={selectedBasisState} onSelectBasis={setSelectedBasisState}/>}
          {activeView==='phase'&&<PhaseView contract={contract} selectedBasisState={selectedBasisState} onSelectBasis={setSelectedBasisState}/>}
          {activeView==='bloch'&&<BlochView contract={contract} selectedQubit={selectedQubit??null} onSelectQubit={selectQubit}/>}
          {activeView==='measurement'&&<MeasurementView contract={contract} selectedBasisState={selectedBasisState} onSelectBasis={setSelectedBasisState}/>}
        </div>
      </>:<div className="ql-state-unavailable">
        <Info size={17}/>
        <div>
          <strong>{unavailableCopy(state.status)}</strong>
          {state.limitations.map((limitation,index)=><small key={'state-'+index+'-'+limitation}>{limitation}</small>)}
          {contract.measurement.limitations.map((limitation,index)=><small key={'measurement-'+index+'-'+limitation}>{limitation}</small>)}
        </div>
      </div>}
      {contract.state.shots!==null&&contract.state.shots!==undefined&&<p className="ql-state-footnote"><Radio size={14}/> {contract.state.shots.toLocaleString()} local-simulator shots; not hardware measurements.</p>}
    </Card>

    {/* Entanglement Analysis Card */}
    <Card title="Qubit and entanglement analysis" description="Reduced-state views appear only when the backend computed them from an actual simulated state.">
      <div className="ql-entanglement-header">
        <Atom size={17}/>
        <Badge tone={contract.entanglement.status==='AVAILABLE'?'green':'amber'}>{contract.entanglement.status.replaceAll('_',' ')}</Badge>
        {contract.entanglement.indicator!==null&&contract.entanglement.indicator!==undefined&&<strong>{contract.entanglement.indicator?'State-dependent entanglement detected':'No single-qubit-versus-rest entanglement detected'}</strong>}
      </div>
      {contract.entanglement.participating_qubits?.length?
        <div className="ql-entanglement-nodes" aria-label="Backend-reported entanglement participants">
          {contract.entanglement.participating_qubits.map(index=><button type="button" key={index} className={selectedQubit===index?'is-selected':''} onClick={()=>selectQubit(index)} aria-pressed={selectedQubit===index}>q[{index}]<small>participant</small></button>)}
        </div>:null}
      {contract.entanglement.status==='AVAILABLE'&&contract.entanglement.reduced_state_measures?.length?
        <div className="ql-reduced-measures">{contract.entanglement.reduced_state_measures.map(measure=><button type="button" key={measure.qubit_index} className={selectedQubit===measure.qubit_index?'is-selected':''} onClick={()=>selectQubit(measure.qubit_index)} aria-pressed={selectedQubit===measure.qubit_index}><span>q[{measure.qubit_index}] purity · linear entropy</span><strong>{measure.purity.toFixed(4)} · {measure.linear_entropy.toFixed(4)}</strong></button>)}</div>
        :<p className="ql-entanglement-limitation">{contract.entanglement.limitations[0]||unavailableCopy(contract.entanglement.status)}</p>}
      {contract.entanglement.method&&<small className="ql-method-note">{contract.entanglement.method}</small>}
    </Card>
  </div>;
}
