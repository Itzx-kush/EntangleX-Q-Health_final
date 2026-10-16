import {useState} from 'react';
import {Check, Copy, Terminal, Activity, Layers, Cpu, Sparkles} from 'lucide-react';

interface DemonstrationTab {
  id: string;
  name: string;
  badge: string;
  description: string;
  code: string;
  qubitCount: number;
  circuitDepth: number;
  shots: number;
  probabilities: {state: string; prob: number}[];
  metrics: {label: string; value: string}[];
}

const DEMO_TABS: DemonstrationTab[] = [
  {
    id: 'hybrid-vqc',
    name: '01 Hybrid VQC',
    badge: 'QUANTUM ML',
    description: 'Variational quantum classifier with parameterized rotation gates and CNOT entanglement.',
    code: `# EntangleX Hybrid VQC Workflow
import pennylane as qml
from entanglex.models import QuantumClassifier

dev = qml.device("default.qubit", wires=4)

@qml.qnode(dev, interface="torch")
def quantum_circuit(weights, x):
    # Angle encoding of normalized clinical biomarkers
    for i in range(4):
        qml.RY(x[i], wires=i)
    
    # Entangling variational layers
    for layer in range(2):
        for i in range(4):
            qml.Rot(*weights[layer, i], wires=i)
        qml.broadcast(unitary=qml.CNOT, pattern="ring", wires=range(4))
        
    return [qml.expval(qml.PauliZ(i)) for i in range(4)]

# Initialize model bound to SIH-26139 benchmark
model = QuantumClassifier(circuit=quantum_circuit, n_qubits=4)
print(f"Parameters: {model.trainable_params} | Device: Local Statevector")`,
    qubitCount: 4,
    circuitDepth: 8,
    shots: 1024,
    probabilities: [
      {state: '|00⟩', prob: 0.42},
      {state: '|01⟩', prob: 0.16},
      {state: '|10⟩', prob: 0.11},
      {state: '|11⟩', prob: 0.31},
    ],
    metrics: [
      {label: 'Circuit Depth', value: '8 layers'},
      {label: 'Entangling Gates', value: '4 CNOTs'},
      {label: 'Simulation Runtime', value: '18.4 ms'},
      {label: 'Reported AUROC', value: '0.864'},
    ],
  },
  {
    id: 'classical-baseline',
    name: '02 Classical Baseline',
    badge: 'CLASSICAL BENCHMARK',
    description: 'Controlled classical models evaluated under identical cross-validation splits.',
    code: `# EntangleX Controlled Baseline Comparison
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from entanglex.evaluation import ProtocolComparator

# Standardized data preprocessing across all model families
comparator = ProtocolComparator(dataset="diabetes_risk_sih26139")

# Train baseline gradient boosting on identical training fold
xgb_baseline = GradientBoostingClassifier(n_estimators=100, max_depth=3)
comparator.fit_and_evaluate(xgb_baseline, name="XGBoost_Baseline")

rf_baseline = RandomForestClassifier(n_estimators=100, random_state=42)
comparator.fit_and_evaluate(rf_baseline, name="Random_Forest_Baseline")

# Summary of shared evaluation bounds
print(comparator.summary_table())`,
    qubitCount: 0,
    circuitDepth: 0,
    shots: 0,
    probabilities: [
      {state: 'Polyuria', prob: 0.38},
      {state: 'Polydipsia', prob: 0.29},
      {state: 'Age/BMI', prob: 0.19},
      {state: 'Alopecia', prob: 0.14},
    ],
    metrics: [
      {label: 'Baseline Model', value: 'XGBoost / RF'},
      {label: 'Cross-Validation', value: '5-fold stratified'},
      {label: 'Feature Count', value: '16 attributes'},
      {label: 'Reported AUROC', value: '0.842'},
    ],
  },
  {
    id: 'quantum-kernel',
    name: '03 Quantum Kernel',
    badge: 'KERNEL ESTIMATION',
    description: 'High-dimensional Hilbert space mapping via quantum state fidelity estimation.',
    code: `# EntangleX Quantum Kernel Estimation
import pennylane as qml
from entanglex.kernels import FidelityQuantumKernel

dev = qml.device("default.qubit", wires=4)

@qml.qnode(dev)
def kernel_circuit(x1, x2):
    # Feature map encoding x1
    for i in range(4):
        qml.Hadamard(wires=i)
        qml.RZ(2.0 * x1[i], wires=i)
    
    # Adjoint feature map encoding x2
    for i in range(4):
        qml.RZ(-2.0 * x2[i], wires=i)
        qml.Hadamard(wires=i)
        
    return qml.probs(wires=range(4))

kernel = FidelityQuantumKernel(qnode=kernel_circuit)
gram_matrix = kernel.compute_matrix(X_train[:16])`,
    qubitCount: 4,
    circuitDepth: 12,
    shots: 2048,
    probabilities: [
      {state: 'Overlap (0,0)', prob: 1.00},
      {state: 'Overlap (0,1)', prob: 0.28},
      {state: 'Overlap (0,2)', prob: 0.14},
      {state: 'Overlap (0,3)', prob: 0.39},
    ],
    metrics: [
      {label: 'Kernel Type', value: 'Fidelity Overlap'},
      {label: 'Hilbert Dimension', value: '2^4 = 16'},
      {label: 'Gram Matrix Rank', value: 'Full Rank (16)'},
      {label: 'Reported AUROC', value: '0.851'},
    ],
  },
];

export function PublicResearchDemonstration() {
  const [activeTabId, setActiveTabId] = useState<string>('hybrid-vqc');
  const [activeQubitWidth, setActiveQubitWidth] = useState<number>(4);
  const [copied, setCopied] = useState<boolean>(false);

  const activeTab = DEMO_TABS.find(t => t.id === activeTabId) || DEMO_TABS[0];

  const handleCopy = () => {
    navigator.clipboard.writeText(activeTab.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="interactive-demo" className="public-demonstration-section public-shell">
      <div className="public-demo-header" data-public-reveal>
        <div className="public-eyebrow">
          <span>03 // WORKBENCH</span>
          <span>Interactive Research Demonstration</span>
        </div>
        <h2 className="public-demo-title">
          Explore the Hybrid Research Workflow in Action
        </h2>
        <p className="public-demo-description">
          Toggle between classical baselines, variational quantum circuits, and quantum kernel
          formulations. All metrics and circuit structures represent reproducible benchmark
          configurations from the EntangleX repository.
        </p>
      </div>

      <div className="public-workbench-card" data-public-reveal>
        {/* Top Control Bar with macOS-style window dots & Tabs */}
        <div className="public-workbench-topbar">
          <div className="public-window-controls" aria-hidden="true">
            <span className="window-dot is-red" />
            <span className="window-dot is-yellow" />
            <span className="window-dot is-green" />
            <span className="public-window-title">entanglex_research_preview.py</span>
          </div>

          {/* Interactive Navigation Tabs */}
          <div className="public-workbench-tabs" role="tablist" aria-label="Research workflow options">
            {DEMO_TABS.map(tab => {
              const isSelected = tab.id === activeTabId;
              return (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  role="tab"
                  type="button"
                  aria-selected={isSelected}
                  aria-controls={`panel-${tab.id}`}
                  tabIndex={isSelected ? 0 : -1}
                  className={`public-workbench-tab ${isSelected ? 'is-active' : ''}`}
                  onClick={() => setActiveTabId(tab.id)}
                >
                  <span>{tab.name}</span>
                </button>
              );
            })}
          </div>

          {/* Code Copy Button */}
          <div className="public-workbench-actions">
            <button
              type="button"
              className="public-copy-btn"
              onClick={handleCopy}
              aria-label="Copy code sample"
            >
              {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
        </div>

        {/* Tab Panel Body (2-Column Grid) */}
        <div
          id={`panel-${activeTab.id}`}
          role="tabpanel"
          aria-labelledby={`tab-${activeTab.id}`}
          className="public-workbench-body"
        >
          {/* Left Column: Syntax Highlighted Code */}
          <div className="public-code-panel">
            <div className="public-code-panel-header">
              <div className="public-code-meta">
                <Terminal size={14} className="text-violet-400" />
                <span className="public-code-badge">{activeTab.badge}</span>
              </div>
              {activeTab.qubitCount > 0 && (
                <div className="public-qubit-selector">
                  <span className="qubit-label">Qubits:</span>
                  <button
                    type="button"
                    className={`qubit-pill ${activeQubitWidth === 2 ? 'is-selected' : ''}`}
                    onClick={() => setActiveQubitWidth(2)}
                  >
                    2Q
                  </button>
                  <button
                    type="button"
                    className={`qubit-pill ${activeQubitWidth === 4 ? 'is-selected' : ''}`}
                    onClick={() => setActiveQubitWidth(4)}
                  >
                    4Q
                  </button>
                </div>
              )}
            </div>

            <pre className="public-code-block">
              <code>{activeTab.code}</code>
            </pre>
          </div>

          {/* Right Column: Live Telemetry & Result Visualization */}
          <div className="public-telemetry-panel">
            <div className="public-telemetry-header">
              <Activity size={15} className="text-cyan-400" />
              <strong>Measured Benchmark Output</strong>
              <span className="public-telemetry-tag">Simulated State</span>
            </div>

            <p className="public-telemetry-description">{activeTab.description}</p>

            {/* Metric Summary Grid */}
            <div className="public-metric-summary-grid">
              {activeTab.metrics.map(metric => (
                <div key={metric.label} className="public-metric-card">
                  <span className="public-metric-label">{metric.label}</span>
                  <strong className="public-metric-value">{metric.value}</strong>
                </div>
              ))}
            </div>

            {/* Measurement Probability / Feature Weight Histogram */}
            <div className="public-histogram-container">
              <div className="public-histogram-title">
                <span>{activeTab.id === 'classical-baseline' ? 'Relative Feature Influence' : 'Measurement Probability Distribution'}</span>
                <span className="public-shots-indicator">
                  {activeTab.shots > 0 ? `${activeTab.shots} shots` : '100% test fold'}
                </span>
              </div>

              <div className="public-histogram-bars">
                {activeTab.probabilities.map(item => (
                  <div key={item.state} className="public-bar-row">
                    <span className="public-bar-state">{item.state}</span>
                    <div className="public-bar-track">
                      <div
                        className="public-bar-fill"
                        style={{width: `${Math.round(item.prob * 100)}%`}}
                      />
                    </div>
                    <span className="public-bar-value">{(item.prob * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Truthful Scientific Boundary Note */}
            <div className="public-scientific-boundary-note">
              <Sparkles size={13} className="text-violet-400 shrink-0" />
              <span>
                *Illustrative research preview based on EntangleX SIH-26139 benchmark dataset.
                Evaluated via local statevector simulator. Not an active quantum hardware job.
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
