import {useEffect, useRef, useState} from 'react';
import {ArrowUpRight, Menu, X} from 'lucide-react';
import {Brand} from '../Brand';

const links = [
  ['Interactive preview', '#interactive-demo'],
  ['Methodology', '#guided-process'],
  ['Architecture', '#technical-stack'],
  ['About', '#about'],
] as const;

export function PublicHeader({onRequestAccess}: {onRequestAccess: (destination?: string) => void}) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const nav = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!open) return;
    function dismiss(event: KeyboardEvent) {
      if (event.key === 'Escape') { setOpen(false); trigger.current?.focus(); }
    }
    function outside(event: PointerEvent) {
      if (!nav.current?.contains(event.target as Node)) setOpen(false);
    }
    window.addEventListener('keydown', dismiss);
    document.addEventListener('pointerdown', outside);
    return () => {
      window.removeEventListener('keydown', dismiss);
      document.removeEventListener('pointerdown', outside);
    };
  }, [open]);
  return <header className="qx-public-header" ref={nav}>
    <div className="qx-wrap qx-masthead">
      <a href="#top" aria-label="EntangleX Q-Health home"><Brand/></a>
      <button ref={trigger} className="qx-nav-toggle" aria-controls="public-nav" aria-expanded={open} aria-label={open ? 'Close navigation' : 'Open navigation menu'} onClick={() => setOpen(!open)}>{open ? <X/> : <Menu/>}</button>
      <nav id="public-nav" className={open ? 'is-open' : ''} aria-label="Main public navigation">{links.map(([label, href]) => <a key={href} href={href} onClick={() => setOpen(false)}>{label}</a>)}</nav>
      <button className="qx-button secondary masthead-signin" onClick={() => onRequestAccess('/')}>Sign in <ArrowUpRight size={15}/></button>
    </div>
  </header>;
}
