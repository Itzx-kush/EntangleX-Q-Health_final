import {AnimatePresence, motion, useReducedMotion} from 'motion/react';
import {Check, ChevronDown, CircleAlert, CircleCheck, Info, X} from 'lucide-react';
import {forwardRef, useEffect, useId, useRef, useState, type AnchorHTMLAttributes, type ButtonHTMLAttributes, type ReactNode, type RefObject} from 'react';
import {motionEasings, motionTokens} from './Motion';

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
  return <article className={`metric metric-${tone}`}><span aria-hidden="true" className="metric-header"><Icon size={16}/> {label}</span><strong>{value}</strong><small>{detail}</small></article>;
}

export function Section({children, title, description, actions, className = ''}: {children: ReactNode; title?: string; description?: string; actions?: ReactNode; className?: string}) {
  return <section className={`foundation-section ${className}`}>{title && <PanelHeader title={title} description={description} actions={actions}/>} {children}</section>;
}

export function Tabs({items, value, onChange, label = 'View options'}: {items: {value: string; label: string; disabled?: boolean}[]; value: string; onChange: (value: string) => void; label?: string}) {
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  function moveFocus(index: number) {
    const enabled = items.map((item, itemIndex) => ({item, itemIndex})).filter(({item}) => !item.disabled);
    const current = enabled.findIndex(({item}) => item.value === items[index]?.value);
    const next = enabled[(current + 1) % enabled.length] ?? enabled[0];
    if (next) tabRefs.current[next.itemIndex]?.focus();
  }
  function moveFocusBack(index: number) {
    const enabled = items.map((item, itemIndex) => ({item, itemIndex})).filter(({item}) => !item.disabled);
    const current = enabled.findIndex(({item}) => item.value === items[index]?.value);
    const next = enabled[(current - 1 + enabled.length) % enabled.length] ?? enabled[0];
    if (next) tabRefs.current[next.itemIndex]?.focus();
  }
  return <div className="foundation-tabs" role="tablist" aria-label={label}>{items.map((item, index) => <button ref={element => {tabRefs.current[index] = element;}} key={item.value} type="button" role="tab" aria-selected={value === item.value} aria-controls={`tab-panel-${item.value}`} tabIndex={value === item.value ? 0 : -1} disabled={item.disabled} className={value === item.value ? 'active' : ''} onClick={() => onChange(item.value)} onKeyDown={event => {if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {event.preventDefault(); moveFocus(index);} if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {event.preventDefault(); moveFocusBack(index);}}}>{value === item.value && <motion.span className="tab-active-indicator" layoutId={`tab-indicator-${label}`} transition={{duration: motionTokens.fast, ease: motionEasings.standard}} aria-hidden="true"/>}{item.label}</button>)}</div>;
}

function useOverlayFocus(open: boolean, onClose: () => void, containerRef: RefObject<HTMLElement | null>, closeRef: RefObject<HTMLButtonElement | null>) {
  const previousFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) {
      previousFocus.current?.focus();
      previousFocus.current = null;
      return;
    }
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const focusFirst = () => closeRef.current?.focus();
    const focusable = () => containerRef.current ? [...containerRef.current.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')] : [];
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {event.preventDefault(); onClose(); return;}
      if (event.key !== 'Tab') return;
      const elements = focusable();
      if (!elements.length) {event.preventDefault(); focusFirst(); return;}
      const first = elements[0];
      const last = elements[elements.length - 1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault(); last.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault(); first.focus();}
    };
    const focusTimer = window.setTimeout(focusFirst, 0);
    document.body.classList.add('overlay-open');
    window.addEventListener('keydown', onKeyDown);
    return () => {window.clearTimeout(focusTimer); window.removeEventListener('keydown', onKeyDown); document.body.classList.remove('overlay-open');};
  }, [open, onClose, containerRef, closeRef]);
}

export function Dialog({open, onClose, title, children}: {open: boolean; onClose: () => void; title: string; children: ReactNode}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const reduce = useReducedMotion();
  useOverlayFocus(open, onClose, panelRef, closeRef);
  return <AnimatePresence>{open && <motion.div className="dialog-layer" role="presentation" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: reduce ? 0 : motionTokens.standard, ease: motionEasings.standard}}><button className="dialog-backdrop" type="button" aria-label="Close dialog" onClick={onClose}/><motion.div ref={panelRef} className="dialog-panel" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} initial={{opacity: 0, y: reduce ? 0 : 12, scale: reduce ? 1 : .99}} animate={{opacity: 1, y: 0, scale: 1}} exit={{opacity: 0, y: reduce ? 0 : 8}} transition={{duration: reduce ? 0 : motionTokens.moderate, ease: motionEasings.emphasized}}><header><h2 id={titleId}>{title}</h2><IconButton label="Close dialog" ref={closeRef} onClick={onClose}><X size={18}/></IconButton></header>{children}</motion.div></motion.div>}</AnimatePresence>;
}

export function Drawer({open, onClose, title, children}: {open: boolean; onClose: () => void; title: string; children: ReactNode}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const titleId = useId();
  const reduce = useReducedMotion();
  useOverlayFocus(open, onClose, panelRef, closeRef);
  return <AnimatePresence>{open && <motion.div className="drawer-layer" role="presentation" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}}><button className="dialog-backdrop" type="button" aria-label="Close drawer" onClick={onClose}/><motion.aside ref={panelRef} className="drawer-panel" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} initial={{x: reduce ? 0 : '100%'}} animate={{x: 0}} exit={{x: reduce ? 0 : '100%'}} transition={{duration: reduce ? 0 : motionTokens.moderate, ease: motionEasings.emphasized}}><header><h2 id={titleId}>{title}</h2><IconButton label="Close drawer" ref={closeRef} onClick={onClose}><X size={18}/></IconButton></header>{children}</motion.aside></motion.div>}</AnimatePresence>;
}

export function Disclosure({title, children, defaultOpen = false}: {title: string; children: ReactNode; defaultOpen?: boolean}) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();
  const reduce = useReducedMotion();
  return <div className={`disclosure ${open ? 'is-open' : ''}`}><button type="button" className="disclosure-trigger" aria-expanded={open} aria-controls={contentId} onClick={() => setOpen(value => !value)}><span>{title}</span><motion.span animate={{rotate: open ? 0 : -90}} transition={{duration: reduce ? 0 : motionTokens.fast}} aria-hidden="true"><ChevronDown size={16}/></motion.span></button><AnimatePresence initial={false}>{open && <motion.div id={contentId} className="disclosure-content" role="region" initial={{opacity: 0, height: 0}} animate={{opacity: 1, height: 'auto'}} exit={{opacity: 0, height: 0}} transition={{duration: reduce ? 0 : motionTokens.moderate, ease: motionEasings.emphasized}}><div>{children}</div></motion.div>}</AnimatePresence></div>;
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
