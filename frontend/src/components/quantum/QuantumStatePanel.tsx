import {useState} from 'react';
import {Atom,Info,Radio} from 'lucide-react';
import {Badge,Card} from '../ui';
import type {QuantumVisualizationContract} from '../../types/quantumVisualization';

type View='probability'|'amplitude'|'phase'|'bloch'|'measurement';
const viewLabels:Record<View,string>={probability:'Probability',amplitude:'Amplitude',phase:'Phase',bloch:'Bloch',measurement:'Measurements'};

function unavailableCopy(status:string){
  if(status==='STRUCTURE_ONLY')return 'Structural preview only. No quantum state was simulated for this context.';
  if(status==='INSUFFICIENT_REPRESENTATION')return 'An encoded representation is not available for this dataset context.';
  if(status==='NOT_APPLICABLE')return 'This state view does not apply to the selected model or simulator.';
  return 'State visualization is not available for the current configuration.';
}

function ProbabilityView({contract}:{contract:QuantumVisualizationContract}){
  const {basis_states:basis,normalized_probability:probabilities}=contract.state;
  if(!basis||!probabilities||basis.length!==probabilities.length||!basis.length){
    return <p className="ql-view-empty">Normalized probability output was not returned by the backend.</p>;
  }
  const rows=basis.map((state,index)=>({state,probability:probabilities[index]}))
    .filter((item)=>Number.isFinite(item.probability))
    .sort((left,right)=>right.probability-left.probability);
  return <div className="ql-probability-list" role="list" aria-label="Backend probability distribution">
    {rows.map((item)=><div className="ql-probability-row" role="listitem" key={item.state}>
      <span className="ql-mono">{`|${item.state}⟩`}</span>
      <span className="ql-probability-track" aria-hidden="true"><i style={{width:`${Math.max(0,Math.min(100,item.probability*100))}%`}}/></span>
      <strong>{(item.probability*100).toFixed(2)}%</strong>
    </div>)}
  </div>;
}

function AmplitudeView({contract}:{contract:QuantumVisualizationContract}){
  const state=contract.state;
  const basis=state.basis_states;
  const real=state.amplitude_real;
  const imaginary=state.amplitude_imaginary;
  const magnitude=state.amplitude_magnitude;
  if(!basis||!real||!imaginary||!magnitude||!basis.length){
    return <p className="ql-view-empty">Statevector amplitudes were not returned by the backend.</p>;
  }
  return <div className="ql-amplitude-list" role="list" aria-label="Simulator statevector amplitudes">
    {basis.map((label,index)=><div className="ql-amplitude-row" role="listitem" key={label}>
      <span className="ql-mono">{`|${label}⟩`}</span>
      <span className="ql-amplitude-track" aria-hidden="true"><i style={{width:`${Math.max(0,Math.min(100,magnitude[index]*100))}%`}}/></span>
      <code>{real[index]?.toFixed(4)} {Number(imaginary[index])<0?'−':'+'} {Math.abs(Number(imaginary[index])).toFixed(4)}i</code>
      <small>|a| {magnitude[index]?.toFixed(4)}</small>
    </div>)}
  </div>;
}

function PhaseView({contract}:{contract:QuantumVisualizationContract}){
  const basis=contract.state.basis_states;
  const phase=contract.state.phase;
  if(!basis||!phase||!basis.length)return <p className="ql-view-empty">Phase values were not returned by the backend.</p>;
  return <div className="ql-phase-list" role="list" aria-label="Statevector phase in radians">
    {basis.map((label,index)=>{
      const radians=phase[index];
      const position=radians===null||radians===undefined?null:Math.max(0,Math.min(100,((radians+Math.PI)/(2*Math.PI))*100));
      return <div className="ql-phase-row" role="listitem" key={label}>
        <span className="ql-mono">{`|${label}⟩`}</span>
        <span className="ql-phase-track" aria-hidden="true">{position!==null&&<i style={{left:`${position}%`}}/>}</span>
        <strong>{radians===null||radians===undefined?'Undefined':`${radians.toFixed(3)} rad`}</strong>
      </div>;
    })}
    <div className="ql-phase-scale"><span>−π</span><span>0</span><span>π</span></div>
  </div>;
}

function MeasurementView({contract}:{contract:QuantumVisualizationContract}){
  const counts=contract.measurement.counts||contract.state.measurement_counts;
  if(!counts||!Object.keys(counts).length)return <p className="ql-view-empty">Backend measurement counts were not returned.</p>;
  const rows=Object.entries(counts).filter(([,count])=>Number.isFinite(count)&&count>=0).sort((left,right)=>right[1]-left[1]);
  const maximum=Math.max(1,...rows.map(([,count])=>count));
  const total=rows.reduce((sum,[,count])=>sum+count,0);
  return <div className="ql-measurement-list" role="list" aria-label="Backend simulator measurement counts">
    <p>Returned shot counts{contract.measurement.shots??contract.state.shots?` · ${contract.measurement.shots??contract.state.shots} shots`:''}. Counts are simulator outputs, not hardware measurements.</p>
    {rows.map(([basis,count])=><div className="ql-measurement-row" role="listitem" key={basis}>
      <span className="ql-mono">{`|${basis}⟩`}</span><span className="ql-measurement-track" aria-hidden="true"><i style={{width:`${count/maximum*100}%`}}/></span><strong>{count.toLocaleString()}</strong>
    </div>)}
    <small>{total.toLocaleString()} total returned counts{contract.measurement.shots===null&&contract.state.shots===null?' (summed from backend counts)':''}.</small>
  </div>;
}

function BlochView({contract}:{contract:QuantumVisualizationContract}){
  const qubits=contract.bloch.qubits;
  if(!qubits?.length)return <p className="ql-view-empty">Reduced-state Bloch vectors were not returned by the backend.</p>;
  return <div className="ql-bloch-grid">
    {qubits.map((qubit)=><article className="ql-bloch-qubit" key={qubit.qubit_index}>
      <div className="ql-bloch-title"><strong>q[{qubit.qubit_index}]</strong><span>reduced single-qubit state</span></div>
      <svg viewBox="0 0 100 100" role="img" aria-label={`Bloch projection for qubit ${qubit.qubit_index}: x ${qubit.x.toFixed(3)}, y ${qubit.y.toFixed(3)}, z ${qubit.z.toFixed(3)}`}>
        <circle cx="50" cy="50" r="36" className="ql-bloch-ring"/>
        <line x1="13" x2="87" y1="50" y2="50" className="ql-bloch-axis"/>
        <line x1="50" x2="50" y1="13" y2="87" className="ql-bloch-axis"/>
        <text x="8" y="54" className="ql-bloch-mark">−x</text><text x="82" y="54" className="ql-bloch-mark">+x</text>
        <text x="53" y="17" className="ql-bloch-mark">|0⟩ +z</text><text x="53" y="91" className="ql-bloch-mark">|1⟩ −z</text>
        <line x1="50" y1="50" x2={50+Math.max(-1,Math.min(1,qubit.x))*34} y2={50-Math.max(-1,Math.min(1,qubit.z))*34} className="ql-bloch-vector"/>
        <circle cx={50+Math.max(-1,Math.min(1,qubit.x))*34} cy={50-Math.max(-1,Math.min(1,qubit.z))*34} r="3.5" className="ql-bloch-point"/>
      </svg>
      <div className="ql-bloch-values">
        <span>x <strong>{qubit.x.toFixed(3)}</strong></span>
        <span>y <strong>{qubit.y.toFixed(3)}</strong></span>
        <span>z <strong>{qubit.z.toFixed(3)}</strong></span>
        <span>Purity <strong>{qubit.purity.toFixed(3)}</strong></span>
        {qubit.polar_angle!==null&&<span>θ <strong>{qubit.polar_angle.toFixed(3)}</strong></span>}
        {qubit.azimuth!==null&&<span>φ <strong>{qubit.azimuth.toFixed(3)}</strong></span>}
      </div>
      <small className="ql-bloch-note">2D x/z projection; y is reported numerically. {qubit.state_representation_status.replaceAll('_',' ')}.</small>
    </article>)}
  </div>;
}

export function QuantumStatePanel({contract,unavailableReason}:{contract:QuantumVisualizationContract|null;unavailableReason?:string}){
  const [requestedView,setRequestedView]=useState<View>('probability');
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
            id={`ql-state-tab-${view}`}
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
                document.getElementById(`ql-state-tab-${next}`)?.focus();
              }
            }}
            key={view}
          >{viewLabels[view]}</button>)}
        </div>
        <div className="ql-state-view" id="ql-state-panel" role="tabpanel" aria-labelledby={`ql-state-tab-${activeView}`}>
          {activeView==='probability'&&<ProbabilityView contract={contract}/>}
          {activeView==='amplitude'&&<AmplitudeView contract={contract}/>}
          {activeView==='phase'&&<PhaseView contract={contract}/>}
          {activeView==='bloch'&&<BlochView contract={contract}/>}
          {activeView==='measurement'&&<MeasurementView contract={contract}/>}
        </div>
      </>:<div className="ql-state-unavailable"><Info size={17}/><div><strong>{unavailableCopy(state.status)}</strong>{state.limitations.map((limitation,index)=><small key={`state-${index}-${limitation}`}>{limitation}</small>)}{contract.measurement.limitations.map((limitation,index)=><small key={`measurement-${index}-${limitation}`}>{limitation}</small>)}</div></div>}
      {contract.state.shots!==null&&contract.state.shots!==undefined&&<p className="ql-state-footnote"><Radio size={14}/> {contract.state.shots.toLocaleString()} local-simulator shots; not hardware measurements.</p>}
    </Card>
    <Card title="Qubit and entanglement analysis" description="Reduced-state views appear only when the backend computed them from an actual simulated state.">
      <div className="ql-entanglement-header">
        <Atom size={17}/>
        <Badge tone={contract.entanglement.status==='AVAILABLE'?'green':'amber'}>{contract.entanglement.status.replaceAll('_',' ')}</Badge>
        {contract.entanglement.indicator!==null&&contract.entanglement.indicator!==undefined&&<strong>{contract.entanglement.indicator?'State-dependent entanglement detected':'No single-qubit-versus-rest entanglement detected'}</strong>}
        {contract.entanglement.participating_qubits?.length? <small>Participants: {contract.entanglement.participating_qubits.map(index=>`q[${index}]`).join(', ')}</small>:null}
      </div>
      {contract.entanglement.status==='AVAILABLE'&&contract.entanglement.reduced_state_measures?.length?
        <div className="ql-reduced-measures">{contract.entanglement.reduced_state_measures.map((measure)=><div key={measure.qubit_index}><span>q[{measure.qubit_index}] purity · linear entropy</span><strong>{measure.purity.toFixed(4)} · {measure.linear_entropy.toFixed(4)}</strong></div>)}</div>
        :<p className="ql-entanglement-limitation">{contract.entanglement.limitations[0]||unavailableCopy(contract.entanglement.status)}</p>}
      {contract.entanglement.method&&<small className="ql-method-note">{contract.entanglement.method}</small>}
    </Card>
  </div>;
}