import type {ButtonHTMLAttributes, ReactNode} from 'react';

type Tone = 'primary' | 'secondary' | 'quiet' | 'quantum' | 'danger';

export function Button({children, tone = 'primary', size = 'md', className = '', ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {tone?: Tone; size?: 'sm' | 'md' | 'lg'}) {
  return <button className={`ui-button ui-button-${tone} ui-button-${size} ${className}`.trim()} {...props}>{children}</button>;
}

export function IconButton({label, children, className = '', ...props}: ButtonHTMLAttributes<HTMLButtonElement> & {label: string}) {
  return <button className={`icon-button ${className}`.trim()} aria-label={label} title={label} {...props}>{children}</button>;
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
  return <Badge tone={tone}>{value.replaceAll('_', ' ')}</Badge>;
}

export function SectionHeader({eyebrow, title, description, actions}: {eyebrow: string; title: string; description: string; actions?: ReactNode}) {
  return <div className="section-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="lead">{description}</p></div>{actions && <div className="header-actions">{actions}</div>}</div>;
}

export function EmptyState({children}: {children: ReactNode}) {
  return <div className="empty-state">{children}</div>;
}

export function LoadingState({children = 'Loading workspace data...'}: {children?: ReactNode}) {
  return <p className="loading-state" role="status"><span className="pulse-indicator" aria-hidden="true"/> {children}</p>;
}

export function ErrorState({children}: {children: ReactNode}) {
  return <div className="error-state" role="alert">{children}</div>;
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