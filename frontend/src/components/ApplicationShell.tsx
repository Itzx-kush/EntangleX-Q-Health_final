import {useEffect, type Dispatch, type ReactNode, type SetStateAction} from 'react';
import {useLocation} from 'react-router-dom';
import {getEnvironmentForPath, getNavigationItemForPath} from '../navigation';
import type {Health} from '../types';
import {Disclaimer, Field} from './Common';
import {EnvironmentNavigation} from './EnvironmentNavigation';

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

  useEffect(() => {
    if (!menu) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenu(false); };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [menu, setMenu]);

  return <div className="app-shell"><a className="skip-link" href="#main">Skip to workspace</a>
    <EnvironmentNavigation open={menu} onNavigate={() => setMenu(false)}/>
    {menu && <button className="navigation-scrim" type="button" aria-label="Close navigation" onClick={() => setMenu(false)}/>} 
    <div className="workspace"><header className="topbar">
      <button className="menu-button secondary" type="button" aria-expanded={menu} aria-controls="environment-navigation" aria-label={menu ? 'Close research workspace navigation' : 'Open research workspace navigation'} onClick={() => setMenu(value => !value)}>{menu ? 'Close' : 'Menu'}</button>
      <div className="workspace-context" aria-live="polite"><span className="context-kicker">{environment.name.toUpperCase()}</span><span className="divider">/</span><span>{page?.label ?? 'Page not found'}</span></div>
      <div className="connection"><span className={`connection-dot ${health.error ? 'disconnected' : ''}`} aria-hidden="true"/>{health.error ? 'Backend unavailable' : health.data ? 'Backend reachable' : 'Connecting...'}<details className="auth-menu"><summary>Connection settings</summary><div><Field label="Optional local API token" help="Stored in memory only; a page refresh clears it."><input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)}/></Field><button type="button" onClick={onApplyToken}>Apply token</button><small>{health.data?.authentication_required ? 'Backend requires a token.' : 'Local-only mode: no token is configured.'}</small></div></details></div>
    </header><main id="main"><Disclaimer/>{children}</main><footer className="workspace-footer">EntangleX Q-Health / Biomedical ML benchmark != clinical validation / No quantum advantage is presumed</footer></div>
  </div>;
}
