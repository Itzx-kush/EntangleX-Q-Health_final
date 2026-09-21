import {useCallback, useEffect, useRef, useState, type DependencyList} from 'react';
export function useLoad<T>(load: () => Promise<T>, dependencies: DependencyList = [], pollMs = 0) {
  const current = useRef(load); current.current = load;
  const [data, setData] = useState<T>(); const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const reload = useCallback(() => setRevision(v => v + 1), []);
  useEffect(() => {
    let active = true;
    let inFlight = false;
    async function refresh() {
      if (inFlight) return;
      inFlight = true;
      try {const value = await current.current(); if (active) {setData(value); setError('');}}
      catch (err) {if (active) setError(err instanceof Error ? err.message : 'Request failed.');}
      finally {inFlight = false; if (active) setLoading(false);}
    }
    setData(undefined); setError(''); setLoading(true); void refresh();
    const timer = pollMs ? window.setInterval(() => {void refresh();}, pollMs) : undefined;
    return () => {active = false; if (timer) clearInterval(timer);};
  }, [...dependencies, revision, pollMs]);
  useEffect(() => {window.addEventListener('qhealth-auth', reload); window.addEventListener('qhealth-data', reload); return () => {window.removeEventListener('qhealth-auth', reload); window.removeEventListener('qhealth-data', reload);};}, [reload]);
  return {data, error, loading, reload};
}

export function useAction() {
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function run<T>(operation: () => Promise<T>): Promise<T | undefined> {
    setBusy(true); setError('');
    try {return await operation();} catch (err) {setError(err instanceof Error ? err.message : 'Operation failed.'); return undefined;} finally {setBusy(false);}
  }
  return {busy, error, run, clearError: () => setError('')};
}
