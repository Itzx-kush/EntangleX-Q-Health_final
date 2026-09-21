import type {CSSProperties, ReactNode} from 'react';
import {useLocation} from 'react-router-dom';

type MotionVariant = 'page' | 'page-exit' | 'reveal' | 'fade' | 'slide-up' | 'slide-inline';

/** A small, CSS-backed motion primitive. It never owns application state. */
export function Motion({children, variant = 'reveal', className = '', delay = 0}: {children: ReactNode; variant?: MotionVariant; className?: string; delay?: number}) {
  return <div className={`motion motion-${variant} ${className}`.trim()} style={{'--motion-delay': `${delay}ms`} as CSSProperties}>{children}</div>;
}

/** Keeps route transitions fast and subtle while preserving the existing router. */
export function PageTransition({children}: {children: ReactNode}) {
  const location = useLocation();
  return <div key={`${location.pathname}${location.search}`} className="route-transition" aria-live="polite">{children}</div>;
}
