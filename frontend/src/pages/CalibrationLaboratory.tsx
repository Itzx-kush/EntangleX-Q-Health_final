import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button, Select } from '../components/ui';
import { Loading, ErrorBanner, JsonDisclosure, Notice } from '../components/Shared';
import { qh } from '../lib/api';

export function CalibrationLaboratory({ model }: { model: any }) {
    const queryClient = useQueryClient();
    const [method, setMethod] = useState<'none' | 'sigmoid' | 'isotonic' | 'temperature_scaling'>('none');
    const [studyId, setStudyId] = useState<string | null>(null);
    const request = {
        model_id: model.id,
        dataset_id: model.dataset_id,
        calibration_method: method,
        calibration_protocol: "dedicated_split",
        sampling_unit: "independent_samples",
        split_seed: 42,
        test_size: 0.2,
        calibration_size: 0.2,
        cv_folds: 3,
        bins: 10
    };
    const preflightQuery = useQuery({
        queryKey: ['calibration-preflight', model.id, method],
        queryFn: () => qh.calibration_preflight(request),
    });

    // Fetch the calibration study if we have an ID
    const studyQuery = useQuery({
        queryKey: ['calibration', studyId],
        queryFn: () => qh.calibration_study(studyId!),
        enabled: Boolean(studyId),
        refetchInterval: (data: any) => (data?.status === 'running' || data?.status === 'created' ? 2000 : false),
    });

    // Mutation to start preflight and create
    const createMutation = useMutation({
        mutationFn: async () => {
            const preflight = await qh.calibration_preflight(request);
            if (!preflight.feasible) {
                throw new Error("Calibration is not feasible: " + preflight.limitations.join("; "));
            }
            return await qh.create_calibration_study(request);
        },
        onSuccess: (data) => {
            setStudyId(data.id);
        }
    });

    const s = studyQuery.data;
    useEffect(() => {
        if (s?.status === 'completed') {
            queryClient.invalidateQueries({queryKey: ['model-card', model.id]});
        }
    }, [s?.status, queryClient, model.id]);

    return (
        <div className="mt-4 rounded-xl border p-4 bg-muted/5">
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-semibold text-lg">Calibration Laboratory</h3>
                <div className="flex gap-2">
                    <Select value={method} onChange={(e: any) => setMethod(e.target.value)}>
                        <option value="none" disabled={preflightQuery.data?.method_support?.none === false}>Uncalibrated Baseline</option>
                        <option value="sigmoid" disabled={preflightQuery.data?.method_support?.sigmoid === false}>Sigmoid (Platt)</option>
                        <option value="isotonic" disabled={preflightQuery.data?.method_support?.isotonic === false}>Isotonic Regression</option>
                        <option value="temperature_scaling" disabled={preflightQuery.data?.method_support?.temperature_scaling === false}>Temperature Scaling</option>
                    </Select>
                    <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || preflightQuery.isLoading || preflightQuery.data?.feasible === false}>
                        Evaluate
                    </Button>
                </div>
            </div>

            {createMutation.error && (
                <ErrorBanner error={(createMutation.error as Error).message} />
            )}
            {preflightQuery.error && <ErrorBanner error={(preflightQuery.error as Error).message} />}
            {preflightQuery.data?.feasible === false && (
                <Notice tone="amber">
                    Calibration is not applicable or feasible: {preflightQuery.data.limitations.join("; ")}
                </Notice>
            )}

            {studyQuery.isLoading && <Loading />}

            {s && s.status === 'failed' && (
                <ErrorBanner error={s.failure?.message || "Calibration failed"} />
            )}

            {s && s.status === 'completed' && (
                <div className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Brier Score</span>
                            <strong className="text-lg">{s.metrics?.brier_score?.toFixed(4)}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Log Loss</span>
                            <strong className="text-lg">{s.metrics?.log_loss?.toFixed(4)}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Expected Calibration Error</span>
                            <strong className="text-lg">{s.metrics?.expected_calibration_error?.toFixed(4)}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Max Calibration Error</span>
                            <strong className="text-lg">{s.metrics?.maximum_calibration_error?.toFixed(4)}</strong>
                        </div>
                    </div>

                    {s.limitations?.length > 0 && (
                        <Notice tone="amber">
                            <strong>Limitations:</strong> {s.limitations.join("; ")}
                        </Notice>
                    )}

                    {s.curves?.reliability_curve && (
                        <div className="rounded-xl border p-4 bg-background">
                            <h4 className="font-semibold mb-4">Reliability Curve</h4>
                            <div className="h-64">
                                
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart
                                        data={s.curves.reliability_curve.map((d: any) => ({
                                            bin: `${d.lower_bound.toFixed(2)}-${d.upper_bound.toFixed(2)}`,
                                            "Predicted": d.mean_predicted_probability,
                                            "Observed": d.observed_positive_rate,
                                            "Ideal": (d.lower_bound + d.upper_bound) / 2
                                        }))}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="bin" />
                                        <YAxis />
                                        <Tooltip />
                                        <Line type="monotone" dataKey="Predicted" stroke="blue" />
                                        <Line type="monotone" dataKey="Observed" stroke="green" />
                                        <Line type="monotone" dataKey="Ideal" stroke="gray" strokeDasharray="5 5" />
                                    </LineChart>
                                </ResponsiveContainer>

                            </div>
                        </div>
                    )}

                    <JsonDisclosure label="Calibration Provenance" value={s} />
                </div>
            )}
        </div>
    );
}
