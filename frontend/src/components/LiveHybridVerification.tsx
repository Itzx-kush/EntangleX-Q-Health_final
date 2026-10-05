import {useState} from 'react';
import {Link} from 'react-router-dom';
import {AlertTriangle,ArrowRight,CheckCircle2,CircleDashed,FlaskConical,LoaderCircle,RotateCcw,ShieldCheck,Sparkles,XCircle} from 'lucide-react';
import {ApiError,ApiTransportError,qh} from '../lib/api';
import type {HybridRuntimeCheck,HybridRuntimeVerification} from '../types/qhealth';
import {Badge,Button,Card} from './ui';
import {ErrorBanner,MetricCard,Notice} from './Shared';
import {dateTime} from '../utils/format';

type LiveHybridVerificationProps={
  datasetName?:string;
  hybridDetailPath?:string;
};

type ErrorState={kind:'transport'|'api';message:string};

const CHECK_ORDER=[
  'pennylane_import',
  'pytorch_import',
  'quantum_device_initialization',
  'preprocessing_and_feature_reduction',
  'hybrid_training',
  'quantum_forward_pass',
  'trainable_quantum_parameters',
  'positive_class_probability',
  'sensitivity_first_threshold',
  'shap_explainability',
  'artifact_save',
  'artifact_reload',
] as const;

const CHECK_LABELS:Record<string,string>={
  pennylane_import:'PennyLane import',
  pytorch_import:'PyTorch import',
  quantum_device_initialization:'Quantum device initialization',
  preprocessing_and_feature_reduction:'Preprocessing / feature reduction',
  hybrid_training:'Hybrid training',
  quantum_forward_pass:'Quantum forward pass',
  trainable_quantum_parameters:'Trainable quantum parameters',
  positive_class_probability:'Positive-class probability',
  sensitivity_first_threshold:'Sensitivity-first threshold',
  shap_explainability:'SHAP explainability',
  artifact_save:'Artifact save',
  artifact_reload:'Artifact reload',
};

const PIPELINE_SEQUENCE=[
  'Existing preprocessing / feature reduction',
  'PennyLane default.qubit initialization',
  'Trainable quantum circuit & expectation values',
  'PyTorch output head & positive-class probability',
  'Sensitivity-first threshold',
  'SHAP explanation',
  'Artifact save / reload',
];

function orderedChecks(checks:Record<string,HybridRuntimeCheck>|null|undefined):[string,HybridRuntimeCheck][]{
  if(!checks)return [];
  const seen=new Set<string>();
  const ordered:[string,HybridRuntimeCheck][]=[];
  for(const key of CHECK_ORDER){
    if(checks[key]){ordered.push([key,checks[key]]);seen.add(key);}
  }
  for(const [key,check] of Object.entries(checks)){
    if(!seen.has(key))ordered.push([key,check]);
  }
  return ordered;
}

function SummaryRow({label,value,mono=false}:{label:string;value:unknown;mono?:boolean}){
  const text=value===null||value===undefined||value===''?'Not returned':String(value);
  return <div className="flex items-start justify-between gap-4 border-b py-2 last:border-b-0">
    <span className="text-xs text-[#56657D]">{label}</span>
    <strong className={(mono?'mono ':'')+'text-right text-xs font-semibold text-[#102A5C]'}>{text}</strong>
  </div>;
}

function probabilityPercent(value:number|undefined|null){
  if(typeof value!=='number'||!Number.isFinite(value))return null;
  return Math.round(value*100);
}

function friendlyModelType(value:string|undefined|null){
  if(value==='hybrid_pennylane_torch')return 'PennyLane + PyTorch Hybrid';
  return value||'Not returned';
}

function CheckRow({name,check}:{name:string;check:HybridRuntimeCheck}){
  const passed=check.status==='PASS';
  return <div className="flex items-start gap-3 rounded-xl border border-[#D8E2EF] bg-white px-3 py-2">
    {passed
      ? <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-[#159A70]" aria-hidden="true"/>
      : <XCircle size={16} className="mt-0.5 shrink-0 text-[#B42318]" aria-hidden="true"/>}
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-[#102A5C]">{CHECK_LABELS[name]||name}</span>
        <Badge tone={passed?'green':'red'}>{check.status}</Badge>
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-[#56657D]">{check.detail}</p>
    </div>
  </div>;
}

function ConfigGrid({result}:{result:HybridRuntimeVerification}){
  const config=result.configuration;
  if(!config)return null;
  const rows=[
    ['Qubits',config.qubits],
    ['Quantum layers',config.quantum_layers],
    ['Hidden dimensions',Array.isArray(config.hidden_dimensions)?config.hidden_dimensions.join(' → '):config.hidden_dimensions],
    ['Epochs',config.epochs],
    ['Batch size',config.batch_size],
    ['Sample cap',config.sample_cap],
    ['CV folds',config.cv_folds],
    ['Seed',config.seed],
  ] as const;
  return <div>
    <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">CONFIGURATION USED BY LIVE RUN</h3>
    <div className="mt-2 grid gap-px overflow-hidden rounded-xl border border-[#D8E2EF] bg-[#D8E2EF] sm:grid-cols-2 lg:grid-cols-4">
      {rows.map(([label,value])=><div key={label} className="bg-[#F7FAFD] px-3 py-2">
        <div className="text-[9px] font-semibold tracking-[0.1em] text-[#56657D]">{label.toUpperCase()}</div>
        <div className="mt-1 break-words text-xs font-semibold text-[#102A5C]">{value===null||value===undefined?'Not returned':String(value)}</div>
      </div>)}
    </div>
  </div>;
}

export function LiveHybridVerification({datasetName,hybridDetailPath}:LiveHybridVerificationProps){
  const [result,setResult]=useState<HybridRuntimeVerification|null>(null);
  const [running,setRunning]=useState(false);
  const [error,setError]=useState<ErrorState|null>(null);

  async function run(force:boolean){
    if(running)return;
    setRunning(true);
    setError(null);
    try{
      setResult(await qh.hybridRuntimeVerification(force));
    }catch(caught){
      if(caught instanceof ApiTransportError){
        setError({kind:'transport',message:caught.message});
      }else if(caught instanceof ApiError){
        setError({kind:'api',message:caught.message});
      }else{
        setError({kind:'api',message:'The live verifier could not be reached.'});
      }
    }finally{
      setRunning(false);
    }
  }

  const checks=result?orderedChecks(result.checks):[];
  const verified=result?.status==='VERIFIED'&&result.verified===true;
  const failed=result!==null&&result.status==='FAILED';
  const probability=result?.prediction?.positive_class_probability;
  const probabilityPct=probabilityPercent(probability);

  return <section className="mt-5" aria-label="Live hybrid runtime verification">
    <Card
      className="border-[#1769E0]/25 bg-white"
      title="Live Hybrid Runtime Verification"
      description="Fresh execution of the actual PennyLane + PyTorch hybrid path in the current backend environment, kept separate from the packaged verified/precomputed demo."
    >
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={result===null?'blue':verified?'green':failed?'red':'blue'}>
          {result===null?'LIVE RUNTIME':verified?'LIVE HYBRID VERIFIED':failed?'LIVE HYBRID VERIFICATION FAILED':'LIVE RUNTIME'}
        </Badge>
        <Badge tone="purple">{datasetName||'Early Stage Diabetes Risk Prediction'}</Badge>
        <Badge tone="green">PennyLane + PyTorch Hybrid</Badge>
        <Badge tone="blue">default.qubit</Badge>
        <Badge tone="amber">Real hardware: false</Badge>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button disabled={running} onClick={()=>void run(Boolean(result))}>
          {running
            ? <><LoaderCircle size={14} className="animate-spin"/>Running…</>
            : result
              ? <><RotateCcw size={14}/>Re-verify Live Runtime</>
              : <><FlaskConical size={14}/>Run Live Verification</>}
        </Button>
        {!running&&result===null&&<span className="text-xs text-[#56657D]">Run the live verifier to execute the real PennyLane + PyTorch hybrid path in the current backend environment.</span>}
        {!running&&result&&<span className="text-xs text-[#56657D]">Re-verify triggers a fresh backend run with <span className="mono">force=true</span>.</span>}
      </div>

      {running&&<div className="mt-4 rounded-2xl border border-[#1769E0]/25 bg-[#1769E0]/[0.045] p-4" role="status" aria-live="polite">
        <div className="flex items-center gap-2 text-sm font-semibold text-[#102A5C]">
          <LoaderCircle size={16} className="animate-spin text-[#1769E0]" aria-hidden="true"/>
          RUNNING LIVE VERIFICATION…
        </div>
        <p className="mt-1 text-xs leading-relaxed text-[#56657D]">Executing the fixed flagship hybrid pipeline in the backend. This performs real preprocessing, hybrid training, quantum expectation evaluation, SHAP and artifact work, and may take a moment.</p>
        <ul className="mt-3 grid gap-1.5 text-xs text-[#56657D] sm:grid-cols-2">
          {PIPELINE_SEQUENCE.map((phase,index)=><li key={phase} className="flex items-center gap-2"><CircleDashed size={13} className="shrink-0 text-[#18B6C9]" aria-hidden="true"/><span>{index+1}. {phase}</span></li>)}
        </ul>
      </div>}

      {error&&<div className="mt-4"><ErrorBanner error={error.message}/>
        <Notice tone="amber">{error.kind==='transport'?'Unable to reach live verifier':'The backend verifier endpoint returned an error'} — this is not a verification PASS or FAIL. The verified demo remains available.</Notice>
      </div>}

      {result===null&&!running&&!error&&<div className="mt-4 rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] px-3 py-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-[#56657D]"><ShieldCheck size={14} className="text-[#56657D]" aria-hidden="true"/>NOT RUN</div>
        <p className="mt-1 text-xs leading-relaxed text-[#56657D]">Run the live verifier to execute the real PennyLane + PyTorch hybrid path in the current backend environment. No result is shown until the backend reports one.</p>
      </div>}

      {result&&<div className="mt-5">
        <div className={'flex items-center gap-2 text-sm font-semibold '+(verified?'text-[#159A70]':'text-[#B42318]')} role="status">
          {verified
            ? <><CheckCircle2 size={16} className="text-[#159A70]" aria-hidden="true"/>LIVE HYBRID VERIFIED</>
            : <><AlertTriangle size={16} className="text-[#B42318]" aria-hidden="true"/>LIVE HYBRID VERIFICATION FAILED</>}
        </div>

        {result.error&&<div className="mt-2"><Notice tone="amber">{result.error}</Notice></div>}

        {failed&&<div className="mt-2"><Notice tone="amber">Verified Demo remains available — the packaged precomputed evidence is unaffected by this live runtime result.</Notice></div>}

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] p-3">
            <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">VERIFICATION SUMMARY</h3>
            <div className="mt-2">
              <SummaryRow label="Last live verification" value={result.verified_at?dateTime(result.verified_at):undefined}/>
              <SummaryRow label="Dataset" value={result.dataset}/>
              <SummaryRow label="Model" value={friendlyModelType(result.model_type)}/>
              <SummaryRow label="Quantum framework" value={result.framework}/>
              <SummaryRow label="Classical framework" value={result.classical_framework}/>
              <SummaryRow label="Execution" value={result.execution}/>
              <SummaryRow label="Backend" value={result.backend}/>
              <SummaryRow label="Real hardware" value={result.real_hardware===false?'False':'See backend response'}/>
            </div>
          </div>

          <div className="rounded-xl border border-[#D8E2EF] bg-[#F7FAFD] p-3">
            <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">LIVE PREDICTION</h3>
            {probabilityPct!==null
              ? <div className="mt-3">
                  <div className="flex items-center justify-between text-xs text-[#56657D]"><span>Research positive-class probability</span><strong className="mono text-[#102A5C]">{probabilityPct}%</strong></div>
                  <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-[#D8E2EF]" role="img" aria-label={`Research positive-class probability ${probabilityPct}%`}>
                    <div className="h-full rounded-full bg-[#18B6C9]" style={{width:`${Math.max(0,Math.min(100,probabilityPct))}%`}}/>
                  </div>
                </div>
              : <p className="mt-2 text-xs text-[#56657D]">No finite positive-class probability was returned.</p>}
            <div className="mt-3">
              <SummaryRow label="Predicted positive class" value={result.prediction?.predicted_positive_class}/>
              <SummaryRow label="Threshold strategy" value={result.prediction?.threshold_strategy}/>
              <SummaryRow label="Selected threshold" value={result.prediction?.operating_threshold} mono/>
              <SummaryRow label="Threshold source" value={result.prediction?.threshold_source}/>
              <SummaryRow label="Target sensitivity" value={result.prediction?.target_sensitivity}/>
            </div>
          </div>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          <MetricCard label="EXPECTATION VALUES" value={result.quantum?.expectation_value_dimension?`${result.quantum.expectation_value_dimension}/sample`:'Not returned'} detail="Quantum representation width"/>
          <MetricCard label="TRAINABLE QUANTUM PARAMS" value={result.quantum?.quantum_parameters_changed===true?'Trained':'Not confirmed'} detail="Parameters changed during training"/>
          <MetricCard label="REAL HARDWARE" value={result.real_hardware===false?'Not used':String(result.real_hardware??false)} detail="Local quantum simulation only"/>
        </div>

        <div className="mt-4">
          <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">INDIVIDUAL CHECKS</h3>
          {checks.length
            ? <div className="mt-2 grid gap-2 md:grid-cols-2">{checks.map(([name,check])=><CheckRow key={name} name={name} check={check}/>)}</div>
            : <p className="mt-2 text-xs text-[#56657D]">No individual checks were returned by the backend.</p>}
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">SHAP VERIFICATION</h3>
            <div className="mt-2 rounded-xl border border-[#D8E2EF] bg-white p-3">
              <div className="flex items-center gap-2">
                {result.checks?.shap_explainability?.status==='PASS'
                  ? <CheckCircle2 size={14} className="text-[#159A70]" aria-hidden="true"/>
                  : <XCircle size={14} className="text-[#B42318]" aria-hidden="true"/>}
                <Badge tone={result.checks?.shap_explainability?.status==='PASS'?'green':'red'}>SHAP</Badge>
              </div>
              <div className="mt-2">
                <SummaryRow label="Explained case count" value={result.shap?.explained_case_count}/>
                <SummaryRow label="Background count" value={result.shap?.background_count}/>
                <SummaryRow label="Output semantics" value={result.shap?.output_semantics}/>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">SHAP explains the supported final hybrid output through feature contributions — not the quantum circuit itself.</p>
            </div>
          </div>
          <div>
            <h3 className="text-[10px] font-semibold tracking-[0.14em] text-[#56657D]">ARTIFACT INTEGRITY</h3>
            <div className="mt-2 rounded-xl border border-[#D8E2EF] bg-white p-3">
              <div className="mt-1"><SummaryRow label="Artifact save" value={result.artifact?.saved===true?'PASS':result.artifact?.saved===false?'FAIL':'Not returned'}/></div>
              <div className="mt-1"><SummaryRow label="Artifact reload" value={result.artifact?.reloaded===true?'PASS':result.artifact?.reloaded===false?'FAIL':'Not returned'}/></div>
              <p className="mt-2 text-[10px] leading-relaxed text-[#56657D]">The verifier saves the live hybrid artifact through the existing storage mechanism, reloads it, and checks that the reloaded model can again produce a valid probability.</p>
            </div>
          </div>
        </div>

        <ConfigGrid result={result}/>

        <div className="mt-4 flex flex-wrap gap-2">
          {hybridDetailPath&&<Link className="btn btn-outline" to={hybridDetailPath}>Open Hybrid Model Detail <ArrowRight size={13}/></Link>}
          <a className="btn btn-outline" href="#hybrid-architecture">View Hybrid Architecture</a>
          <Link className="btn btn-outline" to="/comparison">View 7-Model Comparison <ArrowRight size={13}/></Link>
        </div>
      </div>}

      <div className="mt-4">
        <Notice tone="blue">Research runtime verification — this confirms the implemented hybrid runtime executed successfully in local simulation. It does not establish clinical validation or quantum advantage.</Notice>
      </div>

      <div className="mt-3 flex items-start gap-2 rounded-xl border border-[#D8E2EF] bg-white p-3">
        <Sparkles size={14} className="mt-0.5 shrink-0 text-[#6946D9]" aria-hidden="true"/>
        <p className="text-[11px] leading-relaxed text-[#56657D]">Live verification confirms the hybrid path executes; controlled benchmark evidence determines comparative performance. The existing seven-model benchmark remains the source of comparative performance evidence.</p>
      </div>
    </Card>
  </section>;
}
