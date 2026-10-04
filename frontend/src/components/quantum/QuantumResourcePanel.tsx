import {Scale} from 'lucide-react';
import {Badge,Card} from '../ui';
import type {QuantumVisualizationContract,QuantumVisualizationResources} from '../../types/quantumVisualization';

type Props={contract:QuantumVisualizationContract|null};

function display(value:number|string|null|undefined){
  return value===null||value===undefined||value===''?'Not available':String(value);
}

function ResourceValue({label,value,detail}:{label:string;value:number|string|null|undefined;detail?:string}){
  return <div className="ql-resource-value"><small>{label}</small><strong>{display(value)}</strong>{detail&&<span>{detail}</span>}</div>;
}

function policyTone(status:string){
  if(status==='within_budget')return 'green' as const;
  if(status==='near_budget')return 'amber' as const;
  if(status==='exceeds_budget')return 'red' as const;
  return 'blue' as const;
}

function ResourceMetrics({resources,circuitParameterCount}:{resources:QuantumVisualizationResources;circuitParameterCount:number|null}){
  return <div className="ql-resource-grid">
    <ResourceValue label="Logical qubits" value={resources.logical_qubits}/>
    <ResourceValue label="Logical depth" value={resources.circuit_depth}/>
    <ResourceValue label="Backend gates" value={resources.total_gates}/>
    <ResourceValue label="Circuit parameters" value={circuitParameterCount}/>
    <ResourceValue label="Parameterized gates" value={resources.parameterized_gates}/>
    <ResourceValue label="Entangling gates" value={resources.entangling_gates}/>
    <ResourceValue label="Configured shots" value={resources.shots}/>
    <ResourceValue label="Requested samples" value={resources.sample_count}/>
    <ResourceValue label="Feature dimension" value={resources.feature_dimension}/>
    <ResourceValue label="Optimizer iterations" value={resources.optimizer_iterations}/>
  </div>;
}

export function QuantumResourcePanel({contract}:Props){
  const resources=contract?.resources;
  return <Card title="Resources and bounded policy" description="Backend-derived circuit resources and the existing resource-advisor policy; no frontend thresholds are added.">
    {resources?<>
      <div className="ql-resource-status">
        <Badge tone={policyTone(resources.bounded_policy_status)}>{resources.bounded_policy_status.replaceAll('_',' ')}</Badge>
        <span>{resources.backend_availability} · {resources.simulator_type}</span>
        <span>Policy {resources.policy_version}</span>
      </div>
      <ResourceMetrics resources={resources} circuitParameterCount={contract?.circuit.parameter_count??null}/>
      {resources.resource_category&&<p className="ql-resource-category"><Scale size={15}/> Backend category: <strong>{resources.resource_category}</strong></p>}
      <ul className="ql-limitation-list">{resources.limitations.map((item)=><li key={item}>{item}</li>)}</ul>
    </>:<div className="ql-state-unavailable">Generate a backend preview to inspect resource fields.</div>}

  </Card>;
}