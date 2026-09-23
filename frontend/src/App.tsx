import {Navigate,Route,Routes} from 'react-router-dom';
import {ResearchShell} from './components/ResearchShell';
import {Overview,Datasets,Quality,PipelineStage} from './pages/ResearchPagesCore';
import {Training,Comparison,Quantum,Explainability,PredictionPage} from './pages/ResearchPagesModels';
import {Experiments,ExperimentDetail} from './pages/ResearchPagesStudio';
import {DemoCenter,SettingsPage} from './pages/ResearchPagesSystem';

export default function App(){
  return <ResearchShell>
    <Routes>
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
    </Routes>
  </ResearchShell>;
}
