import {useEffect, useRef, type ReactNode} from 'react';
import {useLenis} from '../hooks/useLenis';

const INTERACTIVE = 'button:not(:disabled), a, [role="button"], summary, input, select, textarea';

export function QHealthMotionSystem({children}: {children: ReactNode}) {
  useLenis();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    const coarse = window.matchMedia?.('(pointer: coarse)').matches ?? false;

    root.classList.add('qhm-enabled');
    if (reduced) root.classList.add('qhm-reduced');
    if (coarse) root.classList.add('qhm-coarse');

    const pointer = {x: innerWidth / 2, y: innerHeight / 2};
    const target = {...pointer};
    let raf = 0;

    const render = () => {
      pointer.x += (target.x - pointer.x) * 0.12;
      pointer.y += (target.y - pointer.y) * 0.12;
      root.style.setProperty('--qhm-x', `${pointer.x}px`);
      root.style.setProperty('--qhm-y', `${pointer.y}px`);
      raf = requestAnimationFrame(render);
    };

    const move = (event: PointerEvent) => {
      target.x = event.clientX;
      target.y = event.clientY;
      const element = (event.target as Element | null)?.closest?.(INTERACTIVE) as HTMLElement | null;
      root.classList.toggle('qhm-hovering', Boolean(element));

      if (element && !reduced && !coarse) {
        const box = element.getBoundingClientRect();
        const dx = (event.clientX - (box.left + box.width / 2)) * 0.10;
        const dy = (event.clientY - (box.top + box.height / 2)) * 0.10;
        element.style.setProperty('--qhm-mx', `${Math.max(-8, Math.min(8, dx))}px`);
        element.style.setProperty('--qhm-my', `${Math.max(-8, Math.min(8, dy))}px`);
        element.classList.add('qhm-magnetic');
      }
    };

    const reset = (event: PointerEvent) => {
      const element = (event.target as Element | null)?.closest?.(INTERACTIVE) as HTMLElement | null;
      if (!element) return;
      element.classList.remove('qhm-magnetic');
      element.style.removeProperty('--qhm-mx');
      element.style.removeProperty('--qhm-my');
    };

    const revealSelector = [
      '.page-header',
      '.hero-panel',
      '.card',
      '.metric',
      '.stat-grid > *',
      '.two-columns > *',
      '.table-scroll',
      '.chart',
      '.dataset-picker',
      '.prediction-result',
      '.notice',
      '.research-context-strip',
      '.workflow-rail',
      '.contextual-action-bar',
      '.circuit-scroll',
      '.job-card',
    ].join(',');

    let observer: IntersectionObserver | null = null;
    if (!reduced && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('qhm-visible');
            observer?.unobserve(entry.target);
          }
        });
      }, {threshold: 0.06, rootMargin: '0px 0px -7% 0px'});

      root.querySelectorAll(revealSelector).forEach(element => {
        element.classList.add('qhm-reveal');
        observer?.observe(element);
      });
    }

    if (!reduced && !coarse) {
      raf = requestAnimationFrame(render);
      window.addEventListener('pointermove', move, {passive: true});
      window.addEventListener('pointerout', reset, {passive: true});
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerout', reset);
      observer?.disconnect();
    };
  }, []);

  return (
    <div ref={rootRef} className="qhm-root">
      <div className="qhm-content">{children}</div>
      <div className="qhm-scene" aria-hidden="true">
        <div className="qhm-spotlight"/>
        <div className="qhm-grid"/>
        <div className="qhm-glow qhm-glow-a"/>
        <div className="qhm-glow qhm-glow-b"/>
        <div className="qhm-particles">
          {Array.from({length: 18}, (_, index) => <i key={index} style={{'--i': index} as React.CSSProperties}/>)}
        </div>
        <div className="qhm-cursor"/>
        <div className="qhm-progress"/>
      </div>
    </div>
  );
}
