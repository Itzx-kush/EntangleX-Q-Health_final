import {useEffect, useRef, type ReactNode} from 'react';

const INTERACTIVE_SELECTOR = 'button:not(:disabled), a, [role="button"]';
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
].join(',');

export function AetherVisualLayer({children}: {children: ReactNode}) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
    const coarsePointer = window.matchMedia?.('(pointer: coarse)').matches ?? false;

    root.classList.add('aether-enabled');
    if (reduceMotion) root.classList.add('aether-reduced');
    if (coarsePointer) root.classList.add('aether-coarse');

    const revealElements = new Set<Element>();
    let observer: IntersectionObserver | null = null;
    let mutations: MutationObserver | null = null;

    if (!reduceMotion && 'IntersectionObserver' in window) {
      observer = new IntersectionObserver(
        entries => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              entry.target.classList.add('aether-reveal-visible');
              observer?.unobserve(entry.target);
            }
          });
        },
        {rootMargin: '0px 0px -8% 0px', threshold: 0.05},
      );

      const registerReveals = (scope: ParentNode) => {
        scope.querySelectorAll(REVEAL_SELECTOR).forEach(element => {
          if (revealElements.has(element)) return;
          revealElements.add(element);
          element.classList.add('aether-reveal');
          observer?.observe(element);
        });
      };

      registerReveals(root);

      mutations = new MutationObserver(records => {
        records.forEach(record => {
          record.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              registerReveals(node as Element);
            }
          });
        });
      });
      mutations.observe(root, {childList: true, subtree: true});
    }

    if (coarsePointer || reduceMotion) {
      return () => {
        observer?.disconnect();
        mutations?.disconnect();
      };
    }

    const cursor = root.querySelector<HTMLElement>('.aether-cursor');
    const interactiveClass = 'aether-magnetic';
    let raf = 0;
    let cursorX = window.innerWidth / 2;
    let cursorY = window.innerHeight / 2;
    let targetCursorX = cursorX;
    let targetCursorY = cursorY;

    const renderCursor = () => {
      cursorX += (targetCursorX - cursorX) * 0.2;
      cursorY += (targetCursorY - cursorY) * 0.2;
      if (cursor) {
        cursor.style.transform = `translate3d(${cursorX}px,${cursorY}px,0) translate3d(-50%,-50%,0)`;
      }
      raf = window.requestAnimationFrame(renderCursor);
    };

    const movePointer = (event: PointerEvent) => {
      targetCursorX = event.clientX;
      targetCursorY = event.clientY;
      root.style.setProperty('--aether-pointer-x', `${event.clientX}px`);
      root.style.setProperty('--aether-pointer-y', `${event.clientY}px`);

      const target = (event.target as Element | null)?.closest?.(INTERACTIVE_SELECTOR) as HTMLElement | null;
      root.classList.toggle('aether-interactive-focus', Boolean(target));

      if (target) {
        const rect = target.getBoundingClientRect();
        const dx = (event.clientX - (rect.left + rect.width / 2)) * 0.16;
        const dy = (event.clientY - (rect.top + rect.height / 2)) * 0.16;
        target.classList.add(interactiveClass);
        target.style.setProperty('--aether-mx', `${Math.max(-7, Math.min(7, dx))}px`);
        target.style.setProperty('--aether-my', `${Math.max(-7, Math.min(7, dy))}px`);
      }
    };

    const clearInteractive = (event: PointerEvent) => {
      const target = (event.target as Element | null)?.closest?.(INTERACTIVE_SELECTOR) as HTMLElement | null;
      if (!target) return;
      target.classList.remove(interactiveClass);
      target.style.removeProperty('--aether-mx');
      target.style.removeProperty('--aether-my');
    };

    const pointerLeave = () => {
      root.classList.remove('aether-interactive-focus');
      root.style.removeProperty('--aether-pointer-x');
      root.style.removeProperty('--aether-pointer-y');
    };

    const scrollUpdate = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      const progress = scrollable > 0 ? window.scrollY / scrollable : 0;
      root.style.setProperty('--aether-scroll-progress', String(Math.max(0, Math.min(1, progress))));
    };

    raf = window.requestAnimationFrame(renderCursor);
    window.addEventListener('pointermove', movePointer, {passive: true});
    window.addEventListener('pointerout', clearInteractive, {passive: true});
    window.addEventListener('pointerleave', pointerLeave, {passive: true});
    window.addEventListener('scroll', scrollUpdate, {passive: true});
    scrollUpdate();

    return () => {
      window.cancelAnimationFrame(raf);
      window.removeEventListener('pointermove', movePointer);
      window.removeEventListener('pointerout', clearInteractive);
      window.removeEventListener('pointerleave', pointerLeave);
      window.removeEventListener('scroll', scrollUpdate);
      observer?.disconnect();
      mutations?.disconnect();
    };
  }, []);

  return (
    <div ref={rootRef} className="aether-visual-root">
      <div className="aether-content">{children}</div>

      <div className="aether-effects" aria-hidden="true">
        <div className="aether-spotlight" />
        <div className="aether-vignette" />
        <div className="aether-grain" />
        <div className="aether-network">
          <svg viewBox="0 0 900 520" preserveAspectRatio="none">
            <g>
              <line x1="90" y1="360" x2="260" y2="180" />
              <line x1="260" y1="180" x2="455" y2="285" />
              <line x1="455" y1="285" x2="650" y2="130" />
              <line x1="650" y1="130" x2="820" y2="300" />
              <line x1="260" y1="180" x2="180" y2="55" />
              <line x1="455" y1="285" x2="515" y2="470" />
              <line x1="650" y1="130" x2="735" y2="35" />
            </g>
            <g className="aether-network-nodes">
              <circle cx="90" cy="360" r="3" />
              <circle cx="260" cy="180" r="4" />
              <circle cx="455" cy="285" r="5" />
              <circle cx="650" cy="130" r="4" />
              <circle cx="820" cy="300" r="3" />
              <circle cx="180" cy="55" r="2.5" />
              <circle cx="515" cy="470" r="2.5" />
              <circle cx="735" cy="35" r="2.5" />
            </g>
          </svg>
        </div>
        <div
          className="aether-cursor"
          role="presentation"
        />
        <div className="aether-scroll-progress" />
      </div>
    </div>
  );
}
