import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowUpDown,
  CheckCircle2,
  Clock,
  Copy,
  ExternalLink,
  Filter,
  History,
  Layers,
  Milestone,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  ShieldAlert,
  Sparkles,
  Terminal,
  X,
  XCircle,
} from 'lucide-react';
import { qh } from '../../lib/api';
import type {
  Job,
  JobCheckpointItem,
  JobEventItem,
  JobProgress,
  ModelRecord,
} from '../../types/qhealth';

export interface QuantumJobManagerProps {
  selectedJobId?: string | null;
  onSelectJob?: (jobId: string | null) => void;
  className?: string;
}

type JobFilterStatus = 'all' | 'active' | 'completed' | 'failed' | 'paused' | 'cancelled';
type SortOrder = 'desc' | 'asc';

const ACTIVE_STATUSES = new Set([
  'queued',
  'running',
  'resuming',
  'checkpointing',
  'pause_requested',
  'cancel_requested',
]);

const TERMINAL_STATUSES = new Set(['succeeded', 'partial', 'failed', 'cancelled']);

function shortId(val?: string | null): string {
  if (!val) return '—';
  if (val.length <= 12) return val;
  return `${val.slice(0, 6)}…${val.slice(-4)}`;
}

function formatDuration(startedAt?: string | null, completedAt?: string | null): string {
  if (!startedAt) return '—';
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  if (isNaN(start) || isNaN(end) || end < start) return '—';
  const sec = Math.round((end - start) / 1000);
  if (sec < 60) return `${sec}s`;
  const min = Math.floor(sec / 60);
  const remSec = sec % 60;
  return `${min}m ${remSec}s`;
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'succeeded':
      return (
        <span className="ql-job-badge is-succeeded">
          <CheckCircle2 size={11} aria-hidden="true" />
          <span>Succeeded</span>
        </span>
      );
    case 'partial':
      return (
        <span className="ql-job-badge is-partial">
          <CheckCircle2 size={11} aria-hidden="true" />
          <span>Partial</span>
        </span>
      );
    case 'running':
      return (
        <span className="ql-job-badge is-running">
          <Activity size={11} className="ql-pulse" aria-hidden="true" />
          <span>Running</span>
        </span>
      );
    case 'resuming':
      return (
        <span className="ql-job-badge is-running">
          <RotateCcw size={11} className="ql-spin" aria-hidden="true" />
          <span>Resuming</span>
        </span>
      );
    case 'checkpointing':
      return (
        <span className="ql-job-badge is-checkpointing">
          <Milestone size={11} className="ql-pulse" aria-hidden="true" />
          <span>Checkpointing</span>
        </span>
      );
    case 'queued':
      return (
        <span className="ql-job-badge is-queued">
          <Clock size={11} aria-hidden="true" />
          <span>Queued</span>
        </span>
      );
    case 'paused':
      return (
        <span className="ql-job-badge is-paused">
          <Pause size={11} aria-hidden="true" />
          <span>Paused</span>
        </span>
      );
    case 'pause_requested':
      return (
        <span className="ql-job-badge is-paused">
          <Pause size={11} className="ql-pulse" aria-hidden="true" />
          <span>Pause Requested</span>
        </span>
      );
    case 'cancelled':
      return (
        <span className="ql-job-badge is-cancelled">
          <XCircle size={11} aria-hidden="true" />
          <span>Cancelled</span>
        </span>
      );
    case 'cancel_requested':
      return (
        <span className="ql-job-badge is-cancelled">
          <XCircle size={11} className="ql-pulse" aria-hidden="true" />
          <span>Cancel Requested</span>
        </span>
      );
    case 'failed':
    case 'interrupted':
      return (
        <span className="ql-job-badge is-failed">
          <AlertCircle size={11} aria-hidden="true" />
          <span>{status === 'interrupted' ? 'Interrupted' : 'Failed'}</span>
        </span>
      );
    case 'recoverable':
      return (
        <span className="ql-job-badge is-recoverable">
          <RotateCcw size={11} aria-hidden="true" />
          <span>Recoverable</span>
        </span>
      );
    default:
      return (
        <span className="ql-job-badge is-unknown">
          <span>{status}</span>
        </span>
      );
  }
}

function getModelKindBadge(modelType: string) {
  if (['vqc', 'qsvc', 'qnn'].includes(modelType)) {
    return (
      <span key={modelType} className="ql-model-tag is-quantum">
        <Sparkles size={9} aria-hidden="true" />
        <span>{modelType.toUpperCase()}</span>
      </span>
    );
  }
  if (modelType === 'hybrid_pennylane_torch') {
    return (
      <span key={modelType} className="ql-model-tag is-hybrid">
        <Layers size={9} aria-hidden="true" />
        <span>PennyLane Hybrid</span>
      </span>
    );
  }
  return (
    <span key={modelType} className="ql-model-tag is-classical">
      <span>{modelType.replaceAll('_', ' ').toUpperCase()}</span>
    </span>
  );
}

export function QuantumJobManager({
  selectedJobId: externalSelectedJobId,
  onSelectJob: externalOnSelectJob,
  className = '',
}: QuantumJobManagerProps) {
  const [internalSelectedJobId, setInternalSelectedJobId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<JobFilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [confirmCancelJobId, setConfirmCancelJobId] = useState<string | null>(null);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const selectedJobId = externalSelectedJobId !== undefined ? externalSelectedJobId : internalSelectedJobId;

  const handleSelectJob = (jobId: string | null) => {
    if (externalOnSelectJob) {
      externalOnSelectJob(jobId);
    } else {
      setInternalSelectedJobId(jobId);
    }
  };

  // 1. Fetch Job List with adaptive polling for active jobs
  const jobsQuery = useQuery({
    queryKey: ['jobs'],
    queryFn: qh.jobs,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (Array.isArray(data) && data.some((job) => ACTIVE_STATUSES.has(job.status))) {
        return 3000;
      }
      return false;
    },
  });

  const jobsList = jobsQuery.data || [];
  const selectedJob = useMemo(
    () => jobsList.find((job) => job.id === selectedJobId) || null,
    [jobsList, selectedJobId]
  );

  const isSelectedJobActive = Boolean(selectedJob && ACTIVE_STATUSES.has(selectedJob.status));

  // 2. Fetch live progress for selected job with controlled polling (stops when terminal)
  const progressQuery = useQuery({
    queryKey: ['job-progress', selectedJobId],
    queryFn: () => (selectedJobId ? qh.jobProgress(selectedJobId) : null),
    enabled: Boolean(selectedJobId),
    refetchInterval: isSelectedJobActive ? 3000 : false,
  });

  // 3. Fetch event history for selected job
  const historyQuery = useQuery({
    queryKey: ['job-history', selectedJobId],
    queryFn: () => (selectedJobId ? qh.jobHistory(selectedJobId) : []),
    enabled: Boolean(selectedJobId),
    staleTime: 5000,
  });

  // 4. Fetch checkpoints for selected job
  const checkpointsQuery = useQuery({
    queryKey: ['job-checkpoints', selectedJobId],
    queryFn: () => (selectedJobId ? qh.jobCheckpoints(selectedJobId) : []),
    enabled: Boolean(selectedJobId),
    staleTime: 5000,
  });

  // Action handlers
  const handlePause = async (job: Job) => {
    setActionInProgress(job.id);
    setActionError(null);
    try {
      await qh.pauseJob(job.id);
      await jobsQuery.refetch();
      if (selectedJobId === job.id) {
        await progressQuery.refetch();
        await historyQuery.refetch();
      }
    } catch (err) {
      setActionError((err as Error).message || 'Failed to pause job safely.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleResume = async (job: Job) => {
    setActionInProgress(job.id);
    setActionError(null);
    try {
      await qh.resumeJob(job.id);
      await jobsQuery.refetch();
      if (selectedJobId === job.id) {
        await progressQuery.refetch();
        await historyQuery.refetch();
      }
    } catch (err) {
      setActionError((err as Error).message || 'Failed to resume job.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleCancel = async (jobId: string) => {
    setActionInProgress(jobId);
    setActionError(null);
    setConfirmCancelJobId(null);
    try {
      await qh.cancelJob(jobId);
      await jobsQuery.refetch();
      if (selectedJobId === jobId) {
        await progressQuery.refetch();
        await historyQuery.refetch();
      }
    } catch (err) {
      setActionError((err as Error).message || 'Failed to cancel job.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleRetry = async (job: Job) => {
    setActionInProgress(job.id);
    setActionError(null);
    try {
      const newJob = await qh.retryJob(job.id);
      await jobsQuery.refetch();
      if (newJob && newJob.id) {
        handleSelectJob(newJob.id);
      }
    } catch (err) {
      setActionError((err as Error).message || 'Failed to retry job.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard?.writeText(id);
    setCopyFeedback(id);
    setTimeout(() => setCopyFeedback(null), 2000);
  };

  // Summary counts
  const summary = useMemo(() => {
    let active = 0;
    let succeeded = 0;
    let failed = 0;
    let paused = 0;
    let cancelled = 0;

    for (const job of jobsList) {
      if (ACTIVE_STATUSES.has(job.status)) active++;
      else if (job.status === 'succeeded' || job.status === 'partial') succeeded++;
      else if (job.status === 'failed' || job.status === 'interrupted') failed++;
      else if (job.status === 'paused') paused++;
      else if (job.status === 'cancelled') cancelled++;
    }

    return { total: jobsList.length, active, succeeded, failed, paused, cancelled };
  }, [jobsList]);

  // Filter and sort jobs
  const filteredJobs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    return jobsList
      .filter((job) => {
        // Status filter
        if (statusFilter === 'active' && !ACTIVE_STATUSES.has(job.status)) return false;
        if (statusFilter === 'completed' && !['succeeded', 'partial'].includes(job.status)) return false;
        if (statusFilter === 'failed' && !['failed', 'interrupted'].includes(job.status)) return false;
        if (statusFilter === 'paused' && job.status !== 'paused') return false;
        if (statusFilter === 'cancelled' && job.status !== 'cancelled') return false;

        // Search query
        if (!q) return true;
        const matchesId = job.id.toLowerCase().includes(q);
        const matchesName = (job.experiment_name || '').toLowerCase().includes(q);
        const matchesModels = (job.models || []).some((m) => m.model_type.toLowerCase().includes(q));
        const matchesState = (job.state || '').toLowerCase().includes(q);
        const matchesPhase = (job.current_phase || '').toLowerCase().includes(q);

        return matchesId || matchesName || matchesModels || matchesState || matchesPhase;
      })
      .sort((a, b) => {
        const timeA = new Date(a.created_at).getTime() || 0;
        const timeB = new Date(b.created_at).getTime() || 0;
        return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
      });
  }, [jobsList, statusFilter, searchQuery, sortOrder]);

  const liveProgress = progressQuery.data;

  return (
    <section
      className={`ql-job-manager-container ${className}`}
      aria-label="Quantum Execution Jobs and Management"
      id="quantum-job-manager"
    >
      {/* Header section */}
      <div className="ql-job-manager-header">
        <div className="ql-job-header-left">
          <div className="ql-job-icon" aria-hidden="true">
            <Terminal size={20} />
          </div>
          <div>
            <span className="ql-eyebrow">EXECUTION LIFECYCLE &amp; OBSERVABILITY</span>
            <h2 className="ql-job-heading">Quantum Jobs &amp; Execution Monitor</h2>
            <p className="ql-job-description">
              Observe durable quantum simulation background jobs, track live checkpoint progress, and review verifiable execution history.
            </p>
          </div>
        </div>

        <div className="ql-job-header-actions">
          <button
            type="button"
            className="btn btn-outline ql-job-refresh-btn"
            onClick={() => jobsQuery.refetch()}
            disabled={jobsQuery.isFetching}
            aria-label="Refresh job registry"
            title="Refresh job list"
          >
            <RefreshCw size={14} className={jobsQuery.isFetching ? 'ql-spin' : ''} aria-hidden="true" />
            <span>{jobsQuery.isFetching ? 'Refreshing…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Summary counters */}
      <div className="ql-job-stats-grid" aria-label="Job execution status summary">
        <div className="ql-job-stat-card">
          <small>Total Jobs</small>
          <strong>{summary.total}</strong>
          <span>Recorded in registry</span>
        </div>
        <div className="ql-job-stat-card">
          <small>Active Jobs</small>
          <strong className="ql-tone-purple">{summary.active}</strong>
          <span>Running or queued</span>
        </div>
        <div className="ql-job-stat-card">
          <small>Succeeded</small>
          <strong className="ql-tone-green">{summary.succeeded}</strong>
          <span>Durable artifacts saved</span>
        </div>
        <div className="ql-job-stat-card">
          <small>Failed / Interrupted</small>
          <strong className="ql-tone-red">{summary.failed}</strong>
          <span>Inspectable errors</span>
        </div>
      </div>

      {/* Action error banner */}
      {actionError && (
        <div className="ql-job-alert-banner is-error" role="alert">
          <AlertTriangle size={16} aria-hidden="true" />
          <div className="ql-job-alert-copy">
            <strong>Job Operation Failed</strong>
            <p>{actionError}</p>
          </div>
          <button
            type="button"
            className="ql-job-alert-close"
            onClick={() => setActionError(null)}
            aria-label="Dismiss error"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Toolbar: Search, Filters, Sort */}
      <div className="ql-job-toolbar" role="search" aria-label="Job filters and search">
        <div className="ql-job-search-box">
          <Search size={14} className="ql-job-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="ql-job-search-input"
            placeholder="Search jobs by ID, experiment name, model (VQC, QNN, etc.)…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search jobs"
          />
          {searchQuery && (
            <button
              type="button"
              className="ql-job-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <div className="ql-job-filter-chips" role="group" aria-label="Filter jobs by status">
          <button
            type="button"
            className={`ql-job-chip ${statusFilter === 'all' ? 'is-active' : ''}`}
            onClick={() => setStatusFilter('all')}
            aria-pressed={statusFilter === 'all'}
          >
            All ({summary.total})
          </button>
          <button
            type="button"
            className={`ql-job-chip ${statusFilter === 'active' ? 'is-active' : ''}`}
            onClick={() => setStatusFilter('active')}
            aria-pressed={statusFilter === 'active'}
          >
            Active ({summary.active})
          </button>
          <button
            type="button"
            className={`ql-job-chip ${statusFilter === 'completed' ? 'is-active' : ''}`}
            onClick={() => setStatusFilter('completed')}
            aria-pressed={statusFilter === 'completed'}
          >
            Succeeded ({summary.succeeded})
          </button>
          <button
            type="button"
            className={`ql-job-chip ${statusFilter === 'failed' ? 'is-active' : ''}`}
            onClick={() => setStatusFilter('failed')}
            aria-pressed={statusFilter === 'failed'}
          >
            Failed ({summary.failed})
          </button>
          {summary.paused > 0 && (
            <button
              type="button"
              className={`ql-job-chip ${statusFilter === 'paused' ? 'is-active' : ''}`}
              onClick={() => setStatusFilter('paused')}
              aria-pressed={statusFilter === 'paused'}
            >
              Paused ({summary.paused})
            </button>
          )}
          {summary.cancelled > 0 && (
            <button
              type="button"
              className={`ql-job-chip ${statusFilter === 'cancelled' ? 'is-active' : ''}`}
              onClick={() => setStatusFilter('cancelled')}
              aria-pressed={statusFilter === 'cancelled'}
            >
              Cancelled ({summary.cancelled})
            </button>
          )}

          <button
            type="button"
            className="ql-job-sort-toggle"
            onClick={() => setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}
            aria-label={`Sort by date: currently ${sortOrder === 'desc' ? 'newest first' : 'oldest first'}`}
            title="Toggle sort order"
          >
            <ArrowUpDown size={12} aria-hidden="true" />
            <span>{sortOrder === 'desc' ? 'Newest' : 'Oldest'}</span>
          </button>
        </div>
      </div>

      {/* Main split view: Job List/Table on left, Selected Job Detail on right */}
      <div className="ql-job-layout">
        {/* Left pane: Job list */}
        <div className="ql-job-list-pane">
          {jobsQuery.isLoading && (
            <div className="ql-job-skeleton" role="status" aria-busy="true" aria-label="Loading job records">
              <div className="ql-skeleton-row" />
              <div className="ql-skeleton-row" />
              <div className="ql-skeleton-row" />
              <span>Loading durable job records…</span>
            </div>
          )}

          {jobsQuery.isError && (
            <div className="ql-job-error" role="alert">
              <AlertCircle size={20} className="ql-error-icon" aria-hidden="true" />
              <div className="ql-error-copy">
                <strong>Unable to Load Execution Jobs</strong>
                <p>{(jobsQuery.error as Error)?.message || 'Failed to retrieve jobs from backend.'}</p>
              </div>
              <button type="button" className="btn btn-outline" onClick={() => jobsQuery.refetch()}>
                Retry
              </button>
            </div>
          )}

          {!jobsQuery.isLoading && !jobsQuery.isError && jobsList.length === 0 && (
            <div className="ql-job-empty" role="status">
              <Terminal size={24} className="ql-empty-icon" aria-hidden="true" />
              <h3>No Execution Jobs Recorded</h3>
              <p>
                No quantum or hybrid training jobs exist in the system yet. Configure and launch a training experiment in Model Lab or Quantum Lab to initiate background execution.
              </p>
              <Link to="/training" className="btn btn-outline">
                Configure Training Experiment
              </Link>
            </div>
          )}

          {!jobsQuery.isLoading && !jobsQuery.isError && jobsList.length > 0 && filteredJobs.length === 0 && (
            <div className="ql-job-empty" role="status">
              <Filter size={24} className="ql-empty-icon" aria-hidden="true" />
              <h3>No Jobs Match Filter</h3>
              <p>
                No jobs match the current query <code>"{searchQuery}"</code> with filter <code>"{statusFilter}"</code>.
              </p>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  setSearchQuery('');
                  setStatusFilter('all');
                }}
              >
                Reset Filters
              </button>
            </div>
          )}

          {/* Jobs Table */}
          {!jobsQuery.isLoading && filteredJobs.length > 0 && (
            <div className="ql-job-table-wrap" role="region" aria-label="Jobs table">
              <table className="ql-job-table">
                <thead>
                  <tr>
                    <th scope="col">Job ID</th>
                    <th scope="col">Experiment / Models</th>
                    <th scope="col">Status</th>
                    <th scope="col">Progress</th>
                    <th scope="col">Duration</th>
                    <th scope="col">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredJobs.map((job) => {
                    const isSelected = selectedJobId === job.id;
                    const isBusy = actionInProgress === job.id;
                    const models = job.models || [];
                    const determinate = job.total_units !== null && job.total_units !== undefined && job.total_units > 0;
                    const progressValue = job.progress ?? 0;

                    return (
                      <tr
                        key={job.id}
                        className={`ql-job-row ${isSelected ? 'is-selected' : ''}`}
                        onClick={() => handleSelectJob(job.id)}
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSelectJob(job.id);
                          }
                        }}
                        aria-selected={isSelected}
                      >
                        {/* Job ID column */}
                        <td className="ql-job-cell-id">
                          <div className="ql-id-group">
                            <code title={job.id}>{shortId(job.id)}</code>
                            <button
                              type="button"
                              className="ql-copy-id-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCopyId(job.id);
                              }}
                              title="Copy full UUID"
                              aria-label={`Copy job ID ${job.id}`}
                            >
                              <Copy size={11} />
                            </button>
                            {copyFeedback === job.id && <span className="ql-copied-pill">Copied</span>}
                          </div>
                          <small className="ql-job-time">{new Date(job.created_at).toLocaleTimeString()}</small>
                        </td>

                        {/* Experiment / Models column */}
                        <td className="ql-job-cell-exp">
                          <strong className="ql-exp-title">
                            {job.experiment_name || `Experiment ${shortId(job.experiment_id)}`}
                          </strong>
                          <div className="ql-job-models-list">
                            {models.map((m) => getModelKindBadge(m.model_type))}
                          </div>
                        </td>

                        {/* Status column */}
                        <td className="ql-job-cell-status">
                          {getStatusBadge(job.status)}
                          {job.state && <small className="ql-job-state-preview">{job.state}</small>}
                        </td>

                        {/* Progress column */}
                        <td className="ql-job-cell-progress">
                          <div className="ql-progress-box">
                            <div className="ql-progress-text">
                              <span>{job.current_phase || (determinate ? 'Progress' : 'Running')}</span>
                              <strong>{determinate ? `${progressValue}%` : '—'}</strong>
                            </div>
                            <div className="ql-progress-track">
                              <div
                                className={`ql-progress-fill ${!determinate && ACTIVE_STATUSES.has(job.status) ? 'is-indeterminate' : ''}`}
                                style={{ width: determinate ? `${progressValue}%` : '100%' }}
                              />
                            </div>
                            {job.total_units ? (
                              <small className="ql-units-note">
                                {job.completed_units ?? 0}/{job.total_units} units
                              </small>
                            ) : null}
                          </div>
                        </td>

                        {/* Duration column */}
                        <td className="ql-job-cell-duration">
                          <span>{formatDuration(job.started_at, job.completed_at)}</span>
                        </td>

                        {/* Actions column */}
                        <td className="ql-job-cell-actions" onClick={(e) => e.stopPropagation()}>
                          <div className="ql-action-btn-group">
                            {/* Pause: only running/resuming/checkpointing */}
                            {['running', 'resuming', 'checkpointing'].includes(job.status) && (
                              <button
                                type="button"
                                className="btn btn-outline ql-btn-sm"
                                onClick={() => handlePause(job)}
                                disabled={isBusy}
                                title="Pause safely at next boundary"
                              >
                                <Pause size={11} aria-hidden="true" />
                                <span>Pause</span>
                              </button>
                            )}

                            {/* Resume: only paused/recoverable */}
                            {['paused', 'recoverable'].includes(job.status) && (
                              <button
                                type="button"
                                className="btn btn-outline ql-btn-sm"
                                onClick={() => handleResume(job)}
                                disabled={isBusy}
                                title="Resume job from checkpoint"
                              >
                                <Play size={11} aria-hidden="true" />
                                <span>Resume</span>
                              </button>
                            )}

                            {/* Retry: only failed/recoverable/interrupted */}
                            {['failed', 'recoverable', 'interrupted'].includes(job.status) && (
                              <button
                                type="button"
                                className="btn btn-outline ql-btn-sm"
                                onClick={() => handleRetry(job)}
                                disabled={isBusy}
                                title="Retry experiment execution"
                              >
                                <RotateCcw size={11} aria-hidden="true" />
                                <span>Retry</span>
                              </button>
                            )}

                            {/* Cancel: active or non-terminal */}
                            {!TERMINAL_STATUSES.has(job.status) && (
                              <button
                                type="button"
                                className="btn btn-outline ql-btn-sm ql-btn-cancel"
                                onClick={() => setConfirmCancelJobId(job.id)}
                                disabled={isBusy || job.status === 'cancel_requested'}
                                title="Cancel execution"
                              >
                                <X size={11} aria-hidden="true" />
                                <span>Cancel</span>
                              </button>
                            )}

                            {/* Inspect button */}
                            <button
                              type="button"
                              className={`btn btn-outline ql-btn-sm ${isSelected ? 'ql-btn-inspect-active' : ''}`}
                              onClick={() => handleSelectJob(isSelected ? null : job.id)}
                              aria-label={`Inspect job ${job.id}`}
                            >
                              <span>{isSelected ? 'Close' : 'Inspect'}</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right pane: Selected Job Inspection Detail */}
        {selectedJob && (
          <aside className="ql-job-detail-panel" aria-label={`Details for job ${selectedJob.id}`}>
            <div className="ql-detail-header">
              <div className="ql-detail-title-group">
                <span className="ql-eyebrow">JOB INSPECTOR</span>
                <h3 className="ql-detail-heading">
                  {selectedJob.experiment_name || `Job Details`}
                </h3>
                <div className="ql-detail-id-box">
                  <code>{selectedJob.id}</code>
                  <button
                    type="button"
                    className="ql-copy-id-btn"
                    onClick={() => handleCopyId(selectedJob.id)}
                    title="Copy full UUID"
                  >
                    <Copy size={12} />
                  </button>
                  {copyFeedback === selectedJob.id && <span className="ql-copied-pill">Copied</span>}
                </div>
              </div>

              <button
                type="button"
                className="ql-detail-close-btn"
                onClick={() => handleSelectJob(null)}
                aria-label="Close job details panel"
              >
                <X size={16} />
              </button>
            </div>

            {/* Live progress and state badge */}
            <div className="ql-detail-status-card">
              <div className="ql-detail-status-row">
                <div className="ql-status-with-pulse">
                  {getStatusBadge(liveProgress?.status || selectedJob.status)}
                  {isSelectedJobActive && (
                    <span className="ql-live-tag">
                      <span className="ql-live-dot" /> LIVE POLLING
                    </span>
                  )}
                </div>
                <span className="ql-detail-phase">
                  {liveProgress?.current_phase || selectedJob.current_phase || 'Ready'}
                </span>
              </div>

              <div className="ql-detail-progress-section">
                <div className="ql-detail-progress-metrics">
                  <span>Completed Units</span>
                  <strong>
                    {liveProgress?.completed_units ?? selectedJob.completed_units ?? 0} /{' '}
                    {liveProgress?.total_units ?? selectedJob.total_units ?? '—'}
                  </strong>
                </div>

                <div className="ql-progress-track">
                  <div
                    className={`ql-progress-fill ${
                      liveProgress?.percentage === null && isSelectedJobActive ? 'is-indeterminate' : ''
                    }`}
                    style={{
                      width: liveProgress?.percentage !== null ? `${liveProgress?.percentage ?? selectedJob.progress}%` : '100%',
                    }}
                  />
                </div>
              </div>

              {selectedJob.state && <p className="ql-detail-state-msg">{selectedJob.state}</p>}
            </div>

            {/* Technical execution details */}
            <div className="ql-detail-specs-grid">
              <div className="ql-spec-box">
                <small>Job Type</small>
                <strong>{selectedJob.job_type || 'training'}</strong>
              </div>
              <div className="ql-spec-box">
                <small>Attempt / Resumes</small>
                <strong>
                  Attempt {selectedJob.attempt_count ?? 0} · {selectedJob.resume_count ?? 0} resumes
                </strong>
              </div>
              <div className="ql-spec-box">
                <small>Submitted</small>
                <strong>{new Date(selectedJob.created_at).toLocaleString()}</strong>
              </div>
              <div className="ql-spec-box">
                <small>Execution Duration</small>
                <strong>{formatDuration(selectedJob.started_at, selectedJob.completed_at)}</strong>
              </div>
              {selectedJob.current_checkpoint_id && (
                <div className="ql-spec-box">
                  <small>Active Checkpoint</small>
                  <code>{shortId(selectedJob.current_checkpoint_id)}</code>
                </div>
              )}
              {selectedJob.active_unit && (
                <div className="ql-spec-box">
                  <small>Active Logical Unit</small>
                  <code>{selectedJob.active_unit}</code>
                </div>
              )}
            </div>

            {/* Model records inside this job */}
            {selectedJob.models && selectedJob.models.length > 0 && (
              <div className="ql-detail-models-section">
                <h4 className="ql-section-subhead">
                  Models in Execution ({selectedJob.models.length})
                </h4>
                <div className="ql-models-table-wrap">
                  <table className="ql-models-table">
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Status</th>
                        <th>Progress</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedJob.models.map((m) => (
                        <tr key={m.id}>
                          <td>
                            <strong>{m.model_type.toUpperCase()}</strong>
                            <small className="ql-model-id-label">{shortId(m.id)}</small>
                          </td>
                          <td>
                            <span className={`ql-model-status is-${m.status}`}>{m.status}</span>
                          </td>
                          <td>{m.progress !== null && m.progress !== undefined ? `${m.progress}%` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Recorded errors disclosure */}
            {selectedJob.errors && selectedJob.errors.length > 0 && (
              <div className="ql-detail-errors-box" role="alert">
                <div className="ql-errors-header">
                  <AlertCircle size={14} aria-hidden="true" />
                  <strong>Recorded Model Failures ({selectedJob.errors.length})</strong>
                </div>
                <ul className="ql-errors-list">
                  {selectedJob.errors.map((err, idx) => (
                    <li key={idx} className="ql-error-item">
                      <code>{(err.code as string) || (err.model_type as string) || 'Failure'}</code>
                      <span>{(err.message as string) || JSON.stringify(err)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Checkpoint Milestones */}
            {checkpointsQuery.data && checkpointsQuery.data.length > 0 && (
              <div className="ql-checkpoints-section">
                <h4 className="ql-section-subhead">
                  Durable Checkpoints ({checkpointsQuery.data.length})
                </h4>
                <div className="ql-checkpoints-list">
                  {checkpointsQuery.data.map((cp: JobCheckpointItem) => (
                    <div key={cp.id} className="ql-checkpoint-item">
                      <Milestone size={12} className="ql-cp-icon" aria-hidden="true" />
                      <div className="ql-cp-copy">
                        <div className="ql-cp-title-row">
                          <strong>{cp.logical_unit || `Checkpoint #${cp.sequence_number}`}</strong>
                          <span className="ql-cp-badge">{cp.checkpoint_type}</span>
                        </div>
                        <small className="ql-cp-time">{new Date(cp.created_at).toLocaleTimeString()}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Event History Timeline */}
            {historyQuery.data && historyQuery.data.length > 0 && (
              <div className="ql-history-section">
                <h4 className="ql-section-subhead">
                  Execution State Transitions ({historyQuery.data.length})
                </h4>
                <div className="ql-history-timeline">
                  {historyQuery.data.map((evt: JobEventItem) => (
                    <div key={evt.id} className="ql-timeline-item">
                      <div className="ql-timeline-dot" />
                      <div className="ql-timeline-body">
                        <div className="ql-timeline-title">
                          <strong>{evt.event_type.replaceAll('_', ' ').toUpperCase()}</strong>
                          <small>{new Date(evt.created_at).toLocaleTimeString()}</small>
                        </div>
                        {evt.from_status && evt.to_status && (
                          <div className="ql-transition-pill">
                            <span>{evt.from_status}</span>
                            <span className="ql-arrow">→</span>
                            <strong>{evt.to_status}</strong>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions in detail view */}
            <div className="ql-detail-actions-bar">
              {['running', 'resuming', 'checkpointing'].includes(selectedJob.status) && (
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => handlePause(selectedJob)}
                  disabled={actionInProgress === selectedJob.id}
                >
                  <Pause size={13} aria-hidden="true" />
                  <span>Pause Safely</span>
                </button>
              )}

              {['paused', 'recoverable'].includes(selectedJob.status) && (
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => handleResume(selectedJob)}
                  disabled={actionInProgress === selectedJob.id}
                >
                  <Play size={13} aria-hidden="true" />
                  <span>Resume Execution</span>
                </button>
              )}

              {['failed', 'recoverable', 'interrupted'].includes(selectedJob.status) && (
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => handleRetry(selectedJob)}
                  disabled={actionInProgress === selectedJob.id}
                >
                  <RotateCcw size={13} aria-hidden="true" />
                  <span>Retry Job</span>
                </button>
              )}

              {!TERMINAL_STATUSES.has(selectedJob.status) && (
                <button
                  type="button"
                  className="btn btn-outline ql-btn-cancel"
                  onClick={() => setConfirmCancelJobId(selectedJob.id)}
                  disabled={actionInProgress === selectedJob.id || selectedJob.status === 'cancel_requested'}
                >
                  <X size={13} aria-hidden="true" />
                  <span>Request Cancellation</span>
                </button>
              )}

              {selectedJob.experiment_id && (
                <Link to={`/experiments/${selectedJob.experiment_id}`} className="btn btn-outline">
                  <ExternalLink size={13} aria-hidden="true" />
                  <span>View Experiment</span>
                </Link>
              )}
            </div>
          </aside>
        )}
      </div>

      {/* Cancellation Confirmation Dialog */}
      {confirmCancelJobId && (
        <div className="ql-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="cancel-dialog-title">
          <div className="ql-modal-box">
            <div className="ql-modal-header">
              <ShieldAlert size={20} className="ql-modal-icon" aria-hidden="true" />
              <h3 id="cancel-dialog-title">Confirm Job Cancellation</h3>
            </div>
            <p className="ql-modal-desc">
              Are you sure you want to cancel job <code>{shortId(confirmCancelJobId)}</code>? Execution will halt at the next safe boundary, and completed model records will be retained.
            </p>
            <div className="ql-modal-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setConfirmCancelJobId(null)}
              >
                Keep Running
              </button>
              <button
                type="button"
                className="btn btn-primary ql-btn-danger"
                onClick={() => handleCancel(confirmCancelJobId)}
              >
                Yes, Cancel Job
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
export default QuantumJobManager;
