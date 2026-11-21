import {useEffect, useLayoutEffect, useState} from 'react';

export type Appearance = {
  theme: 'research'|'dark'|'system';
  sidebar: 'sidebar'|'floating'|'inset';
  layout: 'default'|'icon'|'offcanvas';
  density: 'comfortable'|'compact';
  motion: 'full'|'reduced';
  inspector: boolean;
};

export const defaultAppearance: Appearance = {
  theme: 'research', sidebar: 'inset', layout: 'default', density: 'comfortable', motion: 'full', inspector: false,
};
const storageKeys: Record<keyof Appearance, string> = {
  theme: 'qhealth-theme', sidebar: 'qhealth-sidebar-variant', layout: 'qhealth-layout',
  density: 'qhealth-density', motion: 'qhealth-motion', inspector: 'qhealth-inspector',
};
const changeEvent = 'qhealth-settings-changed';
function choice<T extends string>(value: string|null, allowed: readonly T[], fallback: T): T {
  return allowed.find(option => option === value) ?? fallback;
}
export function readAppearance(): Appearance {
  const read = (key: keyof Appearance) => localStorage.getItem(storageKeys[key]);
  return {
    theme: choice(read('theme') || localStorage.getItem('qhealth-tictac-theme'), ['research', 'dark', 'system'], defaultAppearance.theme),
    sidebar: choice(read('sidebar'), ['sidebar', 'floating', 'inset'], defaultAppearance.sidebar),
    layout: choice(read('layout'), ['default', 'icon', 'offcanvas'], defaultAppearance.layout),
    density: choice(read('density'), ['comfortable', 'compact'], defaultAppearance.density),
    motion: choice(read('motion'), ['full', 'reduced'], defaultAppearance.motion),
    inspector: read('inspector') === 'visible',
  };
}
export function updateAppearance(patch: Partial<Appearance>) {
  for (const key of Object.keys(patch) as (keyof Appearance)[]) {
    const value = patch[key];
    if (value !== undefined) localStorage.setItem(storageKeys[key], typeof value === 'boolean' ? (value ? 'visible' : 'hidden') : value);
  }
  window.dispatchEvent(new Event(changeEvent));
}

export function usePreferences() {
  const [prefs, setPrefs] = useState(readAppearance);
  useEffect(() => {
    const sync = () => setPrefs(readAppearance());
    window.addEventListener(changeEvent, sync);
    window.addEventListener('storage', sync);
    return () => { window.removeEventListener(changeEvent, sync); window.removeEventListener('storage', sync); };
  }, []);
  return prefs;
}
export function useAppearance(active=true) {
  const prefs = usePreferences();
  useLayoutEffect(() => {
    if (!active) return;
    const root = document.documentElement;
    const media = window.matchMedia?.('(prefers-color-scheme: dark)');
    const apply = () => {
      const dark = prefs.theme === 'dark' || (prefs.theme === 'system' && media?.matches);
      root.classList.toggle('dark', Boolean(dark));
      root.dataset.theme = dark ? 'dark' : 'research';
      root.dataset.density = prefs.density;
      root.dataset.motion = prefs.motion;
      root.dataset.layout = prefs.layout;
      root.dataset.sidebar = prefs.sidebar;
    };
    apply();
    media?.addEventListener?.('change', apply);
    return () => media?.removeEventListener?.('change', apply);
  }, [prefs, active]);
  return prefs;
}
