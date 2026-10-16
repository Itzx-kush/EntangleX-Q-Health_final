import { render, screen, fireEvent } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { QuantumGateInspector } from '../components/quantum/QuantumGateInspector';
import { QuantumCircuitExplorer, gateSequence } from '../components/quantum/QuantumCircuitExplorer';
import type { Circuit } from '../types/qhealth';
import type {
  QuantumVisualizationCircuit,
  QuantumVisualizationGate,
  QuantumVisualizationFeatureMapping,
} from '../types/quantumVisualization';

const mockGates: QuantumVisualizationGate[] = [
  {
    gate_index: 0,
    name: 'H',
    gate_type: 'unitary',
    qubits: [0],
    parameters: [],
    control_qubits: [],
    target_qubits: [0],
  },
  {
    gate_index: 1,
    name: 'RY',
    gate_type: 'unitary',
    qubits: [0],
    parameters: ['x[0]'],
    control_qubits: [],
    target_qubits: [0],
  },
  {
    gate_index: 2,
    name: 'CX',
    gate_type: 'entangling',
    qubits: [0, 1],
    parameters: [],
    control_qubits: [0],
    target_qubits: [1],
  },
  {
    gate_index: 3,
    name: 'RZ',
    gate_type: 'unitary',
    qubits: [1],
    parameters: ['θ[0]'],
    control_qubits: [],
    target_qubits: [1],
  },
];

const mockFeatureMappings: QuantumVisualizationFeatureMapping[] = [
  {
    feature_index: 0,
    feature_name: 'Age (standardized)',
    qubit_index: 0,
    parameter_name: 'x[0]',
  },
  {
    feature_index: 1,
    feature_name: 'Blood Glucose',
    qubit_index: 1,
    parameter_name: 'x[1]',
  },
];

const mockCircuit: QuantumVisualizationCircuit = {
  model_type: 'vqc',
  provider_id: 'qiskit_local',
  backend_id: 'statevector',
  execution_mode: 'local_simulator',
  execution_kind: 'simulator',
  hardware_available: false,
  qubits: 4,
  logical_depth: 3,
  parameter_count: 2,
  gate_counts: { h: 1, ry: 1, cx: 1, rz: 1 },
  total_gates: 4,
  gate_sequence: mockGates,
  circuit_text: null,
  feature_map: 'ZZFeatureMap',
  ansatz: 'RealAmplitudes',
  entanglement_strategy: 'linear',
  measurement_path: 'computational_basis',
  output_semantics: 'parity_bitstring',
  limitation: 'Simulated on local classical hardware only.',
};

describe('QuantumGateInspector component', () => {
  it('renders tab headers and initial gate details', () => {
    render(
      <QuantumGateInspector
        selectedGate={mockGates[0]}
        gateIndex={0}
        totalGates={4}
        qubitCount={4}
        featureMappings={mockFeatureMappings}
        modelType="vqc"
      />
    );

    // Tab navigation buttons
    expect(screen.getByRole('tab', { name: /Gate Details/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Feature Bindings/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /Circuit Parameters/i })).toBeInTheDocument();

    // Initial gate inspection content
    expect(screen.getByText('Superposition Gate')).toBeInTheDocument();
    expect(screen.getByText(/Operation Step 1 of 4/i)).toBeInTheDocument();
    expect(screen.getByText('1 Qubit')).toBeInTheDocument();
  });

  it('displays mathematical formulas and parameter roles for inspected gates', () => {
    render(
      <QuantumGateInspector
        selectedGate={mockGates[1]}
        gateIndex={1}
        totalGates={4}
        qubitCount={4}
        featureMappings={mockFeatureMappings}
        modelType="vqc"
      />
    );

    expect(screen.getByText('Parameterized Y-Rotation')).toBeInTheDocument();
    expect(screen.getByText(/Rotates the qubit state vector on the Bloch sphere/i)).toBeInTheDocument();
    expect(screen.getByText(/Ry\(θ\) = exp/i)).toBeInTheDocument();
    expect(screen.getByText('Feature Binding')).toBeInTheDocument();
    expect(screen.getByText(/Age \(standardized\)/i)).toBeInTheDocument();
  });

  it('switches to the Feature Bindings tab and allows selecting features', () => {
    const handleFeatureSelect = vi.fn();

    render(
      <QuantumGateInspector
        selectedGate={mockGates[0]}
        gateIndex={0}
        totalGates={4}
        qubitCount={4}
        featureMappings={mockFeatureMappings}
        onFeatureSelect={handleFeatureSelect}
        modelType="vqc"
      />
    );

    // Click tab
    fireEvent.click(screen.getByRole('tab', { name: /Feature Bindings/i }));

    // Verify feature mappings table
    expect(screen.getByText('Age (standardized)')).toBeInTheDocument();
    expect(screen.getByText('Blood Glucose')).toBeInTheDocument();
    expect(screen.getByText('q[0]')).toBeInTheDocument();
    expect(screen.getByText('q[1]')).toBeInTheDocument();

    // Click feature row / button
    fireEvent.click(screen.getByText('Blood Glucose'));
    expect(handleFeatureSelect).toHaveBeenCalledWith(1);
  });

  it('switches to Circuit Parameters tab and handles parameter updates', () => {
    const handleQuantumConfigChange = vi.fn();
    const handleRegenerate = vi.fn();

    render(
      <QuantumGateInspector
        selectedGate={mockGates[0]}
        gateIndex={0}
        totalGates={4}
        qubitCount={4}
        featureMappings={mockFeatureMappings}
        modelType="vqc"
        quantumConfig={{
          qubits: 4,
          feature_map_reps: 1,
          ansatz_reps: 1,
          shots: 1024,
          backend: 'statevector',
          entanglement: 'linear',
          optimizer: 'COBYLA',
          maxiter: 30,
          noise_probability: 0,
        }}
        onQuantumConfigChange={handleQuantumConfigChange}
        onRegeneratePreview={handleRegenerate}
        isConfigModified={true}
      />
    );

    // Switch tab
    fireEvent.click(screen.getByRole('tab', { name: /Circuit Parameters/i }));

    // Notice configuration modified indicator
    expect(screen.getByText(/Configuration Modified/i)).toBeInTheDocument();

    // Adjust shots select
    const shotsSelect = screen.getByLabelText(/Execution Shots/i);
    fireEvent.change(shotsSelect, { target: { value: '2048' } });
    expect(handleQuantumConfigChange).toHaveBeenCalledWith({ shots: 2048 });

    // Click regenerate preview button
    const regenerateBtn = screen.getByRole('button', { name: /Generate Structural Preview/i });
    fireEvent.click(regenerateBtn);
    expect(handleRegenerate).toHaveBeenCalledTimes(1);
  });

  it('supports previous and next gate navigation', () => {
    const handleGateSelect = vi.fn();

    render(
      <QuantumGateInspector
        selectedGate={mockGates[1]}
        gateIndex={1}
        totalGates={4}
        qubitCount={4}
        onGateSelect={handleGateSelect}
        modelType="vqc"
      />
    );

    const prevBtn = screen.getByRole('button', { name: /Inspect previous gate/i });
    const nextBtn = screen.getByRole('button', { name: /Inspect next gate/i });

    fireEvent.click(prevBtn);
    expect(handleGateSelect).toHaveBeenCalledWith(0);

    fireEvent.click(nextBtn);
    expect(handleGateSelect).toHaveBeenCalledWith(2);
  });
});

describe('QuantumCircuitExplorer component', () => {
  it('renders circuit channels and operation gates', () => {
    render(
      <QuantumCircuitExplorer
        circuit={mockCircuit}
        sourceLabel="Backend structural preview"
        featureMappings={mockFeatureMappings}
      />
    );

    expect(screen.getByText(/Backend structural preview/i)).toBeInTheDocument();
    expect(screen.getByText(/4 qubits/i)).toBeInTheDocument();
    expect(screen.getByText(/3 depth/i)).toBeInTheDocument();
    expect(screen.getAllByText('q[0]').length).toBeGreaterThan(0);
    expect(screen.getAllByText('q[1]').length).toBeGreaterThan(0);
  });

  it('supports keyboard navigation via Arrow keys, Home, and End', () => {
    const handleSelectionChange = vi.fn();

    render(
      <QuantumCircuitExplorer
        circuit={mockCircuit}
        selectedGateIndex={1}
        onSelectionChange={handleSelectionChange}
      />
    );

    const viewport = screen.getByRole('region', { name: /Scrollable multi-qubit circuit/i });

    // Press ArrowRight to move to step 2
    fireEvent.keyDown(viewport, { key: 'ArrowRight' });
    expect(handleSelectionChange).toHaveBeenCalledWith(mockGates[2], 2);

    // Press ArrowLeft to move to step 0
    fireEvent.keyDown(viewport, { key: 'ArrowLeft' });
    expect(handleSelectionChange).toHaveBeenCalledWith(mockGates[0], 0);

    // Press Home to jump to start
    fireEvent.keyDown(viewport, { key: 'Home' });
    expect(handleSelectionChange).toHaveBeenCalledWith(mockGates[0], 0);

    // Press End to jump to end
    fireEvent.keyDown(viewport, { key: 'End' });
    expect(handleSelectionChange).toHaveBeenCalledWith(mockGates[3], 3);
  });

  it('normalizes fitted circuits seamlessly with gateSequence helper', () => {
    const fittedCircuit = {
      qubits: 2,
      depth: 2,
      gates: [
        { name: 'h', qubits: [0], parameters: [] },
        { name: 'cx', qubits: [0, 1], parameters: [] },
      ],
      diagram: '',
      gate_counts: { h: 1, cx: 1 },
    };

    const sequence = gateSequence(fittedCircuit as unknown as Circuit);
    expect(sequence).toHaveLength(2);
    expect(sequence[0].name).toBe('h');
    expect(sequence[1].name).toBe('cx');
    expect(sequence[0].qubits).toEqual([0]);
  });
});
