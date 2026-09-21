import {useEffect, useState, type Dispatch, type ReactNode, type SetStateAction} from 'react';
import {useLocation} from 'react-router-dom';
import {KeyRound, Menu, Search, Settings2, Wifi, X} from 'lucide-react';
import {getEnvironmentForPath, getNavigationItemForPath} from '../navigation';
import type {Health} from '../types';
import {Disclaimer, Field} from './Common';
import {CommandPalette} from './CommandPalette';
import {EnvironmentNavigation} from './EnvironmentNavigation';
import {WorkspaceContext} from './WorkspaceContext';
import {useTheme, type ThemeMode} from '../hooks/useTheme';
import {MobileWorkspaceNav, WorkspaceNavigationBar} from './WorkspaceNavigationBar';

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
  const [collapsed, setCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const {theme, setTheme} = useTheme();

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

  return <div className={`app-shell qhealth-app final-art-direction environment-${environment.id} ${collapsed ? 'shell-collapsed' : ''}`}>
    <MobileWorkspaceNav pathname={pathname}/><a className="skip-link" href="#main">Skip to workspace</a>
    <EnvironmentNavigation open={menu} onNavigate={() => setMenu(false)} collapsed={collapsed} onToggleCollapsed={() => setCollapsed(value => !value)}/>
    {menu && <button className="navigation-scrim" type="button" aria-label="Close navigation" onClick={() => setMenu(false)}/>} 
    <div className="workspace"><header className="topbar global-header">
      <div className="topbar-leading"><button className="menu-button secondary" type="button" aria-expanded={menu} aria-controls="environment-navigation" aria-label={menu ? 'Close research workspace navigation' : 'Open research workspace navigation'} onClick={() => setMenu(value => !value)}>{menu ? <X size={17}/> : <Menu size={17}/>}<span className="menu-button-label">{menu ? 'Close' : 'Menu'}</span></button><div className="topbar-identity"><strong>Q-HEALTH</strong><span>RESEARCH WORKSPACE</span></div><div className="topbar-location"><span className="context-kicker">{environment.name.toUpperCase()}</span><span className="divider">/</span><span>{page?.label ?? 'Page not found'}</span></div></div>
      <button className="command-trigger" type="button" onClick={() => setCommandOpen(true)} aria-label="Open command palette"><Search size={15} aria-hidden="true"/><span>Search workspace</span><kbd>Ctrl/⌘ K</kbd></button>
      <div className="topbar-actions"><span className="connection-badge" role="status" aria-live="polite"><Wifi size={14} aria-hidden="true"/><span className={`connection-dot ${health.error ? 'disconnected' : ''}`} aria-hidden="true"/>{health.error ? 'Unavailable' : health.data ? 'Connected' : 'Checking'}</span><details className="auth-menu"><summary><Settings2 size={13} aria-hidden="true"/><span>Settings</span></summary><div className="settings-popover"><Field label="Appearance" help="Choose a persisted Q-Health theme."><select aria-label="Appearance theme" value={theme} onChange={event => setTheme(event.target.value as ThemeMode)}><option value="light">Q-Health Light</option><option value="dark">Q-Health Dark</option><option value="system">Use system preference</option></select></Field><Field label="Optional local API token" help="Stored in memory only; a page refresh clears it."><KeyRound size={14} aria-hidden="true"/><input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)}/></Field><button type="button" onClick={onApplyToken}>Apply token</button><small>{health.data?.authentication_required ? 'Backend requires a token.' : 'Local-only mode: no token is configured.'}</small></div></details></div>
    </header><WorkspaceNavigationBar pathname={pathname} onOpenSearch={() => setCommandOpen(true)}/><main id="main"><WorkspaceContext pathname={pathname}/><Disclaimer/>{children}</main><footer className="workspace-footer"><span>EntangleX Q-Health</span><span>Research prototype</span><span>{environment.name} / {health.error ? 'Backend unavailable' : health.data ? 'Backend connected' : 'Checking backend'}</span><span className="footer-disclaimer">Biomedical ML benchmark ≠ clinical validation · No quantum advantage is presumed</span></footer></div>
    <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)}/>
  </div>;
}
