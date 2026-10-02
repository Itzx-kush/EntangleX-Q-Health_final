import {lazy,Suspense} from 'react';
import {Navigate,Route,Routes,useLocation} from 'react-router-dom';
import {ResearchShell} from './components/ResearchShell';
import {ThemeToggle} from './components/ThemeToggle';
import {Loading} from './components/Shared';
import {QuantumWorkbench} from './components/QuantumWorkbench';
import {VerifiedDemoLanding,VerifiedPipeline,VerifiedQuality,VerifiedQuantum} from './components/VerifiedDemoViews';
import {useVerifiedDemo} from './hooks/useVerifiedDemo';
import {AiProvider} from './contexts/AiContext';
import {AiPopup} from './components/AiPopup';

const Overview=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Overview})));
const Datasets=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Datasets})));
const Quality=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Quality})));
const PipelineStage=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.PipelineStage})));
const Training=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Training})));
const Comparison=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Comparison})));
const Robustness=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Robustness})));
const Quantum=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Quantum})));
const Explainability=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Explainability})));
const PredictionPage=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.PredictionPage})));
const Experiments=lazy(()=>import('./pages/ResearchPagesStudio').then(m=>({default:m.Experiments})));
const ExperimentDetail=lazy(()=>import('./pages/ResearchPagesStudio').then(m=>({default:m.ExperimentDetail})));
const DemoCenter=lazy(()=>import('./pages/ResearchPagesSystem').then(m=>({default:m.DemoCenter})));
const SettingsPage=lazy(()=>import('./pages/ResearchPagesSystem').then(m=>({default:m.SettingsPage})));
const AccountPage=lazy(()=>import('./pages/AccountPage').then(m=>({default:m.AccountPage})));
const ResearchHistoryPage=lazy(()=>import('./research/ResearchHistoryPage').then(m=>({default:m.ResearchHistoryPage})));
const AiAssistantPage=lazy(()=>import('./pages/AiAssistantPage').then(m=>({default:m.AiAssistantPage})));

export default function App(){
  return <AiProvider><ResearchShell>
    <ThemeToggle/>
    <AiPopup/>
    <WorkspaceRoutes/>
  </ResearchShell></AiProvider>;
}

function WorkspaceRoutes(){
  const location=useLocation();
  return <div className="workspace-route-frame" key={location.pathname}>
    <Suspense fallback={<Loading/>}><Routes location={location}>
      <Route path="/" element={<Overview/>}/>
      <Route path="/datasets" element={<DatasetsRoute/>}/>
      <Route path="/quality" element={<QualityRoute/>}/>
      <Route path="/preprocessing" element={<PreprocessingRoute/>}/>
      <Route path="/features" element={<FeaturesRoute/>}/>
      <Route path="/pca" element={<PcaRoute/>}/>
      <Route path="/training" element={<Training/>}/>
      <Route path="/comparison" element={<Comparison/>}/>
      <Route path="/robustness" element={<Robustness/>}/>
      <Route path="/quantum" element={<QuantumRoute/>}/>
      <Route path="/explainability" element={<Explainability/>}/>
      <Route path="/prediction" element={<PredictionPage/>}/>
      <Route path="/experiments" element={<Experiments/>}/>
      <Route path="/experiments/:id" element={<ExperimentDetail/>}/>
      <Route path="/demo" element={<DemoCenter/>}/>
      <Route path="/account" element={<AccountPage/>}/>
      <Route path="/my-research" element={<ResearchHistoryPage/>}/>
      <Route path="/ai" element={<AiAssistantPage/>}/>
      <Route path="/settings" element={<SettingsPage/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes></Suspense>
  </div>;
}

function DatasetsRoute(){ const demo=useVerifiedDemo(); return demo.active?<VerifiedDemoLanding current="/datasets"/>:<Datasets/>; }
function QualityRoute(){ const demo=useVerifiedDemo(); return demo.active?<VerifiedQuality/>:<Quality/>; }
function PreprocessingRoute(){ const demo=useVerifiedDemo(); return demo.active?<VerifiedPipeline stage="preprocessing"/>:<PipelineStage endpoint="/preprocessing/preview" eyebrow="03 / Prepare" title="Preprocessing" description="Configure leakage-safe transformations that are fitted within the backend research pipeline and carried into every model comparison."/>; }
function FeaturesRoute(){ const demo=useVerifiedDemo(); return demo.active?<VerifiedPipeline stage="features"/>:<PipelineStage endpoint="/feature-selection/preview" eyebrow="04 / Select" title="Feature selection" description="Inspect training-only feature selection decisions without converting benchmark association into biological causation."/>; }
function PcaRoute(){ const demo=useVerifiedDemo(); return demo.active?<VerifiedPipeline stage="pca"/>:<PipelineStage endpoint="/pca/preview" eyebrow="05 / Reduce" title="PCA / dimensions" description="Fit a compact training representation before classical and quantum learning while preserving the held-out evaluation boundary."/>; }
function QuantumRoute(){
  const demo=useVerifiedDemo();
  return demo.active?<VerifiedQuantum/>:<QuantumWorkbench/>;
}
