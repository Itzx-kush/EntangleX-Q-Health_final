import {useState} from 'react';
import {api} from '../services/api';
import {useAction} from '../hooks/useLoad';
import {useDraft} from '../hooks/ExperimentDraft';
import type {Circuit} from '../types';
import {Card, ErrorNotice, Field, JsonView, ModelPicker, Note, PageHeader} from '../components/Common';
import {CircuitDiagram} from '../components/Charts';
import QuantumSettings from '../components/QuantumSettings';
export default function QuantumCircuit() {
  const {draft} = useDraft(); const action = useAction(); const [kind, setKind] = useState<'vqc' | 'qsvc' | 'qnn'>('vqc'); const [modelId, setModelId] = useState(''); const [circuit, setCircuit] = useState<Circuit>();
  async function preview() {const value = await action.run(() => api.post<Circuit>('/quantum/circuit', {quantum: draft.quantum, model_type: kind, seed: draft.seed})); if (value) setCircuit(value);}
  async function registered() {const value = await action.run(() => api.get<Circuit>(`/models/${modelId}/circuit`)); if (value) setCircuit(value);}
    return <><PageHeader eyebrow="08 / Quantum circuit transparency" title="Inspect the quantum representation." description="Examine the feature map and variational ansatz, or retrieve the circuit configuration of a trained model. Circuit preview does not execute a simulator."/><ErrorNotice message={action.error}/><div className="two-columns"><Card title="Parameterized circuit preview"><Field label="Quantum model"><select value={kind} onChange={e => setKind(e.target.value as 'vqc' | 'qsvc' | 'qnn')}><option value="vqc">VQC: feature map + ansatz</option><option value="qsvc">QSVC: kernel feature map</option><option value="qnn">QNN: sampler neural network</option></select></Field><QuantumSettings/><button disabled={action.busy} onClick={() => void preview()}>Generate circuit representation</button></Card><Card title="Registered quantum model"><ModelPicker quantumOnly value={modelId} onChange={setModelId}/><button disabled={!modelId || action.busy} onClick={() => void registered()}>Retrieve registered circuit</button><Note>Qubit count, gate count and logical depth are structural properties. They are not measured hardware performance, runtime speedup or evidence of quantum advantage.</Note></Card></div>
    {circuit && <Card title={`${circuit.model_type.toUpperCase()} / ${circuit.execution_kind}`}><div className="circuit-stats"><span><b>{circuit.qubits}</b> qubits</span><span><b>{circuit.logical_depth}</b> logical depth</span><span><b>{circuit.parameter_count}</b> parameters</span></div><CircuitDiagram circuit={circuit}/><Note>{circuit.limitation}</Note><details><summary>Full text circuit</summary><pre className="circuit-text">{circuit.text}</pre></details><JsonView value={circuit.gate_counts} label="Gate counts"/></Card>}</>;
}
