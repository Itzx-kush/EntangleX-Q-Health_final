import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Atom,
  Binary,
  CheckCircle2,
  Cpu,
  Database,
  ExternalLink,
  FlaskConical,
  Layers3,
  Network,
  ShieldAlert,
  Sparkles,
  Zap,
} from 'lucide-react';
import './QuantumHero.css';

export interface QuantumHeroProps {
  backendStatus: 'online' | 'checking' | 'offline';
  quantumAvailable?: boolean;
  runtimeVerified?: boolean;
  datasetCount?: number | string;
  experimentCount?: number | string;
  readyModelCount?: number | string;
  activeJobCount?: number | string;
  flagshipAvailable?: boolean;
  flagshipModelCount?: number | string;
}

export function QuantumHero({
  backendStatus,
  quantumAvailable = true,
  runtimeVerified = true,
  datasetCount = '—',
  experimentCount = '—',
  readyModelCount = '—',
  activeJobCount = '—',
  flagshipAvailable = true,
  flagshipModelCount = 4,
}: QuantumHeroProps) {
  const [activeTab, setActiveTab] = useState<'pipeline' | 'circuit' | 'boundary'>('pipeline');
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const statusLabel =
    backendStatus === 'online' ? 'BACKEND ONLINE' : backendStatus === 'checking' ? 'CHECKING API' : 'BACKEND OFFLINE';

  return (
    <section className="quantum-hero" aria-label="EntangleX Q-Health Quantum Research Overview">
      {/* Top telemetry & status ribbon */}
      <div className="quantum-hero-top">
        <div className="quantum-hero-badges">
          <span className="quantum-hero-pill quantum-hero-pill-primary">
            <Atom size={13} aria-hidden="true" />
            Hybrid Quantum-Classical ML
          </span>
          <span className="quantum-hero-pill quantum-hero-pill-quantum">
            <Cpu size={13} aria-hidden="true" />
            Qiskit Aer &amp; PennyLane (Local Simulation)
          </span>
          <span
            className={`quantum-hero-pill ${
              backendStatus === 'online' ? 'quantum-hero-pill-online' : 'quantum-hero-pill-primary'
            }`}
          >
            <span className="pulse-dot" aria-hidden="true" />
            {statusLabel}
          </span>
        </div>
        <div className="text-[11px] font-semibold text-[#1769E0] dark:text-[#8FC8FF] flex items-center gap-1.5">
          <ShieldAlert size={13} aria-hidden="true" />
          <span>Research Decision Support · Transparent Simulation</span>
        </div>
      </div>

      {/* Main Hero Grid */}
      <div className="quantum-hero-grid">
        {/* Left Column: Headline, Narrative, and Primary CTAs */}
        <div className="quantum-hero-copy">
          <p className="quantum-hero-eyebrow">QUANTUM-ENHANCED BIOMEDICAL INTELLIGENCE</p>
          <h1 className="quantum-hero-title">
            Hybrid Classical-Quantum Machine Learning for Healthcare Research
          </h1>
          <p className="quantum-hero-desc">
            EntangleX Q-Health bridges clinical tabular data and quantum computing. Evaluate
            variational quantum classifiers (VQC), quantum support vector kernels (QSVC), and
            PennyLane hybrid neural networks alongside verified classical baselines for early
            disease-risk stratification.
          </p>

          <div className="quantum-hero-actions">
            <Link to="/demo" className="quantum-hero-btn-primary" id="hero-launch-demo">
              <span>Launch Verified Demo</span>
              <ArrowRight size={14} aria-hidden="true" />
            </Link>
            <Link to="/datasets" className="quantum-hero-btn-outline" id="hero-open-data-lab">
              <Database size={14} aria-hidden="true" />
              <span>Explore Data Lab</span>
            </Link>
            <Link to="/quantum" className="quantum-hero-btn-ghost" id="hero-quantum-lab">
              <Atom size={13} aria-hidden="true" />
              <span>Quantum Lab</span>
            </Link>
            <Link to="/comparison" className="quantum-hero-btn-ghost" id="hero-model-comparison">
              <Layers3 size={13} aria-hidden="true" />
              <span>Model Comparison</span>
            </Link>
          </div>

          {/* Quick Specifications Strip */}
          <div className="quantum-hero-specs" aria-label="Platform telemetry summary">
            <div className="quantum-spec-item">
              <span>Datasets</span>
              <strong>{datasetCount} Cohorts</strong>
            </div>
            <div className="quantum-spec-item">
              <span>Experiments</span>
              <strong>{experimentCount} Recorded</strong>
            </div>
            <div className="quantum-spec-item">
              <span>Ready Models</span>
              <strong>{readyModelCount} Artifacts</strong>
            </div>
            <div className="quantum-spec-item">
              <span>Simulation Layer</span>
              <strong>{runtimeVerified ? 'Verified Local' : 'Aer Runtime'}</strong>
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Technical Visual */}
        <div className="quantum-hero-visual-card" aria-label="Interactive Quantum Pipeline Architecture">
          <div className="quantum-visual-header">
            <div className="flex items-center gap-2">
              <Binary size={15} className="text-[#1769E0] dark:text-[#8FC8FF]" aria-hidden="true" />
              <strong className="text-xs font-bold tracking-tight text-[#102A5C] dark:text-[#F4F7FB]">
                HYBRID WORKFLOW ARCHITECTURE
              </strong>
            </div>
            <div className="quantum-visual-tabs" role="tablist" aria-label="Visual Modes">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'pipeline'}
                className={`quantum-visual-tab ${activeTab === 'pipeline' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('pipeline')}
              >
                Pipeline
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'circuit'}
                className={`quantum-visual-tab ${activeTab === 'circuit' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('circuit')}
              >
                Circuit Spec
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'boundary'}
                className={`quantum-visual-tab ${activeTab === 'boundary' ? 'is-active' : ''}`}
                onClick={() => setActiveTab('boundary')}
              >
                Boundary
              </button>
            </div>
          </div>

          <div className="quantum-visual-body">
            {activeTab === 'pipeline' && (
              <div className="relative">
                <svg
                  className="hybrid-pipeline-svg"
                  viewBox="0 0 520 220"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  role="img"
                  aria-label="Classical to Quantum to Classical Dataflow Diagram"
                >
                  <defs>
                    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#1769E0" stopOpacity="0.12" />
                      <stop offset="100%" stopColor="#1769E0" stopOpacity="0.04" />
                    </linearGradient>
                    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#6946D9" stopOpacity="0.15" />
                      <stop offset="100%" stopColor="#18B6C9" stopOpacity="0.06" />
                    </linearGradient>
                    <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#159A70" stopOpacity="0.12" />
                      <stop offset="100%" stopColor="#159A70" stopOpacity="0.04" />
                    </linearGradient>
                  </defs>

                  {/* Connecting Flow Lines */}
                  <path
                    d="M 95 110 L 145 110"
                    stroke="#1769E0"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                    className="opacity-70"
                  />
                  <path
                    d="M 235 110 L 285 110"
                    stroke="#6946D9"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                    className="opacity-80"
                  />
                  <path
                    d="M 375 110 L 425 110"
                    stroke="#159A70"
                    strokeWidth="2"
                    strokeDasharray="4 3"
                    className="opacity-70"
                  />

                  {/* Flow Arrows */}
                  <polygon points="145,106 151,110 145,114" fill="#1769E0" />
                  <polygon points="285,106 291,110 285,114" fill="#6946D9" />
                  <polygon points="425,106 431,110 425,114" fill="#159A70" />

                  {/* Node 1: Classical Clinical Features */}
                  <g
                    className="node-rect cursor-pointer"
                    onMouseEnter={() => setHoveredNode('data')}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <rect
                      x="10"
                      y="70"
                      width="85"
                      height="80"
                      rx="10"
                      fill="url(#blueGrad)"
                      stroke={hoveredNode === 'data' ? '#1769E0' : '#D8E2EF'}
                      strokeWidth={hoveredNode === 'data' ? '2' : '1.5'}
                    />
                    <text x="52" y="94" textAnchor="middle" fontSize="10" fontWeight="700" fill="#1769E0">
                      STAGE 01
                    </text>
                    <text x="52" y="112" textAnchor="middle" fontSize="11" fontWeight="750" fill="#102A5C" className="dark:fill-white">
                      Biomarkers
                    </text>
                    <text x="52" y="128" textAnchor="middle" fontSize="9" fill="#64748B">
                      x ∈ ℝᵈ (CSV)
                    </text>
                  </g>

                  {/* Node 2: Dimension Reduction & Scaling */}
                  <g
                    className="node-rect cursor-pointer"
                    onMouseEnter={() => setHoveredNode('pca')}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <rect
                      x="150"
                      y="70"
                      width="85"
                      height="80"
                      rx="10"
                      fill="url(#blueGrad)"
                      stroke={hoveredNode === 'pca' ? '#1769E0' : '#D8E2EF'}
                      strokeWidth={hoveredNode === 'pca' ? '2' : '1.5'}
                    />
                    <text x="192" y="94" textAnchor="middle" fontSize="10" fontWeight="700" fill="#1769E0">
                      STAGE 02
                    </text>
                    <text x="192" y="112" textAnchor="middle" fontSize="11" fontWeight="750" fill="#102A5C" className="dark:fill-white">
                      PCA &amp; Norm
                    </text>
                    <text x="192" y="128" textAnchor="middle" fontSize="9" fill="#64748B">
                      d → n Qubits
                    </text>
                  </g>

                  {/* Node 3: Quantum Feature Map & Ansatz */}
                  <g
                    className="node-rect cursor-pointer"
                    onMouseEnter={() => setHoveredNode('quantum')}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <rect
                      x="290"
                      y="55"
                      width="85"
                      height="110"
                      rx="12"
                      fill="url(#purpleGrad)"
                      stroke={hoveredNode === 'quantum' ? '#6946D9' : '#C4B5FD'}
                      strokeWidth={hoveredNode === 'quantum' ? '2.5' : '1.8'}
                    />
                    <text x="332" y="78" textAnchor="middle" fontSize="10" fontWeight="700" fill="#6946D9">
                      STAGE 03
                    </text>
                    <text x="332" y="96" textAnchor="middle" fontSize="11" fontWeight="800" fill="#102A5C" className="dark:fill-white">
                      Quantum Circuit
                    </text>
                    <text x="332" y="112" textAnchor="middle" fontSize="9" fill="#6946D9" fontWeight="600">
                      U_Φ(x) · U(θ)
                    </text>
                    <text x="332" y="128" textAnchor="middle" fontSize="8" fill="#64748B">
                      CNOT Entangled
                    </text>
                    <text x="332" y="142" textAnchor="middle" fontSize="8" fill="#64748B">
                      Aer / PennyLane
                    </text>
                  </g>

                  {/* Node 4: Classical Evaluation & SHAP */}
                  <g
                    className="node-rect cursor-pointer"
                    onMouseEnter={() => setHoveredNode('eval')}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    <rect
                      x="430"
                      y="70"
                      width="80"
                      height="80"
                      rx="10"
                      fill="url(#greenGrad)"
                      stroke={hoveredNode === 'eval' ? '#159A70' : '#D8E2EF'}
                      strokeWidth={hoveredNode === 'eval' ? '2' : '1.5'}
                    />
                    <text x="470" y="94" textAnchor="middle" fontSize="10" fontWeight="700" fill="#159A70">
                      STAGE 04
                    </text>
                    <text x="470" y="112" textAnchor="middle" fontSize="11" fontWeight="750" fill="#102A5C" className="dark:fill-white">
                      Risk &amp; SHAP
                    </text>
                    <text x="470" y="128" textAnchor="middle" fontSize="9" fill="#64748B">
                      ⟨Z⟩ → ŷ ∈ [0,1]
                    </text>
                  </g>

                  {/* Annotations */}
                  <text x="260" y="200" textAnchor="middle" fontSize="10" fill="#64748B" fontStyle="italic">
                    Hover nodes to view data transformations · Controlled classical-to-quantum execution
                  </text>
                </svg>

                {/* Live Node Tooltip */}
                {hoveredNode && (
                  <div className="mt-2 p-2.5 rounded-lg border border-[#D8E2EF] dark:border-slate-800 bg-[#F7FAFD] dark:bg-slate-900 text-xs">
                    {hoveredNode === 'data' && (
                      <p>
                        <strong>Biomarker Input:</strong> Raw clinical features normalized to prevent gradient saturation. Ingestion supports diabetes, cardiology, and oncology datasets.
                      </p>
                    )}
                    {hoveredNode === 'pca' && (
                      <p>
                        <strong>PCA &amp; Feature Mapping:</strong> Orthogonal projection reducing input dimension to fit simulator qubit limits while retaining &gt;90% variance.
                      </p>
                    )}
                    {hoveredNode === 'quantum' && (
                      <p>
                        <strong>Variational Quantum Layer:</strong> Qiskit ZZFeatureMap / PennyLane AngleEmbedding with parameterized entangling ansatz evaluated on local simulator backends.
                      </p>
                    )}
                    {hoveredNode === 'eval' && (
                      <p>
                        <strong>Measurement &amp; Explainability:</strong> Pauli expectation values fed to classical decision head; Kernel SHAP attributions isolate individual biomarker impacts.
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'circuit' && (
              <div className="space-y-3 py-1 font-mono text-xs">
                <div className="p-3 rounded-lg border border-[#D8E2EF] dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-slate-800">
                    <span className="font-sans font-bold text-slate-700 dark:text-slate-300">LOGICAL CIRCUIT TOPOLOGY</span>
                    <span className="text-[10px] text-purple-600 dark:text-purple-400 font-semibold">4 QUBITS · DEPTH 8</span>
                  </div>
                  <div className="space-y-1.5 text-[11px] text-slate-600 dark:text-slate-400">
                    <div>q[0] ──[H]──[Rz(x₀)]──[Ry(θ₀)]──●──────────────[M] ⟨Z₀⟩</div>
                    <div>q[1] ──[H]──[Rz(x₁)]──[Ry(θ₁)]──X──●───────────[M] ⟨Z₁⟩</div>
                    <div>q[2] ──[H]──[Rz(x₂)]──[Ry(θ₂)]─────X──●────────[M] ⟨Z₂⟩</div>
                    <div>q[3] ──[H]──[Rz(x₃)]──[Ry(θ₃)]────────X────────[M] ⟨Z₃⟩</div>
                  </div>
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 font-sans">
                  <span>Engine: <strong>Qiskit Aer Statevector</strong></span>
                  <span>Ansatz: <strong>RealAmplitudes / EfficientSU2</strong></span>
                </div>
              </div>
            )}

            {activeTab === 'boundary' && (
              <div className="space-y-2 text-xs py-1">
                <div className="p-3 rounded-lg border border-[#D8E2EF] dark:border-slate-800 bg-[#F7FAFD] dark:bg-slate-900">
                  <strong className="block text-[#102A5C] dark:text-[#F4F7FB] mb-1 font-bold">
                    Controlled Classical-Quantum Protocol
                  </strong>
                  <p className="text-slate-600 dark:text-slate-400 leading-relaxed text-[11px]">
                    All quantum operations execute via local statevector and shot-based simulation
                    (Qiskit Aer and PennyLane default.qubit). EntangleX does not claim physical quantum
                    advantage or clinical diagnostic validation.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40">
                    <span className="text-slate-500 block">Gradient Strategy</span>
                    <strong className="text-slate-700 dark:text-slate-200">Parameter-Shift / Adjoint</strong>
                  </div>
                  <div className="p-2 rounded border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40">
                    <span className="text-slate-500 block">Feature Dimension</span>
                    <strong className="text-slate-700 dark:text-slate-200">2 to 8 Qubits (PCA)</strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="quantum-visual-footer">
            <span>Execution Plane: Local Simulation</span>
            <span>Framework: Qiskit Aer &amp; PennyLane</span>
          </div>
        </div>
      </div>
    </section>
  );
}

export function CoreCapabilitiesGrid() {
  const capabilities = [
    {
      title: 'Biomedical Data Lab',
      desc: 'Ingest clinical tabular cohorts, upload custom CSV files, and perform automated schema validation, missing data hygiene, and versioning.',
      icon: <Database size={18} />,
      link: '/datasets',
      tag: 'DATA PREPARATION',
      meta: 'CSV Ingestion & Quality Gates',
    },
    {
      title: 'Classical ML Baselines',
      desc: 'Train and benchmark standard clinical models including Random Forest, Logistic Regression, Support Vector Classifier, and Gradient Boosting.',
      icon: <FlaskConical size={18} />,
      link: '/training',
      tag: 'BENCHMARKING',
      meta: 'Scikit-Learn Baselines',
    },
    {
      title: 'Qiskit Quantum Circuits',
      desc: 'Construct and simulate Variational Quantum Classifiers (VQC), Quantum Kernel SVC (QSVC), and QNNs with parameterized Pauli gates.',
      icon: <Atom size={18} />,
      link: '/quantum',
      tag: 'CIRCUIT SIMULATION',
      meta: 'Qiskit Aer Simulator',
      isQuantum: true,
    },
    {
      title: 'PennyLane Hybrid PyTorch',
      desc: 'Execute differentiable quantum nodes seamlessly coupled into classical torch layers with automatic differentiation and parameter-shift rules.',
      icon: <Network size={18} />,
      link: '/quantum',
      tag: 'HYBRID NEURAL NET',
      meta: 'PennyLane + PyTorch',
      isQuantum: true,
    },
    {
      title: 'Controlled Multi-Model Comparison',
      desc: 'Conduct controlled multi-seed evaluations comparing classical, quantum, and hybrid models across Accuracy, F1, ROC-AUC, and label noise sensitivity.',
      icon: <Layers3 size={18} />,
      link: '/comparison',
      tag: 'RIGOROUS EVALUATION',
      meta: 'ROC/PR & Statistical Tests',
      isGreen: true,
    },
    {
      title: 'Explainability & Decision Support',
      desc: 'Interpret model predictions using Kernel SHAP attributions, feature importance rankings, and individual biomarker risk breakdown waterfall plots.',
      icon: <Sparkles size={18} />,
      link: '/explainability',
      tag: 'INTERPRETABILITY',
      meta: 'Kernel SHAP Evidence',
      isGreen: true,
    },
  ];

  return (
    <section className="mt-8 mb-6" aria-label="EntangleX Q-Health Core Capabilities">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2 mb-4">
        <div>
          <div className="text-[11px] font-bold tracking-wider text-[#1769E0] dark:text-[#8FC8FF] uppercase">
            VERIFIED PLATFORM CAPABILITIES
          </div>
          <h2 className="text-xl font-bold tracking-tight text-[#102A5C] dark:text-[#F4F7FB] mt-1">
            Research-Grade Classical &amp; Quantum Workflows
          </h2>
        </div>
        <Link to="/experiments" className="text-xs font-semibold text-[#1769E0] dark:text-[#8FC8FF] hover:underline flex items-center gap-1">
          <span>View experiment registry</span>
          <ArrowRight size={12} aria-hidden="true" />
        </Link>
      </div>

      <div className="capability-grid">
        {capabilities.map((cap) => (
          <Link key={cap.title} to={cap.link} className="capability-card group">
            <div className="capability-card-head">
              <div
                className={`capability-card-icon ${
                  cap.isQuantum ? 'is-quantum' : cap.isGreen ? 'is-green' : ''
                }`}
              >
                {cap.icon}
              </div>
              <span className="text-[10px] font-bold tracking-wider text-slate-500 uppercase">
                {cap.tag}
              </span>
            </div>
            <h3 className="capability-card-title">{cap.title}</h3>
            <p className="capability-card-desc">{cap.desc}</p>
            <div className="capability-card-meta">
              <span>{cap.meta}</span>
              <ArrowRight
                size={13}
                className="transition-transform group-hover:translate-x-1"
                aria-hidden="true"
              />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

export function HybridWorkflowStrip() {
  const workflowSteps = [
    { step: '01', name: 'Biomedical Data', sub: 'CSV Cohort Ingestion', to: '/datasets' },
    { step: '02', name: 'Quality Preflight', sub: 'Missing Data & Hygiene', to: '/quality' },
    { step: '03', name: 'PCA & Encoding', sub: 'Dimensionality Reduction', to: '/features' },
    { step: '04', name: 'Hybrid Modeling', sub: 'VQC, QSVC & Baselines', to: '/quantum' },
    { step: '05', name: 'Multi-Model Eval', sub: 'Controlled Comparison', to: '/comparison' },
    { step: '06', name: 'SHAP & Decision', sub: 'Feature Attributions', to: '/explainability' },
  ];

  return (
    <section className="mt-8 mb-6 rounded-2xl border border-[#D8E2EF] dark:border-slate-800 bg-[#F7FAFD] dark:bg-slate-900/40 p-4 md:p-5" aria-label="End-to-End Hybrid Quantum Pipeline">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
        <div>
          <div className="text-[11px] font-bold tracking-wider text-[#1769E0] dark:text-[#8FC8FF] uppercase">
            END-TO-END METHODOLOGY
          </div>
          <h2 className="text-base font-bold tracking-tight text-[#102A5C] dark:text-[#F4F7FB] mt-0.5">
            Six-Stage Hybrid Research Lifecycle
          </h2>
        </div>
        <span className="text-[11px] text-slate-500">
          Traceable pipeline from clinical dataset to explainable prediction
        </span>
      </div>

      <div className="workflow-stage-strip">
        {workflowSteps.map((ws) => (
          <Link key={ws.step} to={ws.to} className="workflow-stage-item group">
            <span className="workflow-stage-step">STAGE {ws.step}</span>
            <strong className="workflow-stage-name">{ws.name}</strong>
            <span className="workflow-stage-sub">{ws.sub}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
