import {useState} from 'react';
import {NavLink, Route, Routes} from 'react-router-dom';
import {api, setSessionToken} from './services/api';
import {useLoad} from './hooks/useLoad';
import type {Health} from './types';
import {Disclaimer, Field} from './components/Common';
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
const navigation = [
  ['/', 'Overview', '01'], ['/datasets', 'Datasets', '02'], ['/quality', 'Data quality', '03'], ['/preprocessing', 'Preprocessing', '04'], ['/features', 'Feature selection', '05'], ['/pca', 'PCA / dimensions', '06'], ['/training', 'Training', '07'], ['/comparison', 'Model comparison', '08'], ['/quantum', 'Quantum circuit', '09'], ['/explainability', 'Explainability', '10'], ['/prediction', 'Research prediction', '11'], ['/experiments', 'Experiments', '12'],
];
export default function App() {
  const health = useLoad(() => api.get<Health>('/health'), [], 15000); const [token, setToken] = useState(''); const [menu, setMenu] = useState(false);
  return <div className="app-shell"><a className="skip-link" href="#main">Skip to workspace</a><aside className={`sidebar ${menu ? 'open' : ''}`}><NavLink to="/" className="brand"><img src="/favicon.svg" alt=""/><div><strong>ENTANGLEX</strong><span>Q-HEALTH</span></div></NavLink><p className="sidebar-label">RESEARCH WORKSPACE</p><nav aria-label="Workspace navigation">{navigation.map(([to, label, number]) => <NavLink end={to === '/'} to={to} key={to} onClick={() => setMenu(false)}><span className="nav-index">{number}</span>{label}</NavLink>)}</nav><div className="sidebar-foot"><span className="pill">RESEARCH PROTOTYPE</span><p>Scientific validity wins.<br/>Measured results lead.</p><small>Local simulation / v0.1.0</small></div></aside>
    <div className="workspace"><header className="topbar"><button className="menu-button secondary" aria-expanded={menu} onClick={() => setMenu(!menu)}>Menu</button><span>Biomedical intelligence <span className="divider">/</span> Experiment workspace</span><div className="connection"><span className={`connection-dot ${health.error ? 'disconnected' : ''}`}/>{health.error ? 'Backend unavailable' : health.data ? 'Backend reachable' : 'Connecting...'}<details className="auth-menu"><summary>Connection settings</summary><div><Field label="Optional local API token" help="Stored in memory only; a page refresh clears it."><input type="password" autoComplete="off" value={token} onChange={e => setToken(e.target.value)}/></Field><button onClick={() => {setSessionToken(token); setToken('');}}>Apply token</button><small>{health.data?.authentication_required ? 'Backend requires a token.' : 'Local-only mode: no token is configured.'}</small></div></details></div></header><main id="main"><Disclaimer/><Routes><Route path="/" element={<Dashboard/>}/><Route path="/datasets" element={<Datasets/>}/><Route path="/quality" element={<Quality/>}/><Route path="/preprocessing" element={<Preprocessing/>}/><Route path="/features" element={<FeatureSelection/>}/><Route path="/pca" element={<PCA/>}/><Route path="/training" element={<Training/>}/><Route path="/comparison" element={<Comparison/>}/><Route path="/quantum" element={<QuantumCircuit/>}/><Route path="/explainability" element={<Explainability/>}/><Route path="/prediction" element={<Prediction/>}/><Route path="/experiments" element={<Experiments/>}/><Route path="/experiments/:id" element={<ExperimentDetail/>}/><Route path="*" element={<div className="empty"><h1>Page not found</h1><NavLink to="/">Return to overview</NavLink></div>}/></Routes></main><footer className="workspace-footer">EntangleX Q-Health / Biomedical ML benchmark != clinical validation / No quantum advantage is presumed</footer></div></div>;
}
