import { Notice, Loading, JsonDisclosure } from '../components/Shared';
import { Button } from '../components/ui';
import { useMutation, useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';


import { qh } from '../lib/api';


import { ChartNoAxesCombined, CircuitBoard } from 'lucide-react';

export function QuantumDiagnostics({ model }: { model: any }) {
  const { data: preflight, isLoading: isPreflightLoading } = useQuery({
    queryKey: ['quantum_diagnostics_preflight', model.experiment_id, model.id],
    queryFn: () => qh.quantum_diagnostics_preflight({
      experiment_id: model.experiment_id,
      model_record_id: model.id
    })
  });

  const { data: report, isLoading: isReportLoading, refetch } = useQuery({
    queryKey: ['quantum_diagnostics', model.id],
    queryFn: () => qh.quantum_diagnostics_by_run(model.id),
    retry: false
  });

  const generate = useMutation({
    mutationFn: () => qh.create_quantum_diagnostics({
      experiment_id: model.experiment_id,
      model_record_id: model.id
    }),
    onSuccess: () => refetch()
  });

  if (isPreflightLoading || isReportLoading) {
    return <div className="mt-4 rounded-xl border p-4"><Loading /></div>;
  }

  if (preflight && !preflight.feasible) {
    return (
      <div className="mt-4 rounded-xl border p-4">
        <div className="metric-label flex items-center gap-2">
          <CircuitBoard size={14} />
          QUANTUM RESEARCH DIAGNOSTICS
        </div>
        <div className="mt-3">
          <Notice tone="amber">
            Quantum diagnostics are not available for this model. {preflight.limitations?.[0] || 'Incompatible model type.'}
          </Notice>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="mt-4 rounded-xl border p-4">
        <div className="metric-label flex items-center gap-2">
          <CircuitBoard size={14} />
          QUANTUM RESEARCH DIAGNOSTICS
        </div>
        <p className="mt-3 text-sm muted">No quantum diagnostics report exists for this run.</p>
        <Button className="mt-4" onClick={() => generate.mutate()} disabled={generate.isPending}>
          Generate Diagnostics
        </Button>
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-xl border p-4 bg-slate-50 dark:bg-slate-900/50">
      <div className="flex items-center justify-between mb-4 border-b pb-3">
        <div className="metric-label flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200">
          <CircuitBoard size={15} className="text-blue-600 dark:text-blue-400" />
          QUANTUM RESEARCH DIAGNOSTICS
        </div>
        <span className="text-xs font-mono bg-slate-200 dark:bg-slate-800 px-2 py-1 rounded text-slate-600 dark:text-slate-400">
          ID: {report.id.substring(0, 8)}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Encoding */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Feature Encoding</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Qubits</span>
              <strong className="font-mono">{report.feature_encoding?.qubit_count ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Map Strategy</span>
              <strong className="font-mono text-xs">{report.feature_encoding?.mapping_strategy ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Dim. Reduction</span>
              <strong className="font-mono">{report.feature_encoding?.dimensionality_reduction ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Orig. Features</span>
              <strong className="font-mono">{report.feature_encoding?.original_features ?? 'N/A'}</strong>
            </div>
          </div>
        </div>

        {/* Circuit */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Circuit Structure</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Ansatz</span>
              <strong className="font-mono text-xs">{report.circuit_structure?.ansatz ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Entanglement</span>
              <strong className="font-mono text-xs">{report.circuit_structure?.entanglement_pattern ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Depth (Est.)</span>
              <strong className="font-mono">{report.circuit_structure?.depth ?? 'UNAVAILABLE'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Param. Gates</span>
              <strong className="font-mono">{report.circuit_structure?.parameterized_gates ?? 'UNAVAILABLE'}</strong>
            </div>
          </div>
        </div>

        {/* Execution */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Execution Profile</h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Backend</span>
              <strong className="font-mono text-xs truncate max-w-[120px] text-right" title={report.execution_profile?.backend}>{report.execution_profile?.backend ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Mode</span>
              <strong className="font-mono text-xs">{report.execution_profile?.execution_mode ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Shots</span>
              <strong className="font-mono">{report.execution_profile?.shots ?? 'N/A'}</strong>
            </div>
            <div className="flex justify-between border-b pb-1 border-slate-200 dark:border-slate-800">
              <span className="text-slate-600 dark:text-slate-400">Noise Model</span>
              <strong className="font-mono text-xs text-amber-600 dark:text-amber-400">{report.noise_profile?.noise_enabled ? 'ENABLED' : 'NONE'}</strong>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3 flex items-center gap-2">
          <ChartNoAxesCombined size={14} /> Training Profile & Loss
        </h4>
        <div className="p-4 border border-dashed rounded-lg bg-white dark:bg-slate-950 flex flex-col items-center justify-center text-center text-sm muted min-h-[100px]">
          {report.limitations?.includes("Loss curve history unavailable") ? (
            <p>Loss curve history is <strong>UNAVAILABLE</strong> from local simulators for this model architecture.</p>
          ) : (
            <p>Loss curve data not present.</p>
          )}
        </div>
      </div>

      {report.warnings && report.warnings.length > 0 && (
        <div className="mt-6 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Findings & Warnings</h4>
          {report.warnings.map((w: any, idx: number) => (
            <Notice key={idx} tone={w.severity === 'BLOCKER' ? 'amber' : 'blue'}>
              <strong>{w.title}</strong> ({w.code}): {w.description}
              {w.recommendation && <div className="mt-1 opacity-90"><em>Recommendation: {w.recommendation}</em></div>}
            </Notice>
          ))}
        </div>
      )}

      <div className="mt-6 flex flex-col gap-2">
         <JsonDisclosure label="View complete configuration fingerprint & provenance" value={{
            configuration_fingerprint: report.configuration_fingerprint,
            provenance: report.provenance,
            optimizer_profile: report.optimizer_profile,
            limitations: report.limitations
         }} />
      </div>
    </div>
  );
}
