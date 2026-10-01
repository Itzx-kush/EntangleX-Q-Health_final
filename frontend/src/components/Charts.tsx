import {Bar,BarChart,CartesianGrid,Cell,Line,LineChart,ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
import type {Dataset,Influence,Metrics,ModelRecord,OperatingPoint,RobustnessEvidence} from '../types/qhealth';
import {metric,modelLabels} from '../utils/format';
import {TremorChartTooltip} from './TremorUI';

const modelColors:Record<string,string>={logistic_regression:'var(--chart-blue)',svm:'var(--chart-teal)',random_forest:'var(--chart-amber)',vqc:'var(--chart-purple)',qsvc:'var(--chart-magenta)',qnn:'var(--chart-cyan)'};

export function ClassBalance({dataset}:{dataset:Dataset}){
 const items=Object.entries(dataset.provenance.class_distribution).map(([name,value])=>({name,value}));
 return <ValueBars items={items}/>;
}

export function ValueBars({items}:{items:{name:string;value:number}[]}){
 if(!items.length)return <div className="text-xs muted">No measured values.</div>;
 return <div className="tremor-chart h-[270px]" role="img" aria-label="Measured value comparison"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={items} margin={{top:12,right:12,left:0,bottom:36}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip/>}/><Bar dataKey="value" fill="var(--tremor-accent)" radius={[5,5,0,0]} maxBarSize={46}/></BarChart></ResponsiveContainer></div>;
}

export function MetricBars({metrics}:{metrics:Metrics}){
 return <ValueBars items={[
  ['Accuracy',metrics.accuracy],['Precision',metrics.precision],['Recall',metrics.recall],['F1',metrics.f1],['Specificity',metrics.specificity],['ROC-AUC',metrics.roc_auc]
 ].map(([name,value])=>({name:String(name),value:Number(value??0)}))}/>;
}

export function InfluenceBars({items}:{items:Influence[]}){
 return <ValueBars items={items.slice(0,24).map(item=>({name:item.feature,value:item.signed_mean??item.magnitude}))}/>;
}

export function ScoreLandscape({data}:{data:{score:number,y:number,label:string,id:string,color?:string}[]}){
 return <div className="tremor-chart h-[320px]" role="img" aria-label="Model score landscape"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer margin={{top:16,right:16,bottom:16,left:0}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis type="number" dataKey="score" domain={[0,100]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="y" tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip/>}/><Scatter data={data}>{data.map((d,i)=><Cell key={i} fill={d.color||'var(--tremor-accent)'} fillOpacity={.75}/>)}</Scatter></ScatterChart></ResponsiveContainer></div>;
}

export function RocChart({models}:{models:ModelRecord[]}){
 const curves=models.flatMap(model=>model.metrics.test?.roc_curve?[{name:modelLabels[model.model_type],kind:model.model_type,curve:model.metrics.test.roc_curve}]:[]);
 if(!curves.length)return <div className="h-[300px] grid place-items-center text-sm muted">No measured ROC curve is available.</div>;
 const count=Math.max(...curves.map(c=>c.curve.fpr.length));
 const rows=Array.from({length:count},(_,i)=>{const row:Record<string,number>={x:i/Math.max(count-1,1)};curves.forEach((c,j)=>row['c'+j]=c.curve.tpr[i]??c.curve.tpr.at(-1)??0);return row});
 return <div className="tremor-chart h-[320px]" role="img" aria-label="Measured ROC curves"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:10,right:10,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="x" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><YAxis domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Line type="monotone" dataKey="chance" stroke="transparent" dot={false}/>{curves.map((c,i)=><Line key={c.name} type="monotone" dataKey={'c'+i} name={c.name} stroke={modelColors[c.kind]||'var(--tremor-accent)'} dot={false} strokeWidth={2}/>)}</LineChart></ResponsiveContainer></div>;
}

export function ThresholdTradeoffChart({operatingPoint}:{operatingPoint:OperatingPoint}){
 const rows=[...operatingPoint.curve].sort((a,b)=>a.threshold-b.threshold);
 if(!rows.length)return <div className="h-[260px] grid place-items-center text-sm muted">No validation threshold curve is available for this legacy experiment.</div>;
 return <div className="tremor-chart h-[300px]" role="img" aria-label="Validation sensitivity and specificity by research threshold"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="threshold" type="number" domain={['dataMin','dataMax']} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><YAxis domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>`${Math.round(Number(value)*100)}%`}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>metric(value)}/>}/><Line type="monotone" dataKey="sensitivity" name="Validation sensitivity" stroke="var(--chart-red)" dot={false} strokeWidth={2}/><Line type="monotone" dataKey="specificity" name="Validation specificity" stroke="var(--chart-blue)" dot={false} strokeWidth={2}/>{operatingPoint.selected_threshold!==null&&<ReferenceLine x={operatingPoint.selected_threshold} stroke="var(--chart-purple)" strokeDasharray="4 4" label={{value:'Selected',position:'insideTopRight',fontSize:10,fill:'var(--tremor-muted)'}}/>}</LineChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Selected research threshold: {operatingPoint.selected_threshold===null?'Not feasible':operatingPoint.selected_threshold.toFixed(4)}</p></div>;
}

export function RobustnessDeltaChart({records}:{records:RobustnessEvidence[]}){
 const measured=records.filter(record=>record.status==='evaluated'&&record.perturbed_metrics);
 const names=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 if(!measured.length)return <div className="h-[260px] grid place-items-center text-sm muted">No evaluated perturbation values are available.</div>;
 const rows=names.map(name=>({metric:name,...Object.fromEntries(measured.map(record=>[record.model_id,record.degradation_delta[name]]))}));
 return <div className="tremor-chart h-[300px]" role="img" aria-label="Observed degradation delta chart"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:20}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="metric" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-text)"/>{measured.map(record=><Bar key={record.model_id} dataKey={record.model_id} name={modelLabels[record.model_type]} fill={modelColors[record.model_type]||'var(--tremor-accent)'} radius={[4,4,0,0]}/>)}</BarChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Observed change: perturbed − baseline</p></div>;
}
