import type {ReactNode} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Atom,Database,LoaderCircle,RefreshCw} from 'lucide-react';
import {Card,Badge,Select} from './ui';
import {modelLabels,metric,shortId} from '../utils/format';
import type {Dataset,ModelRecord,Metrics,MetricName} from '../types/qhealth';
import {AnimatedSection,BlurText,GradientText,Reveal,ShinyText} from './reactbits';
import {TremorAccordion,TremorCallout,TremorMetric} from './TremorUI';

export function PageHeader({eyebrow,title,description,actions}:{eyebrow:string;title:string;description:string;actions?:ReactNode}){return <AnimatedSection className="page-hero"><div className="flex flex-wrap items-end justify-between gap-5"><div><div className="eyebrow"><ShinyText>{eyebrow}</ShinyText></div><h1 className="headline"><BlurText>{title}</BlurText></h1><p className="subhead"><GradientText>{description}</GradientText></p></div>{actions&&<div className="flex flex-wrap gap-2">{actions}</div>}</div></AnimatedSection>}
export function StatusBadge({value}:{value:string}){const tone=['ready','succeeded','completed'].includes(value)?'green':['failed','cancelled','interrupted'].includes(value)?'red':value==='running'||value==='queued'?'amber':'blue';return <Badge tone={tone}>{value.replaceAll('_',' ')}</Badge>}
export function MetricCard({label,value,detail,icon}:{label:string;value:ReactNode;detail?:string;icon?:ReactNode}){return <TremorMetric label={label} value={value} detail={detail} icon={icon}/>}
function errorTitle(error:string){
  if(/\b404\b|not found|does not exist/i.test(error))return 'Research record not found';
  if(/\b401\b|\b403\b|permission|unauthori[sz]ed|forbidden/i.test(error))return 'Research access is unavailable';
  if(/network|fetch|offline|unavailable|timed out|timeout/i.test(error))return 'Research service is unavailable';
  return 'Unable to load research data';
}

export function ErrorBanner({error,retry}:{error?:string;retry?:()=>void}){
  if(!error)return null;
  return <TremorCallout tone="red" title={errorTitle(error)}>
    <div className="error-banner-content"><span>{error}</span>{retry&&<button className="btn btn-outline error-banner-retry" type="button" onClick={retry}><RefreshCw size={13}/>Retry</button>}</div>
  </TremorCallout>;
}

export function EmptyState({title,children,action}:{title:string;children:ReactNode;action?:ReactNode}){
  return <Card className="empty-state-card py-12 text-center"><div className="mx-auto mb-3 grid h-11 w-11 place-items-center rounded-full bg-muted"><Atom size={18}/></div><h3 className="font-semibold">{title}</h3><p className="mt-1 text-sm muted">{children}</p>{action&&<div className="mt-4 flex justify-center">{action}</div>}</Card>;
}

export function Loading(){
  return <Reveal><div className="research-loading-state tremor-card" role="status" aria-live="polite" aria-busy="true">
    <div className="research-loading-header"><span className="research-skeleton research-skeleton-eyebrow"/><span className="research-loading-label"><LoaderCircle size={14} className="animate-spin"/>Loading research data…</span></div>
    <span className="research-skeleton research-skeleton-title"/><span className="research-skeleton research-skeleton-copy"/>
    <div className="research-loading-grid"><span className="research-skeleton research-skeleton-panel"/><span className="research-skeleton research-skeleton-panel"/><span className="research-skeleton research-skeleton-panel research-skeleton-panel-wide"/></div>
  </div></Reveal>;
}
export function Notice({children,tone='blue'}:{children:ReactNode;tone?:'blue'|'amber'|'green'}){return <TremorCallout tone={tone}>{children}</TremorCallout>}
export function JsonDisclosure({label,value}:{label:string;value:unknown}){return <TremorAccordion className="mt-4" label={label}><pre className="max-h-[360px] overflow-auto whitespace-pre-wrap break-all text-[10px] leading-relaxed muted">{JSON.stringify(value,null,2)}</pre></TremorAccordion>}
export function ModelSelect({models,value,onChange,quantumOnly=false}:{models:ModelRecord[];value:string;onChange:(v:string)=>void;quantumOnly?:boolean}){const available=models.filter(m=>m.status==='ready'&&(!quantumOnly||['vqc','qsvc','qnn'].includes(m.model_type)));return <label className="field"><span>Registered model</span><Select value={value} onChange={e=>onChange(e.target.value)}><option value="">Choose completed model</option>{available.map(m=><option key={m.id} value={m.id}>{modelLabels[m.model_type]} · {shortId(m.id)}</option>)}</Select></label>}
export function MetricRow({label,value}:{label:string;value:number|null|undefined}){return <div className="flex items-center justify-between border-b py-2 last:border-b-0"><span className="text-xs muted">{label}</span><strong className="mono text-xs">{metric(value)}</strong></div>}
export const metricNames:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];
export function MetricGrid({metrics}:{metrics:Metrics}){return <div className="tremor-metric-grid">{metricNames.map(name=><article className="tremor-metric" key={name}><span className="tremor-metric-label">{name.replace('_',' ')}</span><strong className="tremor-metric-value mt-5 block">{metric(metrics[name],name!=='roc_auc')}</strong></article>)}</div>}
export function DatasetSelect({value,onChange,datasets}:{value:string;onChange:(v:string)=>void;datasets:Dataset[]}){return <Card className="flex flex-wrap items-end gap-3 py-4"><label className="field min-w-[260px] flex-1"><span>Active research dataset</span><Select value={value} onChange={e=>onChange(e.target.value)}><option value="">Select a dataset</option>{datasets.map(d=><option value={d.id} key={d.id}>{d.name} · {d.provenance.row_count} samples</option>)}</Select></label><Link className="btn btn-outline" to="/datasets"><Database size={14}/>Manage datasets</Link></Card>}

export const researchWorkflow=[
  {label:'Data',path:'/datasets',caption:'Register a traceable input'},
  {label:'Quality',path:'/quality',caption:'Validate integrity and balance'},
  {label:'Preprocess',path:'/preprocessing',caption:'Fit transformations safely'},
  {label:'Features',path:'/features',caption:'Select the model representation'},
  {label:'PCA',path:'/pca',caption:'Reduce dimensions where configured'},
  {label:'Train',path:'/training',caption:'Run classical and quantum models'},
  {label:'Compare',path:'/comparison',caption:'Evaluate under shared conditions'},
  {label:'Robustness',path:'/robustness',caption:'Measure controlled degradation'},
  {label:'Explain',path:'/explainability',caption:'Measure feature influence'},
  {label:'Predict',path:'/prediction',caption:'Generate a research output'},
  {label:'Report',path:'/experiments',caption:'Preserve experiment provenance'},
] as const;

export function ResearchPipeline({current}:{current?:string}){
  return <section className="research-pipeline-panel" aria-label="Q-Health research workflow">
    <div className="flex items-start justify-between gap-3">
      <div><div className="eyebrow">TRACEABLE WORKFLOW</div><h2 className="section-title mt-1">From evidence to measured output</h2></div>
      <span className="metric-label hidden sm:block">Select a stage to inspect it</span>
    </div>
    <div className="research-pipeline-steps">
      {researchWorkflow.map((stage,index)=><div className="research-pipeline-step-wrap" key={stage.path}>
        <Link to={stage.path} className={'research-pipeline-step '+(current===stage.path?'is-current':'')} aria-current={current===stage.path?'page':undefined}>
          <span className="research-pipeline-index">{String(index+1).padStart(2,'0')}</span>
          <span><strong>{stage.label}</strong><small>{stage.caption}</small></span>
        </Link>
        {index<researchWorkflow.length-1&&<ArrowRight className="research-pipeline-arrow" size={13} aria-hidden="true"/>}
      </div>)}
    </div>
  </section>;
}
