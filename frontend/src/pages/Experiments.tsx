import {Link, useNavigate} from 'react-router-dom';
import {api, notifyDataChanged} from '../services/api';
import {useAction, useLoad} from '../hooks/useLoad';
import {useDraft} from '../hooks/ExperimentDraft';
import type {Experiment, Job} from '../types';
import {Card, Empty, ErrorNotice, PageHeader, Status} from '../components/Common';
import {dateTime, shortId} from '../utils/format';
export default function Experiments() {
  const list = useLoad(() => api.get<Experiment[]>('/experiments'), [], 5000); const action = useAction(); const {update} = useDraft(); const navigate = useNavigate();
  async function rerun(id: string) {const result = await action.run(() => api.post<{experiment: Experiment; job: Job}>(`/experiments/${id}/rerun`)); if (result) {notifyDataChanged(); navigate(`/experiments/${result.experiment.id}`);}}
  return <><PageHeader eyebrow="11 / Experiment registry" title="Preserve every research decision." description="Dataset hashes, configurations, seeds, versions, failures and measured results remain traceable. Reruns create new experiments and never overwrite their parent."/><ErrorNotice message={list.error || action.error}/><Card title="Recorded experiments">{list.data?.length ? <div className="table-scroll"><table><thead><tr><th>Experiment</th><th>Created</th><th>Status</th><th>Models / seed</th><th>Actions</th></tr></thead><tbody>{list.data.map(e => <tr key={e.id}><td><Link to={`/experiments/${e.id}`}>{shortId(e.id)}</Link><small>Dataset {shortId(e.dataset_id)}{e.parent_id && ` / parent ${shortId(e.parent_id)}`}</small></td><td>{dateTime(e.created_at)}</td><td><Status value={e.status}/></td><td>{e.config.models.join(', ')}<small>Seed {e.config.seed}</small></td><td className="actions"><button className="secondary" disabled={action.busy} onClick={() => void rerun(e.id)}>Rerun unchanged</button><button className="ghost" onClick={() => {update(e.config); navigate('/training');}}>Copy into draft</button></td></tr>)}</tbody></table></div> : <Empty>No experiments are registered. Begin with the dataset and training screens.</Empty>}</Card></>;
}
