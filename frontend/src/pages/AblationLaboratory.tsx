import { useState, useEffect } from 'react';
import type { Experiment } from '../types/qhealth';
import { qh } from '../lib/api';
import { Card, Button } from '../components/ui';
import { Notice, StatusBadge, Loading } from '../components/Shared';
import { GlareHover } from '../components/reactbits';

export function AblationLaboratory({ experiment }: { experiment: Experiment }) {
  const [studies, setStudies] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [configuring, setConfiguring] = useState(false);
  const [componentName, setComponentName] = useState<string>('preprocessing.pca');
  const [operator, setOperator] = useState<string>('DISABLE');
  const [ablationValue, setAblationValue] = useState<string>('');

  const [preflightResult, setPreflightResult] = useState<any | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchStudies = async () => {
      try {
        setLoading(true);
        const data = await qh.ablation_studies(experiment.id);
        if (active) setStudies(data);
      } catch (err: any) {
        if (active) setError(err.message || 'Failed to load ablation studies');
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchStudies();
    return () => { active = false; };
  }, [experiment.id]);

  const handlePreflight = async () => {
    try {
      setPreflightLoading(true);
      const req = {
        base_experiment_id: experiment.id,
        ablation_configs: [
          {
            component: componentName,
            operator,
            ablation_value: ablationValue || undefined
          }
        ]
      };
      const res = await qh.ablation_preflight(req);
      setPreflightResult(res);
    } catch (err: any) {
      setPreflightResult({ feasible: false, blockers: [err.message] });
    } finally {
      setPreflightLoading(false);
    }
  };

  const handleEnqueue = async () => {
    try {
      const req = {
        base_experiment_id: experiment.id,
        ablation_configs: [
          {
            component: componentName,
            operator,
            ablation_value: ablationValue || undefined
          }
        ]
      };
      await qh.create_ablation_study(req);
      setConfiguring(false);
      setPreflightResult(null);
      // Reload studies
      const data = await qh.ablation_studies(experiment.id);
      setStudies(data);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="mt-8">
      <Card title="Ablation Laboratory">
        <p className="muted mb-4">
          Determine the contribution of individual pipeline components to measured model behavior by isolating <strong>one controlled change</strong>.
        </p>

        {error && <Notice tone="amber">{error}</Notice>}

        {!configuring ? (
          <>
            <Button className="mb-6" onClick={() => setConfiguring(true)}>New Ablation Study</Button>
            {loading ? <Loading /> : studies.length === 0 ? (
              <div className="text-center py-6 muted border border-dashed rounded">No ablation studies recorded for this baseline.</div>
            ) : (
              <div className="space-y-4">
                {studies.map(study => (
                  <GlareHover key={study.id} className="border p-4 rounded-xl">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <h4 className="font-semibold flex items-center gap-2">
                          Study {study.id.slice(0, 8)}
                          <StatusBadge value={study.status} />
                        </h4>
                      </div>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4 text-sm mt-4">
                      <div>
                        <div className="metric-label">Changed</div>
                        <ul className="list-disc list-inside muted mt-1">
                          {study.changed_components.map((c: string, i: number) => <li key={i}>{c}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div className="metric-label">Held Constant</div>
                        <ul className="list-disc list-inside muted mt-1">
                          {study.held_constant.slice(0, 3).map((c: string, i: number) => <li key={i}>{c}</li>)}
                          {study.held_constant.length > 3 && <li>+ {study.held_constant.length - 3} more</li>}
                        </ul>
                      </div>
                    </div>
                  </GlareHover>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="border p-4 rounded-xl space-y-4">
            <h4 className="font-semibold border-b pb-2">Configure Ablation</h4>
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="metric-label block mb-1">Component</label>
                <select className="input w-full p-2 border rounded" value={componentName} onChange={e => setComponentName(e.target.value)}>
                  <option value="preprocessing.pca">PCA Dimensionality</option>
                  <option value="preprocessing.scaler">Scaler</option>
                  <option value="preprocessing.imputer">Imputer</option>
                  <option value="preprocessing.feature_selection">Feature Selection</option>
                  <option value="model.family">Model Family</option>
                  <option value="calibration.policy">Calibration Policy</option>
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">Operator</label>
                <select className="input w-full p-2 border rounded" value={operator} onChange={e => setOperator(e.target.value)}>
                  <option value="DISABLE">Disable / Remove</option>
                  <option value="SUBSTITUTE">Substitute</option>
                </select>
              </div>
              {operator === 'SUBSTITUTE' && (
                <div>
                  <label className="metric-label block mb-1">Value</label>
                  <input className="input w-full p-2 border rounded" value={ablationValue} onChange={e => setAblationValue(e.target.value)} placeholder="e.g. minmax, 2, svm" />
                </div>
              )}
            </div>
            
            <div className="flex gap-2">
              <Button onClick={handlePreflight} disabled={preflightLoading}>
                {preflightLoading ? 'Checking...' : 'Run Preflight Check'}
              </Button>
              <Button variant="ghost" onClick={() => { setConfiguring(false); setPreflightResult(null); }}>Cancel</Button>
            </div>

            {preflightResult && (
              <div className="mt-4 border-t pt-4">
                {preflightResult.feasible ? (
                  <Notice tone="green">
                    <strong>Preflight Passed</strong>
                    <ul className="list-disc list-inside mt-2 text-sm">
                      {preflightResult.changed_components.map((c: string, i: number) => <li key={i}>Changes: {c}</li>)}
                    </ul>
                    <div className="mt-4">
                      <Button onClick={handleEnqueue}>Execute Ablation (Enqueues {preflightResult.estimated_run_count} run)</Button>
                    </div>
                  </Notice>
                ) : (
                  <Notice tone="amber">
                    <strong>Preflight Failed</strong>
                    <ul className="list-disc list-inside mt-2 text-sm">
                      {preflightResult.blockers?.map((b: string, i: number) => <li key={i}>{b}</li>)}
                    </ul>
                  </Notice>
                )}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}
