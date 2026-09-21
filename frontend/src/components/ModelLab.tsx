import {Activity, ArrowRight, Brain, Check, FlaskConical, Gauge, Network, Orbit} from 'lucide-react';
import type {ReactNode} from 'react';
import {Link} from 'react-router-dom';
import type {Dataset, ModelRecord} from '../types';
import {environments, isNavigationItemActive, navigationItems} from '../navigation';
const modelLab = environments.find(environment => environment.id === 'model-lab');
const dataRoute = navigationItems.find(item => item.label === 'Datasets')?.path ?? '/datasets';
const quantumRoute = navigationItems.find(item => item.label === 'Quantum circuit')?.path ?? '/quantum';
export function ModelLabPage({currentPath, step, title, description, actions, children}: {currentPath: string; step: string; title: string; description: string; actions?: ReactNode; children: ReactNode}) {
  return <div className="model-lab-page"><header className="model-lab-header"><div><p className="model-lab-eyebrow"><Brain size={14} aria-hidden="true"/> MODEL LAB <span>/</span> {step}</p><h1>{title}</h1><p>{description}</p></div>{actions && <div className="model-lab-header-actions">{actions}</div>}</header><ModelLabWorkflow currentPath={currentPath}/>{children}</div>;
}
export function ModelLabWorkflow({currentPath}: {currentPath: string}) {
  return <nav className="model-lab-workflow" aria-label="Model Lab workflow"><div className="model-lab-workflow-label"><span>EXPERIMENT WORKFLOW</span><small>Navigate independently; stage presence is not completion.</small></div><ol>{modelLab?.items.map((item, index) => {const Icon = item.icon; const active = isNavigationItemActive(item.path, currentPath); return <li key={item.path} className={active ? 'active' : ''}><Link to={item.path} aria-current={active ? 'page' : undefined}><span className="model-workflow-index">{String(index + 1).padStart(2, '0')}</span><Icon size={15} aria-hidden="true"/><span>{item.label}</span></Link>{index < (modelLab?.items.length ?? 0) - 1 && <span className="model-workflow-separator" aria-hidden="true">/</span>}</li>;})}</ol><Link className="model-lab-quantum-link" to={quantumRoute}><Orbit size={14} aria-hidden="true"/> Quantum Lab <ArrowRight size={14} aria-hidden="true"/></Link></nav>;
}
export function ModelLabPanel({title, description, actions, children, className = ''}: {title: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string}) {
  return <section className={`model-lab-panel ${className}`.trim()}><header className="model-lab-panel-header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions && <div className="model-lab-panel-actions">{actions}</div>}</header>{children}</section>;
}
export function ModelLabNote({children, tone = 'neutral'}: {children: ReactNode; tone?: 'neutral' | 'warning' | 'quantum'}) {
  return <aside className={`model-lab-note model-lab-note-${tone}`}><Activity size={16} aria-hidden="true"/><div>{children}</div></aside>;
}
export function ModelLabDatasetContext({dataset, loading = false, error = ''}: {dataset?: Dataset | null; loading?: boolean; error?: string}) {
  return <div className="model-lab-context"><div className="model-lab-context-icon"><Network size={17} aria-hidden="true"/></div><div><span>DATASET CONTEXT</span><strong>{loading ? 'Loading dataset context…' : dataset?.name ?? 'No dataset selected'}</strong><small>{error ? `Dataset context unavailable: ${error}` : dataset ? `${dataset.provenance.row_count} samples · ${dataset.provenance.feature_count} input features` : 'Select a dataset before configuring an experiment.'}</small></div>{dataset && <b><Check size={13} aria-hidden="true"/> Selected</b>}</div>;
}
export function ModelLabModelContext({model, loading = false}: {model?: ModelRecord | null; loading?: boolean}) {
  return <div className="model-lab-context model-lab-model-context"><div className="model-lab-context-icon"><FlaskConical size={17} aria-hidden="true"/></div><div><span>MODEL CONTEXT</span><strong>{loading ? 'Loading model context…' : model ? model.model_type.toUpperCase() : 'No model selected'}</strong><small>{model ? `${model.status.replaceAll('_', ' ')} · experiment ${model.experiment_id.slice(0, 8)}` : 'Choose a completed model to continue.'}</small></div>{model && <b className={`model-lab-status-${model.status}`}><Gauge size={13} aria-hidden="true"/> {model.status.replaceAll('_', ' ')}</b>}</div>;
}
export function ModelLabUnavailable({title, children}: {title: string; children: ReactNode}) {
  return <div className="model-lab-unavailable"><Gauge size={18} aria-hidden="true"/><div><strong>{title}</strong><p>{children}</p></div></div>;
}
export function ModelLabResultHeader({label, children}: {label: string; children: ReactNode}) {
  return <div className="model-lab-result-header"><span>{label}</span><strong>{children}</strong></div>;
}
