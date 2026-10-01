import type {CSSProperties,ReactNode} from 'react';
import {Activity,ArrowUpRight,CheckCircle2,Minus,TriangleAlert} from 'lucide-react';

type Tone='blue'|'green'|'amber'|'red'|'purple'|'slate';

export function WorkbenchRail({items}:{items:{label:string;value:ReactNode;detail?:ReactNode;tone?:Tone}[]}){
  return <section className="workbench-rail" aria-label="Page summary">
    {items.map((item,index)=><article className={'workbench-rail-item tone-'+(item.tone||'blue')} key={index}>
      <div className="workbench-rail-label">{item.label}</div>
      <div className="workbench-rail-value">{item.value??'—'}</div>
      {item.detail&&<div className="workbench-rail-detail">{item.detail}</div>}
    </article>)}
  </section>;
}

export function WorkbenchToolbar({title,description,children}:{title:string;description?:string;children?:ReactNode}){
  return <section className="workbench-toolbar">
    <div><h2>{title}</h2>{description&&<p>{description}</p>}</div>
    {children&&<div className="workbench-toolbar-actions">{children}</div>}
  </section>;
}

export function StatusStrip({items}:{items:{label:string;value:string;status?:'good'|'warning'|'bad'|'neutral'}[]}){
  const icons={good:<CheckCircle2/>,warning:<TriangleAlert/>,bad:<TriangleAlert/>,neutral:<Minus/>};
  return <div className="status-strip">{items.map((item,index)=><div className={'status-strip-item is-'+(item.status||'neutral')} key={index}>
    <span className="status-strip-icon">{icons[item.status||'neutral']}</span>
    <span><small>{item.label}</small><strong>{item.value}</strong></span>
  </div>)}</div>;
}

export function CategoryMeter({value,label,leftLabel='0',rightLabel='100',tone='blue'}:{value:number;label:string;leftLabel?:string;rightLabel?:string;tone?:Tone}){
  const safe=Math.max(0,Math.min(100,Number.isFinite(value)?value:0));
  return <div className={'category-meter tone-'+tone}>
    <div className="category-meter-head"><span>{label}</span><strong>{safe.toFixed(1)}%</strong></div>
    <div className="category-meter-track"><span style={{width:safe+'%'}}/></div>
    <div className="category-meter-scale"><span>{leftLabel}</span><span>{rightLabel}</span></div>
  </div>;
}

export function ProgressRing({value,label,detail,tone='blue'}:{value:number;label:string;detail?:string;tone?:Tone}){
  const safe=Math.max(0,Math.min(100,Number.isFinite(value)?value:0));
  return <div className={'progress-ring tone-'+tone}>
    <div className="progress-ring-visual" style={{'--ring-progress':safe} as CSSProperties}><div><strong>{Math.round(safe)}%</strong></div></div>
    <div><span>{label}</span>{detail&&<small>{detail}</small>}</div>
  </div>;
}

export function RankedList({items,empty='No measured values'}:{items:{label:string;value:number;display?:ReactNode;tone?:Tone}[];empty?:string}){
  const max=Math.max(...items.map(x=>Math.abs(x.value)),0);
  if(!items.length)return <div className="compact-empty"><Activity size={16}/><span>{empty}</span></div>;
  return <div className="ranked-list">{items.map((item,index)=><div className="ranked-row" key={index}>
    <div className="ranked-row-head"><span><em>{String(index+1).padStart(2,'0')}</em>{item.label}</span><strong>{item.display??item.value.toLocaleString()}</strong></div>
    <div className={'ranked-row-track tone-'+(item.tone||'blue')}><span style={{width:(max?Math.abs(item.value)/max*100:0)+'%'}}/></div>
  </div>)}</div>;
}

export function ResearchBoundary({children}:{children:ReactNode}){
  return <aside className="research-boundary"><div><TriangleAlert size={16}/><strong>Research boundary</strong></div><p>{children}</p></aside>;
}

export function InlineLink({children}:{children:ReactNode}){
  return <span className="inline-link">{children}<ArrowUpRight size={12}/></span>;
}

export function PipelineFlow({items}:{items:{label:string;detail?:string;status:'complete'|'current'|'waiting'|'blocked'}[]}){
  return <ol className="pipeline-flow" aria-label="Workflow progression">
    {items.map((item,index)=><li className={'pipeline-flow-step is-'+item.status} key={item.label}>
      <span className="pipeline-flow-index">{String(index+1).padStart(2,'0')}</span>
      <div><strong>{item.label}</strong>{item.detail&&<small>{item.detail}</small>}</div>
    </li>)}
  </ol>;
}

export function DistributionStrip({items}:{items:{label:string;value:number;tone?:Tone}[]}){
  const total=items.reduce((sum,item)=>sum+Math.max(0,item.value),0);
  if(!total)return <div className="distribution-empty">No measured distribution</div>;
  return <div className="distribution">
    <div className="distribution-track" aria-label="Measured distribution">{items.map((item,index)=><span className={'tone-'+(item.tone||'blue')} style={{width:(item.value/total*100)+'%'}} title={`${item.label}: ${item.value}`} key={index}/>)}</div>
    <div className="distribution-legend">{items.map((item,index)=><div key={index}><i className={'tone-'+(item.tone||'blue')}/><span>{item.label}</span><strong>{item.value.toLocaleString()}</strong></div>)}</div>
  </div>;
}

export function ProbabilityBand({probability,threshold,label='Positive-class probability'}:{probability:number|null|undefined;threshold:number|null|undefined;label?:string}){
  const value=probability==null?null:Math.max(0,Math.min(1,probability));
  const cut=threshold==null?null:Math.max(0,Math.min(1,threshold));
  return <div className="probability-band">
    <div className="probability-band-head"><span>{label}</span><strong>{value==null?'Not reported':(value*100).toFixed(1)+'%'}</strong></div>
    <div className="probability-band-track">
      {value!=null&&<span className="probability-band-fill" style={{width:(value*100)+'%'}}/>}
      {cut!=null&&<i className="probability-band-threshold" style={{left:(cut*100)+'%'}}><em>Threshold {(cut*100).toFixed(1)}%</em></i>}
    </div>
    <div className="probability-band-scale"><span>0%</span><span>50%</span><span>100%</span></div>
  </div>;
}

export function EvidenceHeader({eyebrow,title,description,meta,action}:{eyebrow:string;title:string;description?:string;meta?:ReactNode;action?:ReactNode}){
  return <header className="evidence-header">
    <div><span>{eyebrow}</span><h2>{title}</h2>{description&&<p>{description}</p>}{meta&&<div className="evidence-header-meta">{meta}</div>}</div>
    {action&&<div className="evidence-header-action">{action}</div>}
  </header>;
}