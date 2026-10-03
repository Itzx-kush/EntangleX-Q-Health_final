
import type {AlignmentContract,AuditFilterParams,AuditIntegrity,AuditTimeline,Comparison,ControlledComparisonProtocol,Circuit,Dataset,DatasetInspection,DatasetLibraryItem,EvidencePackagePreflight,Explanation,Experiment,ExperimentDetail,ExperimentPipelineResponse,ExperimentProtocolResponse,ExperimentProtocolVersion,Health,Job,LineageSnapshot,ModelCard,ModelRecord,PipelineDiff,PipelinePreflight,PipelineVersion,Prediction,Preview,ProtocolComplianceResponse,ProtocolDiff,ProtocolPreflight,ProtocolTemplate,Quality,QuantumProviderDescriptor,ResearchEvidencePackage,ResourceAdvisorResponse,RobustnessResponse,RobustnessScenario,ScientificAuditEvent,SystemStatus,TrainingConfig,VerifiedEvidencePackage} from '../types/qhealth';

export function resolveApiBase(configured:string|undefined,production:boolean){
  const value=(configured||'/api').trim()||'/api';
  const normalized=value.length>1?value.replace(/\/+$/,''):value;
  if(production){
    try{
      const url=new URL(normalized);
      if(['localhost','127.0.0.1','::1'].includes(url.hostname))throw new Error('Production API base must not target localhost.');
      if(url.protocol!=='https:')throw new Error('Production cross-origin API base must use HTTPS.');
    }catch(error){
      if(normalized.startsWith('/'))return normalized;
      if(error instanceof Error&&error.message.startsWith('Production '))throw error;
      throw new Error('Production API base must be a relative path or absolute HTTPS URL.');
    }
  }
  return normalized;
}
export const apiBase=resolveApiBase(import.meta.env.VITE_API_BASE as string|undefined,import.meta.env.PROD);
const base=apiBase;
let token='';
export function setSessionToken(value:string){token=value.trim();}
async function request(path:string,options:RequestInit={}){
  const headers=new Headers(options.headers);
import type {AlignmentContract,Comparison,ControlledComparisonProtocol,Circuit,Dataset,DatasetInspection,DatasetLibraryItem,EvidencePackagePreflight,Explanation,Experiment,ExperimentDetail,ExperimentPipelineResponse,ExperimentProtocolResponse,ExperimentProtocolVersion,Health,Job,LineageSnapshot,ModelCard,ModelRecord,PipelineDiff,PipelinePreflight,PipelineVersion,Prediction,Preview,ProtocolComplianceResponse,ProtocolDiff,ProtocolPreflight,ProtocolTemplate,Quality,QuantumProviderDescriptor,ResearchEvidencePackage,ResourceAdvisorResponse,RobustnessResponse,RobustnessScenario,SubgroupAnalysisRequest,SubgroupPreflightResponse,SubgroupStudy,SystemStatus,TrainingConfig,VerifiedEvidencePackage} from '../types/qhealth';
import type {AlignmentContract,Comparison,ControlledComparisonProtocol,Circuit,Dataset,DatasetInspection,DatasetLibraryItem,EvidencePackagePreflight,Explanation,Experiment,ExperimentDetail,ExperimentPipelineResponse,ExperimentProtocolResponse,ExperimentProtocolVersion,Health,Job,LineageSnapshot,ModelCard,ModelRecord,PipelineDiff,PipelinePreflight,PipelineVersion,Prediction,Preview,ProtocolComplianceResponse,ProtocolDiff,ProtocolPreflight,ProtocolTemplate,Quality,QuantumProviderDescriptor,ResearchEvidencePackage,ResourceAdvisorResponse,RobustnessResponse,RobustnessScenario,SystemStatus,TrainingConfig,VerifiedEvidencePackage} from '../types/qhealth';

export function resolveApiBase(configured:string|undefined,production:boolean){
  const value=(configured||'/api').trim()||'/api';
  const normalized=value.length>1?value.replace(/\/+$/,''):value;
  if(production){
    try{
      const url=new URL(normalized);
      if(['localhost','127.0.0.1','::1'].includes(url.hostname))throw new Error('Production API base must not target localhost.');
      if(url.protocol!=='https:')throw new Error('Production cross-origin API base must use HTTPS.');
    }catch(error){
      if(normalized.startsWith('/'))return normalized;
      if(error instanceof Error&&error.message.startsWith('Production '))throw error;
      throw new Error('Production API base must be a relative path or absolute HTTPS URL.');
    }
  }
  return normalized;
}

export const apiBase=resolveApiBase(import.meta.env.VITE_API_BASE as string|undefined,import.meta.env.PROD);
const base=apiBase;
let token='';
export function setSessionToken(value:string){token=value.trim();}

async function request(path:string,options:RequestInit={}){
  const headers=new Headers(options.headers);
  if(token) headers.set('Authorization',`Bearer ${token}`);
  if(options.body && !(options.body instanceof FormData)) headers.set('Content-Type','application/json');
  const response=await fetch(`${base}${path}`,{...options,headers,credentials:'omit',cache:'no-store'});
  if(!response.ok){
    const body=await response.json().catch(()=>({})) as {error?:{message?:string;request_id?:string}};
    throw new Error(body.error?.request_id ? `${body.error?.message||'Request failed'} · ${body.error.request_id}` : body.error?.message||`Request failed (${response.status})`);
  }
  return response;
}
export const api={
  get:<T>(path:string)=>request(path).then(r=>r.json() as Promise<T>),
  post:<T>(path:string,body?:unknown)=>request(path,{method:'POST',body:body===undefined?undefined:JSON.stringify(body)}).then(r=>r.json() as Promise<T>),
  upload:<T>(path:string,body:FormData)=>request(path,{method:'POST',body}).then(r=>r.json() as Promise<T>),
  remove:<T=void>(path:string)=>request(path,{method:'DELETE'}).then(async response=>response.status===204?undefined as T:await response.json() as T),
  download:async(path:string,filename:string)=>{const blob=await request(path).then(r=>r.blob());const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),800);}
};

export const qh={

  threshold_preflight:(body:any)=>api.post<any>('/threshold-analysis/preflight',body),
  create_threshold_study:(body:any)=>api.post<any>('/threshold-analysis',body),
  threshold_study:(id:string)=>api.get<any>(`/threshold-analysis/${id}`),

  calibration_preflight:(body:any)=>api.post<any>('/calibration/preflight',body),
  create_calibration_study:(body:any)=>api.post<any>('/calibration',body),
  calibration_study:(id:string)=>api.get<any>(`/calibration/${id}`),

  quantum_diagnostics_preflight:(body:any)=>api.post<any>('/quantum/diagnostics/preflight',body),
  create_quantum_diagnostics:(body:any)=>api.post<any>('/quantum/diagnostics',body),
  quantum_diagnostics_by_run:(model_record_id:string)=>api.get<any>(`/quantum/diagnostics/run/${model_record_id}`),

  ablation_preflight:(body:any)=>api.post<any>('/ablation-studies/preflight',body),
  create_ablation_study:(body:any)=>api.post<any>('/ablation-studies',body),
  ablation_studies:(experiment_id:string)=>api.get<any>(`/ablation-studies/by-experiment/${experiment_id}`),
  ablation_study:(id:string)=>api.get<any>(`/ablation-studies/${id}`),

  health:()=>api.get<Health>('/health'),
  alignment:()=>api.get<AlignmentContract>('/alignment'),
  systemStatus:()=>api.get<SystemStatus>('/system/status'),
  summary:()=>api.get<{counts:{datasets:number;experiments:number;ready_models:number;active_jobs:number};recent_experiments:Experiment[];disclaimer:string}>('/summary'),
  datasets:()=>api.get<Dataset[]>('/datasets'),
  datasetLibrary:()=>api.get<DatasetLibraryItem[]>('/datasets/library'),
  datasetReadiness:()=>api.get<{total:number;verified_demo_ready:number;requires_processing:number;datasets:{slug:string;dataset_status:string;demo_readiness:DatasetLibraryItem['demo_readiness']}[]}>('/datasets/readiness'),
  registerBuiltIn:(slug:string,body?:{target?:string;positive_label?:string})=>api.post<Dataset>(`/datasets/library/${slug}`,body||{}),
  inspectDataset:(form:FormData)=>api.upload<DatasetInspection>('/datasets/inspect',form),
  dataset:(id:string)=>api.get<Dataset>(`/datasets/${id}`),
  validate:(id:string,features:string[]|null)=>api.post<Quality>(`/datasets/${id}/validate`,{features}),
  demo:()=>api.post<Dataset>('/datasets/demo'),
  upload:(form:FormData)=>api.upload<Dataset>('/datasets/upload',form),
  jobs:()=>api.get<Job[]>('/jobs'),
  createJob:(config:TrainingConfig)=>api.post<{job:Job;experiment:Experiment}>('/training/jobs',config),
  pauseJob:(id:string)=>api.post<Job>(`/jobs/${id}/pause`),
  resumeJob:(id:string)=>api.post<Job>(`/jobs/${id}/resume`),
  retryJob:(id:string)=>api.post<Job>(`/jobs/${id}/retry`),
  cancelJob:(id:string)=>api.post<Job>(`/jobs/${id}/cancel`),
  experiments:()=>api.get<Experiment[]>('/experiments'),
  experiment:(id:string)=>api.get<ExperimentDetail>(`/experiments/${id}`),
  experimentPipeline:(id:string)=>api.get<ExperimentPipelineResponse>(`/experiments/${id}/pipeline`),
  pipelines:()=>api.get<PipelineVersion[]>('/pipelines'),
  pipeline:(id:string)=>api.get<PipelineVersion>(`/pipelines/${id}`),
  createPipeline:(body:unknown)=>api.post<PipelineVersion>('/pipelines',body),
  pipelinePreflight:(body:unknown)=>api.post<PipelinePreflight>('/pipelines/preflight',body),
  publishPipeline:(id:string)=>api.post<PipelineVersion>(`/pipelines/${id}/publish`),
  pipelineDiff:(fromId:string,toId:string)=>api.get<PipelineDiff>(`/pipelines/${fromId}/diff/${toId}`),
  experimentProtocol:(id:string)=>api.get<ExperimentProtocolResponse>(`/experiments/${id}/protocol`),
  experimentProtocolCompliance:(id:string)=>api.get<ProtocolComplianceResponse>(`/experiments/${id}/protocol/compliance`),
  attachProtocol:(id:string,protocolVersionId:string)=>api.post<{experiment_id:string;protocol_version_id:string;status:string;protocol_version:ExperimentProtocolVersion}>(`/experiments/${id}/protocol/attach`,{protocol_version_id:protocolVersionId}),
  protocols:()=>api.get<ExperimentProtocolVersion[]>('/protocols'),
  protocol:(id:string)=>api.get<ExperimentProtocolVersion>(`/protocols/${id}`),
  createProtocol:(body:unknown)=>api.post<ExperimentProtocolVersion>('/protocols',body),
  protocolPreflight:(body:unknown)=>api.post<ProtocolPreflight>('/protocols/preflight',body),
  publishProtocol:(id:string)=>api.post<ExperimentProtocolVersion>(`/protocols/${id}/publish`),
  protocolDiff:(fromId:string,toId:string)=>api.get<ProtocolDiff>(`/protocols/${fromId}/diff/${toId}`),
  protocolTemplates:()=>api.get<ProtocolTemplate[]>('/protocol-templates'),
  protocolTemplate:(id:string)=>api.get<ProtocolTemplate>(`/protocol-templates/${id}`),
  instantiateProtocolTemplate:(id:string,body:unknown)=>api.post<ExperimentProtocolVersion&{created:boolean}>(`/protocol-templates/${id}/instantiate`,body),
  deleteExperiment:(id:string)=>api.remove<{id:string;status:'archived';deleted_at:string;already_deleted:boolean;preserved_records:Record<string,number>}>(`/experiments/${id}`),
  comparison:(id:string)=>api.get<Comparison>(`/experiments/${id}/comparison`),
  controlledComparisonPreflight:(id:string)=>api.post<ControlledComparisonProtocol&{preflight:true}>(`/experiments/${id}/controlled-comparison/preflight`,{}),
  createControlledComparison:(id:string)=>api.post<ControlledComparisonProtocol>(`/experiments/${id}/controlled-comparison`,{}),
  verifiedEvidence:(id:string)=>api.get<VerifiedEvidencePackage>(`/experiments/${id}/verified-evidence`),
  evidencePackagePreflight:(id:string)=>api.post<EvidencePackagePreflight>(`/experiments/${id}/evidence-package/preflight`,{}),
  createEvidencePackage:(id:string)=>api.post<ResearchEvidencePackage>(`/experiments/${id}/evidence-package`,{}),
  evidencePackage:(id:string)=>api.get<ResearchEvidencePackage>(`/experiments/${id}/evidence-package`),
  evidencePackageProvenance:(id:string,packageId:string)=>api.get<Pick<ResearchEvidencePackage,'package_id'|'package_fingerprint'|'source_context'|'provenance'|'integrity'|'artifact'>>(`/experiments/${id}/evidence-package/${packageId}/provenance`),
  downloadEvidencePackage:(id:string,packageId:string)=>api.download(
    `/experiments/${id}/evidence-package/${packageId}/download`,
    `qhealth-evidence-package-${packageId}.json`
  ),
  lineage:(id:string,options:{depth:string;direction:'ancestors'|'descendants'|'both';include_artifacts:boolean;include_evidence:boolean})=>{
    const query=new URLSearchParams({
      depth:options.depth,direction:options.direction,
      include_artifacts:String(options.include_artifacts),
      include_evidence:String(options.include_evidence),
    });
    return api.get<LineageSnapshot>(`/experiments/${id}/lineage?${query}`);
  },
  robustness:(id:string,body:{model_ids:string[];scenarios:RobustnessScenario[];random_seed:number;max_samples:number})=>api.post<RobustnessResponse>(`/experiments/${id}/robustness`,body),
  robustnessHistory:(id:string)=>api.get<{id:string;result:RobustnessResponse['results'][number]}[]>(`/experiments/${id}/robustness`),
  rerun:(id:string)=>api.post<{job:Job;experiment:Experiment}>(`/experiments/${id}/rerun`),
  pipelinePreview:(config:TrainingConfig,endpoint='/preprocessing/preview')=>api.post<Preview>(endpoint,config),
  models:()=>api.get<ModelRecord[]>('/models'),
  model:(id:string)=>api.get<ModelRecord>(`/models/${id}`),
  modelCard:(id:string)=>api.get<ModelCard>(`/models/${id}/card`),
  schema:(id:string)=>api.get<{model_id:string;features:{name:string;type:string;nullable:boolean}[];positive_label:string;negative_label:string}>(`/models/${id}/input-schema`),
  sample:(id:string)=>api.get<{features:Record<string,string|number|null>;
sample:string;source:string}>(`/models/${id}/demo-sample`),
  predict:(id:string,body:unknown)=>api.post<Prediction>(`/models/${id}/predict`,body),
  explain:(id:string,body:unknown)=>api.post<Explanation>(`/models/${id}/explain`,body),
  explanations:(id:string)=>api.get<Explanation[]>(`/models/${id}/explanations`),
  capabilities:()=>api.get<{available:boolean;runtime_verified:boolean;execution:string}>('/quantum/capabilities'),
  quantumProviders:()=>api.get<QuantumProviderDescriptor[]>('/quantum/providers'),
  quantumProviderBackends:(providerId:string)=>api.get<QuantumProviderDescriptor['backends']>(`/quantum/providers/${providerId}/backends`),
  quantumProviderPreflight:(body:{provider_id:string;backend_id:string;requested_capabilities:string[];configuration:Record<string,unknown>})=>api.post<{status:'READY'|'BLOCKED';blockers:string[];warnings:string[];configuration_fingerprint:string}>('/quantum/providers/preflight',body),
  resourcePolicy:()=>api.get<ResourceAdvisorResponse['budget_policy']>('/quantum/resource-policy'),
  resourceAdvisor:(body:{model_type:'vqc'|'qsvc'|'qnn';quantum:TrainingConfig['quantum'];feature_dimension:number;sample_count:number;dataset_id:string|null;experiment_id:string|null})=>api.post<ResourceAdvisorResponse>('/quantum/resource-advisor',body),
  circuit:(body:unknown)=>api.post<Circuit>('/quantum/circuit',body),
  fittedCircuit:(id:string)=>api.get<Circuit>(`/models/${id}/circuit`),
  report:(id:string,format:'html'|'json')=>api.download(
    `/experiments/${id}/report?format=${format}`,
    `qhealth-${id}.${format}`
  ),
  aiChat:(body:{message:string;conversation:{role:'user'|'model';content:string}[]})=>
    api.post<{reply:string}>('/ai/chat',body)
};
