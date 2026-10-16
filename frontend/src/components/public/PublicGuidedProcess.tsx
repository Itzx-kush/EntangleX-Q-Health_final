import {useEffect, useRef, useState} from 'react';
import {CheckCircle2, ChevronRight, Database, Dna, FileCheck, Layers} from 'lucide-react';

interface ProcessStage {
  id: string;
  number: string;
  title: string;
  subtitle: string;
  icon: typeof Database;
  description: string;
  items: string[];
  metrics: {label: string; value: string}[];
}

const STAGES: ProcessStage[] = [
  {
    id: 'stage-01',
    number: '01',
    title: 'Data Preparation & Quality Control',
    subtitle: 'Traceable biomedical ingestion and clinical boundary verification',
    icon: Database,
    description:
      'Every research session begins with rigorous missingness profiling, distribution checking, and cryptographic dataset fingerprinting before features are encoded.',
    items: [
      'Automated missing-value analysis and outlier bounds checking',
      'Immutable SHA-256 dataset provenance signatures',
      'Clinical label sanity audits (SIH-26139 reference schema)',
      'Deterministic train/validation/test split isolation',
    ],
    metrics: [
      {label: 'Validation Standard', value: 'Schema Audit Protocol'},
      {label: 'Provenance Policy', value: 'SHA-256 Digest Rule'},
      {label: 'Partition Policy', value: 'Stratified 5-Fold Split'},
    ],
  },
  {
    id: 'stage-02',
    number: '02',
    title: 'Feature Engineering & Selection',
    subtitle: 'Biomarker prioritization and quantum angle encoding',
    icon: Dna,
    description:
      'High-dimensional omic and clinical attributes are ranked through mutual information and variance filters, then scaled into bounded angular phases for quantum circuits.',
    items: [
      'Biomedical mutual-information feature scoring',
      'Correlation redundancy pruning across candidate biomarkers',
      'Min-max phase normalization mapped into [0, π] rotation angles',
      'Compact 4-to-8 qubit feature vector reduction',
    ],
    metrics: [
      {label: 'Biomarker Capacity', value: 'Configurable (4-16)'},
      {label: 'Ranking Criterion', value: 'Mutual Information'},
      {label: 'Phase Mapping', value: 'RY Angle Rotation'},
    ],
  },
  {
    id: 'stage-03',
    number: '03',
    title: 'Hybrid VQC Modelling',
    subtitle: 'Variational quantum circuits trained alongside classical baselines',
    icon: Layers,
    description:
      'Parameterized quantum circuits with entangled rotation layers are trained using PennyLane and statevector simulators under the exact same data partitions as classical models.',
    items: [
      'Parameterized unitary ansatz with ring-topology CNOT gates',
      'Classical gradient backpropagation via parameter-shift rules',
      'Concurrent training of Random Forest, SVM, and XGBoost baselines',
      'Hardware simulator profiling without conflating simulator with hardware',
    ],
    metrics: [
      {label: 'Ansatz Architecture', value: '2-4 Variational Layers'},
      {label: 'Entangling Pattern', value: 'Ring CNOT Topology'},
      {label: 'Benchmark Scope', value: 'VQC + Classical Baselines'},
    ],
  },
  {
    id: 'stage-04',
    number: '04',
    title: 'Controlled Evaluation & Validation',
    subtitle: 'Shared evidence boundaries and noise robustness testing',
    icon: FileCheck,
    description:
      'Models are compared strictly across identical test folds using AUROC, Brier score, and simulated quantum noise models to guarantee truthful scientific claims.',
    items: [
      'Multi-metric evaluation: ROC-AUC, PR-AUC, F1-score, and Brier calibration',
      'Simulated depolarizing noise and shot-noise resilience sweeps',
      'SHAP and quantum state gradient feature attribution',
      'Automated export of reproducible research evidence packages',
    ],
    metrics: [
      {label: 'Holdout Partitioning', value: 'Strict Identical Splits'},
      {label: 'Noise Stress Profiling', value: 'Depolarizing Sweeps'},
      {label: 'Evidence Export', value: 'Reproducible PDF & JSON'},
    ],
  },
];

export function PublicGuidedProcess() {
  const [activeStageId, setActiveStageId] = useState<string>('stage-01');
  const containerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const stageElements = STAGES.map(s => document.getElementById(s.id)).filter(
      Boolean
    ) as HTMLElement[];

    if (!('IntersectionObserver' in window) || stageElements.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            setActiveStageId(entry.target.id);
          }
        });
      },
      {
        root: null,
        rootMargin: '-20% 0px -50% 0px',
        threshold: 0.1,
      }
    );

    stageElements.forEach(el => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const scrollToStage = (stageId: string) => {
    setActiveStageId(stageId);
    const target = document.getElementById(stageId);
    if (target) {
      const topOffset = 100;
      const elementPosition = target.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - topOffset;
      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth',
      });
    }
  };

  return (
    <section id="guided-process" className="public-guided-section" ref={containerRef}>
      <div className="public-guided-shell">
        {/* Section Header */}
        <div className="public-guided-header" data-public-reveal>
          <div className="public-guided-eyebrow">
            <span>02 // METHODOLOGY</span>
            <span>The EntangleX Research Pathway</span>
          </div>
          <h2 className="public-guided-title">
            From Raw Biomarkers to Controlled Quantum Evidence
          </h2>
          <p className="public-guided-subhead">
            EntangleX enforces a transparent four-stage pipeline. No model makes unsupported claims;
            every quantum simulation is benchmarked directly against classical counterparts.
          </p>
        </div>

        {/* Guided Process Layout: Sticky Stepper + Process Cards */}
        <div className="public-guided-layout">
          {/* Sticky Side Indicator (Desktop) */}
          <aside className="public-guided-stepper" aria-label="Process stages navigation">
            <div className="public-stepper-sticky-wrap">
              <span className="public-stepper-label">WORKFLOW STAGES</span>
              <nav className="public-stepper-list" role="tablist">
                {STAGES.map(stage => {
                  const isActive = stage.id === activeStageId;
                  return (
                    <button
                      key={stage.id}
                      type="button"
                      role="tab"
                      aria-selected={isActive}
                      aria-controls={stage.id}
                      className={`public-stepper-item ${isActive ? 'is-active' : ''}`}
                      onClick={() => scrollToStage(stage.id)}
                    >
                      <span className="public-stepper-num">{stage.number}</span>
                      <span className="public-stepper-name">{stage.title}</span>
                      {isActive && <ChevronRight size={14} className="public-stepper-indicator" />}
                    </button>
                  );
                })}
              </nav>
            </div>
          </aside>

          {/* Detailed Cards List */}
          <div className="public-guided-cards">
            {STAGES.map(stage => {
              const Icon = stage.icon;
              const isActive = stage.id === activeStageId;
              return (
                <article
                  key={stage.id}
                  id={stage.id}
                  className={`public-stage-card ${isActive ? 'is-in-view' : ''}`}
                  data-public-reveal
                >
                  <div className="public-stage-header">
                    <div className="public-stage-num-badge">
                      <span>{stage.number}</span>
                    </div>
                    <div className="public-stage-title-wrap">
                      <div className="public-stage-icon-wrap">
                        <Icon size={18} className="public-stage-icon" />
                        <span className="public-stage-tag">STAGE {stage.number}</span>
                      </div>
                      <h3 className="public-stage-title">{stage.title}</h3>
                      <p className="public-stage-subtitle">{stage.subtitle}</p>
                    </div>
                  </div>

                  <p className="public-stage-description">{stage.description}</p>

                  <div className="public-stage-checklist">
                    {stage.items.map(item => (
                      <div key={item} className="public-checklist-item">
                        <CheckCircle2 size={15} className="public-check-icon" />
                        <span>{item}</span>
                      </div>
                    ))}
                  </div>

                  <div className="public-stage-metrics-row">
                    {stage.metrics.map(metric => (
                      <div key={metric.label} className="public-stage-metric-box">
                        <span className="public-stage-metric-label">{metric.label}</span>
                        <strong className="public-stage-metric-val">{metric.value}</strong>
                      </div>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
