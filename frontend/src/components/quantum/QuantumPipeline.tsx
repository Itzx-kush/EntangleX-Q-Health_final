import type {QuantumVisualizationContract} from '../../types/quantumVisualization';

type StageState='complete'|'current'|'waiting';
type Props={contract:QuantumVisualizationContract|null;hasPersistedEvidence:boolean;hasDatasetContext?:boolean;hasCircuitStructure?:boolean};

export function QuantumPipeline({contract,hasPersistedEvidence,hasDatasetContext=false,hasCircuitStructure=false}:Props){
  const hasCircuit=Boolean(contract?.circuit.gate_sequence.length||hasCircuitStructure);
  const simulated=contract?.state.status==='AVAILABLE'||contract?.state.status==='SIMULATION_AVAILABLE';
  const states:{label:string;detail:string;status:StageState}[]=[
    {label:'Data',detail:contract?.dataset_context.dataset_name||(contract?'Dataset context unavailable':'Awaiting preview'),status:contract?.dataset_context.status==='AVAILABLE'||hasDatasetContext?'complete':'current'},
    {label:'Encoding',detail:contract?.encoding.method||'Awaiting preview',status:contract?'complete':'waiting'},
    {label:'Circuit',detail:hasCircuit?(contract?'Backend structure loaded':'Persisted fitted structure loaded'):'Awaiting backend structure',status:hasCircuit?'complete':'waiting'},
    {label:'State',detail:simulated?'Simulator output available':contract?.state.status==='STRUCTURE_ONLY'?'State simulation unavailable for this configuration.':contract?'State representation unavailable':hasCircuit?'Fitted structure only · no state data':'Awaiting backend state',status:simulated?'complete':hasCircuit?'current':'waiting'},
    {label:'Measurement',detail:contract?.measurement.status==='AVAILABLE'?'Simulator output available':'No measurement result',status:contract?.measurement.status==='AVAILABLE'?'complete':'waiting'},
    {label:'Evidence',detail:hasPersistedEvidence?'Persisted model evidence':'Open model evidence when available',status:hasPersistedEvidence?'complete':'waiting'},
  ];
  return <section className="ql-pipeline" aria-label="Quantum computation workflow">
    {states.map((stage,index)=><div className={`ql-pipeline-stage is-${stage.status}`} key={stage.label}>
      <span className="ql-pipeline-index" aria-hidden="true">{String(index+1).padStart(2,'0')}</span>
      <div className="ql-pipeline-copy"><strong>{stage.label}</strong><small>{stage.detail}</small></div>
      {index<states.length-1&&<span className="ql-pipeline-connector" aria-hidden="true"/>}
    </div>)}
  </section>;
}