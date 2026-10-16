import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QuantumJobManager } from '../components/quantum/QuantumJobManager';
import { qh } from '../lib/api';
import type {
  Job,
  JobCheckpointItem,
  JobEventItem,
  JobProgress,
} from '../types/qhealth';

vi.mock('../lib/api', () => ({
  qh: {
    jobs: vi.fn(),
    job: vi.fn(),
    jobProgress: vi.fn(),
    jobHistory: vi.fn(),
    jobCheckpoints: vi.fn(),
    pauseJob: vi.fn(),
    resumeJob: vi.fn(),
    retryJob: vi.fn(),
    cancelJob: vi.fn(),
  },
}));

const mockJobs: Job[] = [
  {
    id: 'job-run-001-active-vqc',
    experiment_id: 'exp-vqc-01',
    experiment_name: 'VQC Quantum Classification Benchmark',
    status: 'running',
    state: 'Training variational quantum circuit',
    progress: 45,
    total_units: 10,
    completed_units: 4,
    failed_units: 0,
    skipped_units: 0,
    active_unit: 'model:vqc:fold-2',
    current_phase: 'quantum_optimization',
    attempt_count: 1,
    resume_count: 0,
    current_checkpoint_id: 'ckpt-vqc-04',
    models: [
      {
        id: 'model-vqc-01',
        experiment_id: 'exp-vqc-01',
        dataset_id: 'ds-cardiac-01',
        model_type: 'vqc',
        status: 'running',
        details: { quantum: { qubits: 4 } },
        metrics: {},
        created_at: '2026-10-16T12:00:00Z',
      },
    ],
    errors: [],
    created_at: '2026-10-16T12:00:00Z',
    updated_at: '2026-10-16T12:00:00Z',
    started_at: '2026-10-16T12:00:05Z',
    completed_at: null,
  },
  {
    id: 'job-run-002-succeeded-qnn',
    experiment_id: 'exp-qnn-02',
    experiment_name: 'QNN Genomic Diagnostic Study',
    status: 'succeeded',
    state: 'Completed successfully',
    progress: 100,
    total_units: 8,
    completed_units: 8,
    failed_units: 0,
    skipped_units: 0,
    active_unit: null,
    current_phase: 'completed',
    attempt_count: 1,
    resume_count: 0,
    current_checkpoint_id: 'ckpt-qnn-final',
    models: [
      {
        id: 'model-qnn-01',
        experiment_id: 'exp-qnn-02',
        dataset_id: 'ds-genomic-02',
        model_type: 'qnn',
        status: 'completed',
        details: { quantum: { qubits: 4 } },
        metrics: {},
        created_at: '2026-10-16T11:00:00Z',
      },
      {
        id: 'model-lr-01',
        experiment_id: 'exp-qnn-02',
        dataset_id: 'ds-genomic-02',
        model_type: 'logistic_regression',
        status: 'completed',
        details: {},
        metrics: {},
        created_at: '2026-10-16T11:00:00Z',
      },
    ],
    errors: [],
    created_at: '2026-10-16T11:00:00Z',
    updated_at: '2026-10-16T11:05:30Z',
    started_at: '2026-10-16T11:00:05Z',
    completed_at: '2026-10-16T11:05:30Z',
  },
  {
    id: 'job-run-003-paused-qsvc',
    experiment_id: 'exp-qsvc-03',
    experiment_name: 'QSVC Quantum Kernel Analysis',
    status: 'paused',
    state: 'Execution paused by user request',
    progress: 30,
    total_units: 10,
    completed_units: 3,
    failed_units: 0,
    skipped_units: 0,
    active_unit: null,
    current_phase: 'quantum_kernel_matrix',
    attempt_count: 1,
    resume_count: 0,
    current_checkpoint_id: 'ckpt-qsvc-03',
    models: [
      {
        id: 'model-qsvc-01',
        experiment_id: 'exp-qsvc-03',
        dataset_id: 'ds-oncology-03',
        model_type: 'qsvc',
        status: 'running',
        details: {},
        metrics: {},
        created_at: '2026-10-16T10:00:00Z',
      },
    ],
    errors: [],
    created_at: '2026-10-16T10:00:00Z',
    updated_at: '2026-10-16T10:00:00Z',
    started_at: '2026-10-16T10:00:05Z',
    completed_at: null,
  },
  {
    id: 'job-run-004-failed-hybrid',
    experiment_id: 'exp-hybrid-04',
    experiment_name: 'PennyLane PyTorch Hybrid Trial',
    status: 'failed',
    state: 'Failed during backpropagation fold 1',
    progress: 20,
    total_units: 5,
    completed_units: 1,
    failed_units: 1,
    skipped_units: 3,
    active_unit: null,
    current_phase: 'hybrid_backprop',
    attempt_count: 1,
    resume_count: 0,
    current_checkpoint_id: 'ckpt-hybrid-01',
    models: [
      {
        id: 'model-hybrid-01',
        experiment_id: 'exp-hybrid-04',
        dataset_id: 'ds-cardiac-01',
        model_type: 'hybrid_pennylane_torch',
        status: 'failed',
        details: {},
        metrics: {},
        created_at: '2026-10-16T09:00:00Z',
      },
    ],
    errors: [{ message: 'ConvergenceError: Gradient exploded at step 142 in quantum layer' }],
    created_at: '2026-10-16T09:00:00Z',
    updated_at: '2026-10-16T09:02:15Z',
    started_at: '2026-10-16T09:00:05Z',
    completed_at: '2026-10-16T09:02:15Z',
  },
];

const mockProgressActive: JobProgress = {
  job_id: 'job-run-001-active-vqc',
  status: 'running',
  percentage: 55,
  determinate: true,
  current_phase: 'quantum_optimization',
  active_unit: 'model:vqc:fold-3',
  total_units: 10,
  completed_units: 5,
  failed_units: 0,
  skipped_units: 0,
};

const mockHistory: JobEventItem[] = [
  {
    id: 'evt-1',
    event_type: 'job_created',
    from_status: null,
    to_status: 'created',
    checkpoint_id: null,
    details: {},
    created_at: '2026-10-16T12:00:00Z',
  },
  {
    id: 'evt-2',
    event_type: 'job_started',
    from_status: 'created',
    to_status: 'running',
    checkpoint_id: null,
    details: {},
    created_at: '2026-10-16T12:00:05Z',
  },
  {
    id: 'evt-3',
    event_type: 'checkpoint_saved',
    from_status: 'running',
    to_status: 'running',
    checkpoint_id: 'ckpt-vqc-04',
    details: {},
    created_at: '2026-10-16T12:01:30Z',
  },
];

const mockCheckpoints: JobCheckpointItem[] = [
  {
    id: 'ckpt-vqc-04',
    job_id: 'job-run-001-active-vqc',
    sequence_number: 4,
    checkpoint_type: 'step',
    status: 'valid',
    logical_unit: 'model:vqc:fold-2',
    completed_units: 4,
    checkpoint_state: {},
    state_fingerprint: 'fp-1234',
    artifact_references: [],
    created_at: '2026-10-16T12:01:30Z',
    validated_at: '2026-10-16T12:01:30Z',
    invalidated_at: null,
  },
];

function renderJobManager(node: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('QuantumJobManager component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(qh.jobs).mockResolvedValue(mockJobs);
    vi.mocked(qh.jobProgress).mockResolvedValue(mockProgressActive);
    vi.mocked(qh.jobHistory).mockResolvedValue(mockHistory);
    vi.mocked(qh.jobCheckpoints).mockResolvedValue(mockCheckpoints);
    vi.mocked(qh.pauseJob).mockResolvedValue({ status: 'pause_requested' } as any);
    vi.mocked(qh.resumeJob).mockResolvedValue({ status: 'resuming' } as any);
    vi.mocked(qh.retryJob).mockResolvedValue({ status: 'queued' } as any);
    vi.mocked(qh.cancelJob).mockResolvedValue({ status: 'cancel_requested' } as any);
  });

  it('renders header, description, and status summary cards accurately', async () => {
    renderJobManager(<QuantumJobManager />);

    expect(screen.getByRole('heading', { name: /Quantum Jobs & Execution Monitor/i })).toBeInTheDocument();
    expect(screen.getByText(/Observe durable quantum simulation background jobs/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('4')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Jobs')).toBeInTheDocument();
    expect(screen.getByText('Active Jobs')).toBeInTheDocument();
  });

  it('renders job cards with real experiment titles, status badges, and model tags', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
      expect(screen.getByText('QNN Genomic Diagnostic Study')).toBeInTheDocument();
      expect(screen.getByText('QSVC Quantum Kernel Analysis')).toBeInTheDocument();
      expect(screen.getByText('PennyLane PyTorch Hybrid Trial')).toBeInTheDocument();
    });

    // Status badges
    expect(screen.getAllByText('Running').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Succeeded').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Paused').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Failed').length).toBeGreaterThanOrEqual(1);
  });

  it('filters job list when status filter pills are clicked', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    // Click Active filter pill
    const activeFilterBtn = screen.getByRole('button', { name: /Active \(1\)/i });
    fireEvent.click(activeFilterBtn);

    expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    expect(screen.queryByText('QNN Genomic Diagnostic Study')).not.toBeInTheDocument();
    expect(screen.queryByText('PennyLane PyTorch Hybrid Trial')).not.toBeInTheDocument();

    // Click Succeeded filter pill
    const succeededFilterBtn = screen.getByRole('button', { name: /Succeeded \(1\)/i });
    fireEvent.click(succeededFilterBtn);

    expect(screen.getByText('QNN Genomic Diagnostic Study')).toBeInTheDocument();
    expect(screen.queryByText('VQC Quantum Classification Benchmark')).not.toBeInTheDocument();

    // Click Failed filter pill
    const failedFilterBtn = screen.getByRole('button', { name: /Failed \(1\)/i });
    fireEvent.click(failedFilterBtn);

    expect(screen.getByText('PennyLane PyTorch Hybrid Trial')).toBeInTheDocument();
  });

  it('searches jobs by text input matching model name, experiment title, or job ID', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('textbox', { name: /Search jobs/i });
    fireEvent.change(searchInput, { target: { value: 'genomic' } });

    expect(screen.getByText('QNN Genomic Diagnostic Study')).toBeInTheDocument();
    expect(screen.queryByText('VQC Quantum Classification Benchmark')).not.toBeInTheDocument();
  });

  it('triggers safe pause action for running job', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    const pauseButton = screen.getByRole('button', { name: /^Pause$/i });
    fireEvent.click(pauseButton);

    await waitFor(() => {
      expect(qh.pauseJob).toHaveBeenCalledWith('job-run-001-active-vqc');
    });
  });

  it('triggers resume action for paused job', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('QSVC Quantum Kernel Analysis')).toBeInTheDocument();
    });

    const resumeButton = screen.getByRole('button', { name: /^Resume$/i });
    fireEvent.click(resumeButton);

    await waitFor(() => {
      expect(qh.resumeJob).toHaveBeenCalledWith('job-run-003-paused-qsvc');
    });
  });

  it('opens confirmation modal before cancelling a job and executes upon confirmation', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    const cancelButtons = screen.getAllByRole('button', { name: /^Cancel$/i });
    expect(cancelButtons.length).toBeGreaterThan(0);
    fireEvent.click(cancelButtons[0]);

    // Modal dialog opens
    expect(screen.getByRole('dialog', { name: /Confirm Job Cancellation/i })).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to cancel job/i)).toBeInTheDocument();

    // Confirm cancellation
    const confirmButton = screen.getByRole('button', { name: /Yes, Cancel Job/i });
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(qh.cancelJob).toHaveBeenCalledWith('job-run-001-active-vqc');
    });
  });

  it('triggers retry action for failed job', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('PennyLane PyTorch Hybrid Trial')).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /^Retry$/i });
    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(qh.retryJob).toHaveBeenCalledWith('job-run-004-failed-hybrid');
    });
  });

  it('opens inspection drawer when a job row is selected, showing checkpoints and history', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[0]);

    // Drawer should show details
    await waitFor(() => {
      expect(screen.getByText('JOB INSPECTOR')).toBeInTheDocument();
      expect(screen.getByText(/Durable Checkpoints/i)).toBeInTheDocument();
      expect(screen.getByText(/Execution State Transitions/i)).toBeInTheDocument();
      expect(screen.getByText('JOB CREATED')).toBeInTheDocument();
    });
  });

  it('displays empty state when no jobs match filter', async () => {
    renderJobManager(<QuantumJobManager />);

    await waitFor(() => {
      expect(screen.getByText('VQC Quantum Classification Benchmark')).toBeInTheDocument();
    });

    const searchInput = screen.getByRole('textbox', { name: /Search jobs/i });
    fireEvent.change(searchInput, { target: { value: 'nonexistent-query-xyz' } });

    expect(screen.getByText('No Jobs Match Filter')).toBeInTheDocument();
  });
});
