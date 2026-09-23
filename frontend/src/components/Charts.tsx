import {Bar,BarChart,CartesianGrid,Cell,Line,LineChart,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
import type {Dataset,Influence,Metrics,ModelRecord} from '../types/qhealth';
import {metric,modelLabels} from '../utils/format';

const modelColors:Record<string,string>={logistic_regression:'#2563eb',svm:'#0f766e',random_forest:'#f59e0b',vqc:'#7c3aed',qsvc:'#c026d3',qnn:'#0891b2'};

export function ClassBalance({dataset}:{dataset:Dataset}){
 const items=Object.entries(dataset.provenance.class_distribution).map(([name,value])=>({name,value}));
 return <ValueBars items={items}/>;
}

export function ValueBars({items}:{items:{name:string;value:number}[]}){
 if(!items.length)return <div className="text-xs muted">No measured values.</div>;
 return <div className="h-[270px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={items} margin={{top:12,right:12,left:0,bottom:36}}><CartesianGrid vertical={false} stroke="hsl(var(--border))"/><XAxis dataKey="name" tick={{fontSize:10}} angle={-18} textAnchor="end" interval={0}/><YAxis tick={{fontSize:10}} tickLine={false} axisLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid hsl(var(--border))',background:'hsl(var(--card))',fontSize:12}}/><Bar dataKey="value" fill="#2563eb" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></div>;
}

export function MetricBars({metrics}:{metrics:Metrics}){
 return <ValueBars items={[
  ['Accuracy',metrics.accuracy],['Precision',metrics.precision],['Recall',metrics.recall],['F1',metrics.f1],['Specificity',metrics.specificity],['ROC-AUC',metrics.roc_auc]
 ].map(([name,value])=>({name:String(name),value:Number(value??0)}))}/>;
}

export function InfluenceBars({items}:{items:Influence[]}){
 return <ValueBars items={items.slice(0,24).map(item=>({name:item.feature,value:item.magnitude}))}/>;
}

export function ScoreLandscape({data}:{data:{score:number,y:number,label:string,id:string,color?:string}[]}){
 return <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:16,right:16,bottom:16,left:0}}><CartesianGrid stroke="hsl(var(--border))" vertical={false}/><XAxis type="number" dataKey="score" domain={[0,100]} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="y" tickLine={false} axisLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid hsl(var(--border))',background:'hsl(var(--card))',fontSize:12}}/><Scatter data={data}>{data.map((d,i)=><Cell key={i} fill={d.color||'#2563eb'} fillOpacity={.7}/>)}</Scatter></ScatterChart></ResponsiveContainer></div>;
}

export function RocChart({models}:{models:ModelRecord[]}){
 const curves=models.flatMap(model=>model.metrics.test?.roc_curve?[{name:modelLabels[model.model_type],kind:model.model_type,curve:model.metrics.test.roc_curve}]:[]);
 if(!curves.length)return <div className="h-[300px] grid place-items-center text-sm muted">No measured ROC curve is available.</div>;
 const count=Math.max(...curves.map(c=>c.curve.fpr.length));
 const rows=Array.from({length:count},(_,i)=>{const row:Record<string,number>={x:i/Math.max(count-1,1)};curves.forEach((c,j)=>row['c'+j]=c.curve.tpr[i]??c.curve.tpr.at(-1)??0);return row});
 return <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={rows} margin={{top:10,right:10,left:0,bottom:18}}><CartesianGrid stroke="hsl(var(--border))" vertical={false}/><XAxis dataKey="x" domain={[0,1]} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><YAxis domain={[0,1]} tickLine={false} axisLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid hsl(var(--border))',background:'hsl(var(--card))',fontSize:12}}/><Line type="monotone" dataKey="chance" stroke="transparent" dot={false}/>{curves.map((c,i)=><Line key={c.name} type="monotone" dataKey={'c'+i} name={c.name} stroke={modelColors[c.kind]||'#2563eb'} dot={false} strokeWidth={2}/>)}</LineChart></ResponsiveContainer></div>;
}
