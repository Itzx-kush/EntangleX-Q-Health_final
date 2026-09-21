import {Button, ErrorState} from '../components/Primitives';
import {Motion} from '../components/Motion';
import {ResearchBrief, ResearchCapabilities, ResearchHero, ResearchPipeline, ResearchSnapshot, ClassicalQuantumPanel, RecentResearchActivity, ResearchFooterNote, type ResearchSummary} from '../components/ResearchOverview';
import {api} from '../services/api';
import {useLoad} from '../hooks/useLoad';

export default function Dashboard() {
  const {data, error, loading, reload} = useLoad<ResearchSummary>(() => api.get('/summary'), [], 7000);
  return <div className="research-overview">
    <ResearchHero/>
    <Motion variant="reveal" delay={70}><ResearchBrief/></Motion>
    {error && <Motion variant="fade"><ErrorState><div className="research-error-content"><span>Research summary unavailable: {error}</span><Button tone="secondary" size="sm" onClick={reload}>Retry summary</Button></div></ErrorState></Motion>}
    <Motion variant="reveal" delay={100}><ResearchSnapshot summary={data} loading={loading}/></Motion>
    <Motion variant="slide-up" delay={140}><ResearchPipeline/></Motion>
    <Motion variant="slide-up" delay={180}><ResearchCapabilities/></Motion>
    <Motion variant="slide-up" delay={220}><ClassicalQuantumPanel/></Motion>
    <Motion variant="slide-up" delay={260}><RecentResearchActivity summary={data} loading={loading}/></Motion>
    <ResearchFooterNote/>
  </div>;
}
