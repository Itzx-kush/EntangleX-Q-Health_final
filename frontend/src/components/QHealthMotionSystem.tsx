import {useEffect, useRef, type CSSProperties, type ReactNode} from 'react';

const INTERACTIVE = 'button:not(:disabled), a, [role="button"], summary, input, select, textarea';
const REVEAL_SELECTOR = [
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

export function QHealthMotionSystem({children}: {children: ReactNode}) {
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
      pointer.x += (target.x - pointer.x) * 0.14;
      pointer.y += (target.y - pointer.y) * 0.14;
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
        const dx = (event.clientX - (box.left + box.width / 2)) * 0.07;
        const dy = (event.clientY - (box.top + box.height / 2)) * 0.07;
        element.style.setProperty('--qhm-mx', `${Math.max(-6, Math.min(6, dx))}px`);
        element.style.setProperty('--qhm-my', `${Math.max(-6, Math.min(6, dy))}px`);
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

    const updateScroll = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollable > 0 ? window.scrollY / scrollable : 0;
      root.style.setProperty('--qhm-scroll', String(Math.max(0, Math.min(1, progress))));
    };

    let observer: IntersectionObserver | null = null;
    let mutations: MutationObserver | null = null;

    const observe = () => {
      if (reduced || !observer) return;
      root.querySelectorAll(REVEAL_SELECTOR).forEach(element => {
        if (element.classList.contains('qhm-visible')) return;
        element.classList.add('qhm-reveal');
        observer?.observe(element);
      });
    };

    if (!reduced && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('qhm-visible');
            observer?.unobserve(entry.target);
          }
        });
      }, {threshold: 0.04, rootMargin: '0px 0px -5% 0px'});

      observe();
      mutations = new MutationObserver(() => observe());
      mutations.observe(root, {childList: true, subtree: true});
    }

    window.addEventListener('scroll', updateScroll, {passive: true});

    if (!reduced && !coarse) {
      raf = requestAnimationFrame(render);
      window.addEventListener('pointermove', move, {passive: true});
      window.addEventListener('pointerout', reset, {passive: true});
    }

    updateScroll();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('scroll', updateScroll);
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerout', reset);
      observer?.disconnect();
      mutations?.disconnect();
    };
  }, []);

  return (
    <div ref={rootRef} className="qhm-root">
      <div className="qhm-content">{children}</div>
      <div className="qhm-scene" aria-hidden="true">
        <div className="qhm-spotlight" />
        <div className="qhm-grid" />
        <div className="qhm-cursor" />
        <div className="qhm-progress" />
      </div>
    </div>
  );
}
