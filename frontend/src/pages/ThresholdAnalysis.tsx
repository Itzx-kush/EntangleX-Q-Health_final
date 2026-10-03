import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Button, Select } from '../components/ui';
import { Loading, ErrorBanner, JsonDisclosure, Notice } from '../components/Shared';
import { qh } from '../lib/api';

export function ThresholdAnalysis({ model }: { model: any }) {
    const queryClient = useQueryClient();
    const [method, setMethod] = useState<string>('youden_j');
    const [targetVal, setTargetVal] = useState<string>('0.9');
    const [metricY, setMetricY] = useState<string>('f1');
    const [studyId, setStudyId] = useState<string | null>(null);
    const request = {
        model_id: model.id,
        dataset_id: model.dataset_id,
        selection_method: method,
        target_value: ["target_sensitivity", "target_specificity", "target_precision", "target_npv"].includes(method) ? parseFloat(targetVal) : null,
        selection_protocol: "dedicated_split",
        sampling_unit: "independent_samples",
    };
    const preflightQuery = useQuery({
        queryKey: ['threshold-preflight', model.id, method, targetVal],
        queryFn: () => qh.threshold_preflight(request),
    });

    const studyQuery = useQuery({
        queryKey: ['threshold_analysis', studyId],
        queryFn: () => qh.threshold_study(studyId!),
        enabled: Boolean(studyId),
        refetchInterval: (data: any) => (data?.status === 'running' || data?.status === 'created' ? 2000 : false),
    });

    const createMutation = useMutation({
        mutationFn: async () => {
            const preflight = await qh.threshold_preflight(request);
            if (!preflight.feasible) {
                throw new Error("Threshold analysis is not feasible: " + preflight.limitations.join("; "));
            }
            return await qh.create_threshold_study(request);
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
                <h3 className="font-semibold text-lg">Threshold Analysis Engine</h3>
                <div className="flex gap-2 items-center">
                    <Select value={method} onChange={(e: any) => setMethod(e.target.value)}>
                        <option value="youden_j">Youden's J</option>
                        <option value="f1_maximization">Max F1</option>
                        <option value="balanced_accuracy_maximization">Max Balanced Accuracy</option>
                        <option value="target_sensitivity">Target Sensitivity</option>
                        <option value="target_specificity">Target Specificity</option>
                    </Select>
                    {["target_sensitivity", "target_specificity", "target_precision", "target_npv"].includes(method) && (
                        <input type="number" step="0.05" min="0" max="1" value={targetVal} onChange={e => setTargetVal(e.target.value)} className="input input-sm w-20" />
                    )}
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
                    Threshold analysis is infeasible: {preflightQuery.data.limitations.join("; ")}
                </Notice>
            )}

            {studyQuery.isLoading && <Loading />}

            {s && s.status === 'failed' && (
                <ErrorBanner error={s.failure?.message || "Analysis failed"} />
            )}

            {s && s.status === 'completed' && (
                <div className="space-y-6">
                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Selected Threshold</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.threshold?.toFixed(4)}</strong>
                            {s.results?.feasible === false && <span className="text-red-500 text-xs block">INFEASIBLE</span>}
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Sensitivity</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.sensitivity?.toFixed(4)}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">Specificity</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.specificity?.toFixed(4)}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">F1 Score</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.f1?.toFixed(4)}</strong>
                        </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-4">
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">TP</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.tp}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">TN</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.tn}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">FP</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.fp}</strong>
                        </div>
                        <div className="rounded-xl border p-4 bg-background">
                            <span className="text-xs muted block">FN</span>
                            <strong className="text-lg">{s.results?.selected_operating_point?.fn}</strong>
                        </div>
                    </div>

                    {s.limitations?.length > 0 && (
                        <Notice tone="amber">
                            <strong>Limitations:</strong> {s.limitations.join("; ")}
                        </Notice>
                    )}

                    {s.results?.sweep && (
                        <div className="rounded-xl border p-4 bg-background">
                            <div className="flex justify-between items-center mb-4">
                                <h4 className="font-semibold">Threshold Sweep</h4>
                                <Select value={metricY} onChange={(e: any) => setMetricY(e.target.value)}>
                                    <option value="sensitivity">Sensitivity</option>
                                    <option value="specificity">Specificity</option>
                                    <option value="f1">F1 Score</option>
                                    <option value="precision">Precision</option>
                                    <option value="balanced_accuracy">Balanced Accuracy</option>
                                </Select>
                            </div>
                            <div className="h-64">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={s.results.sweep}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis dataKey="threshold" type="number" domain={[0, 1]} />
                                        <YAxis domain={[0, 1]} />
                                        <Tooltip />
                                        <Line type="monotone" dataKey={metricY} stroke="blue" dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    <JsonDisclosure label="Threshold Provenance & Config" value={{ configuration: s.configuration, summary: s.summary }} />
                </div>
            )}
        </div>
    );
}
