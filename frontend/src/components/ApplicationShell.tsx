import {useEffect, useState, type Dispatch, type ReactNode, type SetStateAction} from 'react';
import {NavLink, useLocation} from 'react-router-dom';
import {ChevronDown, FlaskConical, KeyRound, Menu, Search, Settings2, Wifi} from 'lucide-react';
import {getEnvironmentForPath, getNavigationItemForPath, environments, isNavigationItemActive} from '../navigation';
import type {Health} from '../types';
import {Disclaimer, Field} from './Common';
import {CommandPalette} from './CommandPalette';
import {WorkspaceContext} from './WorkspaceContext';
import {useTheme, type ThemeMode} from '../hooks/useTheme';
import {ResearchContextStrip, WorkflowRail, ContextualActionBar} from './ResearchWorkspaceChrome';
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
  const [commandOpen, setCommandOpen] = useState(false);
  const {theme, setTheme} = useTheme();
  const {focusMode, immersionMode} = useResearchWorkspace();

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

  return (
    <div className={`app-shell qhealth-app tremor-shell environment-${environment.id} ${focusMode ? 'focus-mode' : ''} ${immersionMode ? 'technical-immersion' : ''}`}>
      <a className="skip-link" href="#main">Skip to workspace</a>
      <header className="tremor-topbar">
        <div className="tremor-topbar-inner">
          <NavLink to="/" end className="tremor-brand" aria-label="Q-Health research overview">
            <img src="/favicon.svg" alt="" />
            <span><strong>Q-HEALTH</strong><small>HYBRID RESEARCH</small></span>
          </NavLink>

          <nav className="tremor-primary-nav" aria-label="Primary research navigation">
            <NavLink to="/" end className={({isActive}) => isActive ? 'active' : ''}>Overview</NavLink>
            <TremorMenu label="Data" active={environment.id === 'data-lab'} items={environments.find(item => item.id === 'data-lab')?.items ?? []} />
            <TremorMenu label="Models" active={environment.id === 'model-lab'} items={environments.find(item => item.id === 'model-lab')?.items ?? []} />
            <NavLink to="/quantum" className={isNavigationItemActive('/quantum', pathname) ? 'active' : ''}>Quantum</NavLink>
            <NavLink to="/experiments" className={isNavigationItemActive('/experiments', pathname) ? 'active' : ''}>Experiments</NavLink>
          </nav>

          <div className="tremor-topbar-actions">
            <button className="tremor-search" type="button" onClick={() => setCommandOpen(true)} aria-label="Search workspace">
              <Search size={15} aria-hidden="true" /><span>Search</span><kbd>⌘K</kbd>
            </button>
            <span className="tremor-status" role="status" aria-live="polite">
              <Wifi size={13} aria-hidden="true" />
              <i className={health.error ? 'offline' : 'online'} />
              {health.error ? 'Offline' : health.data ? 'Connected' : 'Checking'}
            </span>
            <details className="tremor-settings">
              <summary aria-label="Open settings"><Settings2 size={16} /></summary>
              <div className="tremor-settings-popover">
                <Field label="Appearance" help="Choose a persisted Q-Health theme.">
                  <select aria-label="Appearance theme" value={theme} onChange={event => setTheme(event.target.value as ThemeMode)}>
                    <option value="light">Q-Health Light</option>
                    <option value="dark">Q-Health Dark</option>
                    <option value="system">Use system preference</option>
                  </select>
                </Field>
                <Field label="Optional local API token" help="Stored in memory only; a page refresh clears it.">
                  <KeyRound size={14} aria-hidden="true" />
                  <input type="password" autoComplete="off" value={token} onChange={event => setToken(event.target.value)} />
                </Field>
                <button type="button" className="tremor-settings-apply" onClick={onApplyToken}>Apply token</button>
                <small>{health.data?.authentication_required ? 'Backend requires a token.' : 'Local-only mode: no token is configured.'}</small>
              </div>
            </details>
            <button className="tremor-mobile-menu" type="button" onClick={() => setMenu(value => !value)} aria-expanded={menu} aria-label="Open navigation">
              <Menu size={17} />
            </button>
          </div>
        </div>

        <div className="tremor-subbar">
          <div className="tremor-breadcrumb">
            <span>{environment.name}</span><span>/</span><strong>{page?.label ?? 'Workspace'}</strong>
          </div>
          <div className="tremor-subnav">
            <span className="tremor-subnav-label">RESEARCH WORKFLOW</span>
            <WorkflowRail pathname={pathname} />
          </div>
        </div>
      </header>

      {menu && <MobileNavigation onClose={() => setMenu(false)} pathname={pathname} />}

      <ResearchContextStrip onOpenCommand={() => setCommandOpen(true)} />
      <ContextualActionBar pathname={pathname} />

      <div className="tremor-workspace">
        <main id="main" className="tremor-main">
          <WorkspaceContext pathname={pathname} />
          <Disclaimer />
          {children}
        </main>
      </div>

      <footer className="tremor-footer">
        <div><strong>EntangleX Q-Health</strong><span>Research prototype</span></div>
        <span>{environment.name} / {health.error ? 'Backend unavailable' : health.data ? 'Backend connected' : 'Checking backend'}</span>
        <span>Biomedical ML benchmark ≠ clinical validation · No quantum advantage is presumed</span>
      </footer>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  );
}

function TremorMenu({label, active, items}: {label: string; active: boolean; items: {path: string; label: string}[]}) {
  return (
    <details className={active ? 'tremor-menu active' : 'tremor-menu'}>
      <summary>{label}<ChevronDown size={13} /></summary>
      <div className="tremor-menu-popover">
        {items.map(item => <NavLink key={item.path} to={item.path}>{item.label}</NavLink>)}
      </div>
    </details>
  );
}

function MobileNavigation({onClose, pathname}: {onClose: () => void; pathname: string}) {
  return (
    <nav className="tremor-mobile-panel" aria-label="Mobile research navigation">
      <div className="tremor-mobile-panel-header"><strong>Q-HEALTH</strong><button type="button" onClick={onClose}>Close</button></div>
      {environments.map(environment => (
        <section key={environment.id}>
          <span>{environment.name}</span>
          <div>{environment.items.map(item => (
            <NavLink key={item.path} to={item.path} className={isNavigationItemActive(item.path, pathname) ? 'active' : ''} onClick={onClose}>{item.label}</NavLink>
          ))}</div>
        </section>
      ))}
    </nav>
  );
}
