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