import {useState} from 'react';
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query';
import {Activity, AlertTriangle, ArrowRight, CheckCircle2, Clock3, Database, LoaderCircle, Play, RefreshCw, Send, Server, Terminal, WifiOff} from 'lucide-react';
import {api} from '../lib/api';
import './RedisLab.css';

type RedisStatus = {
  enabled: boolean;
  status: 'disabled' | 'online' | 'offline';
  target: string | null;
  latency_ms: number | null;
  message: string;
};
type RedisResponse = {
  enabled: boolean;
  ok: boolean;
  command: string;
  reply?: unknown;
  error?: string;
};
type CommandEntry = {
  id: number;
  input: string;
  ok: boolean;
  output: string;
};

function tokenize(input: string): string[] {
  const result: string[] = [];
  let token = '';
  let quote: "'" | '"' | null = null;
  let escaped = false;
  let active = false;
  for (const char of input.trim()) {
    if (escaped) {
      token += char;
      escaped = false;
      active = true;
    } else if (char === '\\') {
      escaped = true;
      active = true;
    } else if (quote) {
      if (char === quote) quote = null;
      else token += char;
      active = true;
    } else if (char === "'" || char === '"') {
      quote = char;
      active = true;
    } else if (/\s/.test(char)) {
      if (active) {
        result.push(token);
        token = '';
        active = false;
      }
    } else {
      token += char;
      active = true;
    }
  }
  if (escaped) token += '\\';
  if (quote) throw new Error('Close the quotation mark before running this command.');
  if (active) result.push(token);
  return result;
}

const examples = [
  {label: 'PING', command: 'PING', note: 'Check the server response'},
  {label: 'ECHO hello', command: 'ECHO hello', note: 'Send a message and get it back'},
  {label: 'SET greeting "hello world"', command: 'SET greeting "hello world"', note: 'Store a value in memory'},
  {label: 'GET greeting', command: 'GET greeting', note: 'Read the stored value'},
];

export function RedisLab() {
  const queryClient = useQueryClient();
  const [command, setCommand] = useState('PING');
  const [history, setHistory] = useState<CommandEntry[]>([]);
  const [localError, setLocalError] = useState('');

  const statusQuery = useQuery({
    queryKey: ['redis-lab', 'status'],
    queryFn: () => api.get<RedisStatus>('/redis/status'),
    refetchInterval: 5000,
    retry: 1,
  });

  const mutation = useMutation({
    mutationFn: (input: {raw: string; parts: string[]}) =>
      api.post<RedisResponse>('/redis/command', {command: input.parts}),
    onSuccess: (response, input) => {
      setHistory((current) => [{
        id: Date.now(),
        input: input.raw,
        ok: response.ok,
        output: response.ok ? JSON.stringify(response.reply) : (response.error || 'Command failed.'),
      }, ...current].slice(0, 30));
      void queryClient.invalidateQueries({queryKey: ['redis-lab', 'status']});
    },
    onError: (error, input) => {
      setHistory((current) => [{
        id: Date.now(),
        input: input.raw,
        ok: false,
        output: error.message || 'The Q-Health API could not run this command.',
      }, ...current].slice(0, 30));
    },
  });

  const status = statusQuery.data;
  const runCommand = (raw: string) => {
    setLocalError('');
    let parts: string[];
    try {
      parts = tokenize(raw);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : 'Invalid command syntax.');
      return;
    }
    if (!parts.length) {
      setLocalError('Enter a command first.');
      return;
    }
    mutation.mutate({raw: raw.trim(), parts});
  };
  const statusState = status?.status ?? 'loading';
  const StatusIcon = statusState === 'online' ? CheckCircle2 : statusState === 'offline' ? WifiOff : statusState === 'disabled' ? AlertTriangle : LoaderCircle;

  return <div className="redis-lab-page">
    <header className="redis-lab-heading">
      <div>
        <p className="redis-lab-eyebrow"><Database size={14}/> SYSTEMS / OPTIONAL SERVICE</p>
        <h1>Redis Lab</h1>
        <p className="redis-lab-subtitle">Inspect and test your custom Java Redis-compatible server from inside EntangleX Q-Health.</p>
      </div>
      <button className="redis-lab-refresh" type="button" onClick={() => void statusQuery.refetch()} disabled={statusQuery.isFetching}>
        <RefreshCw size={15} className={statusQuery.isFetching ? 'redis-lab-spin' : ''}/> Refresh status
      </button>
    </header>

    <section className="redis-lab-status-grid" aria-label="Redis service status">
      <article className="redis-lab-card redis-lab-status-card">
        <div className="redis-lab-card-top">
          <span className="redis-lab-icon"><Server size={18}/></span>
          <span className={'redis-lab-pill is-' + statusState}><span className="redis-lab-dot"/>{statusState}</span>
        </div>
        <p className="redis-lab-label">Custom Java Redis</p>
        <h2>{statusState === 'online' ? 'Connected' : statusState === 'offline' ? 'Not reachable' : statusState === 'disabled' ? 'Not enabled' : 'Checking connection…'}</h2>
        <p className="redis-lab-muted">{status?.message || (statusQuery.isError ? 'The status endpoint could not be reached.' : 'Checking the optional Redis connection.')}</p>
      </article>
      <article className="redis-lab-card">
        <div className="redis-lab-card-top"><span className="redis-lab-icon"><Activity size={18}/></span><span className="redis-lab-muted">Live check</span></div>
        <p className="redis-lab-label">PING latency</p>
        <h2>{status?.latency_ms != null ? <>{status.latency_ms}<small> ms</small></> : '—'}</h2>
        <p className="redis-lab-muted">Measured when the backend checks the Redis server.</p>
      </article>
      <article className="redis-lab-card">
        <div className="redis-lab-card-top"><span className="redis-lab-icon"><Clock3 size={18}/></span><span className="redis-lab-muted">Auto-refresh · 5s</span></div>
        <p className="redis-lab-label">Connection target</p>
        <h2 className="redis-lab-target">{status?.target || 'Not configured'}</h2>
        <p className="redis-lab-muted">Private service connection used by FastAPI; the browser never connects to Redis TCP directly.</p>
      </article>
    </section>

    {statusState !== 'online' && <section className="redis-lab-notice" role="status">
      <StatusIcon size={19}/>
      <div>
        <strong>{statusState === 'disabled' ? 'Redis is optional and disabled by default' : statusState === 'offline' ? 'The Redis service is currently offline' : 'Checking Redis availability'}</strong>
        <p>{statusState === 'disabled'
          ? 'To try the integration locally, start Q-Health with the Redis Compose overlay described in the integration guide. Your existing research workspace remains available without Redis.'
          : statusState === 'offline'
            ? 'Start the Java Redis service and confirm that FastAPI can reach it. Existing Supabase, Groq, SQLite and ML workflows are not replaced by this service.'
            : 'The status request has not completed yet.'}</p>
      </div>
    </section>}

    <section className="redis-lab-workspace">
      <article className="redis-lab-card redis-lab-terminal-card">
        <div className="redis-lab-section-heading">
          <div><p className="redis-lab-eyebrow">INTERACTIVE CONSOLE</p><h2><Terminal size={19}/> Command playground</h2></div>
          <span className="redis-lab-small-tag">RESP over TCP</span>
        </div>
        <p className="redis-lab-muted">Commands go through the existing FastAPI backend to your Java server. The demo allows only PING, ECHO, SET and GET.</p>
        <div className="redis-lab-examples">
          {examples.map((example) => <button key={example.command} type="button" onClick={() => setCommand(example.command)} title={example.note}>{example.label}</button>)}
        </div>
        <form className="redis-lab-command-form" onSubmit={(event) => {event.preventDefault(); runCommand(command);}}>
          <label htmlFor="redis-command"><span><span className="redis-lab-prompt">redis&gt;</span> Command</span><small>Quoted arguments may contain spaces.</small></label>
          <div className="redis-lab-input-row">
            <input id="redis-command" value={command} onChange={(event) => setCommand(event.target.value)} placeholder='SET greeting "hello world"' autoComplete="off" spellCheck={false}/>
            <button type="submit" disabled={mutation.isPending || statusState !== 'online'}><Play size={14}/>{mutation.isPending ? 'Running…' : 'Run'}</button>
          </div>
          {localError && <p className="redis-lab-inline-error" role="alert">{localError}</p>}
          {statusState !== 'online' && <p className="redis-lab-inline-hint">Connect the Redis service to run commands.</p>}
        </form>
        <div className="redis-lab-history-header"><span>SESSION OUTPUT</span><button type="button" onClick={() => setHistory([])} disabled={!history.length}>Clear output</button></div>
        <div className="redis-lab-output" aria-live="polite">
          {!history.length && <div className="redis-lab-empty"><Terminal size={22}/><strong>Terminal ready</strong><span>Choose a sample command or type PING to begin.</span></div>}
          {history.map((entry) => <div key={entry.id} className="redis-lab-output-entry">
            <div className="redis-lab-output-command"><span className="redis-lab-prompt">redis&gt;</span> {entry.input}<span className={entry.ok ? 'redis-lab-result-ok' : 'redis-lab-result-error'}>{entry.ok ? 'OK' : 'ERROR'}</span></div>
            <pre>{entry.output}</pre>
          </div>)}
        </div>
      </article>

      <aside className="redis-lab-side-column">
        <article className="redis-lab-card">
          <div className="redis-lab-section-heading"><div><p className="redis-lab-eyebrow">REQUEST PATH</p><h2>How it connects</h2></div><ArrowRight size={17}/></div>
          <div className="redis-lab-path">
            <div><span>01</span><div><strong>Q-Health UI</strong><small>Command playground</small></div></div>
            <div className="redis-lab-path-line"/>
            <div><span>02</span><div><strong>FastAPI bridge</strong><small>Authenticated REST API</small></div></div>
            <div className="redis-lab-path-line"/>
            <div><span>03</span><div><strong>Java Redis server</strong><small>TCP + RESP protocol</small></div></div>
          </div>
        </article>
        <article className="redis-lab-card">
          <div className="redis-lab-section-heading"><div><p className="redis-lab-eyebrow">SUPPORTED DEMO COMMANDS</p><h2>Command reference</h2></div></div>
          <div className="redis-lab-command-ref">
            <button type="button" onClick={() => setCommand('PING')}><code>PING</code><span>Check connectivity</span></button>
            <button type="button" onClick={() => setCommand('ECHO hello')}><code>ECHO message</code><span>Return a message</span></button>
            <button type="button" onClick={() => setCommand('SET greeting "hello world"')}><code>SET key value</code><span>Store a string</span></button>
            <button type="button" onClick={() => setCommand('GET greeting')}><code>GET key</code><span>Read a string</span></button>
          </div>
        </article>
        <article className="redis-lab-safety-note"><CheckCircle2 size={17}/><p><strong>Existing storage remains authoritative.</strong><br/>Redis is a separate, optional demonstration service. It does not replace Supabase, SQLite, Groq, model files, or experiment records.</p></article>
      </aside>
    </section>
  </div>;
}
