import {useState} from 'react';
import {Link} from 'react-router-dom';
import {useMutation,useQuery} from '@tanstack/react-query';
import {
  Activity,ArrowUpRight,Atom,CheckCircle2,ChevronRight,Clock3,
  Cpu,ExternalLink,Eye,FlaskConical,Gauge,Layers3,Play,RefreshCw,
  ServerCog,SlidersHorizontal,TerminalSquare
} from 'lucide-react';
import {Button,Card,Select,Badge} from './ui';
import {ErrorBanner,MetricCard,ModelSelect,Notice,PageHeader,StatusBadge} from './Shared';
import {StageNav} from '../pages/ResearchPagesCore';
import {qh} from '../lib/api';
import {useDraft} from '../hooks/useDraft';
import {modelLabels,shortId} from '../utils/format';
import {PipelineFlow,StatusStrip,WorkbenchRail} from './TremorWorkbench';
import type {ModelRecord} from '../types/qhealth';

type QuantumKind='vqc'|'qsvc'|'qnn';

function CircuitGrid({circuit}:{circuit?:{qubits:number;gates:{name:string;qubits:number[];parameters:string[]}[]}}){
  if(!circuit)return <div className="qb-empty-state"><TerminalSquare size={18}/><div><strong>No circuit loaded</strong><span>Generate the backend-returned logical representation to inspect gates.</span></div></div>;
  const rows=Array.from({length:circuit.qubits},(_,q)=>({q,gates:circuit.gates.filter(g=>g.qubits.includes(q))}));
  return <div className="qb-circuit-shell" aria-label="Logical circuit visualization">
    <div className="qb-circuit-toolbar">
      <span>LOGICAL CIRCUIT</span>
      <div><Badge tone="purple">{circuit.qubits} QUBITS</Badge><Badge tone="blue">{circuit.gates.length} GATES</Badge></div>
    </div>
    <div className="qb-circuit-grid">
      {rows.map(row=><div className="qb-circuit-row" key={row.q}>
        <strong>q[{row.q}]</strong>
        <div className="qb-circuit-wire">
          <span className="qb-wire-line" aria-hidden="true"/>
          {row.gates.length?row.gates.map((gate,index)=><span className="qb-gate" key={index} title={gate.parameters.join(', ')}>
            <b>{gate.name}</b>{gate.parameters.length>0&&<small>{gate.parameters.join(', ')}</small>}
          </span>):<span className="qb-idle-gate">idle</span>}
        </div>
      </div>)}
    </div>
    <div className="qb-circuit-footer">
      <span>Measured from backend circuit contract</span>
      <span className="mono">depth {circuit.gates.length?Math.max(...rows.map(r=>r.gates.length)):0}</span>
    </div>
  </div>;
}

function DevicePanel({capability,backend,model,jobs}:{capability:any;backend:string;model:string;jobs:any[]}){
  const latest=jobs[0];
  return <Card className="qb-panel-card" title="Execution plane" description="A qBraid-inspired device and job surface backed only by values already available to EntangleX.">
    <div className="qb-device-stack">
      <div className="qb-device-row is-active">
        <div className="qb-device-icon"><ServerCog size={16}/></div>
        <div className="min-w-0 flex-1"><strong>{backend}</strong><span>Configured experiment backend</span></div>
        <span className={'qb-live-dot '+(capability?.available?'is-online':'is-offline')}/>
        <Badge tone={capability?.available?'green':'amber'}>{capability?.available?'AVAILABLE':'NOT REPORTED'}</Badge>
      </div>
      <div className="qb-device-row">
        <div className="qb-device-icon"><Atom size={16}/></div>
        <div className="min-w-0 flex-1"><strong>{model.toUpperCase()}</strong><span>Selected quantum model family</span></div>
        <Badge tone="purple">LOGICAL</Badge>
      </div>
      <div className="qb-device-row">
        <div className="qb-device-icon"><Layers3 size={16}/></div>
        <div className="min-w-0 flex-1"><strong>Execution boundary</strong><span>{capability?.execution||'Capability detail returned by backend'}</span></div>
      </div>
      {latest&&<div className="qb-device-row">
        <div className="qb-device-icon"><Activity size={16}/></div>
        <div className="min-w-0 flex-1"><strong>Latest job {shortId(latest.id)}</strong><span>{latest.state||latest.status} · {latest.progress ?? 0}%</span></div>
        <StatusBadge value={latest.status}/>
      </div>}
    </div>
    <div className="qb-boundary-note"><Eye size={14}/><span>No hardware availability, QPU identity, queue time or performance claim is inferred when the backend does not return it.</span></div>
  </Card>;
}

function JobTable({jobs}:{jobs:any[]}){
  return <Card className="qb-panel-card" title="Quantum jobs" description="Recent backend jobs, shown without inventing provider or hardware metadata.">
    {jobs.length?<div className="qb-job-table-wrap">
      <table className="data-table qb-job-table">
        <thead><tr><th>Job</th><th>Status</th><th>State</th><th>Progress</th><th>Updated</th></tr></thead>
        <tbody>{jobs.slice(0,6).map(job=><tr key={job.id}>
          <td><span className="mono text-[10px]">{shortId(job.id)}</span><small className="block muted">{shortId(job.experiment_id)}</small></td>
          <td><StatusBadge value={job.status}/></td>
          <td>{job.state||'—'}</td>
          <td><div className="qb-job-progress"><span style={{width:Math.max(0,Math.min(100,Number(job.progress)||0))+'%'}}/><strong>{Math.round(Number(job.progress)||0)}%</strong></div></td>
          <td className="mono text-[10px]">{job.updated_at?new Date(job.updated_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}):'—'}</td>
        </tr>)}</tbody>
      </table>
    </div>:<div className="qb-empty-state"><Clock3 size={18}/><div><strong>No recent jobs</strong><span>Training jobs will appear here when created through Model Lab.</span></div></div>}
  </Card>;
}

export function QuantumWorkbench(){
  const {draft,update,pipeline,quantum}=useDraft();
  const cap=useQuery({queryKey:['quantum-capabilities'],queryFn:qh.capabilities});
  const models=useQuery({queryKey:['models'],queryFn:qh.models});
  const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:5000});
  const [kind,setKind]=useState<QuantumKind>('vqc');
  const [circuit,setCircuit]=useState<any>();
  const [modelId,setModelId]=useState('');
  const [inspector,setInspector]=useState<'circuit'|'resources'>('circuit');
  const preview=useMutation({mutationFn:()=>qh.circuit({quantum:draft.quantum,model_type:kind,seed:draft.seed}),onSuccess:setCircuit});
  const fitted=useMutation({mutationFn:()=>qh.fittedCircuit(modelId),onSuccess:setCircuit});
  const advisor=useMutation({mutationFn:()=>qh.resourceAdvisor({
    model_type:kind,
    quantum:draft.quantum,
    feature_dimension:draft.pipeline.pca_components??draft.quantum.qubits,
    sample_count:draft.max_samples??160,
    dataset_id:draft.dataset_id||null,
    experiment_id:null
  })});
  const advice=advisor.data;
  const liveJobs=(jobs.data||[]).filter(job=>['queued','running','cancel_requested'].includes(job.status));
  const measuredJobs=(jobs.data||[]).filter(job=>['succeeded','completed'].includes(job.status));
  const applyRecommendation=()=>{
    const recommendation=advice?.recommendation?.configuration;
    if(!recommendation)return;
    quantum(recommendation.quantum);
    pipeline({pca_components:recommendation.feature_dimension,angle_scaling:true});
    update({max_samples:recommendation.sample_count});
  };
  const backend=String(draft.quantum.backend||'Configured backend');
  const selectedModels=(models.data||[]).filter((m:ModelRecord)=>m.status==='ready'&&['vqc','qsvc','qnn'].includes(m.model_type));

  return <div className="qb-workbench-page">
    <PageHeader
      eyebrow="Quantum Workbench"
      title="Quantum execution workspace"
      description="Inspect the configured quantum path, backend-returned circuits, resource policy, and experiment jobs without changing the research contract."
      actions={<div className="flex flex-wrap gap-2"><Link className="btn btn-outline" to="/training"><SlidersHorizontal size={13}/>Model Lab</Link><Link className="btn btn-outline" to="/experiments"><FlaskConical size={13}/>Experiments</Link></div>}
    />
    <StageNav current="/quantum"/>

    <div className="qb-command-bar">
      <div className="qb-command-copy"><div className="qb-command-icon"><Atom size={16}/></div><div><strong>EntangleX Quantum Workbench</strong><span>qBraid-inspired cloud-workbench pattern · EntangleX data only</span></div></div>
      <div className="qb-command-actions">
        <span className="qb-env-chip"><span className={'qb-live-dot '+(cap.data?.available?'is-online':'is-offline')}/>{cap.data?.available?'CAPABILITY AVAILABLE':'CAPABILITY NOT REPORTED'}</span>
        <button type="button" className="btn btn-outline" onClick={()=>jobs.refetch()}><RefreshCw size={13}/>Refresh jobs</button>
      </div>
    </div>

    <WorkbenchRail items={[
      {label:'Backend',value:backend,detail:'Configured execution target',tone:cap.data?.available?'green':'amber'},
      {label:'Model family',value:kind.toUpperCase(),detail:'Quantum model selector',tone:'purple'},
      {label:'Logical qubits',value:circuit?.qubits??draft.quantum.qubits,detail:'Configured / backend-returned width',tone:'blue'},
      {label:'Active jobs',value:liveJobs.length,detail:measuredJobs.length+' completed or succeeded',tone:liveJobs.length?'amber':'green'}
    ]}/>

    <PipelineFlow items={[
      {label:'Configure',detail:kind.toUpperCase()+' · '+draft.quantum.qubits+' qubits',status:'current'},
      {label:'Advise',detail:'Bounded resource profile',status:advice?'complete':'waiting'},
      {label:'Inspect',detail:'Backend circuit representation',status:circuit?'complete':'waiting'},
      {label:'Create job',detail:'Training remains in Model Lab',status:liveJobs.length?'current':'waiting'},
      {label:'Evidence',detail:'Persisted job + experiment record',status:measuredJobs.length?'complete':'waiting'}
    ]}/>

    <ErrorBanner error={(cap.error as Error)?.message||(models.error as Error)?.message||(preview.error as Error)?.message||(fitted.error as Error)?.message||(advisor.error as Error)?.message}/>

    <div className="qb-layout mt-4">
      <aside className="qb-sidebar">
        <div className="qb-side-heading"><span>WORKSPACE</span><strong>Quantum</strong></div>
        <button className={'qb-side-item '+(inspector==='circuit'?'is-active':'')} type="button" onClick={()=>setInspector('circuit')}><TerminalSquare size={15}/><span><strong>Circuit</strong><small>Logical gate view</small></span><ChevronRight size={14}/></button>
        <button className={'qb-side-item '+(inspector==='resources'?'is-active':'')} type="button" onClick={()=>setInspector('resources')}><Gauge size={15}/><span><strong>Resources</strong><small>Bounded advisor</small></span><ChevronRight size={14}/></button>
        <div className="qb-side-divider"/>
        <div className="qb-side-section">
          <span className="qb-side-label">Execution</span>
          <div className="qb-side-fact"><Cpu size={13}/><span>Backend</span><strong>{backend}</strong></div>
          <div className="qb-side-fact"><Layers3 size={13}/><span>Shots</span><strong>{draft.quantum.shots}</strong></div>
          <div className="qb-side-fact"><Gauge size={13}/><span>Optimizer</span><strong>{draft.quantum.optimizer}</strong></div>
        </div>
        <div className="qb-side-footer"><Link to="/settings" className="qb-side-link">Workspace settings <ArrowUpRight size={12}/></Link><span>Backend remains read-only</span></div>
      </aside>

      <main className="qb-main-column">
        {inspector==='circuit'?<Card className="qb-panel-card qb-hero-panel" title="Circuit canvas" description="A compact engineering view modeled after a browser quantum IDE.">
          <div className="qb-config-row">
            <label className="field"><span>Quantum model</span><Select aria-label="Quantum model" value={kind} onChange={e=>setKind(e.target.value as QuantumKind)}><option value="vqc">VQC</option><option value="qsvc">QSVC</option><option value="qnn">QNN</option></Select></label>
            <label className="field"><span>Configured backend</span><input className="input" value={backend} readOnly/></label>
            <label className="field"><span>Logical width</span><input className="input mono" value={draft.quantum.qubits} readOnly/></label>
          </div>
          <div className="qb-action-strip">
            <div><span className="qb-kicker">CIRCUIT PREVIEW</span><strong>{circuit?'Backend representation loaded':'No circuit representation loaded'}</strong><small>{circuit?String(circuit.qubits)+' qubits · '+String(circuit.logical_depth)+' depth · '+String(circuit.parameter_count)+' parameters':'Generate a representation from the current draft.'}</small></div>
            <Button disabled={cap.data?.available===false||preview.isPending} onClick={()=>preview.mutate()}><Play size={13}/>{preview.isPending?'Generating…':'Generate circuit'}</Button>
          </div>
          <CircuitGrid circuit={circuit}/>
        </Card>:<Card className="qb-panel-card" title="Resource advisor" description="Deterministic planning data returned by the existing backend advisor.">
          <div className="grid gap-3 md:grid-cols-2">
            <MetricCard label="BACKEND" value={backend} detail={draft.quantum.noise_probability?'Noise '+draft.quantum.noise_probability:'No configured noise'}/>
            <MetricCard label="QUBITS / PCA" value={draft.quantum.qubits+' / '+(draft.pipeline.pca_components??'off')} detail="Logical width / feature dimension"/>
            <MetricCard label="CIRCUIT REPS" value={draft.quantum.feature_map_reps+' + '+draft.quantum.ansatz_reps} detail="Feature map + ansatz"/>
            <MetricCard label="ITERATIONS / SHOTS" value={draft.quantum.maxiter+' / '+draft.quantum.shots} detail={draft.quantum.optimizer+' · '+(draft.max_samples??160)+' samples'}/>
          </div>
          <div className="mt-4 flex flex-wrap gap-2"><Button disabled={advisor.isPending} onClick={()=>advisor.mutate()}><Gauge size={13}/>{advisor.isPending?'Analyzing…':'Analyze resources'}</Button>{advice&&<Button variant="outline" onClick={applyRecommendation}>Apply recommendation</Button>}</div>
          {advice&&<div className="qb-advisor-result">
            <StatusStrip items={[
              {label:'Complexity',value:String(advice.resource_profile?.circuit_complexity||'—'),status:'neutral'},
              {label:'Simulation fit',value:String(advice.resource_profile?.simulation_feasibility||'—'),status:advice.resource_profile?.simulation_feasibility==='FEASIBLE'?'good':'warning'},
              {label:'Budget',value:String(advice.budget_policy?.status||advice.budget_policy?.semantics||'—'),status:'neutral'}
            ]}/>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <Notice tone="blue"><strong>Recommendation:</strong> {advice.recommendation?.reason||'No recommendation reason returned.'}</Notice>
              <Notice tone="amber"><strong>Boundary:</strong> {advice.budget_policy?.semantics||'The resource advisor reports bounded planning information only.'}</Notice>
            </div>
          </div>}
        </Card>}

        <JobTable jobs={jobs.data||[]}/>
        <DevicePanel capability={cap.data} backend={backend} model={kind} jobs={jobs.data||[]}/>

        <Card className="qb-panel-card" title="Registered quantum models" description="Only backend-returned registered models are selectable here.">
          {selectedModels.length?<div className="qb-model-grid">{selectedModels.map(m=><button key={m.id} type="button" className={'qb-model-card '+(modelId===m.id?'is-selected':'')} onClick={()=>setModelId(m.id)}>
            <div><span className="qb-model-icon"><Atom size={14}/></span><StatusBadge value={m.status}/></div>
            <strong>{modelLabels[m.model_type]}</strong><small>{shortId(m.id)}</small>
          </button>)}</div>:<div className="qb-empty-state"><Atom size={18}/><div><strong>No ready quantum model records</strong><span>Train or retrieve a registered model from Model Lab first.</span></div></div>}
          <div className="mt-3 flex flex-wrap gap-2"><Button variant="outline" disabled={!modelId||fitted.isPending} onClick={()=>fitted.mutate()}>{fitted.isPending?'Retrieving…':'Retrieve fitted circuit'}<ExternalLink size={13}/></Button><ModelSelect models={models.data||[]} value={modelId} onChange={setModelId} quantumOnly/></div>
        </Card>
      </main>
    </div>
  </div>;
}
