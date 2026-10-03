import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Download, Play, RefreshCw, AlertCircle, CheckCircle, ShieldAlert } from 'lucide-react';
import { Button, Card, Select, Badge } from '../components/ui';
import { EmptyState, ErrorBanner, JsonDisclosure, Loading, Notice, StatusBadge } from '../components/Shared';
import { qh } from '../lib/api';
import { dateTime, shortId } from '../utils/format';
import type {
  SubgroupStudy,
  SubgroupPreflightResponse,
  SubgroupAnalysisRequest,
  MissingValuePolicy,
  SubgroupMetricValue,
} from '../types/qhealth';

function formatMetric(m?: SubgroupMetricValue) {
  if (!m) return '—';
  if (m.status === 'WITHHELD') return <span className="text-amber-500 font-medium">WITHHELD</span>;
  if (m.status === 'UNDEFINED') return <span className="text-muted-foreground italic">UNDEFINED</span>;
  if (m.status === 'NOT_APPLICABLE') return <span className="text-muted-foreground">N/A</span>;
  if (m.value === null || m.value === undefined) return '—';
  const formatted = (m.value * 100).toFixed(1) + '%';
  if (m.ci_lower !== null && m.ci_lower !== undefined && m.ci_upper !== null && m.ci_upper !== undefined) {
    const lo = (m.ci_lower * 100).toFixed(1);
    const hi = (m.ci_upper * 100).toFixed(1);
    return (
      <span>
        <strong>{formatted}</strong>
        <span className="text-[11px] text-muted-foreground ml-1">[{lo}%–{hi}%]</span>
      </span>
    );
  }
  return <strong>{formatted}</strong>;
}

export function BiomedicalSubgroupAnalysisPanel({ experimentId }: { experimentId: string }) {
  const qc = useQueryClient();
  const [subgroupField, setSubgroupField] = useState('age');
  const [minimumN, setMinimumN] = useState<number>(20);
  const [missingPolicy, setMissingPolicy] = useState<MissingValuePolicy>('exclude');
  const [selectedStudyId, setSelectedStudyId] = useState<string | null>(null);
  const [activeCohortId, setActiveCohortId] = useState<string | null>(null);

  // Load existing studies for this experiment
  const studiesQuery = useQuery({
    queryKey: ['subgroup-studies', experimentId],
    queryFn: () => qh.subgroupStudies(experimentId),
  });

  const currentStudy = selectedStudyId
    ? studiesQuery.data?.find((s) => s.id === selectedStudyId) || studiesQuery.data?.[0]
    : studiesQuery.data?.[0];

  // Preflight Query
  const preflightReq: SubgroupAnalysisRequest = {
    subgroup_field: subgroupField.trim(),
    minimum_n: minimumN,
    missing_value_policy: missingPolicy,
  };

  const preflightQuery = useQuery({
    queryKey: ['subgroup-preflight', experimentId, subgroupField, minimumN, missingPolicy],
    queryFn: () => qh.subgroupPreflight(experimentId, preflightReq),
    enabled: Boolean(subgroupField.trim()),
    retry: false,
  });

  const pfData = preflightQuery.data;

  // Run Subgroup Analysis Mutation
  const runMutation = useMutation({
    mutationFn: () => qh.createSubgroupAnalysis(experimentId, preflightReq),
    onSuccess: (data: SubgroupStudy) => {
      qc.invalidateQueries({ queryKey: ['subgroup-studies', experimentId] });
      setSelectedStudyId(data.id);
    },
  });

  const cohorts = currentStudy?.subgroups || currentStudy?.subgroups_results || [];
  const selectedCohort = cohorts.find((c) => c.id === activeCohortId) || cohorts[0];

  return (
    <Card
      className="mt-5"
      title="Biomedical Subgroup Analysis & Stratified Evaluation"
      description="Evaluate locked model performance across predefined cohorts to identify hidden performance disparities without altering weights or training."
    >
      <ErrorBanner error={(runMutation.error as Error)?.message || (preflightQuery.error as Error)?.message} />

      {/* Configuration & Controls */}
      <div className="rounded-xl border p-4 bg-muted/5 mb-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="field">
            <span className="font-medium text-xs">Subgroup Attribute / Field</span>
            <input
              type="text"
              className="input text-xs"
              value={subgroupField}
              onChange={(e) => setSubgroupField(e.target.value)}
              placeholder="e.g. age, gender, comorbidity"
            />
          </label>

          <label className="field">
            <span className="font-medium text-xs">Minimum Cohort N (Privacy Safeguard)</span>
            <input
              type="number"
              className="input text-xs"
              min={1}
              value={minimumN}
              onChange={(e) => setMinimumN(Math.max(1, parseInt(e.target.value) || 1))}
            />
          </label>

          <label className="field">
            <span className="font-medium text-xs">Missing Value Policy</span>
            <Select
              className="text-xs"
              value={missingPolicy}
              onChange={(e) => setMissingPolicy(e.target.value as MissingValuePolicy)}
            >
              <option value="exclude">Exclude missing rows</option>
              <option value="separate_unknown_group">Separate "Unknown / Missing" cohort</option>
              <option value="error">Error on missing values</option>
            </Select>
          </label>
        </div>

        {/* Preflight Summary */}
        {pfData && (
          <div className="mt-3 pt-3 border-t text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-muted-foreground font-semibold">PREFLIGHT:</span>
              <Badge tone={pfData.feasible ? 'green' : 'amber'}>
                {pfData.feasible ? 'FEASIBLE' : 'BLOCKED'}
              </Badge>
              <span className="text-muted-foreground">
                Eligible samples: <strong>{pfData.eligible_samples}</strong> | Unique values:{' '}
                <strong>{pfData.unique_values_count}</strong> | Missing: <strong>{pfData.missing_values_count}</strong>
              </span>
            </div>

            {pfData.blockers.length > 0 && (
              <div className="mt-2 space-y-1 text-red-600 dark:text-red-400">
                {pfData.blockers.map((b, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <ShieldAlert size={12} /> {b}
                  </div>
                ))}
              </div>
            )}

            {pfData.warnings.length > 0 && (
              <div className="mt-2 space-y-1 text-amber-600 dark:text-amber-400">
                {pfData.warnings.map((w, i) => (
                  <div key={i} className="flex items-center gap-1">
                    <AlertCircle size={12} /> {w}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            disabled={!pfData?.feasible || runMutation.isPending}
            onClick={() => runMutation.mutate()}
          >
            <Play size={13} />
            {runMutation.isPending ? 'Evaluating cohorts…' : 'Run Stratified Evaluation'}
          </Button>

          {studiesQuery.data && studiesQuery.data.length > 0 && (
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-xs text-muted-foreground">Recorded Studies:</span>
              <Select
                className="text-xs min-w-[180px]"
                value={currentStudy?.id || ''}
                onChange={(e) => setSelectedStudyId(e.target.value)}
              >
                {studiesQuery.data.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.subgroup_field} ({dateTime(s.created_at)})
                  </option>
                ))}
              </Select>
            </div>
          )}
        </div>
      </div>

      {/* Main Study Details */}
      {studiesQuery.isLoading ? (
        <Loading />
      ) : !currentStudy ? (
        <EmptyState title="No Subgroup Studies Recorded">
          Configure a subgroup field and trigger stratified evaluation to inspect performance across cohorts.
        </EmptyState>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-3">
            <div className="flex items-center gap-2">
              <StatusBadge value={currentStudy.status} />
              <Badge tone="purple">FIELD: {currentStudy.subgroup_field}</Badge>
              <Badge tone="blue">SCHEMA: {currentStudy.schema_version}</Badge>
              <span className="text-xs text-muted-foreground mono" title={currentStudy.definition_fingerprint}>
                FP: {currentStudy.definition_fingerprint.slice(0, 16)}…
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="text-xs px-2 py-1"
                onClick={() => qh.downloadSubgroupStudy(experimentId, currentStudy.id)}
              >
                <Download size={12} /> Export Study JSON
              </Button>
            </div>
          </div>

          {/* Stratified Cohorts Table */}
          <div className="table-wrap">
            <table className="data-table text-xs">
              <thead>
                <tr>
                  <th>Cohort</th>
                  <th>N (Eval)</th>
                  <th>Pos / Neg</th>
                  <th>Accuracy (95% CI)</th>
                  <th>Sensitivity (95% CI)</th>
                  <th>Specificity (95% CI)</th>
                  <th>ROC-AUC (95% CI)</th>
                  <th>PR-AUC</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {/* Overall reference row */}
                {currentStudy.overall_population && (
                  <tr className="bg-muted/10 font-medium">
                    <td>
                      Overall Population <span className="text-[10px] text-muted-foreground">(Held-out Test)</span>
                    </td>
                    <td>{currentStudy.overall_population.n}</td>
                    <td>
                      {currentStudy.overall_population.positive_n} / {currentStudy.overall_population.negative_n}
                    </td>
                    <td>{formatMetric(currentStudy.overall_population.metrics?.accuracy)}</td>
                    <td>{formatMetric(currentStudy.overall_population.metrics?.sensitivity)}</td>
                    <td>{formatMetric(currentStudy.overall_population.metrics?.specificity)}</td>
                    <td>{formatMetric(currentStudy.overall_population.metrics?.roc_auc)}</td>
                    <td>{formatMetric(currentStudy.overall_population.metrics?.pr_auc)}</td>
                    <td>
                      <Badge tone="blue">OVERALL</Badge>
                    </td>
                  </tr>
                )}

                {/* Cohort rows */}
                {cohorts.map((sub) => {
                  const isSelected = selectedCohort?.id === sub.id;
                  return (
                    <tr
                      key={sub.id}
                      className={`cursor-pointer hover:bg-muted/5 ${isSelected ? 'bg-primary/5 font-semibold' : ''}`}
                      onClick={() => setActiveCohortId(sub.id)}
                    >
                      <td>
                        <span>{sub.label}</span>
                      </td>
                      <td>{sub.population.n}</td>
                      <td>
                        {sub.population.positive_n} / {sub.population.negative_n}
                      </td>
                      <td>{formatMetric(sub.metrics.accuracy)}</td>
                      <td>{formatMetric(sub.metrics.sensitivity)}</td>
                      <td>{formatMetric(sub.metrics.specificity)}</td>
                      <td>{formatMetric(sub.metrics.roc_auc)}</td>
                      <td>{formatMetric(sub.metrics.pr_auc)}</td>
                      <td>
                        <StatusBadge value={sub.status} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Selected Cohort Detail & Disparities */}
          {selectedCohort && (
            <div className="two-grid mt-4">
              <div className="rounded-xl border p-4 text-xs">
                <div className="metric-label">COHORT ACCOUNTING: {selectedCohort.label}</div>
                <div className="mt-2 space-y-1">
                  <div className="flex justify-between border-b py-1">
                    <span className="text-muted-foreground">Cohort Rule</span>
                    <span className="mono">{JSON.stringify(selectedCohort.rule)}</span>
                  </div>
                  <div className="flex justify-between border-b py-1">
                    <span className="text-muted-foreground">Sample Count (N)</span>
                    <strong>{selectedCohort.population.n}</strong>
                  </div>
                  <div className="flex justify-between border-b py-1">
                    <span className="text-muted-foreground">Prevalence (Positive Rate)</span>
                    <strong>{(selectedCohort.population.prevalence * 100).toFixed(1)}%</strong>
                  </div>
                  <div className="flex justify-between border-b py-1">
                    <span className="text-muted-foreground">Status / Reason</span>
                    <span>{selectedCohort.status_reason || selectedCohort.status}</span>
                  </div>
                  {selectedCohort.metrics.roc_auc?.reason && (
                    <div className="flex justify-between border-b py-1 text-amber-600">
                      <span>ROC-AUC Note</span>
                      <span>{selectedCohort.metrics.roc_auc.reason}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Comparisons & Deltas */}
              <div className="rounded-xl border p-4 text-xs">
                <div className="metric-label">DISPARITY & DELTA ANALYSIS</div>
                {(() => {
                  const comp = currentStudy.comparisons?.find((c) => c.subgroup_id === selectedCohort.id);
                  if (!comp) return <p className="mt-2 text-muted-foreground">No comparison calculated.</p>;
                  return (
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between border-b py-1">
                        <span className="text-muted-foreground">Reference Cohort</span>
                        <span>{comp.reference_label}</span>
                      </div>
                      {Object.entries(comp.deltas || {}).map(([mName, delta]) => (
                        <div key={mName} className="flex justify-between border-b py-1">
                          <span className="text-muted-foreground">{mName} Delta</span>
                          <strong className={delta !== null && delta < 0 ? 'text-amber-500' : ''}>
                            {delta !== null ? (delta > 0 ? `+${(delta * 100).toFixed(1)}%` : `${(delta * 100).toFixed(1)}%`) : '—'}
                          </strong>
                        </div>
                      ))}
                      {comp.disparity_ratios?.sensitivity_ratio !== null && comp.disparity_ratios?.sensitivity_ratio !== undefined && (
                        <div className="flex justify-between border-b py-1">
                          <span className="text-muted-foreground">Sensitivity Ratio</span>
                          <strong>{comp.disparity_ratios.sensitivity_ratio.toFixed(2)}x</strong>
                        </div>
                      )}
                      {comp.notes.length > 0 && (
                        <div className="mt-2 text-muted-foreground text-[11px]">
                          {comp.notes.map((n, idx) => (
                            <p key={idx}>{n}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

          {/* Scientific Disclaimer Notice */}
          <Notice tone="amber">
            <strong>Scientific Boundary:</strong> Biomedical Subgroup Analysis reports stratified evaluation evidence
            across predefined cohorts. It does not establish clinical safety, diagnostic efficacy, algorithmic fairness,
            or model superiority. Subgroups with smaller sample sizes carry wider confidence intervals and higher sample
            variance.
          </Notice>

          <JsonDisclosure label="Open full machine-readable subgroup study" value={currentStudy} />
        </div>
      )}
    </Card>
  );
}
