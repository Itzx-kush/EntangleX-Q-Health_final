import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BiomedicalSubgroupAnalysisPanel } from '../pages/BiomedicalSubgroupAnalysis';
import { qh } from '../lib/api';
import type { SubgroupStudy, SubgroupPreflightResponse } from '../types/qhealth';

vi.mock('../lib/api', () => ({
  qh: {
    subgroupStudies: vi.fn(),
    subgroupPreflight: vi.fn(),
    createSubgroupAnalysis: vi.fn(),
    downloadSubgroupStudy: vi.fn(),
  },
}));

const experimentId = '11111111-1111-4111-8111-111111111111';

const mockStudy: SubgroupStudy = {
  id: 'subgroup-study-001',
  schema_version: 'subgroup_analysis_v1',
  experiment_id: experimentId,
  model_id: 'model-001',
  model_type: 'logistic_regression',
  run_id: 'run-001',
  dataset_id: 'dataset-001',
  status: 'completed',
  operation_key: 'subgroup:op-key-123',
  definition_fingerprint: 'a'.repeat(64),
  subgroup_field: 'age',
  configuration: {
    minimum_n: 20,
    missing_value_policy: 'exclude',
  },
  overall_population: {
    n: 100,
    positive_n: 45,
    negative_n: 55,
    prevalence: 0.45,
    missing_n: 0,
    metrics: {
      accuracy: {
        value: 0.85,
        status: 'AVAILABLE',
        ci_lower: 0.76,
        ci_upper: 0.91,
        ci_method: 'wilson_score',
      },
      sensitivity: {
        value: 0.80,
        status: 'AVAILABLE',
        ci_lower: 0.66,
        ci_upper: 0.89,
        ci_method: 'wilson_score',
      },
      specificity: {
        value: 0.89,
        status: 'AVAILABLE',
        ci_lower: 0.78,
        ci_upper: 0.95,
        ci_method: 'wilson_score',
      },
      roc_auc: {
        value: 0.90,
        status: 'AVAILABLE',
        ci_lower: 0.83,
        ci_upper: 0.97,
        ci_method: 'hanley_mcneil',
      },
      pr_auc: {
        value: 0.88,
        status: 'AVAILABLE',
      },
    },
  },
  subgroups: [
    {
      id: 'age_under_40',
      label: 'Age: Under 40',
      rule: { field: 'age', operator: 'less_than', value: 40 },
      status: 'VALID',
      population: {
        n: 40,
        positive_n: 15,
        negative_n: 25,
        prevalence: 0.375,
        excluded_missing_n: 0,
      },
      metrics: {
        accuracy: {
          value: 0.88,
          status: 'AVAILABLE',
          ci_lower: 0.74,
          ci_upper: 0.95,
          ci_method: 'wilson_score',
        },
        sensitivity: {
          value: 0.80,
          status: 'AVAILABLE',
          ci_lower: 0.55,
          ci_upper: 0.93,
          ci_method: 'wilson_score',
        },
        specificity: {
          value: 0.92,
          status: 'AVAILABLE',
          ci_lower: 0.75,
          ci_upper: 0.98,
          ci_method: 'wilson_score',
        },
        roc_auc: {
          value: 0.92,
          status: 'AVAILABLE',
          ci_lower: 0.81,
          ci_upper: 1.0,
          ci_method: 'hanley_mcneil',
        },
        pr_auc: {
          value: 0.89,
          status: 'AVAILABLE',
        },
      },
    },
    {
      id: 'age_tiny',
      label: 'Age: 75+',
      rule: { field: 'age', operator: 'greater_than', value: 74 },
      status: 'TOO_SMALL',
      status_reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
      population: {
        n: 5,
        positive_n: 2,
        negative_n: 3,
        prevalence: 0.40,
        excluded_missing_n: 0,
      },
      metrics: {
        accuracy: {
          value: null,
          status: 'WITHHELD',
          reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
        },
        sensitivity: {
          value: null,
          status: 'WITHHELD',
          reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
        },
        specificity: {
          value: null,
          status: 'WITHHELD',
          reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
        },
        roc_auc: {
          value: null,
          status: 'WITHHELD',
          reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
        },
        pr_auc: {
          value: null,
          status: 'WITHHELD',
          reason: 'Subgroup sample size (N=5) is below minimum reporting threshold (minimum_n=20).',
        },
      },
    },
  ],
  comparisons: [
    {
      subgroup_id: 'age_under_40',
      subgroup_label: 'Age: Under 40',
      reference_id: 'overall',
      reference_label: 'Overall evaluation population',
      status: 'CALCULATED',
      deltas: {
        accuracy: 0.03,
        sensitivity: 0.0,
        specificity: 0.03,
        roc_auc: 0.02,
      },
      disparity_ratios: {
        sensitivity_ratio: 1.0,
      },
      notes: ['Sample size is sufficient for stratified evaluation.'],
    },
  ],
  limitations: [
    'Subgroup analysis reports empirical performance; it does not infer causal relationships.',
  ],
  provenance: {
    model_id: 'model-001',
    dataset_id: 'dataset-001',
  },
  created_at: '2026-10-03T12:00:00Z',
  completed_at: '2026-10-03T12:00:01Z',
};

const mockPreflight: SubgroupPreflightResponse = {
  feasible: true,
  subgroup_field: 'age',
  field_data_type: 'int64',
  unique_values_count: 50,
  missing_values_count: 0,
  suggested_rules: [],
  eligible_samples: 100,
  blockers: [],
  warnings: [],
  limitations: ['Stratified evaluation reports empirical differences.'],
  configuration_fingerprint: 'b'.repeat(64),
};

function renderPanel() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <BiomedicalSubgroupAnalysisPanel experimentId={experimentId} />
    </QueryClientProvider>
  );
}

describe('BiomedicalSubgroupAnalysisPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders title, inputs, and preflight information', async () => {
    vi.mocked(qh.subgroupStudies).mockResolvedValue([]);
    vi.mocked(qh.subgroupPreflight).mockResolvedValue(mockPreflight);

    renderPanel();

    expect(screen.getByText(/Biomedical Subgroup Analysis/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Subgroup Attribute \/ Field/i) || screen.getByDisplayValue('age')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/PREFLIGHT:/i)).toBeInTheDocument();
      expect(screen.getByText('FEASIBLE')).toBeInTheDocument();
      expect(screen.getByText(/Eligible samples:/i)).toBeInTheDocument();
    });
  });

  it('renders cohorts table with Wilson CIs and handles small subgroup protection', async () => {
    vi.mocked(qh.subgroupStudies).mockResolvedValue([mockStudy]);
    vi.mocked(qh.subgroupPreflight).mockResolvedValue(mockPreflight);

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText('Age: Under 40')).toBeInTheDocument();
      expect(screen.getByText('Age: 75+')).toBeInTheDocument();
      expect(screen.getByText('Overall Population')).toBeInTheDocument();
    });

    // Check metric rendering with CI
    expect(screen.getAllByText('88.0%').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('[74.0%–95.0%]')).toBeInTheDocument();

    // Check WITHHELD status for tiny cohort
    const withheldElements = screen.getAllByText('WITHHELD');
    expect(withheldElements.length).toBeGreaterThanOrEqual(1);

    // Check scientific disclaimer notice
    expect(screen.getByText(/Scientific Boundary:/i)).toBeInTheDocument();
  });

  it('displays disparity and delta analysis for selected cohort', async () => {
    vi.mocked(qh.subgroupStudies).mockResolvedValue([mockStudy]);
    vi.mocked(qh.subgroupPreflight).mockResolvedValue(mockPreflight);

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(/DISPARITY & DELTA ANALYSIS/i)).toBeInTheDocument();
      expect(screen.getAllByText(/\+3.0%/i).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('triggers study JSON export on download button click', async () => {
    vi.mocked(qh.subgroupStudies).mockResolvedValue([mockStudy]);
    vi.mocked(qh.subgroupPreflight).mockResolvedValue(mockPreflight);
    vi.mocked(qh.downloadSubgroupStudy).mockResolvedValue(undefined as any);

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(/Export Study JSON/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Export Study JSON/i));
    expect(qh.downloadSubgroupStudy).toHaveBeenCalledWith(experimentId, 'subgroup-study-001');
  });

  it('triggers stratified evaluation mutation when button is clicked', async () => {
    vi.mocked(qh.subgroupStudies).mockResolvedValue([]);
    vi.mocked(qh.subgroupPreflight).mockResolvedValue(mockPreflight);
    vi.mocked(qh.createSubgroupAnalysis).mockResolvedValue(mockStudy);

    renderPanel();

    await waitFor(() => {
      expect(screen.getByText(/Run Stratified Evaluation/i)).not.toBeDisabled();
    });

    fireEvent.click(screen.getByText(/Run Stratified Evaluation/i));

    await waitFor(() => {
      expect(qh.createSubgroupAnalysis).toHaveBeenCalledWith(
        experimentId,
        expect.objectContaining({
          subgroup_field: 'age',
          minimum_n: 20,
          missing_value_policy: 'exclude',
        })
      );
    });
  });
});
