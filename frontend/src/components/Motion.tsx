import {motion, useReducedMotion} from 'motion/react';
import type {CSSProperties, ReactNode} from 'react';
import {useLocation} from 'react-router-dom';

type MotionVariant = 'page' | 'page-exit' | 'reveal' | 'fade' | 'slide-up' | 'slide-inline';

/** A small, CSS-backed motion primitive. It never owns application state. */
export function Motion({children, variant = 'reveal', className = '', delay = 0}: {children: ReactNode; variant?: MotionVariant; className?: string; delay?: number}) {
  const reduce = useReducedMotion();
  const variants = {
    page: {initial: {opacity: 0, y: reduce ? 0 : 10}, animate: {opacity: 1, y: 0}},
    'page-exit': {initial: {opacity: 1}, animate: {opacity: 0}},
    reveal: {initial: {opacity: 0, y: reduce ? 0 : 14}, animate: {opacity: 1, y: 0}},
    fade: {initial: {opacity: 0}, animate: {opacity: 1}},
    'slide-up': {initial: {opacity: 0, y: reduce ? 0 : 18}, animate: {opacity: 1, y: 0}},
    'slide-inline': {initial: {opacity: 0, x: reduce ? 0 : 12}, animate: {opacity: 1, x: 0}},
  }[variant];
  return <motion.div className={`motion motion-${variant} ${className}`.trim()} style={{'--motion-delay': `${delay}ms`} as CSSProperties} initial={variants.initial} animate={variants.animate} transition={{duration: reduce ? 0 : .38, delay: reduce ? 0 : delay / 1000, ease: [0.22, 1, 0.36, 1]}}>{children}</motion.div>;
}

/** Keeps route transitions fast and subtle while preserving the existing router. */
export function PageTransition({children}: {children: ReactNode}) {
  const location = useLocation();
  return <motion.div key={`${location.pathname}${location.search}`} className="route-transition" aria-live="polite" initial={{opacity: 0, y: 6}} animate={{opacity: 1, y: 0}} transition={{duration: .28, ease: [0.22, 1, 0.36, 1]}}>{children}</motion.div>;
}
