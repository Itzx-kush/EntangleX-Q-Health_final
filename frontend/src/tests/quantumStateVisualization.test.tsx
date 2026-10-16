import {fireEvent,render,screen,within} from '@testing-library/react';
import {describe,expect,it,vi} from 'vitest';
import {QuantumStatePanel} from '../components/quantum/QuantumStatePanel';
import type {QuantumVisualizationContract,QuantumVisualizationGate} from '../types/quantumVisualization';

type ContractOverrides=Omit<Partial<QuantumVisualizationContract>,'dataset_context'|'encoding'|'circuit'|'provider'|'state'|'bloch'|'entanglement'|'measurement'|'resources'>&{
  dataset_context?:Partial<QuantumVisualizationContract['dataset_context']>;
  encoding?:Partial<QuantumVisualizationContract['encoding']>;
  circuit?:Partial<QuantumVisualizationContract['circuit']>;
  provider?:Partial<QuantumVisualizationContract['provider']>;
  state?:Partial<QuantumVisualizationContract['state']>;
  bloch?:Partial<QuantumVisualizationContract['bloch']>;
  entanglement?:Partial<QuantumVisualizationContract['entanglement']>;
  measurement?:Partial<QuantumVisualizationContract['measurement']>;
  resources?:Partial<QuantumVisualizationContract['resources']>;
};

const gate=(gate_index:number,name:string,qubits:number[],parameters:string[]=[]):QuantumVisualizationGate=>({
  gate_index,
  name,
  gate_type:name==='CX'?'controlled':'rotation',
  qubits,
  parameters,
  control_qubits:name==='CX'?[0]:[],
  target_qubits:name==='CX'?[1]:[],
});

function makeContract(overrides:ContractOverrides={}):QuantumVisualizationContract{
  const base:QuantumVisualizationContract={
    schema_version:'quantum-visualization-v1',
    request_fingerprint:'test-fingerprint',
    status:'STRUCTURE_ONLY',
    model_type:'vqc',
    dataset_context:{
      status:'NOT_AVAILABLE',
      dataset_id:null,
      dataset_version_id:null,
      dataset_name:null,
      dataset_hash:null,
      raw_feature_count:null,
      raw_feature_names:null,
      represented_feature_count:null,
      selected_feature_names:null,
      configured_input_features:null,
      representation_configuration:{},
      representation_status:'NOT_AVAILABLE',
      representation_source:null,
      row_count:null,
      experiment_id:null,
      limitations:['No dataset context supplied.'],
    },
    encoding:{
      status:'STRUCTURE_ONLY',
      method:'angle',
      description:'Backend structural encoding description.',
      feature_to_qubit_mapping:[],
      encoding_parameters:{},
      encoded_dimension:2,
      angle_scaling:null,
      limitations:[],
    },
    circuit:{
      model_type:'vqc',
      provider_id:'qiskit_local',
      backend_id:'statevector',
      execution_mode:'local_simulator',
      execution_kind:'local_simulator',
      hardware_available:false,
      qubits:2,
      logical_depth:2,
      parameter_count:1,
      gate_counts:{H:1,RY:1},
      total_gates:2,
      gate_sequence:[gate(1,'RY',[0],['theta_0']),gate(0,'H',[0])],
      circuit_text:'H q[0]\nRY(theta_0) q[0]',
      feature_map:'ZZFeatureMap',
      ansatz:'RealAmplitudes',
      entanglement_strategy:'linear',
      measurement_path:'Z expectation',
      output_semantics:'Backend-reported expectation output',
      limitation:'Structural preview only.',
    },
    provider:{
      provider_id:'qiskit_local',
      display_name:'Qiskit local',
      provider_type:'LOCAL_SIMULATOR',
      availability:'AVAILABLE',
      backend_id:'statevector',
      backend_type:'statevector',
      backend_availability:'AVAILABLE',
      execution_mode:'local_simulator',
      hardware_available:false,
    },
    state:{
      status:'STRUCTURE_ONLY',
      execution_source:null,
      simulator:null,
      backend_id:null,
      circuit_scope:null,
      input_sample_count:null,
      basis_states:null,
      amplitude_real:null,
      amplitude_imaginary:null,
      amplitude_magnitude:null,
      phase:null,
      probability:null,
      normalized_probability:null,
      measurement_counts:null,
      shots:null,
      limitations:['No simulation was run.'],
    },
    bloch:{
      status:'NOT_AVAILABLE',
      representation:null,
      qubits:null,
      limitation:'No reduced-state computation was performed.',
    },
    entanglement:{
      status:'STRUCTURE_ONLY',
      indicator:null,
      participating_qubits:null,
      method:null,
      reduced_state_measures:null,
      limitations:['Gate connectivity alone does not establish state entanglement.'],
    },
    measurement:{
      status:'STRUCTURE_ONLY',
      method:'Z measurement path',
      output_semantics:null,
      counts:null,
      shots:null,
      limitations:['No measurement executed.'],
    },
    resources:{
      status:'AVAILABLE',
      logical_qubits:2,
      circuit_depth:2,
      total_gates:2,
      parameterized_gates:1,
      entangling_gates:0,
      shots:null,
      sample_count:null,
      feature_dimension:2,
      optimizer_iterations:100,
      resource_category:'small',
      bounded_policy_status:'within_budget',
      backend_availability:'AVAILABLE',
      simulator_type:'statevector',
      policy_version:'quantum-resource-policy-v1',
      limitations:[],
    },
    hybrid_architecture:null,
    limitations:['Preview does not simulate a state.'],
  };

  return {
    ...base,
    ...overrides,
    dataset_context:{...base.dataset_context,...overrides.dataset_context},
    encoding:{...base.encoding,...overrides.encoding},
    circuit:{...base.circuit,...overrides.circuit},
    provider:{...base.provider,...overrides.provider},
    state:{...base.state,...overrides.state},
    bloch:{...base.bloch,...overrides.bloch},
    entanglement:{...base.entanglement,...overrides.entanglement},
    measurement:{...base.measurement,...overrides.measurement},
    resources:{...base.resources,...overrides.resources},
  };
}

describe('QuantumStatePanel Component', () => {
  it('renders structural preview notice when simulation has not been run', () => {
    render(<QuantumStatePanel contract={makeContract()} />);
    expect(screen.getAllByText('STRUCTURE ONLY').length).toBeGreaterThan(0);
    expect(screen.getByText(/Structural preview only/)).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Probability' })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Bloch' })).not.toBeInTheDocument();
  });

  it('renders interactive vector presets and triggers simulation', () => {
    const onSimulate = vi.fn();
    const onEncodedVectorChange = vi.fn();
    render(
      <QuantumStatePanel
        contract={makeContract()}
        encodedVector={[0.5, 0.5]}
        onEncodedVectorChange={onEncodedVectorChange}
        onSimulate={onSimulate}
        qubitCount={2}
      />
    );

    const uniformBtn = screen.getByRole('button', { name: /Uniform \(0\.5\)/ });
    expect(uniformBtn).toBeInTheDocument();
    fireEvent.click(uniformBtn);
    expect(onEncodedVectorChange).toHaveBeenCalledWith([0.5, 0.5]);

    const zeroBtn = screen.getByRole('button', { name: /Zeros \(0\.0\)/ });
    fireEvent.click(zeroBtn);
    expect(onEncodedVectorChange).toHaveBeenCalledWith([0.0, 0.0]);

    const simBtn = screen.getByRole('button', { name: /Simulate circuit/ });
    expect(simBtn).toBeInTheDocument();
    fireEvent.click(simBtn);
    expect(onSimulate).toHaveBeenCalledTimes(1);
  });

  it('renders probability distribution with sorting and normalization check', () => {
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_local',
        backend_id: 'statevector',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['00', '01', '10', '11'],
        amplitude_real: [0.7071, 0, 0, 0.7071],
        amplitude_imaginary: [0, 0, 0, 0],
        amplitude_magnitude: [0.7071, 0, 0, 0.7071],
        phase: [0, null, null, 0],
        probability: [0.5, 0.0, 0.0, 0.5],
        normalized_probability: [0.5, 0.0, 0.0, 0.5],
        measurement_counts: null,
        shots: null,
        limitations: [],
      },
    });

    render(<QuantumStatePanel contract={contract} />);
    expect(screen.getByRole('tab', { name: 'Probability' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getAllByText('50.00%').length).toBe(2);
    expect(screen.getByText('|00⟩')).toBeInTheDocument();
    expect(screen.getByText('|11⟩')).toBeInTheDocument();
    expect(screen.getByText(/Normalized \(100%\)/)).toBeInTheDocument();
    expect(screen.getByText('Exact Statevector Probabilities')).toBeInTheDocument();

    // Toggle sorting
    const sortIndexBtn = screen.getByRole('button', { name: 'Basis index ↑' });
    fireEvent.click(sortIndexBtn);
    expect(sortIndexBtn).toHaveClass('is-active');

    // Selecting a basis state opens the inspector details
    const state00 = screen.getByText('|00⟩').closest('button')!;
    fireEvent.click(state00);
    expect(screen.getByRole('region', { name: 'Selected basis state details' })).toBeInTheDocument();
    expect(screen.getByText(/Selected state: \|00⟩/)).toBeInTheDocument();
  });

  it('handles small non-zero probabilities gracefully without rounding to 0.00%', () => {
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_local',
        backend_id: 'statevector',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['00', '01'],
        amplitude_real: [0.99999, 0.003],
        amplitude_imaginary: [0, 0],
        amplitude_magnitude: [0.99999, 0.003],
        phase: [0, 0],
        probability: [0.99999, 0.000009],
        normalized_probability: [0.99999, 0.000009],
        measurement_counts: null,
        shots: null,
        limitations: [],
      },
    });

    render(<QuantumStatePanel contract={contract} />);
    expect(screen.getByText('< 0.01%')).toBeInTheDocument();
  });

  it('renders complex amplitudes with formatted signs, magnitude bars, and sorting', () => {
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_local',
        backend_id: 'statevector',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['00', '01'],
        amplitude_real: [0.5, 0.0],
        amplitude_imaginary: [-0.5, 0.7071],
        amplitude_magnitude: [Math.SQRT1_2, 0.7071],
        phase: [-Math.PI / 4, Math.PI / 2],
        probability: [0.5, 0.5],
        normalized_probability: [0.5, 0.5],
        measurement_counts: null,
        shots: null,
        limitations: [],
      },
    });

    render(<QuantumStatePanel contract={contract} />);
    const ampTab = screen.getByRole('tab', { name: 'Amplitude' });
    fireEvent.click(ampTab);
    expect(ampTab).toHaveAttribute('aria-selected', 'true');

    // Negative imaginary formatting check: "0.5000 − 0.5000i"
    expect(screen.getByText(/0\.5000 − 0\.5000i/)).toBeInTheDocument();
    expect(screen.getByText(/0\.0000 \+ 0\.7071i/)).toBeInTheDocument();
    expect(screen.getAllByText(/\|a\|/).length).toBe(2);
  });

  it('renders phase in radians and degrees, and displays Undefined for zero amplitude states', () => {
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_local',
        backend_id: 'statevector',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['00', '01'],
        amplitude_real: [1.0, 0.0],
        amplitude_imaginary: [0.0, 0.0],
        amplitude_magnitude: [1.0, 0.0],
        phase: [1.570796, null], // 01 has zero amplitude, phase is undefined
        probability: [1.0, 0.0],
        normalized_probability: [1.0, 0.0],
        measurement_counts: null,
        shots: null,
        limitations: [],
      },
    });

    render(<QuantumStatePanel contract={contract} />);
    const phaseTab = screen.getByRole('tab', { name: 'Phase' });
    fireEvent.click(phaseTab);
    expect(phaseTab).toHaveAttribute('aria-selected', 'true');

    expect(screen.getByText('1.571 rad')).toBeInTheDocument();
    expect(screen.getByText('90.0°')).toBeInTheDocument();
    expect(screen.getByText('Undefined')).toBeInTheDocument();
    expect(screen.getByText('(|α| = 0)')).toBeInTheDocument();
  });

  it('integrates QuantumBlochExplorer when bloch coordinates are available', () => {
    const onQubitSelect = vi.fn();
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_local',
        backend_id: 'statevector',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['0', '1'],
        amplitude_real: [1.0, 0.0],
        amplitude_imaginary: [0.0, 0.0],
        amplitude_magnitude: [1.0, 0.0],
        phase: [0, null],
        probability: [1.0, 0.0],
        normalized_probability: [1.0, 0.0],
        measurement_counts: null,
        shots: null,
        limitations: [],
      },
      bloch: {
        status: 'AVAILABLE',
        representation: 'single-qubit reduced density matrices',
        limitation: null,
        qubits: [
          {
            qubit_index: 0,
            x: 0.0,
            y: 0.0,
            z: 1.0,
            polar_angle: 0.0,
            azimuth: 0.0,
            purity: 1.0,
            state_representation_status: 'AVAILABLE',
          },
          {
            qubit_index: 1,
            x: 0.5,
            y: 0.0,
            z: 0.5,
            polar_angle: 0.785,
            azimuth: 0.0,
            purity: 0.85,
            state_representation_status: 'AVAILABLE',
          },
        ],
      },
    });

    render(<QuantumStatePanel contract={contract} onQubitSelect={onQubitSelect} />);
    const blochTab = screen.getByRole('tab', { name: 'Bloch' });
    fireEvent.click(blochTab);
    expect(blochTab).toHaveAttribute('aria-selected', 'true');

    expect(screen.getByText(/Single-Qubit Reduced Density Matrices/)).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Bloch projection for qubit 0/ })).toBeInTheDocument();

    const q1Btn = screen.getByRole('tab', { name: /q\[1\]/ });
    fireEvent.click(q1Btn);
    expect(onQubitSelect).toHaveBeenCalledWith(1);
  });

  it('renders finite-shot Aer measurement counts and notes', () => {
    const contract = makeContract({
      status: 'AVAILABLE',
      state: {
        status: 'AVAILABLE',
        execution_source: 'local_simulator',
        simulator: 'qiskit_aer',
        backend_id: 'aer',
        circuit_scope: 'feature_map',
        input_sample_count: 1,
        basis_states: ['00', '11'],
        amplitude_real: null,
        amplitude_imaginary: null,
        amplitude_magnitude: null,
        phase: null,
        probability: [0.6, 0.4],
        normalized_probability: [0.6, 0.4],
        measurement_counts: { '00': 600, '11': 400 },
        shots: 1000,
        limitations: [],
      },
      measurement: {
        status: 'AVAILABLE',
        method: 'simulator shots',
        output_semantics: 'shot counts',
        counts: { '00': 600, '11': 400 },
        shots: 1000,
        limitations: [],
      },
    });

    render(<QuantumStatePanel contract={contract} />);
    const measTab = screen.getByRole('tab', { name: 'Measurements' });
    fireEvent.click(measTab);

    expect(screen.getByText('600')).toBeInTheDocument();
    expect(screen.getByText('400')).toBeInTheDocument();
    expect(screen.getByText(/1,000 total returned counts/)).toBeInTheDocument();
    expect(screen.getByText(/Counts are simulator outputs, not hardware measurements/)).toBeInTheDocument();
  });

  it('displays state indicator banners for loading, stale, and error conditions', () => {
    const onSimulate = vi.fn();

    // 1. Loading state
    const { rerender } = render(
      <QuantumStatePanel
        contract={makeContract()}
        isSimulating={true}
        onSimulate={onSimulate}
      />
    );
    expect(screen.getByText(/Simulating circuit…/)).toBeInTheDocument();

    // 2. Stale state
    rerender(
      <QuantumStatePanel
        contract={makeContract({ status: 'AVAILABLE', state: { status: 'AVAILABLE', basis_states: ['0'], normalized_probability: [1] } })}
        isSimulating={false}
        isStale={true}
        onSimulate={onSimulate}
      />
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/Circuit configuration changed since last simulation/);
    const reSimBtn = within(screen.getByRole('alert')).getByRole('button', { name: /Re-simulate/ });
    fireEvent.click(reSimBtn);
    expect(onSimulate).toHaveBeenCalled();

    // 3. Error state
    rerender(
      <QuantumStatePanel
        contract={makeContract()}
        simulationError="Local simulation memory exhausted"
        onSimulate={onSimulate}
      />
    );
    expect(screen.getByRole('alert')).toHaveTextContent(/Local simulation memory exhausted/);
    const retryBtn = screen.getByRole('button', { name: 'Retry' });
    fireEvent.click(retryBtn);
    expect(onSimulate).toHaveBeenCalledTimes(2);
  });
});
