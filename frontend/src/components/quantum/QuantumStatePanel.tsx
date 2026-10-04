import {useEffect,useState} from 'react';
import {Atom,Info,Radio} from 'lucide-react';
import {Badge,Card} from '../ui';
import {QuantumBlochExplorer} from './QuantumBlochExplorer';
import type {QuantumVisualizationContract} from '../../types/quantumVisualization';

type View='probability'|'amplitude'|'phase'|'bloch'|'measurement';
const viewLabels:Record<View,string>={probability:'Probability',amplitude:'Amplitude',phase:'Phase',bloch:'Bloch',measurement:'Measurements'};
type StateRow={state:string;probability:number;index:number};

function unavailableCopy(status:string){
  if(status==='STRUCTURE_ONLY')return 'Structural preview only. No quantum state was simulated for this context.';
  if(status==='INSUFFICIENT_REPRESENTATION')return 'An encoded representation is not available for this dataset context.';
  if(status==='NOT_APPLICABLE')return 'This state view does not apply to the selected model or simulator.';
  return 'State visualization is not available for the current configuration.';
}

function boundedRows(contract:QuantumVisualizationContract):StateRow[]{
  const basis=contract.state.basis_states||[];
  const probabilities=contract.state.normalized_probability||[];
  return basis.map((state,index)=>({state,probability:Number(probabilities[index]),index}))
    .filter(item=>Number.isFinite(item.probability))
    .sort((left,right)=>right.probability-left.probability)
    .slice(0,32);
}

function ProbabilityView({contract,selectedBasisState,onSelectBasis}:{contract:QuantumVisualizationContract;selectedBasisState:string|null;onSelectBasis:(value:string)=>void}){
  const rows=boundedRows(contract);
  const totalStates=contract.state.basis_states?.length||0;
  if(!rows.length)return <p className="ql-view-empty">Normalized probability output was not returned by the backend.</p>;
  return <div className="ql-state-view-stack">
    {totalStates>rows.length&&<p className="ql-bounded-note">Showing the top 32 basis states by normalized probability. {totalStates} states were returned by the backend.</p>}
    <div className="ql-probability-list" role="list" aria-label="Backend probability distribution">
      {rows.map(item=><button type="button" className={'ql-probability-row '+(selectedBasisState===item.state?'is-selected':'')} role="listitem" key={item.state} onClick={()=>onSelectBasis(item.state)} aria-pressed={selectedBasisState===item.state}>
        <span className="ql-mono">{'|'+item.state+'⟩'}</span>
        <span className="ql-probability-track" aria-hidden="true"><i style={{width:Math.max(0,Math.min(100,item.probability*100))+'%'}}/></span>
        <strong>{(item.probability*100).toFixed(2)}%</strong>
      </button>)}
    </div>
  </div>;
}

function AmplitudeView({contract,selectedBasisState,onSelectBasis}:{contract:QuantumVisualizationContract;selectedBasisState:string|null;onSelectBasis:(value:string)=>void}){
  const state=contract.state;
  const basis=state.basis_states;
  const real=state.amplitude_real;
  const imaginary=state.amplitude_imaginary;
  const magnitude=state.amplitude_magnitude;
  if(!basis||!real||!imaginary||!magnitude||!basis.length)return <p className="ql-view-empty">Statevector amplitudes were not returned by the backend.</p>;
  const rows=basis.map((label,index)=>({label,index,magnitude:Number(magnitude[index])}))
    .filter(item=>Number.isFinite(item.magnitude))
    .sort((left,right)=>right.magnitude-left.magnitude)
    .slice(0,32);
  return <div className="ql-state-view-stack" role="list" aria-label="Simulator statevector amplitudes">
    {basis.length>rows.length&&<p className="ql-bounded-note">Showing the top 32 basis states by amplitude magnitude to keep large statevectors readable.</p>}
    <div className="ql-amplitude-list">
      {rows.map(item=><button type="button" className={'ql-amplitude-row '+(selectedBasisState===item.label?'is-selected':'')} role="listitem" key={item.label} onClick={()=>onSelectBasis(item.label)} aria-pressed={selectedBasisState===item.label}>
        <span className="ql-mono">{'|'+item.label+'⟩'}</span>
        <span className="ql-amplitude-track" aria-hidden="true"><i style={{width:Math.max(0,Math.min(100,item.magnitude*100))+'%'}}/></span>
        <code>{Number(real[item.index]).toFixed(4)} {Number(imaginary[item.index])<0?'−':'+'} {Math.abs(Number(imaginary[item.index])).toFixed(4)}i</code>
        <small>|a| {item.magnitude.toFixed(4)}</small>
      </button>)}
    </div>
  </div>;
}

function PhaseView({contract,selectedBasisState,onSelectBasis}:{contract:QuantumVisualizationContract;selectedBasisState:string|null;onSelectBasis:(value:string)=>void}){
  const basis=contract.state.basis_states;
  const phase=contract.state.phase;
  if(!basis||!phase||!basis.length)return <p className="ql-view-empty">Phase values were not returned by the backend.</p>;
  const rows=basis.map((label,index)=>({label,value:phase[index]}))
    .sort((left,right)=>{
      const lv=left.value===null||left.value===undefined?Number.NEGATIVE_INFINITY:left.value;
      const rv=right.value===null||right.value===undefined?Number.NEGATIVE_INFINITY:right.value;
      return rv-lv;
    })
    .slice(0,32);
  return <div className="ql-state-view-stack" role="list" aria-label="Statevector phase in radians">
    {basis.length>rows.length&&<p className="ql-bounded-note">Showing the first 32 returned phase entries for bounded rendering.</p>}
    <div className="ql-phase-list">
      {rows.map(item=>{
        const radians=item.value;
        const position=radians===null||radians===undefined?null:Math.max(0,Math.min(100,((radians+Math.PI)/(2*Math.PI))*100));
        return <button type="button" className={'ql-phase-row '+(selectedBasisState===item.label?'is-selected':'')} role="listitem" key={item.label} onClick={()=>onSelectBasis(item.label)} aria-pressed={selectedBasisState===item.label}>
          <span className="ql-mono">{'|'+item.label+'⟩'}</span>
          <span className="ql-phase-track" aria-hidden="true">{position!==null&&<i style={{left:position+'%'}}/>}</span>
          <strong>{radians===null||radians===undefined?'Undefined':radians.toFixed(3)+' rad'}</strong>
        </button>;
      })}
      <div className="ql-phase-scale"><span>−π</span><span>0</span><span>π</span></div>
    </div>
  </div>;
}

function MeasurementView({contract,selectedBasisState,onSelectBasis}:{contract:QuantumVisualizationContract;selectedBasisState:string|null;onSelectBasis:(value:string)=>void}){
  const counts=contract.measurement.counts||contract.state.measurement_counts;
  if(!counts||!Object.keys(counts).length)return <p className="ql-view-empty">Backend measurement counts were not returned.</p>;
  const rows=Object.entries(counts).filter(([,count])=>Number.isFinite(count)&&count>=0).sort((left,right)=>right[1]-left[1]).slice(0,32);
  const maximum=Math.max(1,...rows.map(([,count])=>count));
  const totalReturned=Object.values(counts).reduce((sum,count)=>sum+count,0);
  const shotCount=contract.measurement.shots??contract.state.shots;
  return <div className="ql-measurement-list" role="list" aria-label="Backend simulator measurement counts">
    {Object.keys(counts).length>rows.length&&<p className="ql-bounded-note">Showing the top 32 measured basis states by count.</p>}
    <p>Returned shot counts{shotCount!==null&&shotCount!==undefined?' · '+shotCount+' shots':''}. Counts are simulator outputs, not hardware measurements.</p>
    {rows.map(([basis,count])=><button type="button" className={'ql-measurement-row '+(selectedBasisState===basis?'is-selected':'')} role="listitem" key={basis} onClick={()=>onSelectBasis(basis)} aria-pressed={selectedBasisState===basis}>
      <span className="ql-mono">{'|'+basis+'⟩'}</span>
      <span className="ql-measurement-track" aria-hidden="true"><i style={{width:count/maximum*100+'%'}}/></span>
      <strong>{count.toLocaleString()}</strong>
    </button>)}
    <small>{totalReturned.toLocaleString()} total returned counts.</small>
  </div>;
}

function BlochView({contract,selectedQubit,onSelectQubit}:{contract:QuantumVisualizationContract;selectedQubit:number|null;onSelectQubit:(index:number)=>void}){
  const qubits=contract.bloch.qubits;
  if(!qubits?.length)return <p className="ql-view-empty">Reduced-state Bloch vectors were not returned by the backend.</p>;
  return <QuantumBlochExplorer qubits={qubits} selectedQubit={selectedQubit} onSelectQubit={onSelectQubit}/>;
}

export function QuantumStatePanel({
  contract,
  unavailableReason,
  selectedQubit=null,
  onQubitSelect,
}:{
  contract:QuantumVisualizationContract|null;
  unavailableReason?:string;
  selectedQubit?:number|null;
  onQubitSelect?:(index:number)=>void;
}){
  const [requestedView,setRequestedView]=useState<View>('probability');
  const [selectedBasisState,setSelectedBasisState]=useState<string|null>(null);

  useEffect(()=>{
    setRequestedView('probability');
    setSelectedBasisState(null);
  },[contract]);

  const selectQubit=(index:number)=>onQubitSelect?.(index);

  if(!contract){
    return <Card title="Quantum state" description="State and measurement views appear only when supplied by the backend.">
      <div className="ql-state-unavailable"><Info size={17}/><span>{unavailableReason||'Load a backend preview to inspect reported state availability. Preview does not execute a simulation.'}</span></div>
    </Card>;
  }

  const state=contract.state;
  const availableViews:View[]=[];
  if(state.status==='AVAILABLE'||state.status==='SIMULATION_AVAILABLE'){
    const basisCount=state.basis_states?.length||0;
    if(basisCount>0&&state.normalized_probability?.length===basisCount)availableViews.push('probability');
    if(basisCount>0&&state.amplitude_real?.length===basisCount&&state.amplitude_imaginary?.length===basisCount&&state.amplitude_magnitude?.length===basisCount)availableViews.push('amplitude');
    if(basisCount>0&&state.phase?.length===basisCount)availableViews.push('phase');
    if(contract.bloch.status==='AVAILABLE'&&contract.bloch.qubits?.length)availableViews.push('bloch');
  }
  if(contract.measurement.status==='AVAILABLE'&&Object.keys(contract.measurement.counts||state.measurement_counts||{}).length>0)availableViews.push('measurement');
  const activeView=availableViews.includes(requestedView)?requestedView:availableViews[0];

  return <div className="ql-state-stack">
    <Card title="Quantum state" description="Only simulator-returned values are plotted. No encoded values or state are inferred in the browser.">
      <div className="ql-state-status" aria-live="polite">
        <Badge tone={state.status==='AVAILABLE'?'green':state.status==='STRUCTURE_ONLY'?'amber':'blue'}>{state.status.replaceAll('_',' ')}</Badge>
        {state.execution_source&&<span>{state.execution_source} · {state.simulator||'simulator not specified'} · {state.backend_id||'backend not specified'}</span>}
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
      </>:<div className="ql-state-unavailable"><Info size={17}/><div><strong>{unavailableCopy(state.status)}</strong>{state.limitations.map((limitation,index)=><small key={'state-'+index+'-'+limitation}>{limitation}</small>)}{contract.measurement.limitations.map((limitation,index)=><small key={'measurement-'+index+'-'+limitation}>{limitation}</small>)}</div></div>}
      {contract.state.shots!==null&&contract.state.shots!==undefined&&<p className="ql-state-footnote"><Radio size={14}/> {contract.state.shots.toLocaleString()} local-simulator shots; not hardware measurements.</p>}
    </Card>

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
