import {AnimatePresence, motion, useReducedMotion} from 'motion/react';
import type {CSSProperties, ReactNode} from 'react';
import {useLocation} from 'react-router-dom';

export type MotionVariant = 'page' | 'page-exit' | 'reveal' | 'fade' | 'slide-up' | 'slide-inline';

/** Shared motion vocabulary. Keep timing decisions here, not in individual pages. */
export const motionTokens = {
  instant: 0,
  fast: 0.12,
  standard: 0.18,
  moderate: 0.24,
  slow: 0.32,
  page: 0.26,
  reveal: 0.42,
} as const;

export const motionEasings = {
  standard: [0.2, 0.7, 0.2, 1] as const,
  emphasized: [0.16, 1, 0.3, 1] as const,
  decelerate: [0, 0, 0.2, 1] as const,
  accelerate: [0.4, 0, 1, 1] as const,
} as const;

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
  return <motion.div className={`motion motion-${variant} ${className}`.trim()} style={{'--motion-delay': `${delay}ms`} as CSSProperties} initial={variants.initial} animate={variants.animate} transition={{duration: reduce ? 0 : motionTokens.reveal, delay: reduce ? 0 : delay / 1000, ease: motionEasings.emphasized}}>{children}</motion.div>;
}

/** Use for a bounded group of page-level children, never for unbounded lists. */
export function Stagger({children, className = '', delay = 0}: {children: ReactNode; className?: string; delay?: number}) {
  const reduce = useReducedMotion();
  return <motion.div className={`motion-stagger ${className}`.trim()} initial="hidden" animate="visible" variants={{hidden: {}, visible: {transition: {staggerChildren: reduce ? 0 : 0.045, delayChildren: reduce ? 0 : delay / 1000}}}}>{children}</motion.div>;
}

export function StaggerItem({children, className = ''}: {children: ReactNode; className?: string}) {
  const reduce = useReducedMotion();
  return <motion.div className={`motion-stagger-item ${className}`.trim()} variants={{hidden: {opacity: 0, y: reduce ? 0 : 8}, visible: {opacity: 1, y: 0, transition: {duration: reduce ? 0 : motionTokens.standard, ease: motionEasings.emphasized}}}}>{children}</motion.div>;
}

/** Presence wrapper for small state surfaces such as loading, error, and empty states. */
export function StateTransition({children, stateKey}: {children: ReactNode; stateKey: string}) {
  const reduce = useReducedMotion();
  return <AnimatePresence mode="wait" initial={false}><motion.div key={stateKey} initial={{opacity: 0, y: reduce ? 0 : 6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: reduce ? 0 : -4}} transition={{duration: reduce ? 0 : motionTokens.standard, ease: motionEasings.standard}}>{children}</motion.div></AnimatePresence>;
}

/** Keeps route transitions fast and subtle while preserving the existing router. */
export function PageTransition({children}: {children: ReactNode}) {
  const location = useLocation();
  const reduce = useReducedMotion();
  return <AnimatePresence mode="wait" initial={false}><motion.div key={`${location.pathname}${location.search}`} className="route-transition" aria-live="polite" initial={{opacity: 0, y: reduce ? 0 : 6}} animate={{opacity: 1, y: 0}} exit={{opacity: 0, y: reduce ? 0 : -4}} transition={{duration: reduce ? 0 : motionTokens.page, ease: motionEasings.emphasized}}>{children}</motion.div></AnimatePresence>;
}
