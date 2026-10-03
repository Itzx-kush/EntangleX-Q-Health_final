import { fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DatasetQualityScorecardView, DatasetQualityPanel } from '../pages/DatasetQualityScorecard';
import { qh } from '../lib/api';
import type { DatasetQualityPreflightResponse, DatasetQualityScorecard } from '../types/qhealth';

vi.mock('../lib/api', () => ({
  qh: {
    datasetQualityScorecards: vi.fn(),
    latestDatasetQualityScorecard: vi.fn(),
    datasetQualityPreflight: vi.fn(),
    assessDatasetQuality: vi.fn(),
    compareDatasetQualityScorecards: vi.fn(),
    exportDatasetQualityScorecard: vi.fn(),
    experimentDatasetQuality: vi.fn(),
  },
}));

const mockDatasetId = 'd1111111-1111-4111-8111-111111111111';
const mockExperimentId = 'e2222222-2222-4222-8222-222222222222';

const mockScorecard: DatasetQualityScorecard = {
  id: 'sc-12345678-abcd-ef01-2345-6789abcdef01',
  schema_version: 'dataset_quality_scorecard_v1',
  dataset_id: mockDatasetId,
  dataset_version_id: 'dv-1',
  experiment_id: null,
  protocol_version_id: null,
  pipeline_version_id: null,
  status: 'PASS',
  operation_key: 'dataset-quality:sc-1',
  assessment_fingerprint: 'abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yzab5678cdef9012',
  configuration: {},
  summary: {
    overall_status: 'PASS',
    total_checks: 4,
    passed: 4,
    warnings: 0,
    failed: 0,
    not_applicable: 0,
    unverifiable: 0,
    critical_failures: 0,
    high_failures: 0,
    quality_score: 95.5,
    domain_scores: { schema_integrity: 'PASS', completeness: 'PASS' },
  },
  domains: {
    schema_integrity: {
      domain: 'schema_integrity',
      display_name: 'Schema Integrity & Naming',
      status: 'PASS',
      total_checks: 2,
      passed_checks: 2,
      warning_checks: 0,
      failed_checks: 0,
      not_applicable_checks: 0,
      unverifiable_checks: 0,
      summary: '2/2 passed',
      checks: [
        {
          name: 'unique_column_names',
          domain: 'schema_integrity',
          status: 'PASS',
          severity: 'INFO',
          message: 'All column names are unique.',
          details: { column_count: 3 },
        },
      ],
    },
    completeness: {
      domain: 'completeness',
      display_name: 'Completeness & Missingness',
      status: 'PASS',
      total_checks: 2,
      passed_checks: 2,
      warning_checks: 0,
      failed_checks: 0,
      not_applicable_checks: 0,
      unverifiable_checks: 0,
      summary: '2/2 passed',
      checks: [
        {
          name: 'sample_size_adequacy',
          domain: 'completeness',
          status: 'PASS',
          severity: 'INFO',
          message: 'Cohort size is adequate.',
          details: { row_count: 100 },
        },
      ],
    },
  },
  schema_snapshot: {
    total_rows: 100,
    total_features: 2,
    target_column: 'diagnosis',
    columns: [
      {
        name: 'age',
        data_type: 'numeric',
        null_count: 2,
        null_percentage: 0.02,
        distinct_count: 45,
        is_constant: false,
        sample_stats: { numeric: true, mean: 52.3, std: 11.2, min: 24, max: 82 },
      },
    ],
  },
  limitations: ['Protocol conformance was not checked.'],
  provenance: { dataset_hash: 'hash-abc' },
  artifact_id: 'art-1234',
  created_at: '2026-10-03T18:00:00Z',
  completed_at: '2026-10-03T18:01:00Z',
};

const mockPreflight: DatasetQualityPreflightResponse = {
  dataset_id: mockDatasetId,
  dataset_version_id: 'dv-1',
  dataset_name: 'Biomedical Cohort A',
  dataset_hash: 'hash-abc',
  expected_fingerprint: 'expected-fp-999',
  checks_planned: 22,
  domains_planned: ['schema_integrity', 'completeness'],
  context: {},
  ready_to_assess: true,
  reasons: [],
};

function renderScorecardView() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DatasetQualityScorecardView datasetId={mockDatasetId} />
    </QueryClientProvider>,
  );
}

function renderQualityPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DatasetQualityPanel experimentId={mockExperimentId} datasetId={mockDatasetId} />
    </QueryClientProvider>,
  );
}

describe('Dataset Quality Scorecard UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(qh.datasetQualityScorecards).mockResolvedValue([]);
  });

  it('renders a backend-shaped scorecard, domains, and schema columns without obsolete fields', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(mockScorecard);

    renderScorecardView();

    expect(await screen.findByText('95.5')).toBeInTheDocument();
    expect(screen.getAllByText('PASS').length).toBeGreaterThan(0);
    expect(screen.getByText('4 / 4')).toBeInTheDocument();
    expect(screen.getAllByText('Schema Integrity & Naming').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Completeness & Missingness').length).toBeGreaterThan(0);
    expect(screen.getByText('age')).toBeInTheDocument();
    expect(screen.getByText('2 (2.0%)')).toBeInTheDocument();
    expect(screen.getByText('Safe Schema Snapshot & Feature Distribution')).toBeInTheDocument();
    expect(screen.queryByText(/ID Candidate/i)).not.toBeInTheDocument();
  });

  it('renders the typed quality_scorecard_not_found empty state', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(null);

    renderScorecardView();

    expect(await screen.findByText(/Not assessed yet\. No quality scorecard exists/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Run Quality Assessment/i })).toBeEnabled();
    expect(screen.queryByText(/Request failed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Failed to fetch/i)).not.toBeInTheDocument();
  });

  it('keeps backend failures visible instead of treating them as an empty state', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockRejectedValue(new Error('Backend unavailable.'));

    renderScorecardView();

    expect(await screen.findByText('Backend unavailable.')).toBeInTheDocument();
    expect(screen.queryByText(/No quality scorecard exists/i)).not.toBeInTheDocument();
  });

  it('keeps transport failures visible and distinct from no scorecard', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockRejectedValue(
      new Error('Unable to reach the Q-Health backend.'),
    );

    renderScorecardView();

    expect(await screen.findByText('Unable to reach the Q-Health backend.')).toBeInTheDocument();
    expect(screen.queryByText(/Not assessed yet/i)).not.toBeInTheDocument();
  });

  it('shows a visible fallback for malformed scorecard data instead of a blank page', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue({ id: 'partial' } as never);

    renderScorecardView();

    expect(await screen.findByText('Quality scorecard unavailable.')).toBeInTheDocument();
    expect(screen.getByText(/incomplete scorecard payload/i)).toBeInTheDocument();
  });

  it('does not require undefined blocking_reasons or recommendations', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(mockScorecard);

    renderScorecardView();

    expect(await screen.findByText('95.5')).toBeInTheDocument();
    expect(screen.queryByText('Quality scorecard unavailable')).not.toBeInTheDocument();
    expect(screen.getByText('All column names are unique.')).toBeInTheDocument();
  });

  it('renders preflight diagnostics against the backend response shape', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(mockScorecard);
    vi.mocked(qh.datasetQualityPreflight).mockResolvedValue(mockPreflight);

    renderScorecardView();
    await screen.findByText('95.5');
    fireEvent.click(screen.getByText('Preflight Checks'));

    expect(await screen.findByText('Assessment Preflight Diagnostics')).toBeInTheDocument();
    expect(await screen.findByText('expected-fp-999')).toBeInTheDocument();
    expect(await screen.findByText('22 explicit checks')).toBeInTheDocument();
  });

  it('renders the governing scorecard panel with total_features', async () => {
    vi.mocked(qh.experimentDatasetQuality).mockResolvedValue(mockScorecard);

    renderQualityPanel();

    expect(await screen.findByText('Governing Dataset Quality Scorecard')).toBeInTheDocument();
    expect(screen.getByText('Quality Score: 95.5 / 100')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
