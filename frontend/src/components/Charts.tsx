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
 ].filter(([,value])=>typeof value==='number'&&Number.isFinite(value)).map(([name,value])=>({name:String(name),value:value as number}))}/>;
}

export function InfluenceBars({items}:{items:Influence[]}){
 return <ValueBars items={items.slice(0,24).map(item=>({name:item.feature,value:item.magnitude}))}/>;
}

export function ScoreLandscape({data}:{data:{score:number,y:number,label:string,id:string,color?:string}[]}){
 return <div className="h-[320px]"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:16,right:16,bottom:16,left:0}}><CartesianGrid stroke="hsl(var(--border))" vertical={false}/><XAxis type="number" dataKey="score" domain={[0,100]} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="y" tickLine={false} axisLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid hsl(var(--border))',background:'hsl(var(--card))',fontSize:12}}/><Scatter data={data}>{data.map((d,i)=><Cell key={i} fill={d.color||'#2563eb'} fillOpacity={.7}/>)}</Scatter></ScatterChart></ResponsiveContainer></div>;
}

export function RocChart({models}:{models:ModelRecord[]}){
 const curves=models.flatMap(model=>{
  const curve=model.metrics.test?.roc_curve;
  return curve&&curve.fpr.length>0&&curve.tpr.length>0?[{name:modelLabels[model.model_type],kind:model.model_type,curve}]:[];
 });
 if(!curves.length)return <div className="h-[300px] grid place-items-center text-sm muted">No measured ROC curve is available.</div>;
 return <div className="h-[320px]" role="img" aria-label="Measured ROC curves: false positive rate versus true positive rate"><ResponsiveContainer width="100%" height="100%"><ScatterChart margin={{top:10,right:16,left:8,bottom:24}}><CartesianGrid stroke="hsl(var(--border))"/><XAxis type="number" dataKey="fpr" name="False positive rate" domain={[0,1]} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="tpr" name="True positive rate" domain={[0,1]} tickLine={false} axisLine={false}/><Tooltip contentStyle={{borderRadius:12,border:'1px solid hsl(var(--border))',background:'hsl(var(--card))',fontSize:12}}/>{curves.map(c=><Scatter key={c.name} name={c.name} data={c.curve.fpr.map((fpr,i)=>({fpr,tpr:c.curve.tpr[i]})).filter(point=>Number.isFinite(point.fpr)&&Number.isFinite(point.tpr))} line={{stroke:modelColors[c.kind]||'#2563eb',strokeWidth:2}} fill={modelColors[c.kind]||'#2563eb'} isAnimationActive={false}/>)}</ScatterChart></ResponsiveContainer></div>;
}
