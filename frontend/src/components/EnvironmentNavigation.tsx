import {NavLink, useLocation} from 'react-router-dom';
import {Activity, BarChart3, Brain, Database, FlaskConical, Gauge, Microscope, Orbit, Settings2} from 'lucide-react';
import {environments, isNavigationItemActive} from '../navigation';

const icons = {Overview: Activity, Datasets: Database, 'Data quality': Gauge, Preprocessing: Settings2, 'Feature selection': Microscope, 'PCA / dimensions': BarChart3, Training: Brain, 'Model comparison': BarChart3, Explainability: Microscope, 'Research prediction': Activity, 'Quantum circuit': Orbit, Experiments: FlaskConical} as const;

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
          <div className="environment-items">{environment.items.map(item => {const Icon = icons[item.label as keyof typeof icons] ?? Activity; return <NavLink end={item.path === '/'} to={item.path} key={item.path} onClick={onNavigate}><Icon className="nav-icon" size={15} aria-hidden="true"/><span className="nav-index">{item.number}</span><span>{item.label}</span></NavLink>;})}</div>
        </section>;
      })}
    </nav>
    <div className="sidebar-foot"><span className="pill">RESEARCH PROTOTYPE</span><p>Scientific validity wins.<br/>Measured results lead.</p><small>Local simulation / v0.1.0</small></div>
  </aside>;
}
