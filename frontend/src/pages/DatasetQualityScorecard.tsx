import { Component, useState, type ErrorInfo, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle,
  Copy,
  Download,
  FileText,
  GitCompare,
  HelpCircle,
  Layers,
  MinusCircle,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  XCircle,
} from 'lucide-react';
import { Button, Card, Badge } from '../components/ui';
import { ErrorBanner, JsonDisclosure, Loading, MetricCard, Notice } from '../components/Shared';
import { qh } from '../lib/api';
import type {
  DatasetQualityPreflightResponse,
  DatasetQualityScorecard,
  QualityCheckResult,
  QualityCheckSeverity,
  QualityCheckStatus,
  QualityDomainResult,
  ScorecardComparison,
} from '../types/qhealth';
import { shortId } from '../utils/format';

interface DatasetQualityScorecardProps {
  datasetId: string;
  datasetVersionId?: string;
  experimentId?: string;
  protocolVersionId?: string;
  pipelineVersionId?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isDatasetQualityScorecard(value: unknown): value is DatasetQualityScorecard {
  if (!isRecord(value)) return false;
  const summary = value.summary;
  const schema = value.schema_snapshot;
  if (
    typeof value.id !== 'string' ||
    typeof value.status !== 'string' ||
    typeof value.assessment_fingerprint !== 'string' ||
    !Array.isArray(value.limitations) ||
    !isRecord(summary) ||
    typeof summary.quality_score !== 'number' ||
    typeof summary.passed !== 'number' ||
    typeof summary.warnings !== 'number' ||
    typeof summary.failed !== 'number' ||
    !isRecord(value.domains) ||
    !isRecord(schema) ||
    typeof schema.total_rows !== 'number' ||
    typeof schema.total_features !== 'number' ||
    !Array.isArray(schema.columns)
  ) {
    return false;
  }

  const validCheck = (check: unknown) =>
    isRecord(check) &&
    typeof check.name === 'string' &&
    typeof check.domain === 'string' &&
    typeof check.status === 'string' &&
    typeof check.severity === 'string' &&
    typeof check.message === 'string' &&
    isRecord(check.details);
  const validDomain = (domain: unknown) =>
    isRecord(domain) &&
    typeof domain.display_name === 'string' &&
    typeof domain.status === 'string' &&
    typeof domain.passed_checks === 'number' &&
    typeof domain.warning_checks === 'number' &&
    typeof domain.failed_checks === 'number' &&
    Array.isArray(domain.checks) &&
    domain.checks.every(validCheck);
  const validColumn = (column: unknown) =>
    isRecord(column) &&
    typeof column.name === 'string' &&
    typeof column.data_type === 'string' &&
    typeof column.null_count === 'number' &&
    typeof column.null_percentage === 'number' &&
    typeof column.distinct_count === 'number' &&
    typeof column.is_constant === 'boolean' &&
    isRecord(column.sample_stats);

  return Object.values(value.domains).every(validDomain) && schema.columns.every(validColumn);
}

export function DatasetQualityScorecardView(props: DatasetQualityScorecardProps) {
  return (
    <QualityScorecardErrorBoundary>
      <DatasetQualityScorecardContent {...props} />
    </QualityScorecardErrorBoundary>
  );
}

class QualityScorecardErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Keep the failure scoped to this page while preserving the diagnostic in the UI.
    console.error('Dataset quality scorecard render failed', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <Card title="Quality scorecard unavailable" description="The scorecard response could not be rendered safely.">
          <Notice tone="amber">
            <strong className="block mb-1">Quality data is malformed or incomplete.</strong>
            <span className="text-xs">
              {this.state.error.message || 'The backend returned an unexpected scorecard payload.'}
            </span>
          </Notice>
        </Card>
      );
    }
    return this.props.children;
  }
}

function DatasetQualityScorecardContent({
  datasetId,
  datasetVersionId,
  experimentId,
  protocolVersionId,
  pipelineVersionId,
}: DatasetQualityScorecardProps) {
  const qc = useQueryClient();
  const [activeDomain, setActiveDomain] = useState<string>('all');
  const [showPreflight, setShowPreflight] = useState<boolean>(false);
  const [showCompare, setShowCompare] = useState<boolean>(false);
  const [compareTargetId, setCompareTargetId] = useState<string>('');
  const [copiedFp, setCopiedFp] = useState<boolean>(false);

  // Fetch scorecards list for this dataset
  const listQuery = useQuery({
    queryKey: ['dataset-quality-scorecards', datasetId, datasetVersionId],
    queryFn: () => qh.datasetQualityScorecards(datasetId, datasetVersionId),
    enabled: Boolean(datasetId),
  });

  // Fetch latest scorecard
  const latestQuery = useQuery({
    queryKey: ['latest-dataset-quality-scorecard', datasetId, datasetVersionId],
    queryFn: () => qh.latestDatasetQualityScorecard(datasetId, datasetVersionId),
    enabled: Boolean(datasetId),
  });

  const scorecard = latestQuery.data;
  const malformedScorecard =
    latestQuery.isSuccess && scorecard !== null && !isDatasetQualityScorecard(scorecard);
  const renderableScorecard = scorecard && !malformedScorecard ? scorecard : null;

  // Preflight Query
  const preflightQuery = useQuery({
    queryKey: ['dataset-quality-preflight', datasetId, datasetVersionId, protocolVersionId, pipelineVersionId],
    queryFn: () =>
      qh.datasetQualityPreflight(datasetId, {
        dataset_version_id: datasetVersionId,
        protocol_version_id: protocolVersionId,
        pipeline_version_id: pipelineVersionId,
      }),
    enabled: Boolean(datasetId) && showPreflight,
  });

  // Assess Mutation
  const assessMutation = useMutation({
    mutationFn: () =>
      qh.assessDatasetQuality(datasetId, {
        dataset_version_id: datasetVersionId,
        experiment_id: experimentId,
        protocol_version_id: protocolVersionId,
        pipeline_version_id: pipelineVersionId,
      }),
    onSuccess: (newScorecard) => {
      qc.setQueryData(['latest-dataset-quality-scorecard', datasetId, datasetVersionId], newScorecard);
      void qc.invalidateQueries({ queryKey: ['dataset-quality-scorecards', datasetId] });
      setShowPreflight(false);
    },
  });

  // Compare Query
  const compareQuery = useQuery({
    queryKey: ['compare-dataset-quality-scorecards', datasetId, renderableScorecard?.id, compareTargetId],
    queryFn: () => qh.compareDatasetQualityScorecards(datasetId, renderableScorecard?.id || '', compareTargetId),
    enabled: Boolean(datasetId && renderableScorecard?.id && compareTargetId && showCompare),
  });

  const copyFingerprint = (fp: string) => {
    void navigator.clipboard.writeText(fp);
    setCopiedFp(true);
    setTimeout(() => setCopiedFp(false), 2000);
  };

  const domainKeys = renderableScorecard?.domains ? Object.keys(renderableScorecard.domains) : [];
  const criticalFindings = renderableScorecard
    ? Object.values(renderableScorecard.domains).flatMap((domain) =>
        domain.checks
          .filter(
            (check) =>
              check.status === 'FAIL' && (check.severity === 'CRITICAL' || check.severity === 'HIGH'),
          )
          .map((check) => check.message),
      )
    : [];

  return (
    <div className="space-y-5">
      {/* Action / Control Header */}
      <Card
        title="Advanced Dataset Quality Scorecard"
        description="Structured, reproducible assessment of quality, integrity, and biomedical readiness before ML training."
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {renderableScorecard ? (
              <>
                <StatusChip status={renderableScorecard.status} />
                <span className="mono text-xs muted">
                  FP: {renderableScorecard.assessment_fingerprint ? shortId(renderableScorecard.assessment_fingerprint) : '—'}
                </span>
                <button
                  className="btn btn-ghost py-1 px-2 text-xs"
                  onClick={() =>
                    renderableScorecard.assessment_fingerprint &&
                    copyFingerprint(renderableScorecard.assessment_fingerprint)
                  }
                  title="Copy full assessment fingerprint"
                >
                  <Copy size={12} /> {copiedFp ? 'Copied' : 'Copy FP'}
                </button>
              </>
            ) : malformedScorecard ? (
              <Badge tone="amber">INVALID SCORECARD</Badge>
            ) : latestQuery.isLoading ? (
              <Badge tone="blue">LOADING</Badge>
            ) : latestQuery.isSuccess && scorecard === null ? (
              <Badge tone="blue">NOT ASSESSED YET</Badge>
            ) : (
              <Badge tone="amber">ASSESSMENT UNAVAILABLE</Badge>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              onClick={() => setShowPreflight(!showPreflight)}
            >
              <Layers size={13} /> {showPreflight ? 'Hide Preflight' : 'Preflight Checks'}
            </Button>
            <Button
              variant="primary"
              disabled={assessMutation.isPending}
              onClick={() => assessMutation.mutate()}
            >
              <RefreshCw size={13} className={assessMutation.isPending ? 'animate-spin' : ''} />
              {assessMutation.isPending
                ? 'Assessing...'
                : renderableScorecard
                ? 'Re-Assess Dataset'
                : 'Run Quality Assessment'}
            </Button>
            {renderableScorecard && (
              <>
                <Button
                  variant="outline"
                  onClick={() =>
                    qh.exportDatasetQualityScorecard(datasetId, renderableScorecard.id, 'markdown')
                  }
                >
                  <FileText size={13} /> Export MD
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    qh.exportDatasetQualityScorecard(datasetId, renderableScorecard.id, 'json')
                  }
                >
                  <Download size={13} /> Export JSON
                </Button>
                {(listQuery.data?.length ?? 0) > 1 && (
                  <Button
                    variant="outline"
                    onClick={() => setShowCompare(!showCompare)}
                  >
                    <GitCompare size={13} /> Compare
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        <ErrorBanner
          error={
            (assessMutation.error as Error)?.message ||
            (latestQuery.error as Error)?.message ||
            (listQuery.error as Error)?.message
          }
        />
        {malformedScorecard && (
          <Notice tone="amber">
            <strong className="block mb-1">Quality scorecard unavailable.</strong>
            <span className="text-xs">
              The backend returned an incomplete scorecard payload. No quality findings were rendered.
            </span>
          </Notice>
        )}
        {latestQuery.isSuccess && scorecard === null && (
          <Notice tone="blue">Not assessed yet. No quality scorecard exists for this dataset/version yet.</Notice>
        )}

        {/* Preflight Drawer */}
        {showPreflight && (
          <div className="mt-4 rounded-xl border p-4 bg-muted/30">
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <Layers size={14} /> Assessment Preflight Diagnostics
            </h4>
            {preflightQuery.isLoading ? (
              <Loading />
            ) : preflightQuery.data ? (
              <PreflightView
                data={preflightQuery.data}
                onConfirm={() => assessMutation.mutate()}
                isAssessing={assessMutation.isPending}
              />
            ) : preflightQuery.error ? (
              <ErrorBanner error={(preflightQuery.error as Error).message} />
            ) : (
              <Notice tone="amber">Could not retrieve preflight diagnostics.</Notice>
            )}
          </div>
        )}

        {/* Compare Drawer */}
        {showCompare && renderableScorecard && (
          <div className="mt-4 rounded-xl border p-4 bg-muted/20">
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <GitCompare size={14} /> Scorecard Cross-Assessment Comparison
            </h4>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <label className="text-xs">Compare current ({shortId(renderableScorecard.id)}) against:</label>
              <select
                className="select text-xs py-1"
                value={compareTargetId}
                onChange={(e) => setCompareTargetId(e.target.value)}
              >
                <option value="">Select target assessment...</option>
                {(listQuery.data || [])
                  .filter((sc) => sc.id !== renderableScorecard.id)
                  .map((sc) => (
                    <option key={sc.id} value={sc.id}>
                      Scorecard {shortId(sc.id)} · Score {sc.summary?.quality_score?.toFixed(1) ?? '—'} · {sc.status}
                    </option>
                  ))}
              </select>
            </div>
            {compareQuery.isLoading && <Loading />}
            {compareQuery.data && <ComparisonDiffView diff={compareQuery.data} />}
          </div>
        )}
      </Card>

      {latestQuery.isLoading && <Loading />}

      {renderableScorecard && (
        <>
          {/* Top Level Summary Scorecard */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">QUALITY SCORE</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span
                    className={`text-4xl font-extrabold ${
                      renderableScorecard.summary.quality_score >= 85
                        ? 'text-emerald-600'
                      : renderableScorecard.summary.quality_score >= 65
                        ? 'text-amber-500'
                        : 'text-rose-600'
                    }`}
                  >
                    {renderableScorecard.summary.quality_score.toFixed(1)}
                  </span>
                  <span className="text-xs muted">/ 100.0</span>
                </div>
              </div>
              <p className="mt-2 text-xs muted">
                Weighted composite score across 9 scientific domains.
              </p>
            </Card>

            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">OVERALL STATUS</span>
                <div className="mt-2">
                <StatusChip status={renderableScorecard.status} large />
                </div>
              </div>
              <p className="mt-2 text-xs muted">
                {renderableScorecard.status === 'PASS'
                  ? 'All critical quality gates passed.'
                  : renderableScorecard.status === 'WARN'
                  ? 'Non-critical quality warnings detected.'
                  : 'Critical blockers present for ML training.'}
              </p>
            </Card>

            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">CHECKS PASS RATE</span>
                <div className="mt-2 text-2xl font-bold">
                  {renderableScorecard.summary.passed} / {renderableScorecard.summary.total_checks}
                </div>
              </div>
              <div className="mt-2 flex gap-3 text-xs">
                <span className="text-emerald-600 font-semibold">{renderableScorecard.summary.passed} Pass</span>
                <span className="text-amber-500 font-semibold">{renderableScorecard.summary.warnings} Warn</span>
                <span className="text-rose-600 font-semibold">{renderableScorecard.summary.failed} Fail</span>
              </div>
            </Card>

            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">DOMAINS MONITORED</span>
                <div className="mt-2 text-2xl font-bold">9 / 9</div>
              </div>
              <p className="mt-2 text-xs muted">
                Completeness, target, leakage, HIPAA, shift, etc.
              </p>
            </Card>
          </div>

          {/* Blockers & Limitations Notice */}
          {criticalFindings.length > 0 && (
            <Notice tone="amber">
              <strong className="block mb-1">Critical Blocking Findings ({criticalFindings.length}):</strong>
              <ul className="list-disc list-inside space-y-1 text-xs">
                {criticalFindings.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </Notice>
          )}

          {/* Domain Navigation Tabs */}
          <div className="flex flex-wrap items-center gap-2 border-b pb-2">
            <button
              className={`btn btn-sm ${activeDomain === 'all' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setActiveDomain('all')}
            >
              All Domains (9)
            </button>
            {domainKeys.map((key) => {
              const dom = renderableScorecard.domains[key];
              return (
                <button
                  key={key}
                  className={`btn btn-sm flex items-center gap-1.5 ${
                    activeDomain === key ? 'btn-primary' : 'btn-ghost'
                  }`}
                  onClick={() => setActiveDomain(key)}
                >
                  <DomainMiniIcon status={dom.status} />
                  <span>{dom.display_name}</span>
                  {dom.failed_checks > 0 ? (
                    <span className="rounded-full bg-rose-500/20 px-1.5 py-0.2 text-[10px] text-rose-500 font-bold">
                      {dom.failed_checks}
                    </span>
                  ) : dom.warning_checks > 0 ? (
                    <span className="rounded-full bg-amber-500/20 px-1.5 py-0.2 text-[10px] text-amber-500 font-bold">
                      {dom.warning_checks}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>

          {/* Domain Breakdown Section */}
          <div className="space-y-4">
            {domainKeys
              .filter((key) => activeDomain === 'all' || activeDomain === key)
              .map((key) => {
                const dom = renderableScorecard.domains[key];
                return <DomainCard key={key} domain={dom} />;
              })}
          </div>

          {/* Safe Schema Snapshot */}
          {renderableScorecard.schema_snapshot && (
            <Card
              title="Safe Schema Snapshot & Feature Distribution"
              description="Aggregated metadata profile without exposure of patient-level rows or unaggregated records."
            >
              <div className="mb-4 flex flex-wrap gap-4 text-xs muted">
                <span>Total Samples: <strong>{renderableScorecard.schema_snapshot.total_rows.toLocaleString()}</strong></span>
                <span>Total Features: <strong>{renderableScorecard.schema_snapshot.total_features}</strong></span>
                <span>Target: <strong>{renderableScorecard.schema_snapshot.target_column || '—'}</strong></span>
              </div>
              <div className="table-wrap max-h-[380px] overflow-auto">
                <table className="data-table text-xs">
                  <thead>
                    <tr>
                      <th>Feature Name</th>
                      <th>Type</th>
                      <th>Missing Count (%)</th>
                      <th>Unique</th>
                      <th>Summary Statistics</th>
                      <th>Flags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {renderableScorecard.schema_snapshot.columns.map((prof) => (
                      <tr key={prof.name}>
                        <td className="font-semibold">{prof.name}</td>
                        <td><span className="mono">{prof.data_type}</span></td>
                        <td>
                          {prof.null_count} ({(prof.null_percentage * 100).toFixed(1)}%)
                        </td>
                        <td>{prof.distinct_count}</td>
                        <td>
                          {typeof prof.sample_stats.mean === 'number' ? (
                            <span className="mono">
                              µ={prof.sample_stats.mean.toFixed(2)}, σ=
                              {typeof prof.sample_stats.std === 'number'
                                ? prof.sample_stats.std.toFixed(2)
                                : '—'}{' '}
                              [{String(prof.sample_stats.min ?? '—')}, {String(prof.sample_stats.max ?? '—')}]
                            </span>
                          ) : prof.sample_stats.top_categories &&
                            typeof prof.sample_stats.top_categories === 'object' ? (
                            <span className="muted truncate max-w-[200px] inline-block">
                              {Object.entries(prof.sample_stats.top_categories as Record<string, unknown>)
                                .slice(0, 3)
                                .map(([k, v]) => `${k}:${v}`)
                                .join(', ')}
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>
                          {prof.is_constant && <Badge tone="amber">Constant</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Methodological Boundaries */}
          <Card title="Scientific Limitations & Governance Boundary">
            <div className="space-y-2 text-xs">
              {renderableScorecard.limitations.map((lim, idx) => (
                <div key={idx} className="flex items-start gap-2 text-muted">
                  <span className="text-amber-500">•</span>
                  <span>{lim}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-lg border p-3 bg-muted/10 text-xs text-muted">
              <strong>Boundary Notice:</strong> The Advanced Dataset Quality Scorecard evaluates structural, statistical,
              and leak-free readiness for supervised benchmark research. It does not perform automated data repair or
              mutations, nor does it certify clinical diagnostic or treatment safety.
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

function StatusChip({ status, large = false }: { status: QualityCheckStatus; large?: boolean }) {
  const config: Record<QualityCheckStatus, { tone: 'green' | 'amber' | 'red' | 'blue'; icon: typeof CheckCircle }> = {
    PASS: { tone: 'green', icon: CheckCircle },
    WARN: { tone: 'amber', icon: AlertTriangle },
    FAIL: { tone: 'red', icon: XCircle },
    UNVERIFIABLE: { tone: 'amber', icon: HelpCircle },
    NOT_APPLICABLE: { tone: 'blue', icon: MinusCircle },
  };

  const { tone, icon: Icon } = config[status] || { tone: 'blue', icon: MinusCircle };

  return (
    <Badge tone={tone}>
      <span className={`flex items-center gap-1 font-semibold ${large ? 'text-sm py-0.5' : 'text-xs'}`}>
        <Icon size={large ? 15 : 12} />
        {status}
      </span>
    </Badge>
  );
}

function DomainMiniIcon({ status }: { status: QualityCheckStatus }) {
  if (status === 'PASS') return <CheckCircle size={13} className="text-emerald-500" />;
  if (status === 'WARN') return <AlertTriangle size={13} className="text-amber-500" />;
  if (status === 'FAIL') return <XCircle size={13} className="text-rose-500" />;
  return <MinusCircle size={13} className="text-slate-400" />;
}

function SeverityBadge({ severity }: { severity: QualityCheckSeverity }) {
  const tones: Record<QualityCheckSeverity, 'red' | 'amber' | 'blue'> = {
    CRITICAL: 'red',
    HIGH: 'red',
    MEDIUM: 'amber',
    LOW: 'blue',
    INFO: 'blue',
  };
  return <Badge tone={tones[severity] || 'blue'}>{severity}</Badge>;
}

function DomainCard({ domain }: { domain: QualityDomainResult }) {
  return (
    <Card
      title={domain.display_name}
      description={`Domain assessment: ${domain.passed_checks} passed, ${domain.warning_checks} warnings, ${domain.failed_checks} failures.`}
    >
      <div className="space-y-3">
        {domain.checks.map((check) => (
          <CheckResultItem key={check.name} check={check} />
        ))}
      </div>
    </Card>
  );
}

function CheckResultItem({ check }: { check: QualityCheckResult }) {
  const isFailed = check.status === 'FAIL';
  const isWarn = check.status === 'WARN';

  return (
    <div
      className={`rounded-lg border p-3.5 transition-colors ${
        isFailed
          ? 'border-rose-300/50 bg-rose-500/5'
          : isWarn
          ? 'border-amber-300/50 bg-amber-500/5'
          : 'border-border/60'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <StatusChip status={check.status} />
            <span className="font-semibold text-xs mono">{check.name}</span>
            <SeverityBadge severity={check.severity} />
          </div>
          <p className="text-xs text-foreground/90 mt-1">{check.message}</p>
        </div>
      </div>

      {check.recommendation && (
        <div className="mt-2.5 rounded bg-muted/40 p-2 text-xs border border-border/40">
          <strong className="text-primary font-medium">Actionable Recommendation:</strong>{' '}
          <span className="text-muted">{check.recommendation}</span>
        </div>
      )}

      {check.details && Object.keys(check.details).length > 0 && (
        <JsonDisclosure label="Measurement Evidence Details" value={check.details} />
      )}
    </div>
  );
}

function PreflightView({
  data,
  onConfirm,
  isAssessing,
}: {
  data: DatasetQualityPreflightResponse;
  onConfirm: () => void;
  isAssessing: boolean;
}) {
  return (
    <div className="space-y-3 text-xs">
      <div className="grid gap-2 sm:grid-cols-3">
        <div>
          <span className="muted">Expected Fingerprint:</span>
          <div className="mono font-semibold truncate">{data.expected_fingerprint}</div>
        </div>
        <div>
          <span className="muted">Checks Planned:</span>
          <div className="font-semibold">{data.checks_planned} explicit checks</div>
        </div>
        <div>
          <span className="muted">Readiness:</span>
          <div>
            <Badge tone={data.ready_to_assess ? 'green' : 'red'}>
              {data.ready_to_assess ? 'READY' : 'BLOCKED'}
            </Badge>
          </div>
        </div>
      </div>

      <div>
        <span className="muted block mb-1">Planned Domains ({data.domains_planned.length}):</span>
        <div className="flex flex-wrap gap-1">
          {data.domains_planned.map((d) => (
            <span key={d} className="rounded bg-muted px-2 py-0.5 mono text-[11px]">
              {d}
            </span>
          ))}
        </div>
      </div>

      {data.reasons.length > 0 && (
        <div className="text-rose-500 font-semibold">
          {data.reasons.map((r, i) => (
            <div key={i}>• {r}</div>
          ))}
        </div>
      )}

      <div className="pt-2 flex justify-end">
        <Button
          variant="primary"
          disabled={!data.ready_to_assess || isAssessing}
          onClick={onConfirm}
        >
          {isAssessing ? 'Executing Assessment...' : 'Confirm & Execute Assessment'}
        </Button>
      </div>
    </div>
  );
}

function ComparisonDiffView({ diff }: { diff: ScorecardComparison }) {
  return (
    <div className="space-y-3 text-xs">
      <div className="grid gap-2 sm:grid-cols-4 border-b pb-3">
        <div>
          <span className="muted">Status Delta:</span>
          <div className="font-semibold mt-0.5">
            {diff.status_delta.base_status} → {diff.status_delta.target_status}
          </div>
        </div>
        <div>
          <span className="muted">Quality Score Δ:</span>
          <div
            className={`font-bold mt-0.5 ${
              diff.summary_delta.score_delta > 0
                ? 'text-emerald-600'
                : diff.summary_delta.score_delta < 0
                ? 'text-rose-600'
                : 'text-muted'
            }`}
          >
            {diff.summary_delta.score_delta > 0 ? '+' : ''}
            {diff.summary_delta.score_delta.toFixed(1)} pts
          </div>
        </div>
        <div>
          <span className="muted">New Failures:</span>
          <div className="font-semibold text-rose-600 mt-0.5">{diff.new_failures.length}</div>
        </div>
        <div>
          <span className="muted">Resolved Failures:</span>
          <div className="font-semibold text-emerald-600 mt-0.5">{diff.resolved_failures.length}</div>
        </div>
      </div>

      {diff.new_failures.length > 0 && (
        <div>
          <strong className="text-rose-600 block mb-1">New Failures:</strong>
          <div className="space-y-1">
            {diff.new_failures.map((f) => (
              <div key={f.name} className="rounded bg-rose-500/10 p-1.5 border border-rose-300/40">
                <span className="font-semibold">{f.name}:</span> {f.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.resolved_failures.length > 0 && (
        <div>
          <strong className="text-emerald-600 block mb-1">Resolved Failures:</strong>
          <div className="space-y-1">
            {diff.resolved_failures.map((f) => (
              <div key={f.name} className="rounded bg-emerald-500/10 p-1.5 border border-emerald-300/40">
                <span className="font-semibold">{f.name}:</span> {f.message}
              </div>
            ))}
          </div>
        </div>
      )}

      {diff.metric_changes.length > 0 && (
        <div>
          <strong className="block mb-1">Observed Metric Changes:</strong>
          <div className="space-y-1">
            {diff.metric_changes.map((m, idx) => (
              <div key={idx} className="mono text-[11px] text-muted">
                {m.metric}: {String(m.base)} → {String(m.target)} (Δ {String(m.delta)})
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function DatasetQualityPanel({
  experimentId,
  datasetId,
}: {
  experimentId: string;
  datasetId: string;
}) {
  const query = useQuery({
    queryKey: ['experiment-dataset-quality', experimentId],
    queryFn: () => qh.experimentDatasetQuality(experimentId),
    enabled: Boolean(experimentId),
  });

  if (query.isLoading) return <Loading />;
  if (query.error || !query.data) return null;

  const sc = query.data;

  return (
    <Card
      className="mt-5"
      title="Governing Dataset Quality Scorecard"
      description={`Quality scorecard ${shortId(sc.id)} associated with dataset ${shortId(datasetId)}.`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <StatusChip status={sc.status} />
          <span className="font-bold text-sm">
            Quality Score: {sc.summary.quality_score.toFixed(1)} / 100
          </span>
          <span className="mono text-xs muted">FP: {shortId(sc.assessment_fingerprint)}</span>
        </div>
        <div className="text-xs muted">
          {sc.summary.passed} passed · {sc.summary.warnings} warnings · {sc.summary.failed} failed
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-3 text-xs mb-3">
        <div className="rounded border p-2">
          <span className="muted block">Rows / Samples</span>
          <strong>{sc.schema_snapshot?.total_rows ?? '—'}</strong>
        </div>
        <div className="rounded border p-2">
          <span className="muted block">Features</span>
          <strong>{sc.schema_snapshot?.total_features ?? '—'}</strong>
        </div>
        <div className="rounded border p-2">
          <span className="muted block">Target Column</span>
          <strong>{sc.schema_snapshot?.target_column ?? '—'}</strong>
        </div>
      </div>
      <div className="space-y-2">
        {Object.values(sc.domains).slice(0, 4).map((dom) => (
          <div key={dom.domain} className="flex justify-between items-center border-b py-1.5 text-xs last:border-0">
            <span className="font-medium">{dom.display_name}</span>
            <div className="flex items-center gap-1.5">
              <StatusChip status={dom.status} />
              <span className="muted">{dom.passed_checks}/{dom.checks.length} passed</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
