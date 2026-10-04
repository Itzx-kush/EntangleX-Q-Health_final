import {Database,Orbit,Workflow} from 'lucide-react';
import {Badge,Card} from '../ui';
import type {QuantumVisualizationContract,QuantumVisualizationModelType} from '../../types/quantumVisualization';

const modelNames:Record<QuantumVisualizationModelType,string>={
  vqc:'VQC',
  qsvc:'QSVC',
  qnn:'QNN',
  hybrid_pennylane_torch:'PennyLane + PyTorch hybrid',
};

type Props={
  contract:QuantumVisualizationContract|null;
  datasetName?:string;
  modelType:QuantumVisualizationModelType;
  capabilityMessage?:string;
  circuitSource:'preview'|'fitted'|null;
};

function value(input:number|string|null|undefined){
  return input===null||input===undefined||input===''?'Not available':String(input);
}

function safeEncodingValue(input:unknown){
  if(typeof input==='string'||typeof input==='number'||typeof input==='boolean')return String(input);
  return null;
}

export function QuantumContextPanel({contract,datasetName,modelType,capabilityMessage,circuitSource}:Props){
  const circuit=contract?.circuit;
  const provider=contract?.provider;
  const dataset=contract?.dataset_context;
  const status=contract?.state.status??(circuitSource?'STRUCTURE_ONLY':'NOT_AVAILABLE');
  const mappings=contract?.encoding.feature_to_qubit_mapping||[];
  const encodingEntries=Object.entries(contract?.encoding.encoding_parameters||{})
    .filter(([key,value])=>key!=='parameter_names'&&key!=='dataset_representation_configuration'&&safeEncodingValue(value)!==null);
  return <div className="ql-context-stack">
    <section className="ql-context-header" aria-label="Quantum model context">
      <div className="ql-context-title"><div className="ql-context-icon"><Orbit size={19}/></div><div><span className="ql-eyebrow">QUANTUM LAB CONTEXT</span><h2>{dataset?.dataset_name||datasetName||'No dataset selected'}</h2></div></div>
      <div className="ql-context-facts">
        <div><small>MODEL</small><strong>{modelNames[modelType]}</strong></div>
        <div><small>EXECUTION</small><strong>{provider?.execution_mode||'Local simulator'}</strong><span>{provider?.display_name||capabilityMessage||'Backend context loads with circuit preview'}</span></div>
        <div><small>SIMULATION</small><Badge tone={status==='AVAILABLE'?'green':status==='STRUCTURE_ONLY'?'amber':'blue'}>{status.replaceAll('_',' ')}</Badge></div>
        <div><small>LOGICAL QUBITS</small><strong>{value(circuit?.qubits??null)}</strong></div>
        <div><small>CIRCUIT DEPTH</small><strong>{value(circuit?.logical_depth??null)}</strong></div>
        <div><small>PARAMETERS</small><strong>{value(circuit?.parameter_count??null)}</strong></div>
      </div>
      {provider&&<p className="ql-boundary-line"><strong>{provider.backend_id}</strong> · {provider.backend_availability} · hardware {provider.hardware_available?'available':'not available in this execution path'}{circuitSource==='fitted'?' · persisted fitted-circuit record':''}</p>}
    </section>

    <Card title="Feature encoding" description="Feature names and dimensions are metadata. Patient-level feature values are never rendered here.">
      <div className="ql-encoding-flow" aria-label="Feature encoding flow">
        <div><Database size={15}/><strong>Dataset</strong><small>{dataset?.raw_feature_count??'Not available'} raw features</small></div>
        <span aria-hidden="true">→</span>
        <div><Workflow size={15}/><strong>{contract?.encoding.method||'Encoding'}</strong><small>{dataset?.representation_status?.replaceAll('_',' ')||'Preview required'}</small></div>
        <span aria-hidden="true">→</span>
        <div><Orbit size={15}/><strong>Qubit mapping</strong><small>{contract?.encoding.encoded_dimension??'Not available'} configured dimensions</small></div>
      </div>
      {contract?.encoding.description&&<p className="ql-encoding-description">{contract.encoding.description}</p>}
      <div className="ql-encoding-meta">
        <span><small>Raw feature count</small><strong>{value(dataset?.raw_feature_count)}</strong></span>
        <span><small>Represented feature count</small><strong>{value(dataset?.represented_feature_count)}</strong></span>
        <span><small>Representation status</small><strong>{dataset?.representation_status?.replaceAll('_',' ')||'NOT AVAILABLE'}</strong></span>
        <span><small>Representation source</small><strong>{dataset?.representation_source||'Not reported'}</strong></span>
        <span><small>Angle scaling</small><strong>{contract?.encoding.angle_scaling===null||contract?.encoding.angle_scaling===undefined?'Not reported':contract.encoding.angle_scaling?'Enabled':'Disabled'}</strong></span>
        <span><small>Feature-map repetitions</small><strong>{safeEncodingValue(contract?.encoding.encoding_parameters.feature_map_repetitions)??'Not reported'}</strong></span>
      </div>
      {mappings.length>0?<div className="ql-mapping-table-wrap">
        <table className="ql-mapping-table">
          <thead><tr><th>Feature</th><th>Backend parameter</th><th>Qubit</th></tr></thead>
          <tbody>{mappings.map((mapping)=><tr key={`${mapping.feature_index}-${mapping.qubit_index}`}>
            <td>{mapping.feature_name||`Feature ${mapping.feature_index+1}`}</td>
            <td className="ql-mono">{mapping.parameter_name||'Not reported'}</td>
            <td className="ql-mono">q[{mapping.qubit_index}]</td>
          </tr>)}</tbody>
        </table>
      </div>:<p className="ql-encoding-empty">Feature-to-qubit mapping is not available until the backend returns a circuit preview.</p>}
      {contract?.dataset_context.selected_feature_names?.length? <div className="ql-encoding-tags" aria-label="Backend-selected feature names">{contract.dataset_context.selected_feature_names.map((feature,index)=><span key={`${index}-${feature}`}><small>Selected feature {index+1}</small><strong>{feature}</strong></span>)}</div>:null}
      {encodingEntries.length>0&&<div className="ql-encoding-tags">{encodingEntries.map(([key,entry])=><span key={key}><small>{key.replaceAll('_',' ')}</small><strong>{safeEncodingValue(entry)}</strong></span>)}</div>}
      {dataset?.limitations.map((limitation,index)=><p className="ql-encoding-limitation" key={`dataset-${index}-${limitation}`}>{limitation}</p>)}
      {contract?.encoding.limitations.map((limitation,index)=><p className="ql-encoding-limitation" key={`encoding-${index}-${limitation}`}>{limitation}</p>)}
    </Card>
    {contract&&<Card title="Model pathway" description="Model-specific circuit and output semantics reported by the backend.">
      {contract.hybrid_architecture?<div className="ql-hybrid-pathway">
        {[...contract.hybrid_architecture.input_path,...contract.hybrid_architecture.quantum_operations,...contract.hybrid_architecture.output_path].map((stage,index)=><span key={`${index}-${stage}`}>{stage}</span>)}
        <p>{contract.hybrid_architecture.limitation}</p>
      </div>:<div className="ql-model-pathway">
        <span><small>Feature map</small><strong>{contract.circuit.feature_map||'Not reported'}</strong></span>
        <span><small>Variational ansatz</small><strong>{contract.circuit.ansatz||'Not reported / not applicable'}</strong></span>
        <span><small>Measurement path</small><strong>{contract.circuit.measurement_path||'Not reported'}</strong></span>
        <span><small>Output semantics</small><strong>{contract.circuit.output_semantics||'Not reported'}</strong></span>
        <span><small>Model limitation</small><strong>{contract.circuit.limitation||'No additional limitation reported'}</strong></span>
      </div>}
    </Card>}
  </div>;
}