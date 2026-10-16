import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { QuantumHero, CoreCapabilitiesGrid, HybridWorkflowStrip } from '../components/QuantumHero';

describe('QuantumHero component', () => {
  it('renders the hero title, technical badges, and live telemetry', () => {
    render(
      <MemoryRouter>
        <QuantumHero
          backendStatus="online"
          quantumAvailable={true}
          runtimeVerified={true}
          datasetCount={5}
          experimentCount={12}
          readyModelCount={7}
          activeJobCount={0}
          flagshipAvailable={true}
        />
      </MemoryRouter>
    );

    // Primary headline check
    expect(
      screen.getByRole('heading', {
        name: /Hybrid Classical-Quantum Machine Learning for Healthcare Research/i,
      })
    ).toBeInTheDocument();

    // Primary CTAs check
    expect(screen.getByRole('link', { name: /Launch Verified Demo/i })).toHaveAttribute(
      'href',
      '/demo'
    );
    expect(screen.getByRole('link', { name: /Explore Data Lab/i })).toHaveAttribute(
      'href',
      '/datasets'
    );

    // Status pill check
    expect(screen.getByText('BACKEND ONLINE')).toBeInTheDocument();
    expect(screen.getByText(/Qiskit Aer & PennyLane \(Local Simulation\)/i)).toBeInTheDocument();

    // Telemetry summary numbers check
    expect(screen.getByText('5 Cohorts')).toBeInTheDocument();
    expect(screen.getByText('12 Recorded')).toBeInTheDocument();
    expect(screen.getByText('7 Artifacts')).toBeInTheDocument();
  });

  it('switches between pipeline, circuit spec, and boundary tabs', () => {
    render(
      <MemoryRouter>
        <QuantumHero backendStatus="online" />
      </MemoryRouter>
    );

    // Initially in pipeline tab
    expect(screen.getByText('STAGE 01')).toBeInTheDocument();
    expect(screen.getByText('Biomarkers')).toBeInTheDocument();

    // Switch to Circuit Spec tab
    const circuitTab = screen.getByRole('tab', { name: /Circuit Spec/i });
    fireEvent.click(circuitTab);
    expect(screen.getByText('LOGICAL CIRCUIT TOPOLOGY')).toBeInTheDocument();
    expect(screen.getByText(/4 QUBITS · DEPTH 8/i)).toBeInTheDocument();

    // Switch to Boundary tab
    const boundaryTab = screen.getByRole('tab', { name: /Boundary/i });
    fireEvent.click(boundaryTab);
    expect(screen.getByText('Controlled Classical-Quantum Protocol')).toBeInTheDocument();
    expect(
      screen.getByText(/All quantum operations execute via local statevector and shot-based simulation/i)
    ).toBeInTheDocument();
  });
});

describe('CoreCapabilitiesGrid component', () => {
  it('renders all six verified platform capability cards with correct links', () => {
    render(
      <MemoryRouter>
        <CoreCapabilitiesGrid />
      </MemoryRouter>
    );

    expect(screen.getByText('Biomedical Data Lab')).toBeInTheDocument();
    expect(screen.getByText('Classical ML Baselines')).toBeInTheDocument();
    expect(screen.getByText('Qiskit Quantum Circuits')).toBeInTheDocument();
    expect(screen.getByText('PennyLane Hybrid PyTorch')).toBeInTheDocument();
    expect(screen.getByText('Controlled Multi-Model Comparison')).toBeInTheDocument();
    expect(screen.getByText('Explainability & Decision Support')).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Biomedical Data Lab/i })).toHaveAttribute(
      'href',
      '/datasets'
    );
    expect(screen.getByRole('link', { name: /Classical ML Baselines/i })).toHaveAttribute(
      'href',
      '/training'
    );
    expect(screen.getByRole('link', { name: /Controlled Multi-Model Comparison/i })).toHaveAttribute(
      'href',
      '/comparison'
    );
    expect(screen.getByRole('link', { name: /Explainability & Decision Support/i })).toHaveAttribute(
      'href',
      '/explainability'
    );
  });
});

describe('HybridWorkflowStrip component', () => {
  it('renders the six-stage methodology in sequence', () => {
    render(
      <MemoryRouter>
        <HybridWorkflowStrip />
      </MemoryRouter>
    );

    expect(screen.getByText('STAGE 01')).toBeInTheDocument();
    expect(screen.getByText('Biomedical Data')).toBeInTheDocument();
    expect(screen.getByText('STAGE 06')).toBeInTheDocument();
    expect(screen.getByText('SHAP & Decision')).toBeInTheDocument();
  });
});
