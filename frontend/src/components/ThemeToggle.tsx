import { createPortal } from 'react-dom';
import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

const THEME_EVENT = 'qhealth-settings-changed';

/**
 * Header-mounted light/dark switch. ResearchShell remains the source of truth
 * for layout preferences; this control only updates the persisted theme value
 * and asks the shell to re-apply its existing theme pipeline.
 */
export function ThemeToggle() {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'));

  useEffect(() => {
    const sync = () => setIsDark(document.documentElement.classList.contains('dark'));
    const findHeader = () => setTarget(document.querySelector<HTMLElement>('.topbar-actions'));

    sync();
    findHeader();
    window.addEventListener(THEME_EVENT, sync);
    window.addEventListener('resize', findHeader);

    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class', 'data-theme'] });

    return () => {
      window.removeEventListener(THEME_EVENT, sync);
      window.removeEventListener('resize', findHeader);
      observer.disconnect();
    };
  }, []);

  const toggle = () => {
    const nextTheme = isDark ? 'research' : 'dark';
    localStorage.setItem('qhealth-theme', nextTheme);
    window.dispatchEvent(new Event(THEME_EVENT));
    setIsDark(nextTheme === 'dark');
  };

  if (!target) return null;

  return createPortal(
    <button
      type="button"
      className="icon-button theme-toggle"
      onClick={toggle}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
    >
      {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </button>,
    target,
  );
}
