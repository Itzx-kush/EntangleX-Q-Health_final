import {lazy,Suspense} from 'react';
import {Navigate,Route,Routes} from 'react-router-dom';
import {ResearchShell} from './components/ResearchShell';
import {ThemeToggle} from './components/ThemeToggle';
import {Loading} from './components/Shared';
import {ErrorBoundary} from './components/ErrorBoundary';

const Overview=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Overview})));
const Datasets=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Datasets})));
const Quality=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.Quality})));
const PipelineStage=lazy(()=>import('./pages/ResearchPagesCore').then(m=>({default:m.PipelineStage})));
const Training=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Training})));
const Comparison=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Comparison})));
const Quantum=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Quantum})));
const Explainability=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.Explainability})));
const PredictionPage=lazy(()=>import('./pages/ResearchPagesModels').then(m=>({default:m.PredictionPage})));
const Experiments=lazy(()=>import('./pages/ResearchPagesStudio').then(m=>({default:m.Experiments})));
const ExperimentDetail=lazy(()=>import('./pages/ResearchPagesStudio').then(m=>({default:m.ExperimentDetail})));
const DemoCenter=lazy(()=>import('./pages/ResearchPagesSystem').then(m=>({default:m.DemoCenter})));
const SettingsPage=lazy(()=>import('./pages/ResearchPagesSystem').then(m=>({default:m.SettingsPage})));

export default function App(){
  return <ErrorBoundary><ResearchShell>
    <ThemeToggle/>
    <Suspense fallback={<Loading/>}><Routes>
      <Route path="/" element={<Overview/>}/>
      <Route path="/datasets" element={<Datasets/>}/>
      <Route path="/quality" element={<Quality/>}/>
      <Route path="/preprocessing" element={<PipelineStage endpoint="/preprocessing/preview" eyebrow="03 / Prepare" title="Preprocessing" description="Configure leakage-safe transformations that are fitted within the backend research pipeline and carried into every model comparison." />}/>
      <Route path="/features" element={<PipelineStage endpoint="/feature-selection/preview" eyebrow="04 / Select" title="Feature selection" description="Inspect training-only feature selection decisions without converting benchmark association into biological causation." />}/>
      <Route path="/pca" element={<PipelineStage endpoint="/pca/preview" eyebrow="05 / Reduce" title="PCA / dimensions" description="Fit a compact training representation before classical and quantum learning while preserving the held-out evaluation boundary." />}/>
      <Route path="/training" element={<Training/>}/>
      <Route path="/comparison" element={<Comparison/>}/>
      <Route path="/quantum" element={<Quantum/>}/>
      <Route path="/explainability" element={<Explainability/>}/>
      <Route path="/prediction" element={<PredictionPage/>}/>
      <Route path="/experiments" element={<Experiments/>}/>
      <Route path="/experiments/:id" element={<ExperimentDetail/>}/>
      <Route path="/demo" element={<DemoCenter/>}/>
      <Route path="/settings" element={<SettingsPage/>}/>
      <Route path="*" element={<Navigate to="/" replace/>}/>
    </Routes></Suspense>
  </ResearchShell></ErrorBoundary>;
}
