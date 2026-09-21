import {ChevronRight, House, Search} from 'lucide-react';
import type {LucideIcon} from 'lucide-react';
import {Link} from 'react-router-dom';
import {environments, isNavigationItemActive} from '../navigation';

type WorkspaceNavigationBarProps = {
  pathname: string;
  onOpenSearch: () => void;
  hideFromAccessibility?: boolean;
};

const quickLinks = [
  {label: 'Overview', path: '/', tone: 'research'},
  {label: 'Data', path: '/datasets', tone: 'data'},
  {label: 'Models', path: '/training', tone: 'model'},
  {label: 'Quantum', path: '/quantum', tone: 'quantum'},
  {label: 'Experiments', path: '/experiments', tone: 'studio'},
] as const;

export function WorkspaceNavigationBar({pathname, onOpenSearch, hideFromAccessibility = false}: WorkspaceNavigationBarProps) {
  return <nav className="workspace-navigation-bar" aria-label="Quick workspace navigation" aria-hidden={hideFromAccessibility || undefined}>
    <div className="workspace-nav-scroller">
      <Link className={isNavigationItemActive('/', pathname) ? 'workspace-nav-chip active' : 'workspace-nav-chip'} to="/" aria-label="Research overview">
        <House size={13} aria-hidden="true"/>
        <span>Overview</span>
      </Link>
      {quickLinks.slice(1).map(link => <Link key={link.path} to={link.path} className={isNavigationItemActive(link.path, pathname) ? `workspace-nav-chip tone-${link.tone} active` : `workspace-nav-chip tone-${link.tone}`}>
        <span className="workspace-nav-dot" aria-hidden="true"/>
        <span>{link.label}</span>
      </Link>)}
      <span className="workspace-nav-divider" aria-hidden="true"/>
      <Link className="workspace-nav-context" to={environments.find(env => env.items.some(item => isNavigationItemActive(item.path, pathname)))?.items[0]?.path ?? '/'}>Current workspace <ChevronRight size={12} aria-hidden="true"/></Link>
      <button className="workspace-nav-search" type="button" onClick={onOpenSearch}>
        <Search size={13} aria-hidden="true"/>
        <span>Search</span>
        <kbd>Ctrl K</kbd>
      </button>
    </div>
  </nav>;
}

type MobileWorkspaceNavProps = {
  pathname: string;
  hideFromAccessibility?: boolean;
};

export function MobileWorkspaceNav({pathname, hideFromAccessibility = false}: MobileWorkspaceNavProps) {
  return <nav className="mobile-workspace-nav" aria-label="Primary mobile navigation" aria-hidden={hideFromAccessibility || undefined}>
    {quickLinks.map(link => {
      const Icon: LucideIcon = link.label === 'Overview' ? House : link.label === 'Data' ? environments.find(env => env.id === 'data-lab')!.icon : link.label === 'Models' ? environments.find(env => env.id === 'model-lab')!.icon : link.label === 'Quantum' ? environments.find(env => env.id === 'quantum-lab')!.icon : environments.find(env => env.id === 'research-studio')!.icon;
      const active = isNavigationItemActive(link.path, pathname);
      return <Link key={link.path} to={link.path} className={active ? `mobile-workspace-nav-item active tone-${link.tone}` : `mobile-workspace-nav-item tone-${link.tone}`} aria-current={active ? 'page' : undefined}>
        <Icon size={18} strokeWidth={active ? 2.3 : 1.8} aria-hidden="true"/>
        <span>{link.label}</span>
      </Link>;
    })}
  </nav>;
}
