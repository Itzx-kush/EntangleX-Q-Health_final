import {ChevronDown, PanelLeftClose, PanelLeftOpen} from 'lucide-react';
import {AnimatePresence, motion, useReducedMotion} from 'motion/react';
import {useEffect, useRef, useState} from 'react';
import {NavLink, useLocation} from 'react-router-dom';
import {environments, isNavigationItemActive, type EnvironmentId} from '../navigation';
import {motionEasings, motionTokens} from './Motion';

export function EnvironmentNavigation({open, onNavigate, collapsed, onToggleCollapsed}: {open: boolean; onNavigate: () => void; collapsed: boolean; onToggleCollapsed: () => void}) {
  const {pathname} = useLocation();
  const navRef = useRef<HTMLElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  const reduce = useReducedMotion();
  const [expanded, setExpanded] = useState<Record<EnvironmentId, boolean>>(() => Object.fromEntries(environments.map(environment => [environment.id, true])) as Record<EnvironmentId, boolean>);

  useEffect(() => {
    const activeId = environments.find(environment => environment.items.some(item => isNavigationItemActive(item.path, pathname)))?.id;
    if (activeId) setExpanded(value => value[activeId] ? value : {...value, [activeId]: true});
  }, [pathname]);

  useEffect(() => {
    if (!open) { previousFocus.current?.focus(); previousFocus.current = null; return; }
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    window.setTimeout(() => navRef.current?.querySelector<HTMLElement>('a,button')?.focus(), 0);
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); onNavigate(); return; }
      if (event.key !== 'Tab' || !navRef.current) return;
      const focusable = [...navRef.current.querySelectorAll<HTMLElement>('a,button')].filter(element => !element.hasAttribute('disabled'));
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onNavigate]);

  return <aside ref={navRef} id="environment-navigation" className={`sidebar environment-sidebar ${open ? 'open' : ''} ${collapsed ? 'sidebar-collapsed' : ''}`} aria-label="Research workspace navigation" aria-modal={open || undefined}>
    <div className="rail-header"><NavLink to="/" end className="brand" onClick={onNavigate} title="Return to Research overview"><img src="/favicon.svg" alt=""/><div className="brand-copy"><strong>Q-HEALTH</strong><span>HYBRID RESEARCH</span></div></NavLink><button className="rail-collapse-button" type="button" onClick={onToggleCollapsed} aria-label={collapsed ? 'Expand environment navigation' : 'Collapse environment navigation'} title={collapsed ? 'Expand navigation' : 'Collapse navigation'}>{collapsed ? <PanelLeftOpen size={16}/> : <PanelLeftClose size={16}/>}</button></div>
    <p className="sidebar-label">RESEARCH ENVIRONMENTS</p>
    <nav aria-label="Research environments" className="environment-list">
      {environments.map(environment => {
        const active = environment.items.some(item => isNavigationItemActive(item.path, pathname));
        const EnvironmentIcon = environment.icon;
        const isExpanded = collapsed || expanded[environment.id];
        return <section key={environment.id} className={`environment-group ${active ? 'active' : ''}`} aria-label={`${environment.name} environment`} data-active={active ? 'true' : 'false'}>
          <button className="environment-heading" type="button" aria-expanded={collapsed ? undefined : isExpanded} onClick={() => !collapsed && setExpanded(value => ({...value, [environment.id]: !value[environment.id]}))} title={collapsed ? environment.name : undefined}><EnvironmentIcon className="environment-icon" size={15} aria-hidden="true"/><span className="environment-heading-copy"><span className="environment-name">{environment.name}</span><span className="environment-context">{environment.context}</span></span><ChevronDown className="environment-chevron" size={14} aria-hidden="true"/></button>
          <p className="environment-description">{environment.description}</p>
        <AnimatePresence initial={false}>{isExpanded && <motion.div className="environment-items" initial={{opacity: 0, height: reduce ? 'auto' : 0}} animate={{opacity: 1, height: 'auto'}} exit={{opacity: 0, height: reduce ? 'auto' : 0}} transition={{duration: reduce ? 0 : motionTokens.standard, ease: motionEasings.emphasized}}>{environment.items.map(item => {const ItemIcon = item.icon; return <NavLink end={item.path === '/'} to={item.path} key={item.path} onClick={onNavigate} title={collapsed ? item.label : undefined} aria-label={`${item.number} ${item.label}`} aria-current={isNavigationItemActive(item.path, pathname) ? 'page' : undefined} className={({isActive}) => isActive ? 'active' : undefined}>{({isActive}) => <><ItemIcon className="nav-icon" size={15} aria-hidden="true"/><span className="nav-index">{item.number}</span><span className="nav-text">{item.label}</span>{isActive && <motion.span className="nav-active-indicator" layoutId="active-nav-indicator" transition={{duration: reduce ? 0 : motionTokens.fast, ease: motionEasings.emphasized}} aria-hidden="true"/>}</>}</NavLink>;})}</motion.div>}</AnimatePresence>
        </section>;
      })}
    </nav>
    <div className="sidebar-foot"><span className="pill">RESEARCH PROTOTYPE</span><p>Scientific validity wins.<br/>Measured results lead.</p><small>Local simulation / v0.1.0</small></div>
  </aside>;
}
