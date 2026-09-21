import {useState, type FormEvent} from 'react';
import {Link} from 'react-router-dom';
import {api, notifyDataChanged} from '../services/api';
import {useAction, useLoad} from '../hooks/useLoad';
import {useDraft} from '../hooks/ExperimentDraft';
import type {Dataset} from '../types';
import {Card, Empty, ErrorNotice, Field, JsonView, Note, PageHeader} from '../components/Common';
import {shortId} from '../utils/format';
export default function Datasets() {
  const {draft, update} = useDraft(); const list = useLoad(() => api.get<Dataset[]>('/datasets')); const action = useAction();
  const [file, setFile] = useState<File | null>(null); const [deidentified, setDeidentified] = useState(false);
  const [form, setForm] = useState({name: '', domain: 'biomedical', source: 'User-provided', source_url: '', version: 'unspecified', target: '', positive_label: ''});
  const selected = list.data?.find(d => d.id === draft.dataset_id);
  async function demo() {const d = await action.run(() => api.post<Dataset>('/datasets/demo')); if (d) {update({dataset_id: d.id, features: null}); notifyDataChanged();}}
  async function upload(e: FormEvent) {
    e.preventDefault(); if (!file || !deidentified) return;
    const body = new FormData(); body.append('file', file); body.append('metadata_json', JSON.stringify({...form, source_url: form.source_url || null, deidentified: true, sampling_unit: 'independent_samples'}));
    const d = await action.run(() => api.upload<Dataset>('/datasets/upload', body));
    if (d) {update({dataset_id: d.id, features: null}); notifyDataChanged();}
  }
  async function remove(d: Dataset) {if (window.confirm(`Delete unreferenced dataset ${d.name}? This cannot be undone.`)) {const removed = await action.run(async () => {await api.remove(`/datasets/${d.id}`); return true;}); if (removed) {if (draft.dataset_id === d.id) update({dataset_id: '', features: null}); notifyDataChanged();}}}
  return <><PageHeader eyebrow="01 / Dataset provenance" title="Know the source." description="Register a public benchmark or a deidentified CSV. Dataset bytes are hashed and remain immutable once referenced by an experiment."><button disabled={action.busy} onClick={() => void demo()}>Load Wisconsin benchmark</button></PageHeader><ErrorNotice message={action.error || list.error}/>
    <Note>Do not upload identifiable health records. This is a single-workstation research prototype, not a production health-data service. The public demo contains biomedical features without patient identifiers.</Note>
    <Card title="Dataset registry">{list.data?.length ? <div className="table-scroll"><table><thead><tr><th>Dataset</th><th>Samples / features</th><th>Target / positive class</th><th>Actions</th></tr></thead><tbody>{list.data.map(d => <tr key={d.id} className={draft.dataset_id === d.id ? 'selected-row' : ''}><td><strong>{d.name}</strong><small>{shortId(d.id)} / {d.provenance.domain}</small></td><td>{d.provenance.row_count} / {d.provenance.feature_count}</td><td>{d.provenance.target}<small>Positive: {d.provenance.positive_label}</small></td><td className="actions"><button className="secondary" onClick={() => update({dataset_id: d.id, features: null})}>Select</button><button className="ghost" disabled={action.busy} onClick={() => void remove(d)}>Delete</button></td></tr>)}</tbody></table></div> : <Empty>No datasets are registered yet.</Empty>}</Card>
    <div className="two-columns"><Card title="Upload a deidentified CSV"><form onSubmit={e => void upload(e)}><div className="form-grid">{Object.entries(form).map(([key, value]) => <Field key={key} label={key.replaceAll('_', ' ')}><input required={!['source_url'].includes(key)} maxLength={key === 'source_url' ? 500 : 160} value={value} onChange={e => setForm({...form, [key]: e.target.value})}/></Field>)}</div><Field label="CSV file" help="UTF-8, unique headers, one target with exactly two classes; default upload limit 20 MB."><input type="file" accept=".csv,text/csv" required onChange={e => setFile(e.target.files?.[0] || null)}/></Field><label className="check"><input type="checkbox" required checked={deidentified} onChange={e => setDeidentified(e.target.checked)}/>I confirm this file is suitable for local research, contains no patient-identifiable information, and represents independent samples.</label><button type="submit" disabled={action.busy || !file || !deidentified}>{action.busy ? 'Processing...' : 'Validate and register dataset'}</button></form></Card>
    <Card title="Selected dataset provenance">{selected ? <><h3>{selected.name}</h3><p>{selected.provenance.source}</p><p className="mono wrap">SHA-256: {selected.sha256}</p><dl><dt>Positive label</dt><dd>{selected.provenance.positive_label}</dd><dt>Negative label</dt><dd>{selected.provenance.negative_label}</dd><dt>Source version</dt><dd>{selected.provenance.version}</dd></dl><JsonView value={selected.provenance} label="Full provenance metadata"/><Link to="/quality" className="button secondary">Review data quality</Link></> : <Empty>Select a dataset to inspect its provenance. No raw records are listed.</Empty>}</Card></div></>;
}
