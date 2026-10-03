import { useState } from 'react';
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

export function DatasetQualityScorecardView({
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
    queryKey: ['compare-dataset-quality-scorecards', datasetId, scorecard?.id, compareTargetId],
    queryFn: () => qh.compareDatasetQualityScorecards(datasetId, scorecard?.id || '', compareTargetId),
    enabled: Boolean(datasetId && scorecard?.id && compareTargetId && showCompare),
  });

  const copyFingerprint = (fp: string) => {
    void navigator.clipboard.writeText(fp);
    setCopiedFp(true);
    setTimeout(() => setCopiedFp(false), 2000);
  };

  const domainKeys = scorecard?.domains ? Object.keys(scorecard.domains) : [];

  return (
    <div className="space-y-5">
      {/* Action / Control Header */}
      <Card
        title="Advanced Dataset Quality Scorecard"
        description="Structured, reproducible assessment of quality, integrity, and biomedical readiness before ML training."
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            {scorecard ? (
              <>
                <StatusChip status={scorecard.status} />
                <span className="mono text-xs muted">
                  FP: {scorecard.assessment_fingerprint ? shortId(scorecard.assessment_fingerprint) : '—'}
                </span>
                <button
                  className="btn btn-ghost py-1 px-2 text-xs"
                  onClick={() => scorecard.assessment_fingerprint && copyFingerprint(scorecard.assessment_fingerprint)}
                  title="Copy full assessment fingerprint"
                >
                  <Copy size={12} /> {copiedFp ? 'Copied' : 'Copy FP'}
                </button>
              </>
            ) : (
              <Badge tone="blue">NOT ASSESSED YET</Badge>
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
              {assessMutation.isPending ? 'Assessing...' : scorecard ? 'Re-Assess Dataset' : 'Run Quality Assessment'}
            </Button>
            {scorecard && (
              <>
                <Button
                  variant="outline"
                  onClick={() => qh.exportDatasetQualityScorecard(datasetId, scorecard.id, 'markdown')}
                >
                  <FileText size={13} /> Export MD
                </Button>
                <Button
                  variant="outline"
                  onClick={() => qh.exportDatasetQualityScorecard(datasetId, scorecard.id, 'json')}
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

        <ErrorBanner error={(assessMutation.error as Error)?.message || (latestQuery.error as Error)?.message || (listQuery.error as Error)?.message} />
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
        {showCompare && scorecard && (
          <div className="mt-4 rounded-xl border p-4 bg-muted/20">
            <h4 className="font-semibold text-sm mb-2 flex items-center gap-2">
              <GitCompare size={14} /> Scorecard Cross-Assessment Comparison
            </h4>
            <div className="flex flex-wrap items-center gap-3 mb-3">
              <label className="text-xs">Compare current ({shortId(scorecard.id)}) against:</label>
              <select
                className="select text-xs py-1"
                value={compareTargetId}
                onChange={(e) => setCompareTargetId(e.target.value)}
              >
                <option value="">Select target assessment...</option>
                {(listQuery.data || [])
                  .filter((sc) => sc.id !== scorecard.id)
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

      {scorecard && (
        <>
          {/* Top Level Summary Scorecard */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">QUALITY SCORE</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span
                    className={`text-4xl font-extrabold ${
                      scorecard.summary.quality_score >= 85
                        ? 'text-emerald-600'
                        : scorecard.summary.quality_score >= 65
                        ? 'text-amber-500'
                        : 'text-rose-600'
                    }`}
                  >
                    {scorecard.summary.quality_score.toFixed(1)}
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
                  <StatusChip status={scorecard.status} large />
                </div>
              </div>
              <p className="mt-2 text-xs muted">
                {scorecard.status === 'PASS'
                  ? 'All critical quality gates passed.'
                  : scorecard.status === 'WARN'
                  ? 'Non-critical quality warnings detected.'
                  : 'Critical blockers present for ML training.'}
              </p>
            </Card>

            <Card className="flex flex-col justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider muted font-medium">CHECKS PASS RATE</span>
                <div className="mt-2 text-2xl font-bold">
                  {scorecard.summary.passed} / {scorecard.summary.total_checks}
                </div>
              </div>
              <div className="mt-2 flex gap-3 text-xs">
                <span className="text-emerald-600 font-semibold">{scorecard.summary.passed} Pass</span>
                <span className="text-amber-500 font-semibold">{scorecard.summary.warnings} Warn</span>
                <span className="text-rose-600 font-semibold">{scorecard.summary.failed} Fail</span>
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
          {scorecard.blocking_reasons.length > 0 && (
            <Notice tone="amber">
              <strong className="block mb-1">Critical Blocking Findings ({scorecard.blocking_reasons.length}):</strong>
              <ul className="list-disc list-inside space-y-1 text-xs">
                {scorecard.blocking_reasons.map((r, i) => (
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
              const dom = scorecard.domains[key];
              return (
                <button
                  key={key}
                  className={`btn btn-sm flex items-center gap-1.5 ${
                    activeDomain === key ? 'btn-primary' : 'btn-ghost'
                  }`}
                  onClick={() => setActiveDomain(key)}
                >
                  <DomainMiniIcon status={dom.status} />
                  <span>{dom.title}</span>
                  {dom.failures > 0 ? (
                    <span className="rounded-full bg-rose-500/20 px-1.5 py-0.2 text-[10px] text-rose-500 font-bold">
                      {dom.failures}
                    </span>
                  ) : dom.warnings > 0 ? (
                    <span className="rounded-full bg-amber-500/20 px-1.5 py-0.2 text-[10px] text-amber-500 font-bold">
                      {dom.warnings}
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
                const dom = scorecard.domains[key];
                return <DomainCard key={key} domain={dom} />;
              })}
          </div>

          {/* Safe Schema Snapshot */}
          {scorecard.schema_snapshot && (
            <Card
              title="Safe Schema Snapshot & Feature Distribution"
              description="Aggregated metadata profile without exposure of patient-level rows or unaggregated records."
            >
              <div className="mb-4 flex flex-wrap gap-4 text-xs muted">
                <span>Total Samples: <strong>{scorecard.schema_snapshot.total_rows.toLocaleString()}</strong></span>
                <span>Total Features: <strong>{scorecard.schema_snapshot.feature_count}</strong></span>
                <span>Target: <strong>{scorecard.schema_snapshot.target_column || 'None'}</strong></span>
                <span>Positive Class: <strong>{scorecard.schema_snapshot.positive_label || 'None'}</strong></span>
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
                    {Object.entries(scorecard.schema_snapshot.features).map(([name, prof]) => (
                      <tr key={name}>
                        <td className="font-semibold">{name}</td>
                        <td><span className="mono">{prof.data_type}</span></td>
                        <td>
                          {prof.missing_count} ({(prof.missing_percentage * 100).toFixed(1)}%)
                        </td>
                        <td>{prof.unique_count}</td>
                        <td>
                          {prof.mean !== undefined && prof.mean !== null ? (
                            <span className="mono">
                              µ={prof.mean.toFixed(2)}, σ={prof.std?.toFixed(2) ?? '—'} [{prof.min ?? '—'}, {prof.max ?? '—'}]
                            </span>
                          ) : prof.top_categories ? (
                            <span className="muted truncate max-w-[200px] inline-block">
                              {Object.entries(prof.top_categories)
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
                          {prof.is_identifier_candidate && <Badge tone="red">ID Candidate</Badge>}
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
              {scorecard.limitations.map((lim, idx) => (
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
      title={domain.title}
      description={`Domain assessment: ${domain.passed} passed, ${domain.warnings} warnings, ${domain.failures} failures.`}
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
          <strong>{sc.schema_snapshot?.feature_count ?? '—'}</strong>
        </div>
        <div className="rounded border p-2">
          <span className="muted block">Target Column</span>
          <strong>{sc.schema_snapshot?.target_column ?? '—'}</strong>
        </div>
      </div>
      <div className="space-y-2">
        {Object.values(sc.domains).slice(0, 4).map((dom) => (
          <div key={dom.name} className="flex justify-between items-center border-b py-1.5 text-xs last:border-0">
            <span className="font-medium">{dom.title}</span>
            <div className="flex items-center gap-1.5">
              <StatusChip status={dom.status} />
              <span className="muted">{dom.passed}/{dom.checks.length} passed</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
