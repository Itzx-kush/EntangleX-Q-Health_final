import {useState} from 'react';
import {Atom,Brain,ChevronLeft,ChevronRight,Database,FlaskConical,History,LogIn,RefreshCw,Sparkles} from 'lucide-react';
import {Link} from 'react-router-dom';
import {useAuth} from '../auth/AuthProvider';
import {useGuestMigration} from '../auth/GuestMigrationProvider';
import {PageHeader} from '../components/Shared';
import {Badge,Button} from '../components/ui';
import {useResearchHistory} from './useResearchHistory';
import type {ResearchActivity,ResearchActivityType,ResearchHistoryFilter} from './historyTypes';

const filters:{value:ResearchHistoryFilter;label:string}[]=[
  {value:'all',label:'All activity'},
  {value:'experiment',label:'Experiments'},
  {value:'prediction',label:'Predictions'},
  {value:'explanation',label:'Explainability'},
  {value:'quantum',label:'Quantum'},
  {value:'session',label:'Sessions'},
];

const activityMeta:Record<ResearchActivityType,{label:string;icon:typeof History;action:string}>={
  experiment:{label:'Experiment',icon:FlaskConical,action:'Open experiment'},
  prediction:{label:'Prediction',icon:Sparkles,action:'Open prediction'},
  explanation:{label:'Explanation',icon:Brain,action:'Open explanation'},
  quantum:{label:'Quantum',icon:Atom,action:'Open Quantum Lab'},
  session:{label:'Guest session',icon:History,action:'Resume session'},
};

function timeLabel(value:string){
  const date=new Date(value);
  if(Number.isNaN(date.getTime()))return 'Timestamp unavailable';
  const now=new Date();
  const dayStart=new Date(now.getFullYear(),now.getMonth(),now.getDate()).getTime();
  const itemStart=new Date(date.getFullYear(),date.getMonth(),date.getDate()).getTime();
  const days=Math.round((itemStart-dayStart)/86_400_000);
  if(days===0)return `Today · ${new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(date)}`;
  if(days===-1)return `Yesterday · ${new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(date)}`;
  return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(date);
}

function compactId(value:string|null){
  if(!value)return null;
  return value.length>18?`${value.slice(0,8)}…${value.slice(-6)}`:value;
}

function statusTone(status:string|null):'blue'|'green'|'amber'|'red'|'purple'{
  const normalized=status?.toLowerCase()||'';
  if(['completed','succeeded','ready','available'].includes(normalized))return 'green';
  if(['failed','cancelled','unavailable'].includes(normalized))return 'red';
  if(['queued','running','configured','simulated'].includes(normalized))return 'amber';
  return 'blue';
}

export function ResearchActivityItem({record}:{record:ResearchActivity}){
  const meta=activityMeta[record.activity_type];
  const Icon=meta.icon;
  return <li className="research-activity-item">
    <div className={`research-activity-icon is-${record.activity_type}`}><Icon size={16}/></div>
    <div className="research-activity-content">
      <div className="research-activity-heading">
        <div><span className="research-activity-type">{meta.label}</span><h3>{record.title}</h3></div>
        <time dateTime={record.occurred_at}>{timeLabel(record.occurred_at)}</time>
      </div>
      <div className="research-record-meta">
        {record.metadata?.source==='guest_session'&&<span className="research-record-origin">Imported from guest session</span>}
        {record.status&&<Badge tone={statusTone(record.status)}>{record.status.replaceAll('_',' ')}</Badge>}
        {record.model_id&&<span title={record.model_id}>Model · {compactId(record.model_id)}</span>}
        {record.dataset_id&&<span title={record.dataset_id}>Dataset · {compactId(record.dataset_id)}</span>}
        {record.method&&<span>Method · {record.method}</span>}
        {record.reference_id&&<span title={record.reference_id}>Reference · {compactId(record.reference_id)}</span>}
      </div>
    </div>
    <Link className="research-activity-open" to={record.route}>{meta.action}<ChevronRight size={14}/></Link>
  </li>;
}

function HistorySkeleton(){
  return <div className="research-history-skeleton" aria-label="Loading research history" aria-busy="true">
    {[0,1,2,3].map(index=><div key={index}><span/><div><i/><i/></div></div>)}
  </div>;
}

export function ResearchEmptyState({filter='all'}:{filter?:ResearchHistoryFilter}){
  const copy=filter==='all'
    ? 'Run an experiment, generate a research prediction, calculate an explanation, or inspect a backend-generated quantum circuit to begin building your history.'
    : `No ${filters.find(item=>item.value===filter)?.label.toLowerCase()} have been recorded for this account yet.`;
  return <div className="research-history-empty">
    <span><Database size={22}/></span>
    <h2>{filter==='all'?'No research activity yet':`No ${filters.find(item=>item.value===filter)?.label.toLowerCase()} yet`}</h2>
    <p>{copy}</p>
    <div><Link className="btn btn-primary" to="/training">Start an experiment</Link><Link className="btn btn-outline" to="/datasets">Open Data Lab</Link></div>
  </div>;
}

export function RecentResearchPreview(){
  const {isAuthenticated,isConfigured}=useAuth();
  const history=useResearchHistory('all',0,4);
  if(!isAuthenticated)return null;
  if(!isConfigured)return <div className="account-history-setup"><History size={18}/><span><strong>Research history requires Supabase configuration</strong><small>Your account identity remains available.</small></span></div>;
  if(history.isLoading)return <HistorySkeleton/>;
  if(history.isError)return <div className="account-history-setup is-error"><History size={18}/><span><strong>Research history unavailable</strong><small>{(history.error as Error).message}</small></span><button type="button" onClick={()=>history.refetch()}>Retry</button></div>;
  if(!history.data?.records.length)return <ResearchEmptyState/>;
  return <div><ol className="research-activity-list compact">{history.data.records.map(record=><ResearchActivityItem record={record} key={record.id}/>)}</ol><Link className="btn btn-outline mt-4" to="/my-research">View all research activity</Link></div>;
}

export function ResearchHistoryPage(){
  const {isAuthenticated,isConfigured}=useAuth();
  const {beginUpgrade,hasMigratableState}=useGuestMigration();
  const [filter,setFilter]=useState<ResearchHistoryFilter>('all');
  const [page,setPage]=useState(0);
  const pageSize=20;
  const history=useResearchHistory(filter,page,pageSize);

  if(!isAuthenticated)return <div>
    <PageHeader eyebrow="Personal research" title="My Research" description="Private cloud research history is available only to an authenticated EntangleX account."/>
    <div className="research-history-empty"><span><History size={22}/></span><h2>Guest mode is active</h2><p>The existing research prototype remains fully available. Guest actions do not write private cloud history.</p><Button onClick={beginUpgrade}><LogIn size={15}/>{hasMigratableState?'Sign in to save this work':'Go to sign in'}</Button></div>
  </div>;

  return <div className="research-history-page">
    <PageHeader eyebrow="Personal research" title="My Research" description="Your private record of meaningful EntangleX research actions, linked back to the existing scientific workspace." actions={<Link className="btn btn-primary" to="/training">New experiment</Link>}/>

    <section className="research-history-intro">
      <div><span className="account-kicker">User-owned metadata</span><h2>Recent activity</h2><p>References and concise research metadata are stored here. Raw health inputs and full scientific result payloads are not.</p></div>
      <span className="research-history-private"><History size={16}/>Private to your account</span>
    </section>

    {!isConfigured?<div className="research-history-error" role="status"><History size={20}/><div><h2>Research history is not configured</h2><p>Add the public Supabase configuration and apply the repository migration. Core EntangleX research remains available.</p></div></div>:<>
      <div className="research-history-toolbar" aria-label="Research history filters">
        <div className="research-history-filters">{filters.map(item=><button type="button" key={item.value} aria-pressed={filter===item.value} onClick={()=>{setFilter(item.value);setPage(0)}}>{item.label}</button>)}</div>
        {history.data&&<span aria-live="polite">{history.data.total} {history.data.total===1?'record':'records'}</span>}
      </div>

      {history.isLoading?<HistorySkeleton/>:history.isError?<div className="research-history-error" role="alert"><RefreshCw size={20}/><div><h2>Research history unavailable</h2><p>{(history.error as Error).message}</p><Button variant="outline" onClick={()=>history.refetch()}><RefreshCw size={14}/>Retry</Button></div></div>:history.data?.records.length?<>
        <ol className="research-activity-list">{history.data.records.map(record=><ResearchActivityItem record={record} key={record.id}/>)}</ol>
        <nav className="research-history-pagination" aria-label="Research history pages">
          <Button variant="outline" disabled={page===0} onClick={()=>setPage(value=>Math.max(0,value-1))}><ChevronLeft size={14}/>Previous</Button>
          <span>Page {page+1}</span>
          <Button variant="outline" disabled={(page+1)*pageSize>=history.data.total} onClick={()=>setPage(value=>value+1)}>Next<ChevronRight size={14}/></Button>
        </nav>
      </>:<ResearchEmptyState filter={filter}/>}
    </>}
  </div>;
}
