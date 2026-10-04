import {Bar,BarChart,CartesianGrid,Cell,Legend,Line,LineChart,ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
import {useEffect,useMemo,useState} from 'react';
import type {CalibrationDiagnostics,Dataset,Influence,MetricName,Metrics,ModelRecord,OperatingPoint,RobustnessEvidence} from '../types/qhealth';
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

export type RuntimeKind = 'final_training_seconds'|'cv_total_seconds'|'test_inference_seconds'|'test_inference_seconds_per_sample';

function modelFamily(kind:ModelRecord['model_type']){
 if(kind==='hybrid_pennylane_torch')return 'Hybrid';
 if(['vqc','qsvc','qnn'].includes(kind))return 'Quantum';
 return 'Classical';
}
function analysisMetricLabel(name:MetricName){return name==='roc_auc'?'ROC-AUC':name.replaceAll('_',' ').toUpperCase()}

export function ModelMetricBars({models,metricName}:{models:ModelRecord[];metricName:MetricName}){
 const rows=models.map(model=>({name:modelLabels[model.model_type],kind:model.model_type,value:model.metrics.test?.[metricName]})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)) as {name:string;kind:ModelRecord['model_type'];value:number}[];
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted {analysisMetricLabel(metricName)} values are available for the selected model set.</div>;
 return <div className="tremor-chart h-[310px]" role="img" aria-label={'Held-out '+analysisMetricLabel(metricName)+' by model'}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:14,right:12,left:0,bottom:48}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis domain={[0,1]} tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Bar dataKey="value" name={analysisMetricLabel(metricName)} radius={[5,5,0,0]} maxBarSize={52}>{rows.map(row=><Cell key={row.name} fill={modelFamily(row.kind)==='Classical'?'var(--chart-blue)':modelFamily(row.kind)==='Quantum'?'var(--chart-purple)':'var(--chart-cyan)'}/>)}</Bar></BarChart></ResponsiveContainer></div>;
}

export function MetricMatrix({models,metrics=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'] as MetricName[]}:{models:ModelRecord[];metrics?:MetricName[]}){
 const rows=models.map(model=>({model,values:metrics.map(name=>model.metrics.test?.[name])}));
 const hasValue=rows.some(row=>row.values.some(value=>typeof value==='number'&&Number.isFinite(value)));
 if(!hasValue)return <div className="rounded-xl border p-5 text-sm muted">No persisted metric matrix is available for the selected model set.</div>;
 return <div className="overflow-x-auto rounded-xl border"><table className="data-table min-w-[900px]"><thead><tr><th>MODEL</th>{metrics.map(name=><th key={name}>{analysisMetricLabel(name)}</th>)}</tr></thead><tbody>{rows.map(row=><tr key={row.model.id}><th className="text-left">{modelLabels[row.model.model_type]}<span className="mt-1 block text-[10px] font-normal muted">{modelFamily(row.model.model_type)}</span></th>{row.values.map((value,index)=>{const numeric=typeof value==='number'&&Number.isFinite(value)?value:null;const opacity=numeric===null?0.04:0.07+Math.max(0,Math.min(1,numeric))*0.20;return <td className="numeric" key={metrics[index]} style={{backgroundColor:numeric===null?'transparent':'hsl(var(--primary) / '+opacity+')'}}>{numeric===null?'Not recorded':numeric.toFixed(3)}</td>})}</tr>)}</tbody></table></div>;
}

export function CvStabilityChart({models,metricName}:{models:ModelRecord[];metricName:MetricName}){
 const rows=models.map(model=>{const summary=model.metrics.validation?.summary?.[metricName];return {name:modelLabels[model.model_type],mean:summary?.mean??null,std:summary?.std??null,folds:summary?.valid_folds??null}}).filter(row=>typeof row.mean==='number'&&Number.isFinite(row.mean)) as {name:string;mean:number;std:number|null;folds:number|null}[];
 if(!rows.length)return <div className="rounded-xl border p-4 text-sm muted">No persisted cross-validation mean is available for {analysisMetricLabel(metricName)}.</div>;
 return <div className="space-y-3" role="img" aria-label={'Cross-validation mean and standard deviation for '+analysisMetricLabel(metricName)}>{rows.map(row=>{const std=typeof row.std==='number'&&Number.isFinite(row.std)?row.std:0;const low=Math.max(0,Math.min(1,row.mean-std));const high=Math.max(0,Math.min(1,row.mean+std));const left=low*100;const width=Math.max(0,(high-low)*100);const point=row.mean*100;return <div className="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(120px,.55fr)_minmax(0,1.45fr)_120px] items-center" key={row.name}><div className="text-xs font-semibold">{row.name}</div><div className="relative h-8 rounded-lg border bg-muted/20" aria-hidden="true"><span className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-primary/30" style={{left:left+'%',width:width+'%'}}/><span className="absolute top-1/2 h-4 w-1.5 -translate-y-1/2 rounded-full bg-primary shadow-sm" style={{left:'calc('+point+'% - 3px)'}}/></div><div className="text-right text-xs mono"><strong>{row.mean.toFixed(3)}</strong>{row.std!==null?' ± '+row.std.toFixed(3):' · SD n/r'}<span className="block text-[10px] muted">{row.folds??'—'} valid folds</span></div></div>})}<p className="text-[10px] muted">Mean and observed standard deviation only; this view does not represent a confidence interval or significance test.</p></div>;
}

export function RuntimeComparisonChart({models,runtimeKind}:{models:ModelRecord[];runtimeKind:RuntimeKind}){
 const labels:Record<RuntimeKind,string>={final_training_seconds:'Final training',cv_total_seconds:'CV total',test_inference_seconds:'Held-out inference',test_inference_seconds_per_sample:'Inference / sample'};
 const rows=models.map(model=>({name:modelLabels[model.model_type],value:model.metrics.timing?.[runtimeKind]})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)) as {name:string;value:number}[];
 if(!rows.length)return <div className="rounded-xl border p-4 text-sm muted">No persisted {labels[runtimeKind].toLowerCase()} runtime values are available.</div>;
 return <div><div className="tremor-chart h-[300px]" role="img" aria-label={labels[runtimeKind]+' runtime by model'}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:14,right:12,left:0,bottom:48}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><Bar dataKey="value" name={labels[runtimeKind]+' (seconds)'} fill="var(--tremor-accent)" radius={[5,5,0,0]} maxBarSize={52}/></BarChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Observed execution time on the recorded environment; not a general infrastructure benchmark.</p></div>;
}
