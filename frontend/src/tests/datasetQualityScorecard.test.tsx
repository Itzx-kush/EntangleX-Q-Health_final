import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DatasetQualityScorecardView, DatasetQualityPanel } from '../pages/DatasetQualityScorecard';
import { qh } from '../lib/api';
import type { DatasetQualityScorecard, DatasetQualityPreflightResponse } from '../types/qhealth';

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
  status: 'PASS',
  assessment_fingerprint: 'abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx1234yzab5678cdef9012',
  summary: {
    quality_score: 95.5,
    overall_status: 'PASS',
    total_checks: 22,
    passed: 21,
    warnings: 1,
    failed: 0,
    unverifiable: 0,
    domain_scores: {
      schema_integrity: 100.0,
      completeness: 100.0,
      target_integrity: 100.0,
      class_balance: 90.0,
      data_leakage: 100.0,
      sensitive_fields: 100.0,
    },
  },
  domains: {
    schema_integrity: {
      name: 'schema_integrity',
      title: 'Schema Integrity & Naming',
      status: 'PASS',
      passed: 4,
      warnings: 0,
      failures: 0,
      unverifiable: 0,
      checks: [
        {
          name: 'column_naming_hygiene',
          domain: 'schema_integrity',
          status: 'PASS',
          severity: 'INFO',
          message: 'All 8 columns conform to alphanumeric naming standards.',
          details: { column_count: 8 },
        },
      ],
    },
    completeness: {
      name: 'completeness',
      title: 'Completeness & Missingness',
      status: 'PASS',
      passed: 3,
      warnings: 0,
      failures: 0,
      unverifiable: 0,
      checks: [
        {
          name: 'sample_size_adequacy',
          domain: 'completeness',
          status: 'PASS',
          severity: 'INFO',
          message: 'Cohort size (100 rows) exceeds minimum threshold (30 rows).',
          details: { row_count: 100, min_rows: 30 },
        },
      ],
    },
    data_leakage: {
      name: 'data_leakage',
      title: 'Data Leakage & Target Contamination',
      status: 'PASS',
      passed: 3,
      warnings: 0,
      failures: 0,
      unverifiable: 0,
      checks: [
        {
          name: 'target_correlation_leakage',
          domain: 'data_leakage',
          status: 'PASS',
          severity: 'INFO',
          message: 'No features show deterministic target leakage.',
          details: { max_abs_correlation: 0.35 },
        },
      ],
    },
  },
  schema_snapshot: {
    total_rows: 100,
    total_columns: 8,
    feature_count: 7,
    target_column: 'diagnosis',
    positive_label: 'positive',
    features: {
      age: {
        name: 'age',
        data_type: 'int64',
        missing_count: 0,
        missing_percentage: 0.0,
        unique_count: 45,
        is_constant: false,
        is_identifier_candidate: false,
        mean: 52.3,
        std: 11.2,
        min: 24.0,
        max: 82.0,
      },
    },
  },
  limitations: [
    'Experimental protocol version was not specified; protocol conformance was not checked.',
  ],
  recommendations: [],
  blocking_reasons: [],
  artifact_id: 'art-1234',
  created_at: '2026-10-03T18:00:00Z',
};

const mockPreflight: DatasetQualityPreflightResponse = {
  dataset_id: mockDatasetId,
  dataset_version_id: 'dv-1',
  dataset_name: 'Biomedical Cohort A',
  dataset_hash: 'hash-abc',
  expected_fingerprint: 'expected-fp-999',
  checks_planned: 22,
  domains_planned: ['schema_integrity', 'completeness', 'target_integrity'],
  context: {},
  ready_to_assess: true,
  reasons: [],
};

function renderScorecardView() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DatasetQualityScorecardView datasetId={mockDatasetId} />
    </QueryClientProvider>
  );
}

function renderQualityPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DatasetQualityPanel experimentId={mockExperimentId} datasetId={mockDatasetId} />
    </QueryClientProvider>
  );
}

describe('Dataset Quality Scorecard UI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders overall quality score, status, and domain checks', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(mockScorecard);
    vi.mocked(qh.datasetQualityScorecards).mockResolvedValue([mockScorecard]);

    renderScorecardView();

    expect(await screen.findByText('95.5')).toBeInTheDocument();
    expect(screen.getAllByText('PASS').length).toBeGreaterThan(0);
    expect(screen.getByText('21 / 22')).toBeInTheDocument();
    expect(screen.getAllByText('Schema Integrity & Naming').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Completeness & Missingness').length).toBeGreaterThan(0);
    expect(screen.getByText('Safe Schema Snapshot & Feature Distribution')).toBeInTheDocument();
  });

  it('renders the first-assessment empty state without a request-failed banner', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(null);
    vi.mocked(qh.datasetQualityScorecards).mockResolvedValue([]);

    renderScorecardView();

    expect(await screen.findByText(/Not assessed yet\. No quality scorecard exists/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Run Quality Assessment/i})).toBeEnabled();
    expect(screen.queryByText(/Request failed/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Failed to fetch/i)).not.toBeInTheDocument();
  });

  it('keeps a real connection failure visible instead of treating it as not assessed', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockRejectedValue(new Error('Unable to reach the Q-Health backend.'));
    vi.mocked(qh.datasetQualityScorecards).mockResolvedValue([]);

    renderScorecardView();

    expect(await screen.findByText('Unable to reach the Q-Health backend.')).toBeInTheDocument();
    expect(screen.queryByText(/No quality scorecard exists/i)).not.toBeInTheDocument();
  });

  it('toggles and displays preflight check diagnostics', async () => {
    vi.mocked(qh.latestDatasetQualityScorecard).mockResolvedValue(mockScorecard);
    vi.mocked(qh.datasetQualityScorecards).mockResolvedValue([mockScorecard]);
    vi.mocked(qh.datasetQualityPreflight).mockResolvedValue(mockPreflight);

    renderScorecardView();

    await screen.findByText('95.5');
    const preflightBtn = screen.getByText('Preflight Checks');
    fireEvent.click(preflightBtn);

    expect(await screen.findByText('Assessment Preflight Diagnostics')).toBeInTheDocument();
    expect(await screen.findByText('expected-fp-999')).toBeInTheDocument();
    expect(screen.getByText('22 explicit checks')).toBeInTheDocument();
    expect(screen.getByText('READY')).toBeInTheDocument();
  });

  it('renders governing dataset quality panel in experiment detail', async () => {
    vi.mocked(qh.experimentDatasetQuality).mockResolvedValue(mockScorecard);

    renderQualityPanel();

    expect(await screen.findByText('Governing Dataset Quality Scorecard')).toBeInTheDocument();
    expect(screen.getByText('Quality Score: 95.5 / 100')).toBeInTheDocument();
    expect(screen.getByText(/21 passed/i)).toBeInTheDocument();
  });
});
