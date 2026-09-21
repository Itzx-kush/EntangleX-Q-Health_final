import {ArrowRight, CornerDownLeft, Search} from 'lucide-react';
import {AnimatePresence, motion, useReducedMotion} from 'motion/react';
import type {LucideIcon} from 'lucide-react';
import {Fragment, useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent} from 'react';
import {useNavigate} from 'react-router-dom';
import {Dialog} from './Primitives';
import {environments, navigationItems} from '../navigation';

type CommandResult = {kind: 'environment' | 'page'; label: string; path: string; description: string; environmentName: string; Icon: LucideIcon};

export function CommandPalette({open, onClose}: {open: boolean; onClose: () => void}) {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const reduce = useReducedMotion();
  const normalized = query.trim().toLowerCase();
  const results = useMemo<CommandResult[]>(() => {
    const envResults = environments.map(environment => ({kind: 'environment' as const, label: environment.name, path: environment.items[0].path, description: environment.description, environmentName: 'Environment', Icon: environment.icon})).filter(result => !normalized || `${result.label} ${result.description}`.toLowerCase().includes(normalized));
    const pageResults = navigationItems.map(item => ({kind: 'page' as const, label: item.label, path: item.path, description: item.description, environmentName: item.environmentName, Icon: item.icon})).filter(result => !normalized || `${result.label} ${result.description} ${result.environmentName}`.toLowerCase().includes(normalized));
    return [...envResults, ...pageResults];
  }, [normalized]);

  useEffect(() => { if (!open) {setQuery(''); setSelected(0); return;} window.setTimeout(() => inputRef.current?.focus(), 0); }, [open]);
  useEffect(() => { if (!open) return; const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); }; window.addEventListener('keydown', onKeyDown); return () => window.removeEventListener('keydown', onKeyDown); }, [open, onClose]);
  useEffect(() => { setSelected(0); }, [query]);

  function choose(result: CommandResult | undefined) { if (!result) return; navigate(result.path); onClose(); }
  function onInputKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) { if (event.key === 'ArrowDown') {event.preventDefault(); setSelected(index => Math.min(index + 1, results.length - 1));} else if (event.key === 'ArrowUp') {event.preventDefault(); setSelected(index => Math.max(index - 1, 0));} else if (event.key === 'Enter') {event.preventDefault(); choose(results[selected]);} }

  return <Dialog open={open} onClose={onClose} title="Navigate Q-Health workspace"><div className="command-palette">
    <label className="command-search"><Search size={17} aria-hidden="true"/><span className="sr-only">Search workspace navigation</span><input ref={inputRef} role="combobox" aria-expanded="true" aria-controls="command-results" aria-autocomplete="list" aria-activedescendant={results[selected] ? `command-result-${selected}` : undefined} value={query} onChange={event => setQuery(event.target.value)} onKeyDown={onInputKeyDown} placeholder="Search environments and pages" autoComplete="off"/><kbd>Esc</kbd></label>
    <AnimatePresence mode="wait" initial={false}>{results.length ? <motion.div key="results" className="command-results" id="command-results" role="listbox" aria-label="Workspace navigation results" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: reduce ? 0 : .12}}>{results.map((result, index) => {const Icon = result.Icon; const previous = results[index - 1]; const groupHeading = !previous || previous.kind !== result.kind; return <Fragment key={`${result.kind}-${result.path}`}>{groupHeading && <p className="command-group-label">{result.kind === 'environment' ? 'Environments' : 'Pages'}</p>}<button id={`command-result-${index}`} role="option" aria-selected={selected === index} className={`command-result ${selected === index ? 'selected' : ''}`} onMouseEnter={() => setSelected(index)} onClick={() => choose(result)}><span className="command-result-icon"><Icon size={16} aria-hidden="true"/></span><span><strong>{result.label}</strong><small>{result.kind === 'environment' ? 'Environment' : result.environmentName} <span>·</span> {result.description}</small></span><ArrowRight size={15} aria-hidden="true"/></button></Fragment>;})}</motion.div> : <motion.div key="empty" className="command-empty" role="status" initial={{opacity: 0}} animate={{opacity: 1}} exit={{opacity: 0}} transition={{duration: reduce ? 0 : .12}}><Search size={20} aria-hidden="true"/><strong>No workspace locations found</strong><span>Try an environment or page name.</span></motion.div>}</AnimatePresence>
    <footer className="command-footer"><span><CornerDownLeft size={13} aria-hidden="true"/> Open</span><span><kbd>↑</kbd><kbd>↓</kbd> Move</span><span><kbd>Ctrl</kbd><span>/</span><kbd>⌘</kbd><kbd>K</kbd> Command</span></footer>
  </div></Dialog>;
}
