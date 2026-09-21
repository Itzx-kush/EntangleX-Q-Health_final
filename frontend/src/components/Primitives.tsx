import {AnimatePresence, motion, useReducedMotion} from 'motion/react';
import {Check, CircleAlert, CircleCheck, Info, X} from 'lucide-react';
import {forwardRef, useEffect, useRef, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactNode} from 'react';

type Tone = 'primary' | 'secondary' | 'quiet' | 'quantum' | 'danger';

export function Button({children, tone = 'primary', size = 'md', loading = false, className = '', as, href, ...props}: (ButtonHTMLAttributes<HTMLButtonElement> | AnchorHTMLAttributes<HTMLAnchorElement>) & {tone?: Tone; size?: 'sm' | 'md' | 'lg'; loading?: boolean; as?: 'a'; href?: string}) {
  const classes = `ui-button ui-button-${tone} ui-button-${size} ${className}`.trim();
  if (as === 'a') return <a href={href} className={classes} aria-busy={loading || undefined} {...props as AnchorHTMLAttributes<HTMLAnchorElement>}>{loading && <span className="button-spinner" aria-hidden="true"/>}{children}</a>;
  return <button className={classes} aria-busy={loading || undefined} {...props as ButtonHTMLAttributes<HTMLButtonElement>}>{loading && <span className="button-spinner" aria-hidden="true"/>}{children}</button>;
}

export const IconButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & {label: string}>(function IconButton({label, children, className = '', ...props}, ref) {
  return <button ref={ref} className={`icon-button ${className}`.trim()} aria-label={label} title={label} {...props}>{children}</button>;
});

export function PanelHeader({eyebrow, title, description, actions}: {eyebrow?: string; title: string; description?: string; actions?: ReactNode}) {
  return <header className="panel-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2>{title}</h2>{description && <p>{description}</p>}</div>{actions && <div className="panel-header-actions">{actions}</div>}</header>;
}

export function MetricCard({label, value, detail, icon: Icon = Info, tone = 'research'}: {label: string; value: ReactNode; detail: string; icon?: typeof Info; tone?: 'research' | 'quantum' | 'neutral'}) {
  return <article className={`metric-card metric-card-${tone}`}><div className="metric-card-top"><span className="metric-card-icon" aria-hidden="true"><Icon size={16}/></span><span className="metric-card-label">{label}</span></div><strong>{value}</strong><small>{detail}</small></article>;
}

export function Section({children, title, description, actions, className = ''}: {children: ReactNode; title?: string; description?: string; actions?: ReactNode; className?: string}) {
  return <section className={`foundation-section ${className}`}>{title && <PanelHeader title={title} description={description} actions={actions}/>} {children}</section>;
}

export function Tabs({items, value, onChange}: {items: {value: string; label: string}[]; value: string; onChange: (value: string) => void}) {
  return <div className="foundation-tabs" role="tablist" aria-label="View options">{items.map(item => <button key={item.value} role="tab" aria-selected={value === item.value} className={value === item.value ? 'active' : ''} onClick={() => onChange(item.value)}>{item.label}</button>)}</div>;
}

export function Dialog({open, onClose, title, children}: {open: boolean; onClose: () => void; title: string; children: ReactNode}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const reduce = useReducedMotion();
  useEffect(() => { if (!open) return; closeRef.current?.focus(); const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose(); window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey); }, [open, onClose]);
  return <AnimatePresence>{open && <motion.div className="dialog-layer" role="presentation" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: reduce ? 0 : .18}}><button className="dialog-backdrop" aria-label="Close dialog" onClick={onClose}/><motion.div className="dialog-panel" role="dialog" aria-modal="true" aria-labelledby="dialog-title" initial={{opacity: 0, y: reduce ? 0 : 12, scale: reduce ? 1 : .98}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: reduce ? 0 : 8}}><header><h2 id="dialog-title">{title}</h2><IconButton label="Close dialog" ref={closeRef} onClick={onClose}><X size={18}/></IconButton></header>{children}</motion.div></motion.div>}</AnimatePresence>;
}

export function Drawer({open, onClose, title, children}: {open: boolean; onClose: () => void; title: string; children: ReactNode}) {
  const reduce = useReducedMotion();
  return <AnimatePresence>{open && <motion.div className="drawer-layer" role="presentation" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}><button className="dialog-backdrop" aria-label="Close drawer" onClick={onClose}/><motion.aside className="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawer-title" initial={{x: '100%'}} animate={{x: 0}} exit={{x: '100%'}} transition={{duration: reduce ? 0 : .24, ease: [0.22, 1, 0.36, 1]}}><header><h2 id="drawer-title">{title}</h2><IconButton label="Close drawer" onClick={onClose}><X size={18}/></IconButton></header>{children}</motion.aside></motion.div>}</AnimatePresence>;
}

export function Toast({message, tone = 'success', onDismiss}: {message: string; tone?: 'success' | 'error' | 'info'; onDismiss: () => void}) {
  const Icon = tone === 'success' ? CircleCheck : tone === 'error' ? CircleAlert : Info;
  return <div className={`toast toast-${tone}`} role={tone === 'error' ? 'alert' : 'status'}><Icon size={17} aria-hidden="true"/><span>{message}</span><IconButton label="Dismiss notification" onClick={onDismiss}><X size={16}/></IconButton></div>;
}

export function Badge({children, tone = 'neutral', className = ''}: {children: ReactNode; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'quantum' | 'research'; className?: string}) {
  return <span className={`ui-badge ui-badge-${tone} ${className}`.trim()}>{children}</span>;
}

export function Surface({children, className = '', as = 'div'}: {children: ReactNode; className?: string; as?: 'div' | 'section' | 'article'}) {
  const Component = as;
  return <Component className={`ui-surface ${className}`.trim()}>{children}</Component>;
}

export function StatusPill({value}: {value: string}) {
  const tone = ['ready', 'succeeded'].includes(value) ? 'success' : ['failed', 'partial', 'interrupted', 'cancelled'].includes(value) ? 'warning' : 'info';
  return <Badge tone={tone} className="status-transition">{value.replaceAll('_', ' ')}</Badge>;
}

export function SectionHeader({eyebrow, title, description, actions}: {eyebrow: string; title: string; description: string; actions?: ReactNode}) {
  return <div className="section-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead">{description}</p></div>{actions && <div className="header-actions">{actions}</div>}</div>;
}

export function EmptyState({children}: {children: ReactNode}) {
  return <div className="empty-state motion-state state-empty">{children}</div>;
}

export function LoadingState({children = 'Loading workspace data...'}: {children?: ReactNode}) {
  return <p className="loading-state motion-state state-loading" role="status"><span className="pulse-indicator" aria-hidden="true"/> {children}</p>;
}

export function ErrorState({children}: {children: ReactNode}) {
  return <div className="error-state motion-state state-error" role="alert">{children}</div>;
}

export function Divider({label}: {label?: string}) {
  return <div className={`ui-divider ${label ? 'ui-divider-labeled' : ''}`}>{label && <span>{label}</span>}</div>;
}

export function QuantumMark({label = 'Quantum state'}: {label?: string}) {
  return <span className="quantum-mark" role="img" aria-label={label}><i/><i/><i/></span>;
}

export function CircuitDivider() {
  return <div className="circuit-divider" aria-hidden="true"><span/><span/><span/></div>;
}

export function Tooltip({label, children}: {label: string; children: ReactNode}) {
  return <span className="ui-tooltip"><span className="ui-tooltip-trigger">{children}</span><span className="ui-tooltip-content" role="tooltip">{label}</span></span>;
}

export function SuccessState({children}: {children: ReactNode}) {
  return <div className="motion-state state-success" role="status"><span className="state-icon" aria-hidden="true"><Check size={13}/></span><span>{children}</span></div>;
}

export function RetryState({children, onRetry}: {children: ReactNode; onRetry: () => void}) {
  return <div className="motion-state state-retry" role="alert"><span>{children}</span><button className="ui-button ui-button-sm ui-button-secondary" onClick={onRetry}>Retry</button></div>;
}
