import type {AlignmentContract,Comparison,Circuit,Dataset,DatasetInspection,DatasetLibraryItem,Explanation,Experiment,ExperimentDetail,Health,Job,ModelRecord,Prediction,Preview,Quality,ResourceAdvisorResponse,RobustnessResponse,RobustnessScenario,SystemStatus,TrainingConfig,VerifiedEvidencePackage} from '../types/qhealth';

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
  remove:(path:string)=>request(path,{method:'DELETE'}).then(()=>undefined),
  download:async(path:string,filename:string)=>{const blob=await request(path).then(r=>r.blob());const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),800);}
};

export const qh={
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
  jobs:()=>api.get<Job[]>('/training/jobs'),
  createJob:(config:TrainingConfig)=>api.post<{job:Job;experiment:Experiment}>('/training/jobs',config),
  cancelJob:(id:string)=>api.post<Job>(`/training/jobs/${id}/cancel`),
  experiments:()=>api.get<Experiment[]>('/experiments'),
  experiment:(id:string)=>api.get<ExperimentDetail>(`/experiments/${id}`),
  comparison:(id:string)=>api.get<Comparison>(`/experiments/${id}/comparison`),
  verifiedEvidence:(id:string)=>api.get<VerifiedEvidencePackage>(`/experiments/${id}/verified-evidence`),
  robustness:(id:string,body:{model_ids:string[];scenarios:RobustnessScenario[];random_seed:number;max_samples:number})=>api.post<RobustnessResponse>(`/experiments/${id}/robustness`,body),
  robustnessHistory:(id:string)=>api.get<{id:string;result:RobustnessResponse['results'][number]}[]>(`/experiments/${id}/robustness`),
  rerun:(id:string)=>api.post<{job:Job;experiment:Experiment}>(`/experiments/${id}/rerun`),
  pipelinePreview:(config:TrainingConfig,endpoint='/preprocessing/preview')=>api.post<Preview>(endpoint,config),
  models:()=>api.get<ModelRecord[]>('/models'),
  model:(id:string)=>api.get<ModelRecord>(`/models/${id}`),
  schema:(id:string)=>api.get<{model_id:string;features:{name:string;type:string;nullable:boolean}[];positive_label:string;negative_label:string}>(`/models/${id}/input-schema`),
  sample:(id:string)=>api.get<{features:Record<string,string|number|null>;
sample:string;source:string}>(`/models/${id}/demo-sample`),
  predict:(id:string,body:unknown)=>api.post<Prediction>(`/models/${id}/predict`,body),
  explain:(id:string,body:unknown)=>api.post<Explanation>(`/models/${id}/explain`,body),
  explanations:(id:string)=>api.get<Explanation[]>(`/models/${id}/explanations`),
  capabilities:()=>api.get<{available:boolean;runtime_verified:boolean;execution:string}>('/quantum/capabilities'),
  resourcePolicy:()=>api.get<ResourceAdvisorResponse['budget_policy']>('/quantum/resource-policy'),
  resourceAdvisor:(body:{model_type:'vqc'|'qsvc'|'qnn';quantum:TrainingConfig['quantum'];feature_dimension:number;sample_count:number;dataset_id:string|null;experiment_id:string|null})=>api.post<ResourceAdvisorResponse>('/quantum/resource-advisor',body),
  circuit:(body:unknown)=>api.post<Circuit>('/quantum/circuit',body),
  fittedCircuit:(id:string)=>api.get<Circuit>(`/models/${id}/circuit`),
  report:(id:string,format:'html'|'json')=>api.download(`/experiments/${id}/report?format=${format}`,`qhealth-${id}.${format}`)
};
