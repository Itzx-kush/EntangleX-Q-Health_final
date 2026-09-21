import {Activity, ArrowRight, Beaker, Brain, CheckCircle2, Database, FlaskConical, GitCompareArrows, Orbit, ShieldCheck} from 'lucide-react';
import {Link} from 'react-router-dom';
import type {Experiment} from '../types';
import {environments, navigationItems} from '../navigation';
import {dateTime, shortId} from '../utils/format';
import {EmptyState, MetricCard, StatusPill} from './Primitives';
import {Motion} from './Motion';

export type ResearchSummary = {counts: {datasets?: number; experiments?: number; ready_models?: number; active_jobs?: number}; recent_experiments: Experiment[]; disclaimer?: string};

type RouteTarget = {path: string; label: string; description: string};
function pageTarget(label: string): RouteTarget { const item = navigationItems.find(candidate => candidate.label === label); return {path: item?.path ?? '/', label: item?.label ?? label, description: item?.description ?? ''}; }
function environmentTarget(id: string): RouteTarget { const environment = environments.find(candidate => candidate.id === id); const item = environment?.items[0]; return {path: item?.path ?? '/', label: environment?.name ?? id, description: environment?.description ?? ''}; }

const pipelineStages = [
  {number: '01', label: 'Data', description: 'Ingest and inspect biomedical inputs.', target: pageTarget('Datasets'), tone: 'data'},
  {number: '02', label: 'Prepare', description: 'Apply reproducible quality and preprocessing steps.', target: pageTarget('Preprocessing'), tone: 'prepare'},
  {number: '03', label: 'Model', description: 'Train classical and hybrid approaches.', target: pageTarget('Training'), tone: 'model'},
  {number: '04', label: 'Evaluate', description: 'Compare measured results under shared conditions.', target: pageTarget('Model comparison'), tone: 'evaluate'},
  {number: '05', label: 'Research', description: 'Organize experiments and interpret evidence.', target: pageTarget('Experiments'), tone: 'research'},
] as const;

export function ResearchHero() {
  const data = pageTarget('Datasets');
  const studio = environmentTarget('research-studio');
  return <Motion variant="slide-up"><header className="research-hero">
    <div className="research-hero-copy"><p className="research-eyebrow"><Activity size={14} aria-hidden="true"/> Research workspace <span> / </span> Q-Health</p><h1>A traceable path through biomedical intelligence and controlled experimentation.</h1><p className="research-hero-lead">An experimental workspace for preparing biomedical data, evaluating classical and quantum approaches, and organizing reproducible research workflows.</p><div className="research-hero-actions"><Link className="ui-button ui-button-primary ui-button-md" to={data.path}>Begin with data <ArrowRight size={16}/></Link><Link className="ui-button ui-button-secondary ui-button-md" to={studio.path}>Open Research Studio</Link></div><div className="research-hero-note"><ShieldCheck size={15} aria-hidden="true"/><span>Measured results lead. Uncomputed values remain absent.</span></div></div>
    <ResearchFlowGraphic/>
  </header></Motion>;
}

function ResearchFlowGraphic() {
  const nodes = [
    {label: 'DATA', icon: Database, target: pageTarget('Datasets'), tone: 'data'},
    {label: 'MODEL', icon: Brain, target: pageTarget('Training'), tone: 'model'},
    {label: 'QUANTUM', icon: Orbit, target: pageTarget('Quantum circuit'), tone: 'quantum'},
    {label: 'EVALUATE', icon: GitCompareArrows, target: pageTarget('Model comparison'), tone: 'evaluate'},
  ] as const;
  return <div className="research-flow-graphic" role="img" aria-label="Q-Health research pathway from data to model to quantum experimentation to evaluation"><div className="flow-graphic-label">RESEARCH PATHWAY</div><div className="flow-node-list">{nodes.map((node, index) => {const Icon = node.icon; return <div className="flow-node-wrap" key={node.label}><Link className={`flow-node flow-node-${node.tone}`} to={node.target.path}><span className="flow-node-icon"><Icon size={17} aria-hidden="true"/></span><span><strong>{node.label}</strong><small>{node.target.label}</small></span></Link>{index < nodes.length - 1 && <span className="flow-connector" aria-hidden="true"><ArrowRight size={15}/></span>}</div>;})}</div><div className="flow-graphic-footer"><span>CLASSICAL BASELINES</span><span>+</span><span>QUANTUM MODELS</span><span className="flow-footer-arrow">→</span><span>CONTROLLED COMPARISON</span></div></div>;
}

export function ResearchBrief() {
  return <section className="research-brief"><div className="research-section-kicker"><span>CONTEXT</span><span className="section-kicker-line"/></div><div><h2>A workspace for evidence before advantage.</h2><p>Q-Health connects dataset preparation, model training, quantum experimentation, and research tracking in one controlled environment. Classical baselines and quantum models are evaluated under the same research workflow; the application does not presume which approach will be better.</p></div><div className="research-brief-aside"><Beaker size={19} aria-hidden="true"/><span>Research prototype<br/><small>Biomedical ML / local simulation</small></span></div></section>;
}

export function ResearchSnapshot({summary, loading}: {summary?: ResearchSummary; loading: boolean}) {
  const counts = summary?.counts;
  const value = (key: keyof NonNullable<ResearchSummary['counts']>) => { const result = counts?.[key]; return typeof result === 'number' ? result : 'Unavailable'; };
  return <section className="research-snapshot" aria-labelledby="research-snapshot-title"><div className="research-section-heading"><div><p className="research-eyebrow plain">CURRENT RESEARCH STATE</p><h2 id="research-snapshot-title">Workspace snapshot</h2><p>Values shown here are returned by the application summary endpoint.</p></div><span className="snapshot-source"><Activity size={13} aria-hidden="true"/> Backend summary</span></div><div className="research-snapshot-grid"><MetricCard label="Datasets" value={loading ? '—' : value('datasets')} detail={loading ? 'Loading summary' : 'Available research inputs'} icon={Database}/><MetricCard label="Experiments" value={loading ? '—' : value('experiments')} detail={loading ? 'Loading summary' : 'Recorded benchmark runs'} icon={FlaskConical}/><MetricCard label="Ready models" value={loading ? '—' : value('ready_models')} detail={loading ? 'Loading summary' : 'Backend-reported model records'} icon={Brain} tone="quantum"/><MetricCard label="Active jobs" value={loading ? '—' : value('active_jobs')} detail={loading ? 'Loading summary' : 'Queued or running jobs'} icon={Activity}/></div></section>;
}

export function ResearchPipeline() {
  return <section className="research-pipeline" aria-labelledby="research-pipeline-title"><div className="research-section-heading"><div><p className="research-eyebrow plain">HOW THE WORKSPACE CONNECTS</p><h2 id="research-pipeline-title">A measured path from data to research output.</h2><p>Each stage is a real workspace entry point. A route being available does not imply that its computation has completed.</p></div><span className="pipeline-mark" aria-hidden="true"><span/><span/><span/></span></div><ol className="research-pipeline-list">{pipelineStages.map((stage, index) => <li className={`pipeline-stage pipeline-stage-${stage.tone}`} key={stage.number}><Link to={stage.target.path}><span className="pipeline-stage-number">{stage.number}</span><span className="pipeline-stage-body"><strong>{stage.label}</strong><span>{stage.description}</span><em>Open {stage.target.label} <ArrowRight size={13} aria-hidden="true"/></em></span></Link>{index < pipelineStages.length - 1 && <span className="pipeline-arrow" aria-hidden="true">→</span>}</li>)}</ol></section>;
}

export function ResearchCapabilities() {
  const capabilities = environments.filter(environment => environment.id !== 'research');
  return <section className="research-capabilities" aria-labelledby="research-capabilities-title"><div className="research-section-heading"><div><p className="research-eyebrow plain">RESEARCH ENVIRONMENTS</p><h2 id="research-capabilities-title">Choose the next workspace.</h2><p>Move from the overview into the part of the research workflow you want to inspect or run.</p></div></div><div className="research-capability-grid">{capabilities.map(environment => {const Icon = environment.icon; const target = environment.items[0]; return <article className={`research-capability capability-${environment.id}`} key={environment.id}><div className="capability-icon"><Icon size={19} aria-hidden="true"/></div><div className="capability-copy"><p>{environment.context}</p><h3>{environment.name}</h3><span>{environment.description}</span></div><Link to={target.path} aria-label={`Open ${environment.name}`}><ArrowRight size={16} aria-hidden="true"/></Link></article>;})}</div></section>;
}

export function ClassicalQuantumPanel() {
  const model = environmentTarget('model-lab'); const quantum = environmentTarget('quantum-lab');
  return <section className="classical-quantum-panel" aria-labelledby="classical-quantum-title"><div className="cq-copy"><p className="research-eyebrow plain">CONTROLLED COMPARISON</p><h2 id="classical-quantum-title">Classical baselines and quantum models share the same research question.</h2><p>Q-Health provides a place to configure, measure, and compare both approaches. Interpretations remain tied to the measured benchmark and its limitations.</p><div className="cq-actions"><Link className="text-link" to={model.path}>Explore Model Lab <ArrowRight size={14}/></Link><Link className="text-link quantum-link" to={quantum.path}>Enter Quantum Lab <Orbit size={14}/></Link></div></div><div className="cq-equation" aria-label="Classical baselines plus quantum models lead to controlled comparison and measured evaluation"><span>CLASSICAL<br/><small>BASELINES</small></span><b>+</b><span className="cq-quantum">QUANTUM<br/><small>MODELS</small></span><b>→</b><span>MEASURED<br/><small>EVALUATION</small></span></div></section>;
}

export function RecentResearchActivity({summary, loading}: {summary?: ResearchSummary; loading: boolean}) {
  const experiments = summary?.recent_experiments ?? [];
  return <section className="research-activity" aria-labelledby="research-activity-title"><div className="research-section-heading"><div><p className="research-eyebrow plain">RESEARCH STUDIO</p><h2 id="research-activity-title">Recent activity</h2><p>Only experiments returned by the backend are shown.</p></div><Link className="text-link" to={environmentTarget('research-studio').path}>Open experiment log <ArrowRight size={14}/></Link></div>{loading ? <div className="activity-skeleton" aria-label="Loading recent research activity"><span/><span/><span/></div> : experiments.length ? <div className="research-activity-list">{experiments.map(experiment => <Link to={`/experiments/${experiment.id}`} key={experiment.id}><span className="activity-icon"><FlaskConical size={15} aria-hidden="true"/></span><span className="activity-copy"><strong>{shortId(experiment.id)}</strong><small>{dateTime(experiment.created_at)} · Dataset {shortId(experiment.dataset_id)}</small></span><StatusPill value={experiment.status}/><ArrowRight size={14} aria-hidden="true"/></Link>)}</div> : <EmptyState><FlaskConical size={21} aria-hidden="true"/><strong>No research activity available</strong><span>Completed or in-progress experiments will appear here when the backend returns them.</span><Link className="text-link" to={pageTarget('Datasets').path}>Open Data Lab <ArrowRight size={14}/></Link></EmptyState>}</section>;
}

export function ResearchFooterNote() {
  return <div className="research-footer-note"><CheckCircle2 size={16} aria-hidden="true"/><span>Research boundary: model-generated outputs support investigation and decision support; they are not clinical diagnosis or validation.</span></div>;
}
