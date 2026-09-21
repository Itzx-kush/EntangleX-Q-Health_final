import {Activity, ArrowRight, Brain, Database, FlaskConical, ShieldCheck} from 'lucide-react';
import {Link} from 'react-router-dom';
import {api} from '../services/api';
import {useLoad} from '../hooks/useLoad';
import type {Experiment} from '../types';
import {Button, EmptyState, ErrorState, LoadingState, MetricCard, Section, StatusPill, Surface} from '../components/Primitives';
import {Motion} from '../components/Motion';
import {dateTime, shortId} from '../utils/format';

export default function Dashboard() {
  const {data, error} = useLoad(() => api.get<{counts: Record<string, number>; recent_experiments: Experiment[]}>('/summary'), [], 7000);
  const isLoading = !data && !error;
  return <div className="dashboard-page">
    <Motion variant="slide-up">
      <header className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <div className="dashboard-meta"><span>Biomedical research workspace</span><span className="meta-rule"/><span>Evidence before advantage</span></div>
          <h1>Build a traceable path from data to prediction.</h1>
          <p>Prepare biomedical features, compare classical and quantum models, and keep every conclusion tied to a measured experiment.</p>
          <div className="dashboard-actions">
            <Button as="a" href="/datasets" tone="primary">Begin with a dataset <ArrowRight size={16}/></Button>
            <Button as="a" href="/experiments" tone="secondary">View experiments</Button>
          </div>
        </div>
        <div className="dashboard-meta"><Activity size={15}/><span>Local research workspace</span></div>
      </header>
    </Motion>

    {error && <ErrorState>{error}</ErrorState>}
    {isLoading && <Surface className="dashboard-loading"><LoadingState>Loading workspace summary from the backend...</LoadingState></Surface>}

    <Motion variant="reveal" delay={80}>
      <div className="dashboard-metrics" aria-label="Workspace summary">
        <MetricCard label="Datasets" value={data?.counts.datasets ?? '—'} detail="Available research inputs" icon={Database}/>
        <MetricCard label="Experiments" value={data?.counts.experiments ?? '—'} detail="Recorded benchmark runs" icon={FlaskConical}/>
        <MetricCard label="Registered models" value={data?.counts.ready_models ?? '—'} detail="Ready for research use" icon={Brain} tone="quantum"/>
        <MetricCard label="Active jobs" value={data?.counts.active_jobs ?? '—'} detail="Backend-reported activity" icon={Activity}/>
      </div>
    </Motion>

    <div className="dashboard-grid">
      <Motion variant="slide-up" delay={140}>
        <Surface className="dashboard-card" as="section">
          <Section title="Recent experiments" description="The latest records returned by the research API." actions={<Link className="text-link" to="/experiments">Open log <ArrowRight size={14}/></Link>}>
            {data?.recent_experiments.length ? <div className="record-list">{data.recent_experiments.map(experiment => <Link to={`/experiments/${experiment.id}`} key={experiment.id}><div><strong>{shortId(experiment.id)}</strong><small>{dateTime(experiment.created_at)}</small></div><StatusPill value={experiment.status}/></Link>)}</div> : !isLoading && <EmptyState><FlaskConical size={22} aria-hidden="true"/><strong>No experimental results yet</strong><span>Load a benchmark and run the workflow; displayed metrics will be calculated at runtime.</span><Link className="text-link" to="/datasets">Open datasets <ArrowRight size={14}/></Link></EmptyState>}
          </Section>
        </Surface>
      </Motion>
      <Motion variant="slide-up" delay={200}>
        <Surface className="dashboard-card" as="section">
          <Section title="Research boundaries" description="Guardrails remain visible where interpretation matters.">
            <div className="research-boundary"><h3>Prediction is not diagnosis.</h3><p>Classifier scores are model outputs, not clinically validated individual risk. The benchmark demonstrates a methodology, not a screening device.</p></div>
            <div className="research-boundary quantum"><h3>Simulation is not hardware.</h3><p>VQC and QSVC run on local simulators. A favorable metric alone does not establish general quantum advantage.</p></div>
            <Link to="/comparison" className="text-link">Review model comparison <ArrowRight size={14}/></Link>
          </Section>
        </Surface>
      </Motion>
    </div>
    <div className="dashboard-footer-note"><ShieldCheck size={16}/><span>Shared partitions, training-only transformations, and visible false negatives are part of the research contract.</span></div>
  </div>;
}
