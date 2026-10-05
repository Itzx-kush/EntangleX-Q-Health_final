import {Bar,BarChart,CartesianGrid,Cell,ErrorBar,Legend,Line,LineChart,ReferenceLine,ResponsiveContainer,Scatter,ScatterChart,Tooltip,XAxis,YAxis} from 'recharts';
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

export type RuntimeKind='final_training_seconds'|'cv_total_seconds'|'test_inference_seconds'|'test_inference_seconds_per_sample';

const runtimeLabels:Record<RuntimeKind,string>={
 final_training_seconds:'Final training',
 cv_total_seconds:'CV total',
 test_inference_seconds:'Held-out inference',
 test_inference_seconds_per_sample:'Inference / sample'
};

const chartMetricLabel=(name:MetricName)=>name==='roc_auc'?'ROC-AUC':name.replaceAll('_',' ').toUpperCase();

export function ModelMetricBars({models,metricName}:{models:ModelRecord[];metricName:MetricName}){
 const rows=models.map(model=>({id:model.id,name:modelLabels[model.model_type],modelType:model.model_type,value:model.metrics.test?.[metricName]})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value));
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted held-out values are available for {chartMetricLabel(metricName)}.</div>;
 return <div className="tremor-chart h-[320px]" role="img" aria-label={`Held-out ${chartMetricLabel(metricName)} by model`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:12,right:12,left:0,bottom:54}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis domain={[0,1]} tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Bar dataKey="value" name={chartMetricLabel(metricName)} radius={[5,5,0,0]} maxBarSize={52}>{rows.map(row=><Cell key={row.id} fill={modelColors[row.modelType]||'var(--tremor-accent)'}/>)}</Bar></BarChart></ResponsiveContainer></div>;
}

export function MetricMatrix({models}:{models:ModelRecord[]}){
 const rows=models.filter(model=>Object.values(model.metrics.test||{}).some(value=>typeof value==='number'&&Number.isFinite(value)));
 const columns:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];
 if(!rows.length)return <div className="h-[240px] grid place-items-center text-sm muted">No persisted model metrics are available for the matrix.</div>;
 return <div className="table-wrap overflow-x-auto"><div className="min-w-[900px] rounded-xl border" role="table" aria-label="Held-out metric matrix">
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
 const rows=models.map(model=>{const summary=model.metrics.validation?.summary?.[metricName];return {id:model.id,name:modelLabels[model.model_type],modelType:model.model_type,mean:summary?.mean,std:summary?.std,validFolds:summary?.valid_folds??0};}).filter(row=>typeof row.mean==='number'&&Number.isFinite(row.mean)&&typeof row.std==='number'&&Number.isFinite(row.std));
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted cross-validation mean ± SD is available for {chartMetricLabel(metricName)}.</div>;
 return <div className="tremor-chart h-[320px]" role="img" aria-label={`Cross-validation ${chartMetricLabel(metricName)} mean and standard deviation by model`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} margin={{top:18,right:18,left:0,bottom:54}}><CartesianGrid vertical={false} stroke="var(--tremor-grid)"/><XAxis dataKey="name" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} angle={-18} textAnchor="end" interval={0}/><YAxis domain={[0,1]} tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(3)}/>}/><Bar dataKey="mean" name="CV mean" radius={[5,5,0,0]} maxBarSize={46}>{rows.map(row=><Cell key={row.id} fill={modelColors[row.modelType]||'var(--tremor-accent)'}/>) }<ErrorBar dataKey="std" width={9} strokeWidth={1.5} direction="y"/></Bar></BarChart></ResponsiveContainer><p className="mt-1 text-center text-[11px] muted">Error bars show persisted cross-validation standard deviation; valid-fold count is available in the source table.</p></div>;
}

export function RuntimeComparisonChart({models,runtimeKind}:{models:ModelRecord[];runtimeKind:RuntimeKind}){
 const rows=models.map(model=>({id:model.id,name:modelLabels[model.model_type],modelType:model.model_type,value:model.metrics.timing?.[runtimeKind]})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)&&row.value>=0);
 if(!rows.length)return <div className="h-[300px] grid place-items-center text-sm muted">No persisted {runtimeLabels[runtimeKind].toLowerCase()} measurements are available.</div>;
 return <div className="tremor-chart h-[320px]" role="img" aria-label={`${runtimeLabels[runtimeKind]} by model`}><ResponsiveContainer width="100%" height="100%"><BarChart accessibilityLayer data={rows} layout="vertical" margin={{top:10,right:18,left:8,bottom:10}}><CartesianGrid horizontal={false} stroke="var(--tremor-grid)"/><XAxis type="number" tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(3)}/><YAxis type="category" dataKey="name" width={150} tick={{fontSize:10,fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'var(--tremor-hover)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><Bar dataKey="value" name={runtimeLabels[runtimeKind]} radius={[0,5,5,0]} maxBarSize={24}>{rows.map(row=><Cell key={row.id} fill={modelColors[row.modelType]||'var(--tremor-accent)'}/>)}</Bar></BarChart></ResponsiveContainer></div>;
}

export type RobustnessTrendRecord={modelId:string;modelType:ModelRecord['model_type'];scenario:string;level:number;delta:Partial<Record<MetricName,number|null>>};

export function RobustnessTrendChart({records}:{records:RobustnessTrendRecord[]}){
 const measured=records.filter(record=>Number.isFinite(record.level)&&typeof record.delta.accuracy==='number'&&Number.isFinite(record.delta.accuracy));
 if(measured.length<2)return <div className="h-[280px] grid place-items-center text-sm muted">Multiple persisted perturbation levels are required for a robustness trend.</div>;
 const series=Array.from(new Map(measured.map(record=>[`${record.modelId}::${record.scenario}`,record])).values());
 const levels=[...new Set(measured.map(record=>record.level))].sort((a,b)=>a-b);
 const rows=levels.map(level=>{const row:Record<string,number|null|number>={level};for(const item of series)row[`${item.modelId}::${item.scenario}`]=measured.find(record=>record.modelId===item.modelId&&record.scenario===item.scenario&&record.level===level)?.delta.accuracy??null;return row;});
 return <div><div className="tremor-chart h-[320px]" role="img" aria-label="Accuracy degradation delta by perturbation level"><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:20,left:0,bottom:18}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="level" type="number" domain={['dataMin','dataMax']} tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-text)"/>{series.map((item,index)=><Line key={`${item.modelId}::${item.scenario}`} type="monotone" dataKey={`${item.modelId}::${item.scenario}`} name={`${modelLabels[item.modelType]} · ${item.scenario.replaceAll('_',' ')}`} stroke={modelColors[item.modelType]||'var(--tremor-accent)'} strokeWidth={2} strokeDasharray={index%2===0?undefined:'5 4'} dot={{r:3}} connectNulls={false}/>)}</LineChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Accuracy delta is perturbed minus baseline. Only persisted perturbation levels are plotted.</p></div>;
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

type RobustnessTrendRecord={modelId:string;modelType:ModelRecord['model_type'];scenario:string;level:number;delta:Partial<Record<MetricName,number|null>>};

export function RobustnessTrendChart({records}:{records:RobustnessTrendRecord[]}){
 const scenarios=useMemo(()=>[...new Set(records.map(record=>record.scenario))],[records]);
 const [scenario,setScenario]=useState(scenarios[0]||'');
 const scenarioModels=useMemo(()=>[...new Set(records.filter(record=>record.scenario===scenario).map(record=>record.modelId))],[records,scenario]);
 const [modelId,setModelId]=useState(scenarioModels[0]||'');
 const [metricName,setMetricName]=useState<MetricName>('accuracy');
 useEffect(()=>{if(!scenarios.includes(scenario))setScenario(scenarios[0]||'')},[scenarios,scenario]);
 useEffect(()=>{if(!scenarioModels.includes(modelId))setModelId(scenarioModels[0]||'')},[scenarioModels,modelId]);
 const modelRecords=records.filter(record=>record.scenario===scenario&&record.modelId===modelId).sort((a,b)=>a.level-b.level);
 const availableMetrics=(['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'] as MetricName[]).filter(name=>modelRecords.some(record=>typeof record.delta[name]==='number'&&Number.isFinite(record.delta[name] as number)));
 useEffect(()=>{if(!availableMetrics.includes(metricName))setMetricName(availableMetrics[0]||'accuracy')},[availableMetrics,metricName]);
 if(!records.length)return null;
 if(!modelRecords.length||modelRecords.length<2)return <div className="rounded-xl border p-4 text-sm muted">A robustness trend requires at least two persisted perturbation levels for one scenario and model. The detailed evidence table remains authoritative.</div>;
 const rows=modelRecords.map(record=>({level:record.level,value:record.delta[metricName]??null})).filter(row=>typeof row.value==='number'&&Number.isFinite(row.value)) as {level:number;value:number}[];
 if(rows.length<2)return <div className="rounded-xl border p-4 text-sm muted">The selected scenario/model does not have two numeric observations for {analysisMetricLabel(metricName)}.</div>;
 return <div><div className="mb-4 grid gap-3 md:grid-cols-3"><label className="field"><span>Perturbation scenario</span><select className="select" value={scenario} onChange={event=>setScenario(event.target.value)}>{scenarios.map(item=><option value={item} key={item}>{item.replaceAll('_',' ')}</option>)}</select></label><label className="field"><span>Model</span><select className="select" value={modelId} onChange={event=>setModelId(event.target.value)}>{scenarioModels.map(id=><option value={id} key={id}>{modelLabels[records.find(record=>record.modelId===id)?.modelType||'logistic_regression']}</option>)}</select></label><label className="field"><span>Observed metric change</span><select className="select" value={metricName} onChange={event=>setMetricName(event.target.value as MetricName)}>{availableMetrics.map(name=><option value={name} key={name}>{analysisMetricLabel(name)}</option>)}</select></label></div><div className="tremor-chart h-[290px]" role="img" aria-label={'Observed '+analysisMetricLabel(metricName)+' change across '+scenario.replaceAll('_',' ')+' perturbation levels'}><ResponsiveContainer width="100%" height="100%"><LineChart accessibilityLayer data={rows} margin={{top:12,right:14,left:0,bottom:20}}><CartesianGrid stroke="var(--tremor-grid)" vertical={false}/><XAxis dataKey="level" type="number" tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'var(--tremor-muted)'}} tickLine={false} axisLine={false} tickFormatter={value=>Number(value).toFixed(2)}/><Tooltip cursor={{stroke:'var(--tremor-border)'}} content={<TremorChartTooltip valueFormatter={value=>value.toFixed(4)}/>}/><ReferenceLine y={0} stroke="var(--tremor-border)"/><Line type="linear" dataKey="value" name="Observed change" stroke="var(--tremor-accent)" strokeWidth={2} dot={{r:3}}/></LineChart></ResponsiveContainer></div><p className="mt-1 text-center text-[11px] muted">Observed change = backend-provided degraded minus baseline value for the selected persisted scenario/model.</p></div>;
}
