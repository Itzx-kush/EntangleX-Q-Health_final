import {Bar,BarChart,CartesianGrid,Cell,Legend,Line,LineChart,ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
import type {CalibrationDiagnostics,Dataset,Influence,Metrics,ModelRecord,OperatingPoint,RobustnessEvidence} from '../types/qhealth';
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
 const values=items.slice(0,12).map(item=>({name:item.feature,value:item.signed_mean??item.magnitude}));
 if(!values.length)return <div className="text-xs muted">No measured contributions.</div>;
 const height=Math.max(260,values.length*28);
 return <div className="tremor-chart" style={{height}} role="img" aria-label="Signed feature contributions"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={values} layout="vertical" margin={{top:8,right:14,left:8,bottom:8}}>
  <CartesianGrid horizontal={false} stroke="var(--tremor-grid)"/>
  <XAxis type="number" tick={{fontSize:9,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(3)}/>
  <YAxis type="category" dataKey="name" width={104} tick={{fontSize:9,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/>
  <Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/>
  <ReferenceLine x={0} stroke="var(--tremor-border)"/>
  <Bar dataKey="value" radius={[0,4,4,0]} maxBarSize={16}>{values.map((item,index)=><Cell key={index} fill={item.value<0?'var(--tremor-warn)':'var(--tremor-accent)'}/>)}</Bar>
 </BarChart></ResponsiveContainer></div>;
}

export function ScoreLandscape({data}:{data:{score:number,y:number,label:string,id:string,color?:string}[]}){
 return <div className="tremor-chart h-[320px]" role="img" aria-label="Model score landscape"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer margin={{top:16,right:16,bottom:16,left:0}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis type="number" dataKey="score" domain={[0,100]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="y" tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip/>}/><Scatter data={data}>{data.map((d,i)=><Cell key={i} fill={d.color||'var(--tremor-accent)'} fillOpacity={.75}/>)}</Scatter></ScatterChart></ResponsiveContainer></div>;
}

export function RocChart({models}:{models:ModelRecord[]}){
 const curves=models.flatMap(model=>{
  const curve=model.metrics.test?.roc_curve;
  if(!curve||!curve.fpr.length||curve.fpr.length!==curve.tpr.length)return [];
  return [{name:modelLabels[model.model_type],kind:model.model_type,auc:model.metrics.test?.roc_auc,points:curve.fpr.map((fpr,index)=>({fpr,tpr:curve.tpr[index]}))}];
 });
 if(!curves.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted held-out ROC curve is available. Models without valid curve coordinates are excluded.</div>;
 return <div><div className="mb-3 flex flex-wrap gap-2">{curves.map(curve=><span className="rounded-full border px-2.5 py-1 text-[10px]" key={curve.name}><strong>{curve.name}</strong> · ROC-AUC {metric(curve.auc)}</span>)}</div><div className="tremor-chart h-[320px]" role="img" aria-label="Persisted held-out ROC curves"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer margin={{top:10,right:16,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)"/><XAxis type="number" dataKey="fpr" name="False-positive rate" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><YAxis type="number" dataKey="tpr" name="True-positive rate" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Scatter name="Chance reference" data={[{fpr:0,tpr:0},{fpr:1,tpr:1}]} line={{stroke:'var(--tremor-muted)',strokeDasharray:'4 4'}} shape={<circle r={0}/>}/>{curves.map(curve=><Scatter key={curve.name} name={curve.name} data={curve.points} line={{stroke:modelColors[curve.kind]||'var(--tremor-accent)',strokeWidth:2}} fill={modelColors[curve.kind]||'var(--tremor-accent)'} shape={<circle r={0}/>}/>)}</ScatterChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Held-out/test evidence only. Curves use persisted false-positive and true-positive coordinates; ranking remains tied to the stated metric.</p></div>;
}

export function ThresholdTradeoffChart({operatingPoint}:{operatingPoint:OperatingPoint}){
 const rows=[...operatingPoint.curve].filter(point=>Number.isFinite(point.threshold)).sort((a,b)=>a.threshold-b.threshold);
 if(!rows.length)return <div className="h-[260px] grid place-items-center text-sm muted">No persisted validation threshold curve is available for this experiment.</div>;
 const series=[
  ['sensitivity','Validation sensitivity','var(--chart-red)'],['specificity','Validation specificity','var(--chart-blue)'],
  ['precision','Validation precision','var(--chart-amber)'],['recall','Validation recall','var(--chart-magenta)'],['f1','Validation F1','var(--chart-teal)']
 ] as const;
 return <div><div className="tremor-chart h-[320px]" role="img" aria-label="Persisted validation metrics by research threshold"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="threshold" type="number" domain={['dataMin','dataMax']} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><YAxis domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>`${Math.round(Number(value)*100)}%`}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>metric(value)}/>}/><Legend wrapperStyle={{fontSize:10}}/>{series.map(([key,name,color])=>rows.some(row=>row[key]!==null&&row[key]!==undefined)?<Line key={key} type="monotone" dataKey={key} name={name} stroke={color} dot={false} strokeWidth={key==='sensitivity'||key==='specificity'?2:1.4}/>:null)}{operatingPoint.selected_threshold!==null&&<ReferenceLine x={operatingPoint.selected_threshold} stroke="var(--chart-purple)" strokeDasharray="4 4" label={{value:'Selected',position:'insideTopRight',fontSize:10,fill:'var(--tremor-muted)'}}/>}</LineChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Selected research threshold: {operatingPoint.selected_threshold===null?'Not feasible':operatingPoint.selected_threshold.toFixed(4)} · persisted out-of-fold validation evidence</p></div>;
}

export function CalibrationChart({calibration}:{calibration:CalibrationDiagnostics}){
 const curve=calibration.reliability_curve;
 if(!curve||!curve.mean_probability?.length||curve.mean_probability.length!==curve.observed_positive_fraction?.length)return <div className="h-[240px] grid place-items-center text-sm muted">No persisted reliability curve is available.</div>;
 const rows=curve.mean_probability.map((predicted,index)=>({predicted,observed:curve.observed_positive_fraction[index]}));
 return <div><div className="tremor-chart h-[280px]" role="img" aria-label="Persisted held-out probability reliability curve"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer margin={{top:12,right:16,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)"/><XAxis type="number" dataKey="predicted" name="Mean model probability" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}}/><YAxis type="number" dataKey="observed" name="Observed positive fraction" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}}/><Tooltip content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Scatter name="Identity reference" data={[{predicted:0,observed:0},{predicted:1,observed:1}]} line={{stroke:'var(--tremor-muted)',strokeDasharray:'4 4'}} shape={<circle r={0}/>}/><Scatter name="Persisted reliability bins" data={rows} line={{stroke:'var(--tremor-accent)',strokeWidth:2}} fill="var(--tremor-accent)"/></ScatterChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Held-out benchmark probability diagnostics; not clinical calibration evidence.</p></div>;
}

export function RobustnessDeltaChart({records}:{records:RobustnessEvidence[]}){
 const measured=records.filter(record=>record.status==='evaluated'&&record.perturbed_metrics);
 const names=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 if(!measured.length)return <div className="h-[260px] grid place-items-center text-sm muted">No evaluated perturbation values are available.</div>;
 const rows=names.map(name=>({metric:name,...Object.fromEntries(measured.map(record=>[record.model_id,record.degradation_delta[name]]))}));
 return <div className="tremor-chart h-[300px]" role="img" aria-label="Observed degradation delta chart"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:20}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="metric" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-text)"/>{measured.map(record=><Bar key={record.model_id} dataKey={record.model_id} name={modelLabels[record.model_type]} fill={modelColors[record.model_type]||'var(--tremor-accent)'} radius={[4,4,0,0]}/>)}</BarChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Observed change: perturbed − baseline</p></div>;
}
