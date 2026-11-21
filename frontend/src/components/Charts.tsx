import {ChartValues} from './ChartValues';
import {familyColor, families, modelFamily} from '../lib/modelFamily';
import {Bar,BarChart,CartesianGrid,Cell,ErrorBar,Legend,Line,LineChart,ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
import {useEffect,useMemo,useState} from 'react';
import type {CalibrationDiagnostics,Dataset,Influence,MetricName,Metrics,ModelRecord,OperatingPoint,RobustnessEvidence} from '../types/qhealth';
import {metric,modelLabels} from '../utils/format';
import {TremorChartTooltip} from './TremorUI';

const modelColors:Record<string,string>={logistic_regression:'var(--chart-blue)',svm:'var(--chart-teal)',random_forest:'var(--chart-amber)',vqc:'var(--chart-purple)',qsvc:'var(--chart-magenta)',qnn:'var(--chart-cyan)',hybrid_pennylane_torch:'var(--qx-hybrid)'};

export function ClassBalance({dataset}:{dataset:Dataset}){
 const items=Object.entries(dataset.provenance.class_distribution).map(([name,value])=>({name,value}));
 return <ValueBars items={items}/>;
}

export function ValueBars({items,unit=''}:{items:{name:string;value:number}[];unit?:string}){
 const measured=items.filter(row=>Number.isFinite(row.value));
 if(!measured.length)return <p className="muted">No measured values.</p>;
 const max=unit==='%'?100:Math.max(...measured.map(row=>Math.abs(row.value)),Number.EPSILON);
 return <div className="value-comparison"><dl>{measured.map((item,i)=><div key={i}><dt>{item.name}</dt><dd><i aria-hidden="true" style={{width:Math.abs(item.value)/max*100+'%'}}/><strong>{Number(item.value.toFixed(4))}{unit}</strong></dd></div>)}</dl>
   <ChartValues columns={['Category',unit?'Value ('+unit+')':'Value']} rows={measured.map(row=>[row.name,row.value])}/></div>;
}
export function MetricBars({metrics}:{metrics:Metrics}){
 const names=['accuracy','precision','recall','f1','specificity','roc_auc'] as const;
 return <ValueBars items={names.flatMap(key=>{const value=metrics[key];return typeof value==='number'&&Number.isFinite(value)?[{name:chartMetricLabel(key),value:value*100}]:[]})} unit="%"/>;
}
export function InfluenceBars({items}:{items:Influence[]}){
 const values=items.slice(0,12).map(item=>({name:item.feature,value:item.signed_mean??item.magnitude}));
 if(!values.length)return <div className="text-xs muted">No measured contributions.</div>;
 const height=Math.max(260,values.length*28);
 return <><div className="tremor-chart" style={{height}} role="img" aria-label="Signed feature contributions"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={values} layout="vertical" margin={{top:8,right:14,left:8,bottom:8}}>
  <CartesianGrid horizontal={false} stroke="var(--tremor-grid)"/>
  <XAxis type="number" tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(3)}/>
  <YAxis type="category" dataKey="name" width={104} tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/>
  <Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/>
  <ReferenceLine x={0} stroke="var(--tremor-border)"/>
  <Bar dataKey="value" radius={[0,4,4,0]} maxBarSize={16}>{values.map((item,index)=><Cell key={index} fill={item.value<0?'var(--tremor-warn)':'var(--tremor-accent)'}/>)}</Bar>
 </BarChart></ResponsiveContainer></div><ChartValues columns={['Feature','Contribution']} rows={values.map(row=>[row.name,row.value])}/></>;
}

export function ScoreLandscape({data}:{data:{score:number,y:number,label:string,id:string,color?:string}[]}){
 return <><div className="tremor-chart h-[320px]" role="img" aria-label="Model score landscape"><div aria-hidden="true" className="h-full"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer={false} margin={{top:16,right:16,bottom:16,left:0}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis type="number" dataKey="score" domain={[0,100]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis type="number" dataKey="y" tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip/>}/><Scatter aria-hidden="true" data={data}>{data.map((d,i)=><Cell key={i} fill={d.color||'var(--tremor-accent)'} fillOpacity={.75}/>)}</Scatter></ScatterChart></ResponsiveContainer></div></div><ChartValues columns={['Model','Score','Position']} rows={data.map(row=>[row.label,row.score,row.y])}/></>;
}

export function RocChart({models}:{models:ModelRecord[]}){
 const curves=models.flatMap(model=>{
  const curve=model.metrics.test?.roc_curve;
  if(!curve||!curve.fpr.length||curve.fpr.length!==curve.tpr.length)return [];
  return [{name:modelLabels[model.model_type],kind:model.model_type,auc:model.metrics.test?.roc_auc,points:curve.fpr.map((fpr,index)=>({fpr,tpr:curve.tpr[index]}))}];
 });
 if(!curves.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted held-out ROC curve is available. Models without valid curve coordinates are excluded.</div>;
 return <div><div className="mb-3 flex flex-wrap gap-2">{curves.map(curve=><span className="rounded-full border px-2.5 py-1 text-[10px]" key={curve.name}><strong>{curve.name}</strong> · ROC-AUC {metric(curve.auc)}</span>)}</div><div className="tremor-chart h-[320px]" role="img" aria-label="Persisted held-out ROC curves"><div aria-hidden="true" className="h-full"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer={false} margin={{top:10,right:16,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)"/><XAxis type="number" dataKey="fpr" name="False-positive rate" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><YAxis type="number" dataKey="tpr" name="True-positive rate" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={v=>Number(v).toFixed(1)}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Scatter aria-hidden="true" name="Chance reference" data={[{fpr:0,tpr:0},{fpr:1,tpr:1}]} line={{stroke:'var(--tremor-muted)',strokeDasharray:'4 4'}} shape={<circle r={0}/>}/>{curves.map(curve=><Scatter aria-hidden="true" key={curve.name} name={curve.name} data={curve.points} line={{stroke:modelColors[curve.kind]||'var(--tremor-accent)',strokeWidth:2}} fill={modelColors[curve.kind]||'var(--tremor-accent)'} shape={<circle r={0}/>}/>)}</ScatterChart></ResponsiveContainer></div></div><p className="mt-1 text-center text-[11px] muted">Held-out/test evidence only. Horizontal: false-positive rate. Vertical: true-positive rate.</p><ChartValues columns={['Model','False-positive rate','True-positive rate']} rows={curves.flatMap(curve=>curve.points.map(point=>[curve.name,point.fpr,point.tpr]))}/></div>;
}

export function ThresholdTradeoffChart({operatingPoint}:{operatingPoint:OperatingPoint}){
 const rows=[...operatingPoint.curve].filter(point=>Number.isFinite(point.threshold)).sort((a,b)=>a.threshold-b.threshold);
 if(!rows.length)return <div className="h-[260px] grid place-items-center text-sm muted">No persisted validation threshold curve is available for this experiment.</div>;
 const series=[
  ['sensitivity','Validation sensitivity','var(--chart-red)'],['specificity','Validation specificity','var(--chart-blue)'],
  ['precision','Validation precision','var(--chart-amber)'],['recall','Validation recall','var(--chart-magenta)'],['f1','Validation F1','var(--chart-teal)']
 ] as const;
 return <div><div className="tremor-chart h-[320px]" role="img" aria-label="Persisted validation metrics by research threshold"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="threshold" type="number" domain={['dataMin','dataMax']} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><YAxis domain={[0,1]} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>`${Math.round(Number(value)*100)}%`}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>metric(value)}/>}/><Legend wrapperStyle={{fontSize:11}}/>{series.map(([key,name,color])=>rows.some(row=>row[key]!==null&&row[key]!==undefined)?<Line key={key} type="linear" dataKey={key} name={name} stroke={color} dot={false} strokeWidth={key==='sensitivity'||key==='specificity'?2:1.4}/>:null)}{operatingPoint.selected_threshold!==null&&<ReferenceLine x={operatingPoint.selected_threshold} stroke="var(--chart-purple)" strokeDasharray="4 4" label={{value:'Selected',position:'insideTopRight',fontSize:11,fill:'var(--tremor-muted)'}}/>}</LineChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Selected research threshold: {operatingPoint.selected_threshold===null?'Not feasible':operatingPoint.selected_threshold.toFixed(4)} · persisted out-of-fold validation evidence</p></div>;
}

export function CalibrationChart({calibration}:{calibration:CalibrationDiagnostics}){
 const curve=calibration.reliability_curve;
 if(!curve||!curve.mean_probability?.length||curve.mean_probability.length!==curve.observed_positive_fraction?.length)return <div className="h-[240px] grid place-items-center text-sm muted">No persisted reliability curve is available.</div>;
 const rows=curve.mean_probability.map((predicted,index)=>({predicted,observed:curve.observed_positive_fraction[index]}));
 return <div><div className="tremor-chart h-[280px]" role="img" aria-label="Persisted held-out probability reliability curve"><div aria-hidden="true" className="h-full"><ResponsiveContainer width="100%" height="100%"><ScatterChart accessibilityLayer={false} margin={{top:12,right:16,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)"/><XAxis type="number" dataKey="predicted" name="Mean model probability" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}}/><YAxis type="number" dataKey="observed" name="Observed positive fraction" domain={[0,1]} tick={{fill:'var(--tremor-muted)'}}/><Tooltip content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Scatter aria-hidden="true" name="Identity reference" data={[{predicted:0,observed:0},{predicted:1,observed:1}]} line={{stroke:'var(--tremor-muted)',strokeDasharray:'4 4'}} shape={<circle r={0}/>}/><Scatter aria-hidden="true" name="Persisted reliability bins" data={rows} line={{stroke:'var(--tremor-accent)',strokeWidth:2}} fill="var(--tremor-accent)"/></ScatterChart></ResponsiveContainer></div></div><p className="mt-1 text-center text-[11px] muted">Held-out benchmark probability diagnostics; not clinical calibration evidence.</p><ChartValues columns={['Mean predicted probability','Observed positive fraction']} rows={rows.map(row=>[row.predicted,row.observed])}/></div>;
}

export type RuntimeKind='final_training_seconds'|'cv_total_seconds'|'test_inference_seconds'|'test_inference_seconds_per_sample';

const runtimeLabels:Record<RuntimeKind,string>={
 final_training_seconds:'Final training',
 cv_total_seconds:'CV total',
 test_inference_seconds:'Held-out inference',
 test_inference_seconds_per_sample:'Inference / sample'
};

const chartMetricLabel=(name:MetricName)=>name==='roc_auc'?'ROC-AUC':name.replaceAll('_',' ').toUpperCase();

export function ModelMetricBars({models,metricName}:{models:ModelRecord[];metricName:MetricName}){
 const rows=models.map(model=>({id:model.id,name:modelLabels[model.model_type],family:modelFamily(model.model_type),value:model.metrics.test?.[metricName]}));
 if(!rows.some(row=>typeof row.value==='number'&&Number.isFinite(row.value)))return <p className="muted">No persisted held-out values are available for {chartMetricLabel(metricName)}.</p>;
 const label='Held-out '+chartMetricLabel(metricName)+' by model';
 return <figure className="benchmark-figure" aria-label={label}>
   <figcaption><strong>{label}</strong><span>Test set · unit interval</span></figcaption>
   <ul className="family-key" aria-label="Model families">{families.filter(family=>rows.some(row=>row.family===family)).map(family=><li key={family}><i style={{backgroundColor:familyColor[family]}}/>{family}</li>)}</ul>
   <ol className="bar-rows">{rows.map(row=><li key={row.id} data-family={row.family}>
     <span className="bar-name">{row.name}<small>{row.family}</small></span>
     <span className="bar-track" aria-hidden="true">{typeof row.value==='number'&&Number.isFinite(row.value)&&<i style={{width:(100*row.value)+'%',backgroundColor:familyColor[row.family]}}/>}</span>
     <span className="bar-value">{typeof row.value==='number'&&Number.isFinite(row.value)?String(Number(row.value.toFixed(4))):'—'}</span>
   </li>)}</ol><div className="bar-scale" aria-hidden="true"><span>0</span><span>0.25</span><span>0.50</span><span>0.75</span><span>1</span></div>
 </figure>;
}

export function MetricMatrix({models}:{models:ModelRecord[]}){
 const rows=models.filter(model=>Object.values(model.metrics.test||{}).some(value=>typeof value==='number'&&Number.isFinite(value)));
 const columns:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];
 if(!rows.length)return <div className="h-[240px] grid place-items-center text-sm muted">No persisted model metrics are available for the matrix.</div>;
 return <div tabIndex={0} className="table-wrap overflow-x-auto"><div className="min-w-[900px] rounded-xl border" role="table" aria-label="Held-out metric matrix">
  <div className="grid items-center border-b bg-muted/20 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide muted" style={{gridTemplateColumns:`minmax(190px,1.6fr) repeat(${columns.length},minmax(92px,1fr))`}} role="row">
   <span role="columnheader">Model</span>{columns.map(name=><span role="columnheader" key={name}>{chartMetricLabel(name)}</span>)}
  </div>
  {rows.map(model=><div className="grid items-center gap-0 border-b last:border-b-0" style={{gridTemplateColumns:`minmax(190px,1.6fr) repeat(${columns.length},minmax(92px,1fr))`}} role="row" key={model.id}>
   <div className="px-3 py-3 text-xs font-semibold" role="rowheader">{modelLabels[model.model_type]}</div>
   {columns.map(name=>{const value=model.metrics.test?.[name];const normalized=typeof value==='number'&&Number.isFinite(value)?Math.max(0,Math.min(1,value)):null;return <div className="px-2 py-2" role="cell" key={name}><div className="rounded-lg border px-2 py-2 text-center mono text-[11px] font-semibold" style={normalized===null?undefined:{background:`color-mix(in srgb, var(--chart-purple) ${Math.round(8+normalized*18)}%, transparent)`}}>{normalized===null?'—':normalized.toFixed(3)}</div></div>})}
  </div>)}
 </div></div>;
}

export function CvStabilityChart({models,metricName}:{models:ModelRecord[];metricName:MetricName}){
 const rows=models.map(model=>{const summary=model.metrics.validation?.summary?.[metricName];return {id:model.id,name:modelLabels[model.model_type],modelType:model.model_type,mean:summary?.mean,std:summary?.std,validFolds:summary?.valid_folds};}).filter(row=>typeof row.mean==='number'&&Number.isFinite(row.mean)&&typeof row.std==='number'&&Number.isFinite(row.std));
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted cross-validation mean ± SD is available for {chartMetricLabel(metricName)}.</div>;
 return <><div className="tremor-chart h-[320px]" role="img" aria-label={`Cross-validation ${chartMetricLabel(metricName)} mean and standard deviation by model`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:18,right:18,left:0,bottom:54}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis domain={[0,1]} tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Bar dataKey="mean" name="CV mean" radius={[5,5,0,0]} maxBarSize={46}>{rows.map(row=><Cell key={row.id} fill={modelColors[row.modelType]||'var(--tremor-accent)'}/>) }<ErrorBar dataKey="std" width={9} strokeWidth={1.5} direction="y"/></Bar></BarChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Error bars show persisted cross-validation standard deviation; valid-fold count is available in the source table.</p></div><ChartValues columns={['Model','CV mean','CV SD','Valid folds']} rows={rows.map(row=>[row.name,row.mean,row.std,row.validFolds])}/></>;
}

export function RuntimeComparisonChart({models,runtimeKind}:{models:ModelRecord[];runtimeKind:RuntimeKind}){
 const rows=models.map(model=>({id:model.id,name:modelLabels[model.model_type],modelType:model.model_type,value:model.metrics.timing?.[runtimeKind]})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)&&row.value>=0);
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted {runtimeLabels[runtimeKind].toLowerCase()} measurements are available.</div>;
 return <><div className="tremor-chart h-[320px]" role="img" aria-label={`${runtimeLabels[runtimeKind]} by model`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} layout="vertical" margin={{top:10,right:18,left:8,bottom:10}}><CartesianGrid horizontal={false} stroke="var(--tremor-grid)"/><XAxis type="number" tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(3)}/><YAxis type="category" dataKey="name" width={150} tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><Bar dataKey="value" name={runtimeLabels[runtimeKind]} radius={[0,5,5,0]} maxBarSize={24}>{rows.map(row=><Cell key={row.id} fill={modelColors[row.modelType]||'var(--tremor-accent)'}/>)}</Bar></BarChart></ResponsiveContainer></div><ChartValues columns={['Model',runtimeLabels[runtimeKind]+' (seconds)']} rows={rows.map(row=>[row.name,row.value])}/></>;
}

export type RobustnessTrendRecord={modelId:string;modelType:ModelRecord['model_type'];scenario:string;level:number;delta:Partial<Record<MetricName,number|null>>};

export function RobustnessTrendChart({records}:{records:RobustnessTrendRecord[]}){
 const measured=records.filter(record=>Number.isFinite(record.level)&&typeof record.delta.accuracy==='number'&&Number.isFinite(record.delta.accuracy));
 if(measured.length<2)return <div className="h-[280px] grid place-items-center text-sm muted">Multiple persisted perturbation levels are required for a robustness trend.</div>;
 const series=Array.from(new Map(measured.map(record=>[`${record.modelId}::${record.scenario}`,record])).values());
 const levels=[...new Set(measured.map(record=>record.level))].sort((a,b)=>a-b);
 const rows=levels.map(level=>{const row:Record<string,number|null|number>={level};for(const item of series)row[`${item.modelId}::${item.scenario}`]=measured.find(record=>record.modelId===item.modelId&&record.scenario===item.scenario&&record.level===level)?.delta.accuracy??null;return row;});
 return <div><div className="tremor-chart h-[320px]" role="img" aria-label="Accuracy degradation delta by perturbation level"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:20,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="level" type="number" domain={['dataMin','dataMax']} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-text)"/>{series.map((item,index)=><Line key={`${item.modelId}::${item.scenario}`} type="linear" dataKey={`${item.modelId}::${item.scenario}`} name={`${modelLabels[item.modelType]} · ${item.scenario.replaceAll('_',' ')}`} stroke={modelColors[item.modelType]||'var(--tremor-accent)'} strokeWidth={2} strokeDasharray={index%2===0?undefined:'5 4'} dot={{r:3}} connectNulls={false}/>)}</LineChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Accuracy delta is perturbed minus baseline. Only persisted perturbation levels are plotted.</p></div>;
}

export function RobustnessDeltaChart({records}:{records:RobustnessEvidence[]}){
 const measured=records.filter(record=>record.status==='evaluated'&&record.perturbed_metrics);
 const names=['accuracy','sensitivity','specificity','f1','roc_auc'] as const;
 if(!measured.length)return <div className="h-[260px] grid place-items-center text-sm muted">No evaluated perturbation values are available.</div>;
 const rows=names.map(name=>({metric:name,...Object.fromEntries(measured.map(record=>[record.model_id,record.degradation_delta[name]]))}));
 return <div className="tremor-chart h-[300px]" role="img" aria-label="Observed degradation delta chart"><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:20}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="metric" tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fontSize:11,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-text)"/>{measured.map(record=><Bar key={record.model_id} dataKey={record.model_id} name={modelLabels[record.model_type]} fill={modelColors[record.model_type]||'var(--tremor-accent)'} radius={[4,4,0,0]}/>)}</BarChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Observed change: perturbed − baseline</p></div>;
}
