import { useState, useId } from 'react';
import { Atom, Cpu, Info, Sliders, SlidersHorizontal, Table, Sparkles, RefreshCw, Layers } from 'lucide-react';
import { Badge, Button, Select } from '../ui';
import type {
  QuantumVisualizationFeatureMapping,
  QuantumVisualizationGate,
} from '../../types/quantumVisualization';
import type { QuantumConfig, HybridModelConfig } from '../../types/qhealth';

interface Props {
  selectedGate: QuantumVisualizationGate | null;
  gateIndex: number;
  totalGates: number;
  qubitCount: number;
  featureMappings?: QuantumVisualizationFeatureMapping[];
  selectedFeatureIndex?: number | null;
  onFeatureSelect?: (index: number) => void;
  onGateSelect?: (index: number) => void;
  quantumConfig?: QuantumConfig;
  hybridConfig?: HybridModelConfig;
  modelType: 'vqc' | 'qsvc' | 'qnn' | 'hybrid_pennylane_torch';
  onQuantumConfigChange?: (patch: Partial<QuantumConfig>) => void;
  onHybridConfigChange?: (patch: Partial<HybridModelConfig>) => void;
  isConfigModified?: boolean;
  onRegeneratePreview?: () => void;
  isRegenerating?: boolean;
}

interface GateExplanation {
  category: string;
  badgeTone: 'purple' | 'blue' | 'green' | 'amber';
  description: string;
  mathFormula?: string;
  parameterRole: string;
}

function getGateExplanation(gateName: string): GateExplanation {
  const norm = gateName.trim().toLowerCase();

  if (norm === 'h' || norm === 'hadamard') {
    return {
      category: 'Superposition Gate',
      badgeTone: 'purple',
      description:
        'Puts a computational basis state into an equal quantum superposition (|0⟩ → |+⟩, |1⟩ → |–⟩). Essential for parallel state space exploration.',
      mathFormula: 'H = 1/√2 [[1, 1], [1, -1]]',
      parameterRole: 'Fixed unitary operation without free parameters.',
    };
  }

  if (norm.startsWith('ry') || norm.includes('rotation_y')) {
    return {
      category: 'Parameterized Y-Rotation',
      badgeTone: 'blue',
      description:
        'Rotates the qubit state vector on the Bloch sphere around the Y-axis by angle θ. Preserves real probability amplitudes for classification.',
      mathFormula: 'Ry(θ) = exp(-i(θ/2)Y) = [[cos(θ/2), -sin(θ/2)], [sin(θ/2), cos(θ/2)]]',
      parameterRole: 'Continuous rotation angle θ bound to input feature or variational weight.',
    };
  }

  if (norm.startsWith('rz') || norm.includes('rotation_z')) {
    return {
      category: 'Parameterized Z-Rotation',
      badgeTone: 'blue',
      description:
        'Applies a phase rotation by angle ϕ around the Z-axis of the Bloch sphere, altering the relative quantum phase between basis states.',
      mathFormula: 'Rz(ϕ) = exp(-i(ϕ/2)Z) = [[e^(-iϕ/2), 0], [0, e^(iϕ/2)]]',
      parameterRole: 'Phase angle parameter modulating relative basis phase.',
    };
  }

  if (norm.startsWith('rx') || norm.includes('rotation_x')) {
    return {
      category: 'Parameterized X-Rotation',
      badgeTone: 'blue',
      description:
        'Rotates the state vector on the Bloch sphere around the X-axis by angle θ, producing bit-flip rotations.',
      mathFormula: 'Rx(θ) = exp(-i(θ/2)X) = [[cos(θ/2), -i sin(θ/2)], [-i sin(θ/2), cos(θ/2)]]',
      parameterRole: 'Continuous rotation angle θ.',
    };
  }

  if (norm === 'cx' || norm.startsWith('cx_') || norm === 'cnot') {
    return {
      category: 'Two-Qubit Entangler',
      badgeTone: 'green',
      description:
        'Controlled-NOT gate. Flips the target qubit conditionally if the control qubit is in state |1⟩, creating maximal Bell entanglement.',
      mathFormula: 'CNOT |c, t⟩ = |c, t ⊕ c⟩',
      parameterRole: 'Two-qubit parity operation with fixed connectivity.',
    };
  }

  if (norm === 'cz' || norm.startsWith('cz_')) {
    return {
      category: 'Controlled Phase Gate',
      badgeTone: 'green',
      description:
        'Applies a conditional phase flip (-1) when both control and target qubits are in state |11⟩.',
      mathFormula: 'CZ |11⟩ = -|11⟩',
      parameterRole: 'Entangling phase interaction.',
    };
  }

  if (norm === 'swap') {
    return {
      category: 'Register Exchange',
      badgeTone: 'amber',
      description: 'Swaps the quantum states between two logical qubit wires.',
      mathFormula: 'SWAP |a, b⟩ = |b, a⟩',
      parameterRole: 'Permutation of qubit states.',
    };
  }

  if (norm.includes('angleembedding') || norm.includes('angle_embedding')) {
    return {
      category: 'Biomedical Feature Encoding',
      badgeTone: 'purple',
      description:
        'Encodes continuous normalized classical biomedical features into single-qubit rotation angles on logical wires: θ_i = 2·arcsin(x_i) or π·x_i.',
      mathFormula: 'U_enc(x) = ⨂ Ry(θ_i(x_i))',
      parameterRole: 'Dataset feature-bound angles with angle scaling in [-π, π].',
    };
  }

  if (norm.includes('stronglyentangling') || norm.includes('strongly_entangling')) {
    return {
      category: 'Variational Ansatz Template',
      badgeTone: 'blue',
      description:
        'Multi-layer parameterized ansatz alternating single-qubit Euler rotations with cyclic CNOT entanglers to optimize classification decision boundaries.',
      mathFormula: 'U(θ) = ∏ [Entangler · ⨂ R(α, β, γ)]',
      parameterRole: 'Trainable variational weight tensors optimized during classical loop.',
    };
  }

  return {
    category: 'Unitary Operation',
    badgeTone: 'blue',
    description:
      'Standard unitary quantum gate operation executing in the backend-compiled circuit sequence.',
    parameterRole: 'Backend-defined operation parameter.',
  };
}

export function QuantumGateInspector({
  selectedGate,
  gateIndex,
  totalGates,
  qubitCount,
  featureMappings = [],
  selectedFeatureIndex = null,
  onFeatureSelect,
  onGateSelect,
  quantumConfig,
  hybridConfig,
  modelType,
  onQuantumConfigChange,
  onHybridConfigChange,
  isConfigModified = false,
  onRegeneratePreview,
  isRegenerating = false,
}: Props) {
  const [activeTab, setActiveTab] = useState<'gate' | 'bindings' | 'config'>('gate');
  const baseId = useId();

  const explanation = selectedGate ? getGateExplanation(selectedGate.name) : null;

  return (
    <div
      className="ql-gate-inspector-panel tremor-card"
      role="region"
      aria-label="Quantum gate and parameter inspector"
    >
      <div className="ql-inspector-header">
        <div className="flex items-center gap-2">
          <div className="ql-inspector-icon">
            <Atom size={16} aria-hidden="true" />
          </div>
          <div>
            <span className="ql-eyebrow">DEVELOPMENT WORKSPACE</span>
            <h3 className="text-sm font-bold tracking-tight m-0">Gate & Parameter Inspector</h3>
          </div>
        </div>
        <div className="ql-inspector-tabs" role="tablist" aria-label="Inspector views">
          <button
            type="button"
            role="tab"
            id={`${baseId}-tab-gate`}
            aria-selected={activeTab === 'gate'}
            aria-controls={`${baseId}-panel-gate`}
            className={`ql-tab-btn ${activeTab === 'gate' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('gate')}
          >
            <Layers size={13} aria-hidden="true" />
            <span>Gate Details</span>
          </button>
          <button
            type="button"
            role="tab"
            id={`${baseId}-tab-bindings`}
            aria-selected={activeTab === 'bindings'}
            aria-controls={`${baseId}-panel-bindings`}
            className={`ql-tab-btn ${activeTab === 'bindings' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('bindings')}
          >
            <Table size={13} aria-hidden="true" />
            <span>Feature Bindings ({featureMappings.length})</span>
          </button>
          <button
            type="button"
            role="tab"
            id={`${baseId}-tab-config`}
            aria-selected={activeTab === 'config'}
            aria-controls={`${baseId}-panel-config`}
            className={`ql-tab-btn ${activeTab === 'config' ? 'is-active' : ''}`}
            onClick={() => setActiveTab('config')}
          >
            <Sliders size={13} aria-hidden="true" />
            <span>Circuit Parameters</span>
            {isConfigModified && <span className="ql-modified-dot" title="Configuration modified" />}
          </button>
        </div>
      </div>

      {activeTab === 'gate' && (
        <div
          id={`${baseId}-panel-gate`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-gate`}
          className="ql-inspector-body"
        >
          {selectedGate ? (
            <div className="ql-gate-card">
              <div className="ql-gate-card-top">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="ql-gate-symbol" aria-hidden="true">
                    {selectedGate.name.replace(/[^a-zA-Z0-9]/g, '').slice(0, 4).toUpperCase()}
                  </span>
                  <div>
                    <strong className="text-base font-bold text-foreground block">
                      {selectedGate.name}
                    </strong>
                    <span className="text-xs text-muted-foreground">
                      Operation Step {gateIndex + 1} of {totalGates}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {explanation && <Badge tone={explanation.badgeTone}>{explanation.category}</Badge>}
                  <Badge tone="blue">
                    {selectedGate.qubits.length > 1 ? `${selectedGate.qubits.length} Qubits` : '1 Qubit'}
                  </Badge>
                </div>
              </div>

              {/* Functional Explanation */}
              {explanation && (
                <div className="ql-math-callout" role="note">
                  <div className="flex items-start gap-2">
                    <Info size={14} className="text-blue-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                    <div>
                      <p className="text-xs text-foreground font-medium m-0">
                        {explanation.description}
                      </p>
                      {explanation.mathFormula && (
                        <code className="ql-math-formula block mt-1.5">{explanation.mathFormula}</code>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Wire & Connectivity Metadata */}
              <div className="ql-inspector-grid mt-3">
                <div className="ql-meta-box">
                  <span className="ql-meta-label">TARGET WIRES</span>
                  <strong className="ql-mono">
                    {selectedGate.target_qubits.length
                      ? selectedGate.target_qubits.map((q) => `q[${q}]`).join(', ')
                      : selectedGate.qubits.map((q) => `q[${q}]`).join(', ')}
                  </strong>
                </div>
                <div className="ql-meta-box">
                  <span className="ql-meta-label">CONTROL WIRES</span>
                  <strong className="ql-mono">
                    {selectedGate.control_qubits.length
                      ? selectedGate.control_qubits.map((q) => `q[${q}]`).join(', ')
                      : 'None (Uncontrolled)'}
                  </strong>
                </div>
                <div className="ql-meta-box">
                  <span className="ql-meta-label">GATE TYPE</span>
                  <strong>{selectedGate.gate_type || 'Unitary operation'}</strong>
                </div>
                <div className="ql-meta-box">
                  <span className="ql-meta-label">PARAMETER COUNT</span>
                  <strong className="ql-mono">{selectedGate.parameters.length}</strong>
                </div>
              </div>

              {/* Parameters Breakdown */}
              <div className="mt-3">
                <span className="ql-eyebrow mb-1.5 block">GATE PARAMETERS &amp; BOUND VALUES</span>
                {selectedGate.parameters.length > 0 ? (
                  <div className="ql-params-table-wrap">
                    <table className="data-table text-xs">
                      <thead>
                        <tr>
                          <th>Parameter Symbol</th>
                          <th>Role / Binding</th>
                          <th>Valid Range</th>
                          <th>Associated Feature</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedGate.parameters.map((param, pIdx) => {
                          const isFeatureBound = param.includes('x[') || param.toLowerCase().includes('feature');
                          const isTrainable = param.includes('θ') || param.includes('theta') || param.includes('weight');
                          
                          // Check if parameter matches a feature mapping
                          const matchedMapping = featureMappings.find((m) =>
                            param.includes(`x[${m.feature_index}]`) || (m.parameter_name && param.includes(m.parameter_name))
                          );

                          return (
                            <tr key={`${pIdx}-${param}`}>
                              <td className="ql-mono font-bold text-primary">{param}</td>
                              <td>
                                {isFeatureBound ? (
                                  <Badge tone="purple">Feature Binding</Badge>
                                ) : isTrainable ? (
                                  <Badge tone="blue">Trainable Weight</Badge>
                                ) : (
                                  <Badge tone="blue">Fixed Angle</Badge>
                                )}
                              </td>
                              <td className="ql-mono text-muted-foreground">
                                {isFeatureBound ? '[-π, π]' : '[0, 2π]'}
                              </td>
                              <td>
                                {matchedMapping ? (
                                  <button
                                    type="button"
                                    className="ql-feature-link text-xs font-semibold text-primary"
                                    onClick={() => onFeatureSelect?.(matchedMapping.feature_index)}
                                    title="Highlight this feature wire in circuit explorer"
                                  >
                                    {matchedMapping.feature_name || `Feature ${matchedMapping.feature_index + 1}`} (q[{matchedMapping.qubit_index}])
                                  </button>
                                ) : (
                                  <span className="text-muted-foreground">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-3 bg-muted/40 rounded border border-border/60 text-xs text-muted-foreground">
                    This gate executes a fixed unitary matrix with no variable parameters.
                  </div>
                )}
              </div>

              {/* Navigation controls */}
              <div className="ql-gate-nav-actions mt-3 flex items-center justify-between">
                <Button
                  variant="outline"
                  disabled={gateIndex <= 0}
                  onClick={() => onGateSelect?.(gateIndex - 1)}
                  aria-label="Inspect previous gate"
                >
                  ← Previous Gate
                </Button>
                <span className="text-xs text-muted-foreground">
                  Step {gateIndex + 1} of {totalGates}
                </span>
                <Button
                  variant="outline"
                  disabled={gateIndex >= totalGates - 1}
                  onClick={() => onGateSelect?.(gateIndex + 1)}
                  aria-label="Inspect next gate"
                >
                  Next Gate →
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center text-sm text-muted-foreground">
              <Atom size={24} className="mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p>No circuit gate is currently selected.</p>
              <small>Click any gate box in the circuit view above or step through with playback.</small>
            </div>
          )}
        </div>
      )}

      {activeTab === 'bindings' && (
        <div
          id={`${baseId}-panel-bindings`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-bindings`}
          className="ql-inspector-body"
        >
          <div className="mb-2">
            <p className="text-xs text-muted-foreground m-0">
              Interactive feature-to-qubit binding ledger derived directly from the backend visualization contract. Clicking a row highlights its logical qubit wire and associated gates.
            </p>
          </div>

          {featureMappings.length > 0 ? (
            <div className="ql-params-table-wrap">
              <table className="data-table text-xs">
                <thead>
                  <tr>
                    <th>Input Feature</th>
                    <th>Target Qubit</th>
                    <th>Parameter Variable</th>
                    <th>Scaling / Transformation</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {featureMappings.map((mapping) => {
                    const isSelected = selectedFeatureIndex === mapping.feature_index;
                    return (
                      <tr
                        key={`map-${mapping.feature_index}-${mapping.qubit_index}`}
                        className={`cursor-pointer ${isSelected ? 'bg-primary/10 font-medium' : 'hover:bg-muted/40'}`}
                        onClick={() => onFeatureSelect?.(mapping.feature_index)}
                      >
                        <td>
                          <strong>{mapping.feature_name || `Feature ${mapping.feature_index + 1}`}</strong>
                          <span className="block text-[10px] text-muted-foreground">
                            Column Index: {mapping.feature_index}
                          </span>
                        </td>
                        <td className="ql-mono font-semibold">q[{mapping.qubit_index}]</td>
                        <td className="ql-mono text-primary">{mapping.parameter_name || `x[${mapping.feature_index}]`}</td>
                        <td>
                          <Badge tone="green">Angle Scaling [-π, π]</Badge>
                        </td>
                        <td>
                          <button
                            type="button"
                            className={`btn btn-outline py-1 px-2 text-[10px] ${isSelected ? 'btn-primary' : ''}`}
                            onClick={() => onFeatureSelect?.(mapping.feature_index)}
                            aria-pressed={isSelected}
                          >
                            {isSelected ? 'Highlighted' : 'Select Wire'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-6 text-center text-sm text-muted-foreground bg-muted/30 rounded border border-border">
              <Table size={24} className="mx-auto mb-2 opacity-50" aria-hidden="true" />
              <p>No feature-to-qubit mappings available in current preview.</p>
              <small>Feature bindings are computed when a dataset context is supplied with the structural preview.</small>
            </div>
          )}
        </div>
      )}

      {activeTab === 'config' && (
        <div
          id={`${baseId}-panel-config`}
          role="tabpanel"
          aria-labelledby={`${baseId}-tab-config`}
          className="ql-inspector-body"
        >
          <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
            <div>
              <p className="text-xs text-muted-foreground m-0">
                Adjust bounded circuit generation parameters grounded in backend simulation limits.
              </p>
            </div>
            {isConfigModified && (
              <span className="animate-pulse">
                <Badge tone="amber">
                  Configuration Modified (Regenerate Preview)
                </Badge>
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Logical Qubits */}
            <div className="field">
              <label htmlFor={`${baseId}-qubits`} className="text-xs font-semibold">
                Logical Qubits ({modelType === 'hybrid_pennylane_torch' ? (hybridConfig?.qubits ?? 4) : (quantumConfig?.qubits ?? 4)})
              </label>
              <input
                id={`${baseId}-qubits`}
                type="range"
                min={2}
                max={6}
                step={1}
                value={modelType === 'hybrid_pennylane_torch' ? (hybridConfig?.qubits ?? 4) : (quantumConfig?.qubits ?? 4)}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  if (modelType === 'hybrid_pennylane_torch') {
                    onHybridConfigChange?.({ qubits: val });
                  } else {
                    onQuantumConfigChange?.({ qubits: val });
                  }
                }}
                className="w-full accent-primary"
                aria-valuemin={2}
                aria-valuemax={6}
                aria-valuenow={modelType === 'hybrid_pennylane_torch' ? (hybridConfig?.qubits ?? 4) : (quantumConfig?.qubits ?? 4)}
              />
              <small className="text-[10px] text-muted-foreground">
                Logical register width (2–6 qubits, capped for statevector simulation safety).
              </small>
            </div>

            {/* Feature Map Repetitions */}
            {modelType !== 'hybrid_pennylane_torch' ? (
              <div className="field">
                <label htmlFor={`${baseId}-fmap-reps`} className="text-xs font-semibold">
                  Feature-Map Repetitions
                </label>
                <Select
                  id={`${baseId}-fmap-reps`}
                  value={String(quantumConfig?.feature_map_reps ?? 1)}
                  onChange={(e) => onQuantumConfigChange?.({ feature_map_reps: Number(e.target.value) })}
                >
                  <option value="1">1 Layer (Linear Encoding)</option>
                  <option value="2">2 Layers (Enhanced Separation)</option>
                  <option value="3">3 Layers (Deep Encoding)</option>
                  <option value="4">4 Layers (Maximum Bounded)</option>
                </Select>
                <small className="text-[10px] text-muted-foreground">
                  Number of repeating feature-encoding blocks.
                </small>
              </div>
            ) : (
              <div className="field">
                <label htmlFor={`${baseId}-hybrid-layers`} className="text-xs font-semibold">
                  PennyLane Quantum Layers
                </label>
                <Select
                  id={`${baseId}-hybrid-layers`}
                  value={String(hybridConfig?.quantum_layers ?? 2)}
                  onChange={(e) => onHybridConfigChange?.({ quantum_layers: Number(e.target.value) })}
                >
                  <option value="1">1 Strongly Entangling Layer</option>
                  <option value="2">2 Strongly Entangling Layers</option>
                  <option value="3">3 Strongly Entangling Layers</option>
                  <option value="4">4 Strongly Entangling Layers</option>
                </Select>
                <small className="text-[10px] text-muted-foreground">
                  Depth of variational ansatz blocks in hybrid model.
                </small>
              </div>
            )}

            {/* Ansatz Repetitions */}
            {modelType !== 'hybrid_pennylane_torch' && (
              <div className="field">
                <label htmlFor={`${baseId}-ansatz-reps`} className="text-xs font-semibold">
                  Ansatz Repetitions
                </label>
                <Select
                  id={`${baseId}-ansatz-reps`}
                  value={String(quantumConfig?.ansatz_reps ?? 1)}
                  onChange={(e) => onQuantumConfigChange?.({ ansatz_reps: Number(e.target.value) })}
                >
                  <option value="1">1 Repetition (Lightweight)</option>
                  <option value="2">2 Repetitions (Standard Expressive)</option>
                  <option value="3">3 Repetitions (Deep Ansatz)</option>
                </Select>
                <small className="text-[10px] text-muted-foreground">
                  Number of parameter optimization blocks in VQC/QNN.
                </small>
              </div>
            )}

            {/* Simulator Backend */}
            <div className="field">
              <label htmlFor={`${baseId}-backend`} className="text-xs font-semibold">
                Simulator Backend
              </label>
              {modelType === 'hybrid_pennylane_torch' ? (
                <Select
                  id={`${baseId}-backend`}
                  value={hybridConfig?.backend ?? 'default.qubit'}
                  onChange={() => onHybridConfigChange?.({ backend: 'default.qubit' })}
                >
                  <option value="default.qubit">PennyLane default.qubit (Local Simulator)</option>
                </Select>
              ) : (
                <Select
                  id={`${baseId}-backend`}
                  value={quantumConfig?.backend ?? 'statevector'}
                  onChange={(e) => onQuantumConfigChange?.({ backend: e.target.value as 'statevector' | 'aer' })}
                >
                  <option value="statevector">Qiskit Aer Statevector (Ideal Exact)</option>
                  <option value="aer">Qiskit Aer Simulator (Shot Sampling)</option>
                </Select>
              )}
              <small className="text-[10px] text-muted-foreground">
                All simulation executes on local scientific engines.
              </small>
            </div>

            {/* Shots */}
            {modelType !== 'hybrid_pennylane_torch' && (
              <div className="field">
                <label htmlFor={`${baseId}-shots`} className="text-xs font-semibold">
                  Execution Shots
                </label>
                <Select
                  id={`${baseId}-shots`}
                  value={String(quantumConfig?.shots ?? 1024)}
                  onChange={(e) => onQuantumConfigChange?.({ shots: Number(e.target.value) })}
                >
                  <option value="256">256 Shots</option>
                  <option value="512">512 Shots</option>
                  <option value="1024">1,024 Shots (Default)</option>
                  <option value="2048">2,048 Shots</option>
                  <option value="4096">4,096 Shots (Max Bounded)</option>
                </Select>
                <small className="text-[10px] text-muted-foreground">
                  Number of circuit evaluations for measurement statistics.
                </small>
              </div>
            )}

            {/* Entanglement Strategy */}
            {modelType !== 'hybrid_pennylane_torch' && (
              <div className="field">
                <label htmlFor={`${baseId}-entanglement`} className="text-xs font-semibold">
                  Entanglement Strategy
                </label>
                <Select
                  id={`${baseId}-entanglement`}
                  value={quantumConfig?.entanglement ?? 'linear'}
                  onChange={(e) => onQuantumConfigChange?.({ entanglement: e.target.value as 'linear' | 'full' })}
                >
                  <option value="linear">Linear (Nearest-neighbor CX)</option>
                  <option value="full">Full (All-to-all CX)</option>
                </Select>
                <small className="text-[10px] text-muted-foreground">
                  Coupling map for two-qubit entangling gates.
                </small>
              </div>
            )}
          </div>

          <div className="mt-4 pt-3 border-t border-border flex items-center justify-between gap-3 flex-wrap">
            <span className="text-xs text-muted-foreground">
              Parameter changes update your workspace draft safely and never start unprompted training.
            </span>
            <Button
              onClick={onRegeneratePreview}
              disabled={isRegenerating}
              className="flex items-center gap-1.5"
            >
              <RefreshCw size={14} className={isRegenerating ? 'animate-spin' : ''} aria-hidden="true" />
              <span>{isRegenerating ? 'Generating...' : 'Generate Structural Preview'}</span>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
