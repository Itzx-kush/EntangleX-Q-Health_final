import {useEffect, useRef} from 'react';

export function useDialogFocus<T extends HTMLElement>(active = true) {
  const ref = useRef<T>(null);
  useEffect(() => {
    const element = ref.current;
    if (!active || !element) return;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const controls = () => Array.from(element.querySelectorAll<HTMLElement>(
      'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'
    )).filter(item => !item.hidden && getComputedStyle(item).display !== 'none');
    controls()[0]?.focus();
    function contain(event: KeyboardEvent) {
      if (event.key !== 'Tab') return;
      const list = controls();
      const end = event.shiftKey ? list[0] : list.at(-1);
      if (document.activeElement !== end) return;
      event.preventDefault();
      (event.shiftKey ? list.at(-1) : list[0])?.focus();
    }
    element.addEventListener('keydown', contain);
    return () => { element.removeEventListener('keydown', contain); if (trigger?.isConnected) trigger.focus({preventScroll: true}); };
  }, [active]);
  return ref;
}
