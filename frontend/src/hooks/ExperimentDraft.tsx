import {createContext, useContext, useEffect, useState, type ReactNode} from 'react';
import type {TrainingConfig, PipelineConfig, QuantumConfig} from '../types';
export const defaultDraft: TrainingConfig = {
  dataset_id: '', features: null, models: ['logistic_regression', 'svm', 'random_forest'],
  pipeline: {imputer: 'median', scaler: 'standard', outlier_strategy: 'none', lower_quantile: 0.01, upper_quantile: 0.99, log_features: [], ratios: [], selection: 'anova', k_features: 12, variance_threshold: 0, pca_components: 4, pca_whiten: false, angle_scaling: true},
  quantum: {backend: 'statevector', qubits: 4, feature_map_reps: 1, ansatz_reps: 1, entanglement: 'linear', optimizer: 'COBYLA', maxiter: 30, shots: 1024, noise_probability: 0},
  parameters: {logistic_c: 1, svm_c: 1, svm_kernel: 'rbf', forest_trees: 100, forest_max_depth: null, class_weight: null},
  seed: 42, test_size: 0.2, cv_folds: 3, max_samples: 160, duplicate_policy: 'reject', probability_threshold: 0.5, calibration: 'none', calibration_folds: 3,
};
interface DraftContext {draft: TrainingConfig; update: (patch: Partial<TrainingConfig>) => void; pipeline: (patch: Partial<PipelineConfig>) => void; quantum: (patch: Partial<QuantumConfig>) => void; reset: () => void;}
const Context = createContext<DraftContext | null>(null);
export function DraftProvider({children}: {children: ReactNode}) {
  const [draft, setDraft] = useState<TrainingConfig>(() => {
    try {const stored = localStorage.getItem('qhealth-config-v1'); if (stored) {const value = JSON.parse(stored) as Partial<TrainingConfig>; return {...defaultDraft, ...value, pipeline: {...defaultDraft.pipeline, ...value.pipeline}, quantum: {...defaultDraft.quantum, ...value.quantum}, parameters: {...defaultDraft.parameters, ...value.parameters}};}} catch { /* Fall back to a clean configuration. */ }
    return defaultDraft;
  });
  useEffect(() => {try {localStorage.setItem('qhealth-config-v1', JSON.stringify(draft));} catch { /* Browser persistence may be disabled. */ }}, [draft]);
  return <Context.Provider value={{draft, update: patch => setDraft(d => ({...d, ...patch})), pipeline: patch => setDraft(d => ({...d, pipeline: {...d.pipeline, ...patch}})), quantum: patch => setDraft(d => ({...d, quantum: {...d.quantum, ...patch}})), reset: () => setDraft(defaultDraft)}}>{children}</Context.Provider>;
}
export function useDraft() {const value = useContext(Context); if (!value) throw new Error('DraftProvider is required.'); return value;}
