import {useState} from 'react';
import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart as RechartsLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {Circuit} from '../types';
import {metric} from '../utils/format';

export function BarChart({items, label, percent = false}: {items: {name: string; value: number}[]; label: string; percent?: boolean}) {
  if (!items.length) return <p className="empty">No measured values available.</p>;
  const data = items.map(item => ({name: item.name, value: item.value, display: percent ? metric(item.value) : item.value.toFixed(4)}));
  return (
    <div className="chart tremor-chart-card" role="img" aria-label={label}>
      <div className="tremor-chart-heading">
        <div>
          <span className="tremor-overline">MEASURED VALUE</span>
          <strong>{label}</strong>
        </div>
      </div>
      <div className="tremor-chart-frame">
        <ResponsiveContainer width="100%" height={280}>
          <RechartsBarChart data={data} margin={{top: 8, right: 8, left: -12, bottom: 12}} barCategoryGap="28%">
            <CartesianGrid vertical={false} stroke="var(--tq-grid)" />
            <XAxis dataKey="name" tickLine={false} axisLine={false} tick={{fontSize: 11, fill: 'var(--tq-muted)'}} />
            <YAxis tickLine={false} axisLine={false} tick={{fontSize: 11, fill: 'var(--tq-muted)'}} width={42} />
            <Tooltip cursor={{fill: 'var(--tq-hover)'}} contentStyle={{borderRadius: 12, border: '1px solid var(--tq-border)', background: 'var(--tq-panel)', boxShadow: '0 12px 32px rgba(15,23,42,.10)', fontSize: 12}} formatter={(value) => [percent ? metric(Number(value)) : Number(value).toFixed(4), 'Value']} />
            <Bar dataKey="value" name="Value" radius={[6,6,0,0]} fill="var(--tq-chart-primary)" maxBarSize={44} />
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
      <div className="tremor-chart-caption"><span>Hover bars for exact measured values.</span><span>{items.length} series</span></div>
    </div>
  );
}

export function ROCChart({curves}: {curves: {name: string; fpr: number[]; tpr: number[]}[]}) {
  if (!curves.length) return <p className="empty">ROC curves appear only after measured evaluation.</p>;
  const points = Math.max(...curves.map(curve => curve.fpr.length));
  const data = Array.from({length: points}, (_, index) => {
    const row: Record<string, number> = {threshold: index + 1, fpr: index / Math.max(points - 1, 1)};
    curves.forEach((curve, curveIndex) => {
      row[`curve_${curveIndex}`] = curve.tpr[index] ?? curve.tpr[curve.tpr.length - 1] ?? 0;
    });
    return row;
  });
  return (
    <div className="chart tremor-chart-card" role="img" aria-label="Held-out receiver operating characteristic curves">
      <div className="tremor-chart-heading">
        <div>
          <span className="tremor-overline">CONTROLLED EVALUATION</span>
          <strong>ROC curves</strong>
        </div>
      </div>
      <div className="tremor-chart-frame">
        <ResponsiveContainer width="100%" height={300}>
          <RechartsLineChart data={data} margin={{top: 8, right: 8, left: -12, bottom: 18}}>
            <CartesianGrid vertical={false} stroke="var(--tq-grid)" />
            <XAxis dataKey="threshold" type="number" domain={[1, points]} tickLine={false} axisLine={false} tick={{fontSize: 11, fill: 'var(--tq-muted)'}} label={{value:'Threshold point', position:'insideBottom', offset:-8, fontSize:11, fill:'var(--tq-muted)'}} />
            <YAxis domain={[0,1]} tickLine={false} axisLine={false} tick={{fontSize: 11, fill: 'var(--tq-muted)'}} width={38} />
            <Tooltip cursor={{stroke: 'var(--tq-border)'}} contentStyle={{borderRadius: 12, border: '1px solid var(--tq-border)', background: 'var(--tq-panel)', boxShadow: '0 12px 32px rgba(15,23,42,.10)', fontSize: 12}} />
            <Legend wrapperStyle={{fontSize:12, paddingTop:8}} />
            {curves.map((curve, curveIndex) => <Line key={curve.name} type="monotone" dataKey={`curve_${curveIndex}`} name={curve.name} stroke={`var(--tq-chart-${curveIndex % 4 + 1})`} strokeWidth={2.5} dot={{r:2.5}} activeDot={{r:5}} connectNulls />)}
          </RechartsLineChart>
        </ResponsiveContainer>
      </div>
      <div className="tremor-chart-caption"><span>Same evaluation surface for each model.</span><span>{curves.length} model{curves.length === 1 ? '' : 's'}</span></div>
    </div>
  );
}

export function CircuitDiagram({circuit}: {circuit: Circuit}) {
  const [zoom, setZoom] = useState(1); const gates = circuit.gates.slice(0, 100), width = Math.max(560, gates.length * 52 + 90), height = circuit.qubits * 62 + 30;
  return <div className="circuit-viewer"><div className="circuit-toolbar" role="toolbar" aria-label="Circuit viewer controls"><button type="button" className="secondary" onClick={() => setZoom(value => Math.min(1.8, Number((value + .1).toFixed(1))))}>Zoom in</button><button type="button" className="secondary" onClick={() => setZoom(value => Math.max(.6, Number((value - .1).toFixed(1))))}>Zoom out</button><button type="button" className="ghost" onClick={() => setZoom(1)}>Reset zoom</button><span className="circuit-zoom-readout">{Math.round(zoom * 100)}%</span></div><div className="circuit-scroll"><div className="circuit-zoom-stage" style={{width: width * zoom, height: height * zoom}}><svg width={width} height={height} style={{transform: `scale(${zoom})`, transformOrigin: 'top left'}} role="img" aria-label={`${circuit.qubits}-qubit parameterized circuit`}>{Array.from({length: circuit.qubits}, (_, i) => <g key={i}><text x={8} y={42 + i * 62}>q[{i}]</text><line className="wire" x1={55} x2={width - 10} y1={37 + i * 62} y2={37 + i * 62}/></g>)}{gates.map((gate, i) => {const x = 85 + i * 52; return <g key={i}><title>{gate.name}: {gate.parameters.join(', ')}</title>{gate.qubits.length > 1 && <line className="gate-link" x1={x} x2={x} y1={37 + Math.min(...gate.qubits) * 62} y2={37 + Math.max(...gate.qubits) * 62}/>} {gate.qubits.map(q => <g key={q}><rect className="gate" x={x - 19} y={20 + q * 62} width={38} height={34} rx={4}/><text x={x} y={42 + q * 62} textAnchor="middle">{gate.name}</text></g>)}</g>;})}</svg></div></div>{circuit.gates.length > 100 && <p>Diagram shows the first 100 instructions; the full text circuit is provided below.</p>}</div>;
}
