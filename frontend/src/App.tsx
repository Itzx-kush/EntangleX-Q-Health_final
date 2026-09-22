import {useState} from 'react';
import {NavLink, Route, Routes} from 'react-router-dom';
import {IntroGate} from './components/Intro';
import {PageTransition} from './components/Motion';
import {api, setSessionToken} from './services/api';
import {useLoad} from './hooks/useLoad';
import type {Health} from './types';
import {ApplicationShell} from './components/ApplicationShell';
import Dashboard from './pages/Dashboard';
import Datasets from './pages/Datasets';
import Quality from './pages/Quality';
import Preprocessing from './pages/Preprocessing';
import FeatureSelection from './pages/FeatureSelection';
import PCA from './pages/PCA';
import Training from './pages/Training';
import Comparison from './pages/Comparison';
import QuantumCircuit from './pages/QuantumCircuit';
import Explainability from './pages/Explainability';
import Prediction from './pages/Prediction';
import Experiments from './pages/Experiments';
import ExperimentDetail from './pages/ExperimentDetail';
import {ResearchWorkspaceProvider} from './hooks/ResearchWorkspace';
export default function App() {
  const health = useLoad(() => api.get<Health>('/health'), [], 15000); const [token, setToken] = useState(''); const [menu, setMenu] = useState(false);
  return <IntroGate><ResearchWorkspaceProvider><ApplicationShell health={health} token={token} setToken={setToken} menu={menu} setMenu={setMenu} onApplyToken={() => {setSessionToken(token); setToken('');}}><PageTransition><Routes><Route path="/" element={<Dashboard/>}/><Route path="/datasets" element={<Datasets/>}/><Route path="/quality" element={<Quality/>}/><Route path="/preprocessing" element={<Preprocessing/>}/><Route path="/features" element={<FeatureSelection/>}/><Route path="/pca" element={<PCA/>}/><Route path="/training" element={<Training/>}/><Route path="/comparison" element={<Comparison/>}/><Route path="/quantum" element={<QuantumCircuit/>}/><Route path="/explainability" element={<Explainability/>}/><Route path="/prediction" element={<Prediction/>}/><Route path="/experiments" element={<Experiments/>}/><Route path="/experiments/:id" element={<ExperimentDetail/>}/><Route path="*" element={<div className="empty"><h1>Page not found</h1><NavLink to="/">Return to overview</NavLink></div>}/></Routes></PageTransition></ApplicationShell></ResearchWorkspaceProvider></IntroGate>;
}
