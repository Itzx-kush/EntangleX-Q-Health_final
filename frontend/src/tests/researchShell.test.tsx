import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ResearchShell } from '../components/ResearchShell';
import { AiProvider } from '../contexts/AiContext';

vi.mock('../lib/api', () => ({
  setSessionToken: vi.fn(),
  api: {
    get: vi.fn(() => Promise.resolve([])),
    post: vi.fn(() => Promise.resolve({})),
    remove: vi.fn(() => Promise.resolve(undefined)),
  },
  qh: {
    health: vi.fn(() =>
      Promise.resolve({
        status: 'ok',
        version: 'test',
        mode: 'local',
        authentication_required: false,
        quantum: { available: true, runtime_verified: true, execution: 'local simulation' },
        disclaimer: 'Research only',
      })
    ),
    systemStatus: vi.fn(() =>
      Promise.resolve({
        status: 'ok',
        version: 'test',
        mode: 'local',
        database_available: true,
        storage_available: true,
        quantum: { available: true, runtime_verified: true, execution: 'local simulation' },
        model_capabilities: [],
        supported_models: { classical: [], quantum: [], qiskit_quantum: [], pennylane_hybrid: [] },
        jobs: { queued: 0, running: 0, active: 0 },
      })
    ),
    summary: vi.fn(() =>
      Promise.resolve({
        counts: { datasets: 5, experiments: 12, ready_models: 7, active_jobs: 0 },
        recent_experiments: [],
        disclaimer: 'Research only',
      })
    ),
    jobs: vi.fn(() => Promise.resolve([])),
    alignment: vi.fn(() =>
      Promise.resolve({
        contract_version: '2026-09-30',
        models: [],
        showcase: {
          id: 'early-stage-diabetes',
          display_name: 'Early Stage Diabetes Risk Prediction',
          label: 'Featured SIH demonstration',
          featured_dataset_slug: 'early-stage-diabetes',
          disease_domain: 'endocrinology',
          target: 'diabetes_status',
          positive_class: 'positive',
          dataset_hash: 'hash',
          research_only_disclaimer: 'Research benchmark only.',
          recommended_models: [],
        },
        flagship_experiment_preset: {
          id: 'sih-diabetes-demonstration',
          display_name: 'SIH Diabetes Demonstration',
          dataset_slug: 'early-stage-diabetes',
          models: [],
          auto_start_training: false,
          threshold_strategy: 'target_sensitivity',
          evidence_requirements: [],
        },
        flagship_architecture: {
          model_id: 'hybrid_pennylane_torch',
          status: 'IMPLEMENTED',
          stages: ['Classical preprocessing', 'PennyLane quantum circuit', 'PyTorch classical output head', 'SHAP explanation'],
        },
      })
    ),
    datasetLibrary: vi.fn(() => Promise.resolve([])),
  },
}));

function renderShell(initialEntry = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AiProvider>
          <ResearchShell>
            <div data-testid="test-child-content">Active Workspace Route</div>
          </ResearchShell>
        </AiProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ResearchShell component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders primary navigation groups, links, and workspace content', () => {
    renderShell('/');

    expect(screen.getByTestId('test-child-content')).toBeInTheDocument();

    // Check primary navigation items
    expect(screen.getByRole('link', { name: /^Overview$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Datasets$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Quantum Lab$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Comparison$/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^Experiment registry$/i })).toBeInTheDocument();
  });

  it('marks active navigation route with active and is-active classes', () => {
    renderShell('/quantum');

    const quantumLink = screen.getByRole('link', { name: /^Quantum Lab$/i });
    expect(quantumLink).toHaveClass('active');
    expect(quantumLink).toHaveClass('is-active');
  });

  it('displays the OS-appropriate command palette shortcut indicator', () => {
    renderShell('/');

    const triggers = screen.getAllByRole('button', { name: /Open command palette/i });
    expect(triggers.length).toBeGreaterThan(0);

    // Should contain either Ctrl+K or ⌘K
    const textContent = triggers[0].textContent;
    expect(textContent).toMatch(/Ctrl\+K|⌘K/);
  });

  it('opens and closes the command palette modal with accessible attributes', async () => {
    renderShell('/');

    const triggers = screen.getAllByRole('button', { name: /Open command palette/i });
    fireEvent.click(triggers[0]);

    // Dialog should be displayed with role and aria-modal
    const dialog = await screen.findByRole('dialog', { name: /Command palette/i });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');

    // Search input should be present
    const searchInput = screen.getByPlaceholderText(/Search actions and research areas…/i);
    expect(searchInput).toBeInTheDocument();

    // Press Escape to close
    fireEvent.keyDown(window, { key: 'Escape' });
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /Command palette/i })).not.toBeInTheDocument();
    });
  });

  it('opens and closes the theme & layout configuration drawer', async () => {
    renderShell('/');

    const configButton = screen.getByRole('button', { name: /Open theme and layout settings/i });
    fireEvent.click(configButton);

    const drawer = await screen.findByRole('dialog', { name: /Theme and layout settings/i });
    expect(drawer).toBeInTheDocument();
    expect(drawer).toHaveAttribute('aria-modal', 'true');

    // Close button
    const closeBtn = screen.getByRole('button', { name: /Close theme and layout/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /Theme and layout settings/i })).not.toBeInTheDocument();
    });
  });

  it('renders mobile menu button with accessible labels and attributes', () => {
    renderShell('/');

    const mobileBtn = screen.getByRole('button', { name: /^Open navigation$/i });
    expect(mobileBtn).toBeInTheDocument();
    expect(mobileBtn).toHaveAttribute('aria-expanded');
  });
});
