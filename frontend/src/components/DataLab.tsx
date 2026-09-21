import {ArrowRight, Beaker, Check, Database, FlaskConical, Gauge, Microscope, Orbit, Settings2} from 'lucide-react';
import type {ReactNode} from 'react';
import {Link} from 'react-router-dom';
import type {Dataset} from '../types';
import {environments, isNavigationItemActive, navigationItems} from '../navigation';

const dataLab = environments.find(environment => environment.id === 'data-lab');
const modelRoute = navigationItems.find(item => item.label === 'Training')?.path ?? '/training';

export function DataLabPage({currentPath, step, title, description, actions, children}: {currentPath: string; step: string; title: string; description: string; actions?: ReactNode; children: ReactNode}) {
  return <div className="data-lab-page"><header className="data-lab-header"><div><p className="data-lab-eyebrow"><Database size={14} aria-hidden="true"/> DATA LAB <span>/</span> {step}</p><h1>{title}</h1><p>{description}</p></div>{actions && <div className="data-lab-header-actions">{actions}</div>}</header><DataLabWorkflow currentPath={currentPath}/>{children}</div>;
}

export function DataLabWorkflow({currentPath}: {currentPath: string}) {
  return <nav className="data-lab-workflow" aria-label="Data Lab workflow"><div className="data-lab-workflow-label"><span>PREPARATION WORKFLOW</span><small>Navigate independently; route presence is not completion.</small></div><ol>{dataLab?.items.map((item, index) => {const Icon = item.icon; const active = isNavigationItemActive(item.path, currentPath); return <li key={item.path} className={active ? 'active' : ''}><Link to={item.path} aria-current={active ? 'page' : undefined}><span className="workflow-index">{item.number}</span><Icon size={15} aria-hidden="true"/><span>{item.label}</span></Link>{index < (dataLab?.items.length ?? 0) - 1 && <span className="workflow-separator" aria-hidden="true">/</span>}</li>;})}</ol><Link className="data-lab-model-link" to={modelRoute}>Continue to Model Lab <ArrowRight size={14} aria-hidden="true"/></Link></nav>;
}

export function DataLabPanel({title, description, actions, children, className = ''}: {title: string; description?: string; actions?: ReactNode; children: ReactNode; className?: string}) {
  return <section className={`data-lab-panel ${className}`.trim()}><header className="data-lab-panel-header"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{actions && <div className="data-lab-panel-actions">{actions}</div>}</header>{children}</section>;
}

export function DataLabNote({children, tone = 'neutral'}: {children: ReactNode; tone?: 'neutral' | 'warning' | 'research'}) {
  return <aside className={`data-lab-note data-lab-note-${tone}`}><Beaker size={16} aria-hidden="true"/><div>{children}</div></aside>;
}

export function DataLabDatasetContext({dataset, loading = false, error = ''}: {dataset?: Dataset | null; loading?: boolean; error?: string}) {
  return <div className="data-lab-dataset-context"><div className="data-lab-context-icon"><Database size={17} aria-hidden="true"/></div><div className="data-lab-context-copy"><span>ACTIVE DATASET CONTEXT</span><strong>{loading ? 'Loading dataset context…' : dataset?.name ?? 'No dataset selected'}</strong><small>{error ? `Dataset context unavailable: ${error}` : dataset ? `${dataset.provenance.row_count} samples · ${dataset.provenance.feature_count} input features · ${dataset.provenance.domain}` : 'Select a dataset to inspect and prepare biomedical inputs.'}</small></div>{dataset && <span className="data-lab-context-state"><Check size={13} aria-hidden="true"/> Selected</span>}</div>;
}

export function DataLabUnavailable({title, children}: {title: string; children: ReactNode}) {
  return <div className="data-lab-unavailable"><Gauge size={18} aria-hidden="true"/><div><strong>{title}</strong><p>{children}</p></div></div>;
}

export function DataLabResultHeader({label, children}: {label: string; children: ReactNode}) {
  return <div className="data-lab-result-header"><span>{label}</span><strong>{children}</strong></div>;
}

export function DataLabFeatureIcon({kind}: {kind: 'selection' | 'pca' | 'preprocessing' | 'quality'}) {
  const Icon = kind === 'selection' ? Microscope : kind === 'pca' ? Orbit : kind === 'preprocessing' ? Settings2 : FlaskConical;
  return <span className={`data-lab-feature-icon data-lab-feature-icon-${kind}`}><Icon size={17} aria-hidden="true"/></span>;
}
