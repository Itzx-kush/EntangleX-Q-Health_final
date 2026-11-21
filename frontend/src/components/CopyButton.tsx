import {useEffect, useRef, useState} from 'react';
import {Check, Copy} from 'lucide-react';

export function CopyButton({value, label = 'Copy'}: {value: string; label?: string}) {
  const [state, setState] = useState<'idle'|'copied'|'error'>('idle');
  const generation = useRef(0);
  useEffect(() => { setState('idle'); return () => { generation.current++; }; }, [value]);
  useEffect(() => {
    if (state === 'idle') return;
    const timer = window.setTimeout(() => setState('idle'), 3000);
    return () => window.clearTimeout(timer);
  }, [state]);
  async function copy() {
    const id = ++generation.current;
    try {
      await navigator.clipboard.writeText(value);
      if (id === generation.current) setState('copied');
    } catch {
      if (id === generation.current) setState('error');
    }
  }
  return <span className="copy-control"><button type="button" className="btn btn-outline" aria-label={label} onClick={copy}>
    {state === 'copied' ? <Check size={14}/> : <Copy size={14}/>} {state === 'copied' ? 'Copied' : 'Copy'}
  </button><span role="status" className={state === 'error' ? 'copy-hint' : 'sr-only'}>{state === 'error' ? 'Select the text and copy manually.' : state === 'copied' ? 'Copied to clipboard.' : ''}</span></span>;
}
