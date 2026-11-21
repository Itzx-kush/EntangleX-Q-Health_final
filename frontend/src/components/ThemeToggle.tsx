import {useSyncExternalStore} from 'react';
import {Moon, Sun} from 'lucide-react';
import {updateAppearance, usePreferences} from '../lib/appearance';
const prefersDark=()=>Boolean(window.matchMedia?.('(prefers-color-scheme: dark)').matches);
function onSystemTheme(change:()=>void){
  const query=window.matchMedia?.('(prefers-color-scheme: dark)');
  query?.addEventListener?.('change',change);
  return ()=>query?.removeEventListener?.('change',change);
}
export function ThemeToggle() {
  const {theme} = usePreferences();
  const systemDark=useSyncExternalStore(onSystemTheme,prefersDark);
  const dark = theme === 'dark' || (theme === 'system' && systemDark);
  const label = dark ? 'Switch to light theme' : 'Switch to dark theme';
  return <button type="button" className="icon-button theme-toggle" aria-label={label} title={label}
    onClick={() => updateAppearance({theme:dark?'research':'dark'})}>{dark?<Sun size={16}/>:<Moon size={16}/>}</button>;
}
