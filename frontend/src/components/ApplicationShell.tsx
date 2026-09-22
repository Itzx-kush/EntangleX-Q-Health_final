import {useEffect, useState, type Dispatch, type ReactNode, type SetStateAction} from 'react';
import {NavLink, Routes, useLocation} from 'react-router-dom';
import {Activity, Brain, CheckCircle2, Database, FlaskConical, KeyRound, Menu, Orbit, Search, Settings2, Wifi, X} from 'lucide-react';
import {getEnvironmentForPath, getNavigationItemForPath} from '../navigation';
import type {Health} from '../types';
import {Disclaimer, Field} from './Common';
import {CommandPalette} from './CommandPalette';
import {EnvironmentNavigation} from './EnvironmentNavigation';
import {WorkspaceContext} from './WorkspaceContext';
import {useTheme, type ThemeMode} from '../hooks/useTheme';
import {WorkspaceNavigationBar, MobileWorkspaceNav} from './WorkspaceNavigationBar';
import {ContextualActionBar, ResearchContextStrip, WorkflowRail} from './ResearchWorkspaceChrome';
import {useResearchWorkspace} from '../hooks/ResearchWorkspace';

type HealthState = {data?: Health; error: string};

type ApplicationShellProps = {
  children: ReactNode;
  health: HealthState;
  token: string;
  setToken: Dispatch<SetStateAction<string>>;
  menu: boolean;
  setMenu: Dispatch<SetStateAction<boolean>>;
  onApplyToken: () => void;
};

export function ApplicationShell({children, health, token, setToken, menu, setMenu, onApplyToken}: ApplicationShellProps) {
  const {pathname} = useLocation();
  const environment = getEnvironmentForPath(pathname);
  const page = getNavigationItemForPath(pathname);
  const [collapsed, setCollapsed] = useState(true);
  const [navigationHovered, setNavigationHovered] = useState(false);
  const shellCollapsed = collapsed && !navigationHovered;
  const [commandOpen, setCommandOpen] = useState(false);
  const {theme, setTheme} = useTheme();
  const {focusMode, immersionMode} = useResearchWorkspace();

  useEffect(() => {
    if (!menu) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenu(false); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [menu, setMenu]);

  useEffect(() => {
    const openCommandPalette = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener('keydown', openCommandPalette);
    return () => window.removeEventListener('keydown', openCommandPalette);
  }, []);

  useEffect(() => { setMenu(false); }, [pathname, setMenu]);

  return <div className={`app-shell qhealth-app final-art-direction environment-${environment.id} ${shellCollapsed ? 'shell-collapsed' : ''} ${focusMode ? 'focus-mode' : ''} ${immersionMode ? 'technical-immersion' : ''}`}>
    <a className="skip-link" href="#main">Skip to workspace</a>
    <EnvironmentNavigation open={menu} onNavigate={() => setMenu(false)} collapsed={shellCollapsed} onToggleCollapsed={() => setCollapsed(value => !value)} onHoverChange={setNavigationHovered}/>
    {menu && <button className="navigation-scrim" type="button" aria-label="Close navigation" onClick={() => setMenu(false)}/>} 
    <div className="workspace"><header className="topbar global-header">
      <div className="topbar-leading"><button className="menu-button secondary" type="button" aria-expanded={menu} aria-controls="environment-navigation" aria-label={menu ? 'Close research workspace navigation' : 'Open research workspace navigation'} onClick={() => setMenu(value => !value)}>{menu ? <X size={17}/> : <Menu size={17}/>}<span className="menu-button-label">{menu ? 'Close' : 'Menu'}</span></button><div className="topbar-identity"><strong>Q-HEALTH</strong><span>RESEARCH WORKSPACE</span></div><div className="topbar-location"><span className="context-kicker">{environment.name.toUpperCase()}</span><span className="divider">/</span><strong>{page?.label ?? 'Page not found'}</strong></div></div>
      <button className="command-trigger" type="button" onClick={() => setCommandOpen(true)} aria-label="Open command palette"><Search size={15} aria-hidden="true"/><span>Search workspace</span><kbd>Ctrl/⌘ K</kbd></button>
      <div className="topbar-actions"><span className="connection-badge" role="status" aria-live="polite"><Wifi size={14} aria-hidden="true"/><span className={`connection-dot ${health.error ? 'disconnected' : ''}`} aria-hidden="true"/>{health.error ? 'Unavailable' : health.data ? 'Connected' : 'Checking'}</span><details className="auth-menu"><summary><Settings2 size={13} aria-hidden="true"/><span>Settings</span></summary><div className="settings-popover"><Field label="Appearance" help="Choose a persisted Q-Health theme."><select aria-label="Appearance theme" value={theme} onChange={event => setTheme(event.target.value as ThemeMode)}><option value="light">Q-Health Light</option><option value="dark">Q-Health Dark</option><option value="system">Use system preference</option></select></Field><Field label="Optional local API token" help="Stored in memory only; a page refresh clears it."><KeyRound size={14} aria-hidden="true"/><input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)}/></Field><button type="button" onClick={onApplyToken}>Apply token</button><small>{health.data?.authentication_required ? 'Backend requires a token.' : 'Local-only mode: no token is configured.'}</small></div></details></div>
    </header><ResearchContextStrip onOpenCommand={() => setCommandOpen(true)}/><WorkspaceNavigationBar pathname={pathname} onOpenSearch={() => setCommandOpen(true)} hideFromAccessibility/><div className="workspace-body"><main id="main"><WorkspaceContext pathname={pathname}/><WorkflowRail pathname={pathname}/><ContextualActionBar pathname={pathname}/><Disclaimer/>{children}</main><ResearchContextRail health={health}/></div><MobileWorkspaceNav pathname={pathname} hideFromAccessibility/><footer className="workspace-footer"><span>EntangleX Q-Health</span><span>Research prototype</span><span>{environment.name} / {health.error ? 'Backend unavailable' : health.data ? 'Backend connected' : 'Checking backend'}</span><span className="footer-disclaimer">Biomedical ML benchmark ≠ clinical validation · No quantum advantage is presumed</span></footer></div>
    <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)}/>
  </div>;
}

function ResearchContextRail({health}: {health: HealthState}) {
  const {dataset, experiment, job, jobs, selectedModelLabel} = useResearchWorkspace();
  const activeJobs = jobs.filter(item => ['running', 'queued'].includes(item.status));
  const backendLabel = health.error ? 'Unavailable' : health.data ? 'Connected' : 'Checking';
  return <aside className="research-context-rail" aria-label="Current research context">
    <div className="rail-card rail-context-card">
      <div className="rail-card-heading"><span className="eyebrow">CURRENT RESEARCH</span><Activity size={15} aria-hidden="true"/></div>
      <dl className="rail-facts">
        <div><dt>Dataset</dt><dd title={dataset?.name}>{dataset?.name ?? 'Not selected'}</dd></div>
        <div><dt>Model</dt><dd>{selectedModelLabel ?? experiment?.config.models?.[0] ?? 'Not selected'}</dd></div>
        <div><dt>Experiment</dt><dd>{experiment?.id ? experiment.id.slice(0, 12) : 'No active experiment'}</dd></div>
      </dl>
    </div>
    <div className="rail-card">
      <div className="rail-card-heading"><span className="eyebrow">SYSTEM STATUS</span><span className={`rail-status-dot ${health.error ? 'is-danger' : 'is-live'}`}/></div>
      <div className="rail-status-row"><span>Backend</span><strong>{backendLabel === 'Checking' ? 'Pending' : backendLabel}</strong></div>
      <div className="rail-status-row"><span>Quantum runtime</span><strong>{health.data?.quantum.available ? 'Available' : 'Not reported'}</strong></div>
      <div className="rail-status-row"><span>Execution</span><strong>{health.data?.quantum.execution ?? 'Not reported'}</strong></div>
    </div>
    <div className="rail-card">
      <div className="rail-card-heading"><span className="eyebrow">ACTIVE JOBS</span><span className="rail-count">{activeJobs.length}</span></div>
      {activeJobs.length ? <ul className="rail-job-list">{activeJobs.slice(0, 3).map(item => <li key={item.id}><span className="job-icon"><Activity size={13}/></span><span><strong>{item.status}</strong><small>{Math.round(item.progress)}% · {item.id.slice(0, 8)}</small></span></li>)}</ul> : <p className="rail-empty"><CheckCircle2 size={14}/> No queued or running jobs</p>}
    </div>
    <div className="rail-card rail-lab-card">
      <div className="rail-card-heading"><span className="eyebrow">RESEARCH LABS</span><Orbit size={15}/></div>
      <div className="rail-lab-list"><span><Database size={13}/> Data Lab</span><span><Brain size={13}/> Model Lab</span><span><FlaskConical size={13}/> Research Studio</span></div>
    </div>
  </aside>;
}
