import {useEffect, type ReactNode} from 'react';
import {Link} from 'react-router-dom';
import {api} from '../services/api';
import {useLoad} from '../hooks/useLoad';
import {useDraft} from '../hooks/ExperimentDraft';
import type {Dataset, ModelRecord, Metrics, MetricName} from '../types';
import {metric, modelLabels, shortId} from '../utils/format';
export const disclaimer = 'Research Prototype: This platform provides model-generated disease-risk predictions for research and decision-support purposes. Predictions are based on benchmark or user-provided datasets and are not a substitute for professional medical diagnosis, treatment, or clinical validation.';
export function Disclaimer() {return <aside className="disclaimer" role="note"><span className="disclaimer-mark" aria-hidden="true">i</span><p>{disclaimer}</p></aside>;}
export function PageHeader({eyebrow, title, description, children}: {eyebrow: string; title: string; description: string; children?: ReactNode}) {return <header className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead">{description}</p></div><div className="header-actions">{children}</div></header>;}
export function Card({title, children, className = ''}: {title?: string; children: ReactNode; className?: string}) {return <section className={`card ${className}`}>{title && <h2>{title}</h2>}{children}</section>;}
export function ErrorNotice({message}: {message?: string}) {return message ? <div className="notice error" role="alert">{message}</div> : null;}
export function Note({children}: {children: ReactNode}) {return <div className="notice">{children}</div>;}
export function Empty({children}: {children: ReactNode}) {return <div className="empty">{children}</div>;}
export function Loading() {return <p className="loading" role="status">Loading workspace data...</p>;}
export function Status({value}: {value: string}) {return <span className={`status status-${value}`}>{value.replaceAll('_', ' ')}</span>;}
export function JsonView({value, label = 'Configuration and provenance'}: {value: unknown; label?: string}) {return <details className="json-view"><summary>{label}</summary><pre>{JSON.stringify(value, null, 2)}</pre></details>;}
export function Field({label, help, children}: {label: string; help?: string; children: ReactNode}) {return <label className="field"><span>{label}</span>{children}{help && <small>{help}</small>}</label>;}
export function DatasetPicker() {
  const {draft, update} = useDraft(); const {data, error} = useLoad(() => api.get<Dataset[]>('/datasets'));
  return <div className="dataset-picker"><Field label="Active research dataset"><select value={draft.dataset_id} onChange={e => update({dataset_id: e.target.value, features: null})}><option value="">Select a dataset</option>{data?.map(d => <option key={d.id} value={d.id}>{d.name} ({d.provenance.row_count} samples)</option>)}</select></Field><Link className="text-link" to="/datasets">Manage datasets</Link><ErrorNotice message={error}/></div>;
}
export function useActiveDataset() {const {draft} = useDraft(); return useLoad<Dataset | null>(() => draft.dataset_id ? api.get(`/datasets/${draft.dataset_id}`) : Promise.resolve(null), [draft.dataset_id]);}
export function ModelPicker({value, onChange, quantumOnly = false}: {value: string; onChange: (id: string) => void; quantumOnly?: boolean}) {
  const {data, error} = useLoad(() => api.get<ModelRecord[]>('/models'));
  const available = data?.filter(m => m.status === 'ready' && (!quantumOnly || ['vqc', 'qsvc'].includes(m.model_type)));
  useEffect(() => {if (!value && available?.length) onChange(available[0].id);}, [data, value, quantumOnly]);
  return <><Field label="Registered model"><select value={value} onChange={e => onChange(e.target.value)}><option value="">Choose a completed model</option>{available?.map(m => <option value={m.id} key={m.id}>{modelLabels[m.model_type]} / {shortId(m.id)} / experiment {shortId(m.experiment_id)}</option>)}</select></Field><ErrorNotice message={error}/>{available?.length === 0 && <Empty>No completed models. <Link to="/training">Run an experiment first.</Link></Empty>}</>;
}
export const metricDefinitions: Record<MetricName, string> = {
  sensitivity: 'Ability to correctly identify positive cases: TP / (TP + FN).', specificity: 'Ability to correctly identify negative cases: TN / (TN + FP).',
  accuracy: 'Fraction of samples assigned the correct class.', precision: 'Fraction of predicted positives that are observed positives.', recall: 'Recall of the configured positive class; identical to sensitivity.', f1: 'Harmonic mean of positive-class precision and recall.', roc_auc: 'Discrimination across decision thresholds, not calibration.',
};
export function MetricGrid({metrics}: {metrics: Metrics}) {
  const names: MetricName[] = ['sensitivity', 'specificity', 'roc_auc', 'f1', 'accuracy', 'precision', 'recall'];
  return <div className="metric-grid">{names.map(name => <div className={`metric ${name === 'sensitivity' ? 'primary-metric' : ''}`} key={name}><span>{name.replace('_', '-').toUpperCase()}</span><strong>{metric(metrics[name], name !== 'roc_auc')}</strong><small>{metricDefinitions[name]}</small></div>)}</div>;
}
export function ConfusionMatrix({metrics}: {metrics: Metrics}) {return <div className="confusion"><table><caption>Observed class (rows) vs predicted class (columns)</caption><thead><tr><th scope="col">Observed / predicted</th><th scope="col">Negative</th><th scope="col">Positive</th></tr></thead><tbody><tr><th scope="row">Negative</th><td>TN <strong>{metrics.true_negative}</strong></td><td>FP <strong>{metrics.false_positive}</strong></td></tr><tr><th scope="row">Positive</th><td className="false-negative">FN <strong>{metrics.false_negative}</strong></td><td>TP <strong>{metrics.true_positive}</strong></td></tr></tbody></table><p><b>False negative:</b> actually positive, predicted negative. <b>False positive:</b> actually negative, predicted positive. These are benchmark errors, not demonstrated clinical outcomes.</p></div>;}
