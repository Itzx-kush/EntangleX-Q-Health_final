import {forwardRef, type HTMLAttributes, type ReactNode} from 'react';

type TremorCardProps = HTMLAttributes<HTMLDivElement> & {
  as?: 'div' | 'section' | 'article';
  decoration?: 'top' | 'left' | 'none';
  decorationTone?: 'research' | 'quantum' | 'data' | 'model';
};

export function TremorCard({
  children,
  className = '',
  as = 'div',
  decoration = 'none',
  decorationTone = 'research',
  ...props
}: TremorCardProps) {
  const Component = as;
  return (
    <Component
      className={`tremor-card tremor-decoration-${decoration} tremor-decoration-${decorationTone} ${className}`.trim()}
      {...props}
    >
      {children}
    </Component>
  );
}

export function TremorMetric({
  label,
  value,
  detail,
  icon,
  tone = 'research',
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  icon?: ReactNode;
  tone?: 'research' | 'quantum' | 'neutral';
}) {
  return (
    <TremorCard as="article" decoration="top" decorationTone={tone === 'quantum' ? 'quantum' : 'research'} className={`tremor-metric tremor-metric-${tone}`}>
      <div className="tremor-metric-label">{icon}<span>{label}</span></div>
      <div className="tremor-metric-value">{value}</div>
      {detail !== undefined && <div className="tremor-metric-detail">{detail}</div>}
    </TremorCard>
  );
}

export function TremorBadge({
  children,
  variant = 'neutral',
  className = '',
}: {
  children: ReactNode;
  variant?: 'default' | 'neutral' | 'success' | 'error' | 'warning' | 'info' | 'quantum' | 'research';
  className?: string;
}) {
  return <span className={`tremor-badge tremor-badge-${variant} ${className}`.trim()}>{children}</span>;
}

export function TremorProgress({value, max = 100, tone = 'research'}: {value: number; max?: number; tone?: 'research' | 'quantum'}) {
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`tremor-progress tremor-progress-${tone}`} role="progressbar" aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
      <span style={{width: `${percent}%`}} />
    </div>
  );
}

export const TremorSectionHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(function TremorSectionHeader(
  {className = '', ...props},
  ref,
) {
  return <div ref={ref} className={`tremor-section-header ${className}`.trim()} {...props} />;
});
