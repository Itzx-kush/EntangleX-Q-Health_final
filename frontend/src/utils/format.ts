export function metric(value: number | null | undefined, percent = true): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Not measured';
  return percent ? `${(value * 100).toFixed(1)}%` : value.toFixed(3);
}
export function seconds(value: number | null | undefined): string {return value === null || value === undefined ? 'Not measured' : `${value.toFixed(3)} s`;}
export function shortId(value: string) {return value.slice(0, 8);}
export function dateTime(value: string) {return new Date(/(?:Z|[+-]\\d\\d:\\d\\d)$/.test(value) ? value : `${value}Z`).toLocaleString();}
export const modelLabels = {logistic_regression: 'Logistic Regression', svm: 'SVM', random_forest: 'Random Forest', vqc: 'VQC', qsvc: 'QSVC', qnn: 'QNN', hybrid_pennylane_torch: 'PennyLane + PyTorch Hybrid'} as const;
export const isQiskitQuantumModel = (model:string|null|undefined):boolean => model==='vqc'||model==='qsvc'||model==='qnn';
export const isHybridModel = (model:string|null|undefined):boolean => model==='hybrid_pennylane_torch';
export const isQuantumFamilyModel = (model:string|null|undefined):boolean => isQiskitQuantumModel(model)||isHybridModel(model);
export const isQuantum = isQuantumFamilyModel;
export const isActive = (status: string) => ['queued', 'running', 'cancel_requested'].includes(status);
