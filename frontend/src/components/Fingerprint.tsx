import {CopyButton} from './CopyButton';
export function Fingerprint({value}: {value: string}) {
  return <details className="fingerprint"><summary>SHA-256 · {value.slice(0,8)}…</summary><code>{value}</code><CopyButton value={value} label="Copy SHA-256 fingerprint"/></details>;
}
