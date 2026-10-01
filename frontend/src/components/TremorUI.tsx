import type {CSSProperties,KeyboardEvent,ReactNode} from 'react';
import {useId,useMemo,useState} from 'react';
import {AlertTriangle,CheckCircle2,ChevronDown,Info} from 'lucide-react';
import {Area,AreaChart,Bar,BarChart,Cell,CartesianGrid,Pie,PieChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';

export function TremorBadge({children,tone='blue'}:{children:ReactNode;tone?:'blue'|'green'|'amber'|'red'|'purple'}){
  return <span className={'tremor-badge tone-'+tone}>{children}</span>;
}

export function TremorCard({children,className='',title,description,action}:{children:ReactNode;className?:string;title?:ReactNode;description?:ReactNode;action?:ReactNode}){
  return <section className={'tremor-card glass-card '+className}>
    {(title||description||action)&&<header className="tremor-card-head">
      <div className="min-w-0"><h2 className="tremor-card-title">{title}</h2>{description&&<p className="tremor-card-description">{description}</p>}</div>
      {action&&<div className="tremor-card-action">{action}</div>}
    </header>}
    <div className="tremor-card-body">{children}</div>
  </section>;
}

export function TremorCallout({children,tone='blue',title}:{children:ReactNode;tone?:'blue'|'amber'|'green'|'red';title?:ReactNode}){
  const Icon=tone==='green'?CheckCircle2:tone==='amber'||tone==='red'?AlertTriangle:Info;
  return <aside className={'tremor-callout tone-'+tone} role={tone==='red'?'alert':'note'}>
    <Icon aria-hidden="true"/>
    <div>{title&&<strong>{title}</strong>}<div>{children}</div></div>
  </aside>;
}

export function TremorAccordion({label,children,className=''}:{label:ReactNode;children:ReactNode;className?:string}){
  return <details className={'tremor-accordion '+className}>
    <summary><span>{label}</span><ChevronDown aria-hidden="true"/></summary>
    <div className="tremor-accordion-body">{children}</div>
  </details>;
}

export function TremorMetric({label,value,detail,icon,trend}:{label:string;value:ReactNode;detail?:ReactNode;icon?:ReactNode;trend?:string}){
  return <article className="tremor-metric">
    <div className="tremor-metric-top"><div><span className="tremor-metric-label">{label}</span>{detail&&<p className="tremor-metric-detail">{detail}</p>}</div>{icon&&<span className="tremor-metric-icon">{icon}</span>}</div>
    <div className="tremor-metric-value-row"><strong className="tremor-metric-value">{value}</strong>{trend&&<span className="tremor-trend">{trend}</span>}</div>
  </article>;
}

export function TremorChartTooltip({active,payload,label,valueFormatter}:{active?:boolean;payload?:Array<{name?:string;value?:number;payload?:Record<string,unknown>}>;label?:string|number;valueFormatter?:(value:number)=>ReactNode}){
  if(!active||!payload?.length)return null;
  return <div className="tremor-tooltip" role="status"><div className="tremor-tooltip-label">{label}</div>{payload.map((item,index)=><div className="tremor-tooltip-row" key={index}><span>{item.name}</span><strong>{typeof item.value==='number'?(valueFormatter?.(item.value)??item.value.toLocaleString()):String(item.value??'—')}</strong></div>)}</div>;
}

export function TremorBarChart({data,category,value,height=260,showGrid=false}:{data:Record<string,any>[];category:string;value:string;height?:number;showGrid?:boolean}){
  const grad=useId().replace(/:/g,'');
  return <div className="tremor-chart" style={{height}} role="img" aria-label={`${value} by ${category}`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={data} margin={{top:12,right:10,left:0,bottom:28}}>
    <defs><linearGradient id={grad} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="var(--tremor-accent)" stopOpacity=".95"/><stop offset="100%" stopColor="var(--tremor-accent-2)" stopOpacity=".68"/></linearGradient></defs>
    {showGrid&&<CartesianGrid vertical={false} stroke="var(--tremor-grid)"/>}
    <XAxis dataKey={category} tickLine={false} axisLine={false} tick={{fontSize:10,fill:'var(--tremor-muted)'}} interval={0}/>
    <YAxis tickLine={false} axisLine={false} tick={{fontSize:10,fill:'var(--tremor-muted)'}} width={40}/>
    <Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip/>}/>
    <Bar dataKey={value} radius={[6,6,2,2]} fill={'url(#'+grad+')'} maxBarSize={44}/>
  </BarChart></ResponsiveContainer></div>;
}

export function TremorAreaChart({data,xKey,categories,height=260}:{data:Record<string,any>[];xKey:string;categories:{key:string;label:string}[];height?:number}){
  const id=useId().replace(/:/g,'');
  const colors=['var(--tremor-accent)','var(--tremor-accent-2)','var(--tremor-accent-3)'];
  return <div className="tremor-chart" style={{height}} role="img" aria-label={`${categories.map(item=>item.label).join(', ')} by ${xKey}`}><ResponsiveContainer width="100%" height="100%"><AreaChart accessibilityLayer data={data} margin={{top:12,right:10,left:0,bottom:22}}>
    <defs>{categories.map((_,i)=><linearGradient key={i} id={id+i} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={colors[i%colors.length]} stopOpacity=".30"/><stop offset="100%" stopColor={colors[i%colors.length]} stopOpacity=".02"/></linearGradient>)}</defs>
    <CartesianGrid vertical={false} stroke="var(--tremor-grid)"/>
    <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{fontSize:10,fill:'var(--tremor-muted)'}}/>
    <YAxis tickLine={false} axisLine={false} tick={{fontSize:10,fill:'var(--tremor-muted)'}} width={40}/>
    <Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip/>}/>
    {categories.map((c,i)=><Area key={c.key} type="monotone" dataKey={c.key} name={c.label} stroke={colors[i%colors.length]} strokeWidth={2.2} fill={'url(#'+id+i+')'} dot={false}/>)}
  </AreaChart></ResponsiveContainer></div>;
}

export function TremorDonut({data,nameKey,valueKey,height=220,centerLabel}:{data:Record<string,any>[];nameKey:string;valueKey:string;height?:number;centerLabel?:ReactNode}){
  const colors=['var(--tremor-accent)','var(--tremor-accent-2)','var(--tremor-accent-3)','var(--tremor-accent-4)','var(--tremor-accent-5)'];
  const total=useMemo(()=>data.reduce((sum,item)=>sum+Number(item[valueKey]||0),0),[data,valueKey]);
  const [active,setActive]=useState<number|null>(null);
  return <div className="tremor-donut-layout">
    <div className="tremor-donut-chart" style={{height}} role="img" aria-label={`${valueKey} distribution by ${nameKey}`}><ResponsiveContainer width="100%" height="100%"><PieChart accessibilityLayer>
      <Pie data={data} dataKey={valueKey} nameKey={nameKey} innerRadius="70%" outerRadius="92%" paddingAngle={2} startAngle={90} endAngle={-270} stroke="var(--tremor-card)" strokeWidth={2} isAnimationActive={false} activeIndex={active??undefined} activeShape={(props:any)=><path {...props} opacity=".92"/>} onMouseEnter={(_,i)=>setActive(i)} onMouseLeave={()=>setActive(null)}>
        {data.map((_,i)=><Cell key={i} fill={colors[i%colors.length]}/>)}
      </Pie>
      <Tooltip content={<TremorChartTooltip/>}/>
    </PieChart></ResponsiveContainer>{centerLabel&&<div className="tremor-donut-center"><strong>{centerLabel}</strong><span>{total.toLocaleString()} total</span></div>}</div>
    <div className="tremor-legend">{data.map((item,i)=><button type="button" aria-pressed={active===i} className={'tremor-legend-row '+(active===i?'is-active':'')} key={String(item[nameKey])} onFocus={()=>setActive(i)} onBlur={()=>setActive(null)} onClick={()=>setActive(current=>current===i?null:i)} onMouseEnter={()=>setActive(i)} onMouseLeave={()=>setActive(null)}><span className="tremor-legend-dot" style={{'--legend-color':colors[i%colors.length]} as CSSProperties}/><span className="truncate">{String(item[nameKey])}</span><strong>{Number(item[valueKey]||0).toLocaleString()}</strong></button>)}</div>
  </div>;
}

export function TremorTracker({items}:{items:{label:string;status:'good'|'warning'|'error'|'neutral';tooltip?:string}[]}){
  const tone:{[key:string]:string}={good:'var(--tremor-good)',warning:'var(--tremor-warn)',error:'var(--tremor-bad)',neutral:'var(--tremor-neutral)'};
  return <div className="tremor-tracker" role="img" aria-label={items.map(item=>`${item.label}: ${item.status}`).join(', ')}>{items.map((item,index)=><span aria-hidden="true" key={index} title={item.tooltip||item.label} className="tremor-track-block" style={{background:tone[item.status]}}/>)}</div>;
}

export function TremorProgressBar({value,label,detail}:{value:number;label?:string;detail?:string}){
  const safe=Math.max(0,Math.min(100,value));
  return <div className="tremor-progress-row"><div className="min-w-0 flex-1">{label&&<div className="flex items-center justify-between gap-3"><span className="tremor-progress-label truncate">{label}</span><strong className="mono text-[11px]">{Math.round(safe)}%</strong></div>}{detail&&<p className="tremor-progress-detail">{detail}</p>}<div className="tremor-progress" role="progressbar" aria-label={label||'Progress'} aria-valuemin={0} aria-valuemax={100} aria-valuenow={safe}><span style={{width:safe+'%'}}/></div></div></div>;
}

export function TremorListRow({children,meta,status,href}:{children:ReactNode;meta?:ReactNode;status?:ReactNode;href?:string}){
  const body=<><div className="min-w-0 flex-1">{children}</div><div className="flex items-center gap-3">{meta}{status}</div></>;
  return href?<a href={href} className="tremor-list-row">{body}</a>:<div className="tremor-list-row">{body}</div>;
}

export function TremorTabs({items,active,onChange}:{items:string[];active:string;onChange:(v:string)=>void}){
  const move=(event:KeyboardEvent<HTMLButtonElement>,index:number)=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();
    const next=event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowRight'?1:-1)+items.length)%items.length;
    onChange(items[next]);
    (event.currentTarget.parentElement?.children[next] as HTMLElement|undefined)?.focus();
  };
  return <div className="tremor-tabs" role="tablist">{items.map((item,index)=><button type="button" role="tab" tabIndex={item===active?0:-1} aria-selected={item===active} className={item===active?'is-active':''} onKeyDown={event=>move(event,index)} onClick={()=>onChange(item)} key={item}>{item}</button>)}</div>;
}
