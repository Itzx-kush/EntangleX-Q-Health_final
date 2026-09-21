import {NavLink, useLocation} from 'react-router-dom';
import {environments, isNavigationItemActive} from '../navigation';

export function EnvironmentNavigation({open, onNavigate}: {open: boolean; onNavigate: () => void}) {
  const {pathname} = useLocation();
  return <aside id="environment-navigation" className={`sidebar environment-sidebar ${open ? 'open' : ''}`} aria-label="Research workspace navigation">
    <NavLink to="/" end className="brand" onClick={onNavigate}><img src="/favicon.svg" alt=""/><div><strong>ENTANGLEX</strong><span>Q-HEALTH</span></div></NavLink>
    <p className="sidebar-label">RESEARCH ENVIRONMENTS</p>
    <nav aria-label="Research environments" className="environment-list">
      {environments.map(environment => {
        const active = environment.items.some(item => isNavigationItemActive(item.path, pathname));
        return <section key={environment.id} className={`environment-group ${active ? 'active' : ''}`} aria-label={`${environment.name} environment`} data-active={active ? 'true' : 'false'}>
          <div className="environment-heading"><span className="environment-name">{environment.name}</span><span className="environment-context">{environment.context}</span></div>
          <p className="environment-description">{environment.description}</p>
          <div className="environment-items">{environment.items.map(item => <NavLink end={item.path === '/'} to={item.path} key={item.path} onClick={onNavigate}><span className="nav-index">{item.number}</span><span>{item.label}</span></NavLink>)}</div>
        </section>;
      })}
    </nav>
    <div className="sidebar-foot"><span className="pill">RESEARCH PROTOTYPE</span><p>Scientific validity wins.<br/>Measured results lead.</p><small>Local simulation / v0.1.0</small></div>
  </aside>;
}
