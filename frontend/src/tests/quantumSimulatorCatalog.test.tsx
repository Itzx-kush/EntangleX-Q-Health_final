import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QuantumSimulatorCatalog } from '../components/quantum/QuantumSimulatorCatalog';
import { qh } from '../lib/api';
import type { QuantumProviderDescriptor, QuantumProviderHealthResponse } from '../types/qhealth';

vi.mock('../lib/api', () => ({
  qh: {
    quantumProviders: vi.fn(),
    quantumProviderHealth: vi.fn(),
  },
}));

const mockProviders: QuantumProviderDescriptor[] = [
  {
    provider_id: 'qiskit_local',
    display_name: 'Qiskit Local Simulator',
    provider_type: 'LOCAL_SIMULATOR',
    enabled: true,
    availability: 'AVAILABLE',
    backends: [
      {
        backend_id: 'statevector',
        display_name: 'Exact Statevector',
        provider_id: 'qiskit_local',
        backend_type: 'LOCAL_SIMULATOR',
        available: true,
        capabilities: {
          supports_sampling: 'SUPPORTED',
          supports_statevector: 'SUPPORTED',
          supports_estimator: 'UNKNOWN',
          supports_shots: 'UNSUPPORTED',
          supports_noise_model: 'UNSUPPORTED',
          supports_hardware_execution: 'UNSUPPORTED',
          supports_async_jobs: 'UNSUPPORTED',
          supports_cancellation: 'UNSUPPORTED',
          supports_batching: 'SUPPORTED',
          supports_gradients: 'UNKNOWN',
          supports_parameterized_circuits: 'SUPPORTED',
          max_qubits: null,
          max_shots: null,
        },
      },
      {
        backend_id: 'aer',
        display_name: 'Qiskit Aer Simulator',
        provider_id: 'qiskit_local',
        backend_type: 'LOCAL_SIMULATOR',
        available: true,
        capabilities: {
          supports_sampling: 'SUPPORTED',
          supports_statevector: 'SUPPORTED',
          supports_estimator: 'UNKNOWN',
          supports_shots: 'SUPPORTED',
          supports_noise_model: 'SUPPORTED',
          supports_hardware_execution: 'UNSUPPORTED',
          supports_async_jobs: 'UNSUPPORTED',
          supports_cancellation: 'UNSUPPORTED',
          supports_batching: 'SUPPORTED',
          supports_gradients: 'UNKNOWN',
          supports_parameterized_circuits: 'SUPPORTED',
          max_qubits: null,
          max_shots: 16384,
        },
      },
    ],
  },
  {
    provider_id: 'pennylane_local',
    display_name: 'PennyLane Local Simulator',
    provider_type: 'LOCAL_SIMULATOR',
    enabled: true,
    availability: 'AVAILABLE',
    backends: [
      {
        backend_id: 'default.qubit',
        display_name: 'PennyLane default.qubit',
        provider_id: 'pennylane_local',
        backend_type: 'LOCAL_SIMULATOR',
        available: true,
        capabilities: {
          supports_sampling: 'SUPPORTED',
          supports_statevector: 'SUPPORTED',
          supports_estimator: 'SUPPORTED',
          supports_shots: 'SUPPORTED',
          supports_noise_model: 'UNSUPPORTED',
          supports_hardware_execution: 'UNSUPPORTED',
          supports_async_jobs: 'UNSUPPORTED',
          supports_cancellation: 'UNSUPPORTED',
          supports_batching: 'SUPPORTED',
          supports_gradients: 'SUPPORTED',
          supports_parameterized_circuits: 'SUPPORTED',
          max_qubits: null,
          max_shots: null,
        },
      },
    ],
  },
];

const mockHealth: QuantumProviderHealthResponse = {
  providers: [
    {
      provider_id: 'qiskit_local',
      availability: 'AVAILABLE',
      packages_present: {
        qiskit: true,
        qiskit_machine_learning: true,
        qiskit_aer: true,
      },
      runtime_verified: false,
      execution: 'local quantum simulation only; no hardware credentials or hardware execution',
    },
    {
      provider_id: 'pennylane_local',
      availability: 'AVAILABLE',
      packages_present: {
        pennylane: true,
      },
      runtime_verified: false,
      execution: 'local quantum simulation only; no hardware credentials or hardware execution',
    },
  ],
};

function renderCatalog(node: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{node}</QueryClientProvider>);
}

describe('QuantumSimulatorCatalog Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders registered quantum simulation providers and backends from backend metadata', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog activeBackendId="statevector" activeProviderId="qiskit_local" />);

    // Check title and description
    expect(screen.getByText(/Quantum Simulators & Execution Providers/i)).toBeInTheDocument();
    expect(screen.getByText(/DISCOVERY & EXECUTION CATALOG/i)).toBeInTheDocument();

    // Check providers
    await waitFor(() => {
      expect(screen.getByText('Qiskit Local Simulator')).toBeInTheDocument();
      expect(screen.getByText('PennyLane Local Simulator')).toBeInTheDocument();
    });

    // Check backends
    expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    expect(screen.getByText('Qiskit Aer Simulator')).toBeInTheDocument();
    expect(screen.getByText('PennyLane default.qubit')).toBeInTheDocument();

    // Check package readiness pills
    expect(screen.getByText('qiskit')).toBeInTheDocument();
    expect(screen.getByText('qiskit_aer')).toBeInTheDocument();
    expect(screen.getByText('pennylane')).toBeInTheDocument();
  });

  it('truthfully discloses the classical local simulation boundary without claiming hardware', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    });

    expect(screen.getByText(/Classical Local Simulation Boundary/i)).toBeInTheDocument();

    expect(
      screen.getByText(/Physical quantum hardware execution, remote cloud queues, and QPU device reservations are explicitly unsupported/i)
    ).toBeInTheDocument();

    // Multiple "Physical Hardware" rows explicitly stating Unsupported
    const hardwareLabels = screen.getAllByText('Physical Hardware');
    expect(hardwareLabels.length).toBe(3);
  });

  it('displays accurate capability matrix and max shots for backends', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    });

    // Aer backend displays max shots
    expect(screen.getByText(/Max 16,384 shots/i)).toBeInTheDocument();
    expect(screen.getByText(/Max Shots:/i)).toBeInTheDocument();
    expect(screen.getByText('16,384')).toBeInTheDocument();
  });

  it('filters backends by provider category chips', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText('Qiskit Local Simulator')).toBeInTheDocument();
      expect(screen.getByText('PennyLane Local Simulator')).toBeInTheDocument();
    });

    // Click PennyLane filter chip
    const pennylaneChip = screen.getByRole('button', { name: /PennyLane Local/i });
    fireEvent.click(pennylaneChip);

    // PennyLane is visible, Qiskit is filtered out
    expect(screen.getByText('PennyLane Local Simulator')).toBeInTheDocument();
    expect(screen.queryByText('Qiskit Local Simulator')).not.toBeInTheDocument();

    // Click Noise Modeling filter chip
    const noiseChip = screen.getByRole('button', { name: /Noise Modeling/i });
    fireEvent.click(noiseChip);

    // Aer supports noise, statevector and pennylane do not
    expect(screen.getByText('Qiskit Aer Simulator')).toBeInTheDocument();
    expect(screen.queryByText('Exact Statevector')).not.toBeInTheDocument();
    expect(screen.queryByText('PennyLane default.qubit')).not.toBeInTheDocument();

    // Click All Backends
    const allChip = screen.getByRole('button', { name: /All Backends/i });
    fireEvent.click(allChip);
    expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    expect(screen.getByText('PennyLane default.qubit')).toBeInTheDocument();
  });

  it('filters backends by text search query', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search simulators/i);
    fireEvent.change(searchInput, { target: { value: 'aer' } });

    // Aer matches, statevector and pennylane do not
    expect(screen.getByText('Qiskit Aer Simulator')).toBeInTheDocument();
    expect(screen.queryByText('Exact Statevector')).not.toBeInTheDocument();
    expect(screen.queryByText('PennyLane default.qubit')).not.toBeInTheDocument();
  });

  it('displays empty state when search query matches nothing, and resets filters', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search simulators/i);
    fireEvent.change(searchInput, { target: { value: 'non_existent_backend' } });

    expect(screen.getByText(/No Simulators Match Your Filter Criteria/i)).toBeInTheDocument();

    // Click Reset Filters
    const resetBtn = screen.getByRole('button', { name: /Reset Filters/i });
    fireEvent.click(resetBtn);

    expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    expect(screen.getByText('PennyLane default.qubit')).toBeInTheDocument();
  });

  it('highlights the active backend and triggers selection callback on click', async () => {
    vi.mocked(qh.quantumProviders).mockResolvedValue(mockProviders);
    vi.mocked(qh.quantumProviderHealth).mockResolvedValue(mockHealth);
    const onSelectBackend = vi.fn();

    renderCatalog(
      <QuantumSimulatorCatalog
        activeBackendId="statevector"
        activeProviderId="qiskit_local"
        onSelectBackend={onSelectBackend}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Exact Statevector')).toBeInTheDocument();
    });

    // Active badge on statevector
    expect(screen.getByText('Active in Workspace')).toBeInTheDocument();
    expect(screen.getByText('Active Backend')).toBeInTheDocument();

    // Select aer backend
    const selectButtons = screen.getAllByRole('button', { name: /Use in Quantum Lab/i });
    expect(selectButtons.length).toBe(2); // Aer and default.qubit

    fireEvent.click(selectButtons[0]); // Click Aer
    expect(onSelectBackend).toHaveBeenCalledWith('qiskit_local', 'aer');

    fireEvent.click(selectButtons[1]); // Click PennyLane
    expect(onSelectBackend).toHaveBeenCalledWith('pennylane_local', 'default.qubit');
  });

  it('displays loading skeleton while discovery queries are pending', () => {
    vi.mocked(qh.quantumProviders).mockReturnValue(new Promise(() => {}));
    vi.mocked(qh.quantumProviderHealth).mockReturnValue(new Promise(() => {}));

    renderCatalog(<QuantumSimulatorCatalog />);

    expect(screen.getByLabelText(/Discovering quantum providers/i)).toBeInTheDocument();
    expect(screen.getByText(/Discovering quantum providers and simulator backends/i)).toBeInTheDocument();
  });

  it('displays error state and provides retry action when provider discovery fails', async () => {
    vi.mocked(qh.quantumProviders).mockRejectedValue(new Error('Connection to quantum registry failed.'));
    vi.mocked(qh.quantumProviderHealth).mockRejectedValue(new Error('Connection to quantum registry failed.'));

    renderCatalog(<QuantumSimulatorCatalog />);

    await waitFor(() => {
      expect(screen.getByText(/Unable to Load Quantum Providers/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Connection to quantum registry failed/i)).toBeInTheDocument();

    const retryBtn = screen.getByRole('button', { name: /Retry Discovery/i });
    expect(retryBtn).toBeInTheDocument();
    fireEvent.click(retryBtn);

    expect(qh.quantumProviders).toHaveBeenCalledTimes(2);
  });
});
