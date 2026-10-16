import {useState} from 'react';
import {Check, Copy, Terminal, Activity, Sparkles} from 'lucide-react';

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
  visualizationTitle: string;
  visualizationIndicator: string;
}

const DEMO_TABS: DemonstrationTab[] = [
  {
    id: 'hybrid-vqc',
    name: '01 Hybrid VQC',
    badge: 'QUANTUM ML',
    description: 'Variational quantum classifier with parameterized rotation gates and ring-topology CNOT entanglement.',
    code: `# Illustrative Hybrid VQC Workflow (PennyLane + PyTorch Template)
# Parameterized ansatz for normalized clinical biomarker classification
import pennylane as qml
import torch

dev = qml.device("default.qubit", wires=4)

@qml.qnode(dev, interface="torch", diff_method="backprop")
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

# Conceptual hybrid torch layer wrapper
weight_shapes = {"weights": (2, 4, 3)}
qlayer = qml.qnn.TorchLayer(quantum_circuit, weight_shapes)
print("Ansatz: 2 Layers | Entanglement: Ring CNOT | Backend: default.qubit")`,
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
      {label: 'Qubit Register', value: '4 Qubits'},
      {label: 'Variational Depth', value: '2 Parameterized Layers'},
      {label: 'Entangling Pattern', value: 'Ring Topology (CNOT)'},
      {label: 'Encoding Scheme', value: 'RY Angle Mapping'},
    ],
    visualizationTitle: 'Illustrative Statevector Projection (Synthetic Sample)',
    visualizationIndicator: 'Synthetic 1024-shot sample',
  },
  {
    id: 'classical-baseline',
    name: '02 Classical Baseline',
    badge: 'CLASSICAL BENCHMARK',
    description: 'Controlled classical estimators (Gradient Boosting and Random Forest) evaluated under identical cross-validation splits.',
    code: `# Controlled Classical Baseline Evaluation (scikit-learn)
# Standardized evaluation protocol on early-stage-diabetes benchmark
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import StratifiedKFold

# Target benchmark dataset: Early Stage Diabetes Risk Prediction (16 features)
dataset_slug = "early-stage-diabetes"

# Standardized 5-fold stratified cross-validation protocol
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Train baseline Gradient Boosting on shared fold partition
gb_model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=42)

# Train baseline Random Forest under identical cross-validation splits
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)

# Note: Illustrative research workflow template for benchmark evaluation
print(f"Protocol: Stratified 5-Fold CV | Benchmark: {dataset_slug}")`,
    qubitCount: 0,
    circuitDepth: 0,
    shots: 0,
    probabilities: [
      {state: 'Polyuria', prob: 0.38},
      {state: 'Polydipsia', prob: 0.29},
      {state: 'Age / BMI', prob: 0.19},
      {state: 'Alopecia', prob: 0.14},
    ],
    metrics: [
      {label: 'Baseline Models', value: 'Gradient Boosting / Random Forest'},
      {label: 'Validation Protocol', value: 'Stratified 5-Fold CV'},
      {label: 'Dataset Benchmark', value: 'early-stage-diabetes'},
      {label: 'Partition Consistency', value: 'Shared Split Folds'},
    ],
    visualizationTitle: 'Illustrative Feature Attribution (Conceptual Weights)',
    visualizationIndicator: 'Conceptual importance sample',
  },
  {
    id: 'quantum-kernel',
    name: '03 Quantum Kernel',
    badge: 'KERNEL ESTIMATION',
    description: 'High-dimensional Hilbert space mapping via quantum state fidelity estimation.',
    code: `# Illustrative Quantum Kernel Estimation (PennyLane Template)
# Pairwise quantum state fidelity overlap |⟨ψ(x₁)|ψ(x₂)⟩|² in 2⁴ Hilbert space
import pennylane as qml
import numpy as np

dev = qml.device("default.qubit", wires=4)

@qml.qnode(dev)
def kernel_circuit(x1, x2):
    # Feature map encoding x1 (Hadamard + RZ phase rotation)
    for i in range(4):
        qml.Hadamard(wires=i)
        qml.RZ(2.0 * x1[i], wires=i)
    
    # Adjoint feature map encoding x2
    for i in range(4):
        qml.RZ(-2.0 * x2[i], wires=i)
        qml.Hadamard(wires=i)
        
    return qml.probs(wires=range(4))

# Fidelity kernel is the probability of returning to ground state |0000⟩
def compute_fidelity_kernel(x1, x2):
    return kernel_circuit(x1, x2)[0]

# Note: Conceptual research template for pairwise Gram matrix estimation
print("Hilbert Space: 2⁴ = 16 | Kernel: State Fidelity Overlap")`,
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
      {label: 'Kernel Formulation', value: 'Fidelity State Overlap'},
      {label: 'Feature Dimension', value: '4 Input Attributes'},
      {label: 'Hilbert Space', value: '2⁴ = 16 Dimension'},
      {label: 'Gram Matrix Target', value: 'Pairwise Inner Product'},
    ],
    visualizationTitle: 'Synthetic Pairwise State Fidelity (Conceptual Overlap)',
    visualizationIndicator: 'Synthetic matrix sample',
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
          formulations. All metrics and circuit structures represent protocol specifications
          from the EntangleX repository. Output distributions are illustrative synthetic samples
          for workflow demonstration.
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

        {/* Prominent Scientific Integrity Disclosure Banner */}
        <div className="public-demo-disclosure" role="note" aria-label="Scientific evidence disclosure">
          <div className="public-demo-disclosure-badge">
            <Sparkles size={12} className="text-violet-400" />
            <span>ILLUSTRATIVE RESEARCH PREVIEW</span>
          </div>
          <p className="public-demo-disclosure-text">
            Displayed code samples, circuit metrics, and distributions represent conceptual research architectures and synthetic test samples. No live quantum hardware execution or unverified benchmark claim is asserted. Precomputed benchmark evidence, dataset catalogs, and reproducible experiment records can be inspected in the authenticated workspace.
          </p>
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
              <strong>Conceptual Simulation Preview</strong>
              <span className="public-telemetry-tag">Illustrative Sample</span>
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

            {/* Synthetic Sample / Feature Weight Histogram */}
            <div className="public-histogram-container">
              <div className="public-histogram-title">
                <span>{activeTab.visualizationTitle}</span>
                <span className="public-shots-indicator">
                  {activeTab.visualizationIndicator}
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
                *Illustrative research preview based on EntangleX benchmark protocols. Values shown are synthetic sample projections for interface demonstration, not live model executions.
              </span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
