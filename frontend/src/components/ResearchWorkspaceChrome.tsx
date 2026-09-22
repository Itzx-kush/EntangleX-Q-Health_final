import {ArrowRight, Circle, Command, Focus, Maximize2, Minimize2, Play, X} from 'lucide-react';
import {Link, useNavigate} from 'react-router-dom';
import {useResearchWorkspace} from '../hooks/ResearchWorkspace';
import {modelLabels, shortId} from '../utils/format';

const stages: Array<{id: string; label: string; path: string}> = [
  {id: 'data', label: 'Data', path: '/datasets'}, {id: 'quality', label: 'Quality', path: '/quality'},
  {id: 'preprocess', label: 'Preprocess', path: '/preprocessing'}, {id: 'features', label: 'Features', path: '/features'},
  {id: 'pca', label: 'PCA', path: '/pca'}, {id: 'train', label: 'Train', path: '/training'},
  {id: 'evaluate', label: 'Evaluate', path: '/comparison'}, {id: 'explain', label: 'Explain', path: '/explainability'},
  {id: 'predict', label: 'Predict', path: '/prediction'}, {id: 'experiment', label: 'Experiment', path: '/experiments'},
];

function statusLabel(value?: string) { return value ? value.replaceAll('_', ' ').toUpperCase() : undefined; }

export function ResearchContextStrip({onOpenCommand}: {onOpenCommand: () => void}) {
  const {dataset, experiment, job, selectedModelLabel, stage, focusMode, setFocusMode, immersionMode, setImmersionMode} = useResearchWorkspace();
  return <div className="research-context-strip" aria-label="Current research context">
    <div className="research-context-primary">
      <span className="research-context-title">CURRENT RESEARCH CONTEXT</span>
      <span><b>Dataset</b> {dataset?.name ?? 'Not selected'}</span>
      <span><b>Model</b> {experiment?.config.models?.[0] ? modelLabels[experiment.config.models[0]] : selectedModelLabel ? modelLabels[selectedModelLabel as keyof typeof modelLabels] : 'Not selected'}</span>
      <span><b>Experiment</b> {experiment ? shortId(experiment.id) : 'Not selected'}</span>
      {job && <span className="research-job-chip"><span className="status-dot" aria-hidden="true"/><b>Job</b> {statusLabel(job.status)}</span>}
    </div>
    <div className="research-context-actions">
      <button className="context-command-trigger" type="button" onClick={onOpenCommand}><Command size={13} aria-hidden="true"/> Commands <kbd>⌘K</kbd></button>
      <button className="context-icon-button" type="button" aria-pressed={focusMode} aria-label={focusMode ? 'Exit focus mode' : 'Enter focus mode'} title={focusMode ? 'Exit focus mode' : 'Enter focus mode'} onClick={() => setFocusMode(!focusMode)}>{focusMode ? <Minimize2 size={14}/> : <Focus size={14}/>}</button>
      <button className="context-icon-button" type="button" aria-pressed={immersionMode} aria-label={immersionMode ? 'Exit technical immersion mode' : 'Enter technical immersion mode'} title={immersionMode ? 'Exit technical immersion mode' : 'Enter technical immersion mode'} onClick={() => setImmersionMode(!immersionMode)}><Maximize2 size={14}/></button>
    </div>
  </div>;
}

export function WorkflowRail({pathname}: {pathname: string}) {
  const {stage, dataset, experiment} = useResearchWorkspace();
  const activeIndex = Math.max(0, stages.findIndex(item => item.id === stage));
  return <nav className="workflow-rail" aria-label="Research workflow progress">
    <span className="workflow-label">WORKFLOW</span>
    {stages.map((item, index) => {
      const current = item.id === stage;
      const viewed = index < activeIndex && Boolean(dataset || experiment);
      return <Link key={item.id} to={item.path} className={`workflow-step ${current ? 'current' : ''} ${viewed ? 'viewed' : ''}`} aria-current={current ? 'step' : undefined} title={`Open ${item.label}`}>
        <span className="workflow-marker">{current ? <Circle size={8} fill="currentColor"/> : <span/>}</span><span>{item.label}</span>
      </Link>;
    })}
  </nav>;
}

export function ContextualActionBar({pathname}: {pathname: string}) {
  const navigate = useNavigate();
  const {dataset, experiment, job, stage} = useResearchWorkspace();
  const links: Array<{label: string; path: string; icon?: React.ReactNode}> = [];
  if (dataset && stage !== 'train') links.push({label: 'Configure preprocessing', path: '/preprocessing', icon: <ArrowRight size={13}/>});
  if (dataset && stage !== 'train') links.push({label: 'Open training', path: '/training', icon: <Play size={13}/>});
  if (experiment) {
    if (stage !== 'evaluate') links.push({label: 'Compare results', path: '/comparison', icon: <ArrowRight size={13}/>});
    if (stage !== 'explain') links.push({label: 'Explain model', path: '/explainability', icon: <ArrowRight size={13}/>});
    if (stage !== 'predict') links.push({label: 'Research prediction', path: '/prediction', icon: <ArrowRight size={13}/>});
    if (stage !== 'experiment') links.push({label: 'Open experiment', path: `/experiments/${experiment.id}`, icon: <ArrowRight size={13}/>});
  }
  if (!links.length && !job) return null;
  return <div className="contextual-action-bar" aria-label="Contextual actions">
    <div><span className="action-bar-kicker">NEXT BEST ACTION</span><strong>{job && ['running', 'queued'].includes(job.status) ? 'Training is in progress.' : dataset ? 'Continue the research workflow.' : 'Select a dataset to begin.'}</strong></div>
    <div className="action-bar-actions">{links.slice(0, 3).map(link => <button key={link.path} className="secondary" onClick={() => navigate(link.path)}>{link.icon}{link.label}</button>)}{pathname !== '/' && <Link className="context-dismiss" to={pathname} aria-label="Current context preserved"><X size={13}/></Link>}</div>
  </div>;
}