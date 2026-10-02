import type {NewResearchActivity,ResearchMetadata} from '../research/historyTypes';

export const ACTIVE_GUEST_SESSION_KEY='qhealth-active-guest-session';
const MIGRATION_KEY='qhealth-guest-migration';
const DRAFT_KEY='qhealth-tictac-draft';
const DEMO_KEY='qhealth-verified-demo-context';

export type GuestMigrationStatus='pending'|'importing'|'completed'|'failed';

export type GuestMigrationSnapshot={
  version:1;
  migrationId:string;
  status:GuestMigrationStatus;
  createdAt:string;
  destination:string;
  datasetId:string|null;
  experimentId:string|null;
  metadata:ResearchMetadata;
  error:string|null;
};

function safeJson(raw:string|null):Record<string,unknown>{
  if(!raw)return {};
  try{
    const value=JSON.parse(raw);
    return value&&typeof value==='object'&&!Array.isArray(value)?value:{};
  }catch{return {}}
}

function text(value:unknown){
  return typeof value==='string'&&value.trim()?value.trim():null;
}

function numberValue(value:unknown){
  return typeof value==='number'&&Number.isFinite(value)?value:null;
}

function stringList(value:unknown){
  return Array.isArray(value)?value.filter((item):item is string=>typeof item==='string').slice(0,12):[];
}

function objectValue(value:unknown){
  return value&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
}

export function ensureActiveGuestSession(){
  try{
    const existing=sessionStorage.getItem(ACTIVE_GUEST_SESSION_KEY);
    const prior=readGuestMigration();
    if(existing&&prior?.status!=='completed')return existing;
    const id=typeof crypto.randomUUID==='function'?crypto.randomUUID():`guest-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    sessionStorage.setItem(ACTIVE_GUEST_SESSION_KEY,id);
    return id;
  }catch{return null}
}

export function inspectMigratableGuestState(destination:string){
  try{
    const migrationId=sessionStorage.getItem(ACTIVE_GUEST_SESSION_KEY);
    if(!migrationId)return null;
    const draft=safeJson(localStorage.getItem(DRAFT_KEY));
    const demo=safeJson(localStorage.getItem(DEMO_KEY));
    const pipeline=objectValue(draft.pipeline);
    const quantum=objectValue(draft.quantum);
    const hybrid=objectValue(draft.hybrid);
    const datasetId=text(draft.dataset_id)||text(demo.datasetId);
    const experimentId=Boolean(demo.active)?text(demo.experimentId):null;
    const models=stringList(draft.models);
    const changedConfiguration=Boolean(
      datasetId
      ||experimentId
      ||Array.isArray(draft.features)&&draft.features.length>0
      ||numberValue(draft.seed)!==null&&numberValue(draft.seed)!==42
      ||numberValue(draft.test_size)!==null&&numberValue(draft.test_size)!==.2
      ||numberValue(draft.cv_folds)!==null&&numberValue(draft.cv_folds)!==3
      ||numberValue(draft.max_samples)!==null&&numberValue(draft.max_samples)!==160
      ||text(draft.duplicate_policy)!==null&&text(draft.duplicate_policy)!=='reject'
      ||text(draft.threshold_strategy)!==null&&text(draft.threshold_strategy)!=='fixed'
      ||text(draft.calibration)!==null&&text(draft.calibration)!=='none'
      ||text(pipeline.imputer)!==null&&text(pipeline.imputer)!=='median'
      ||text(pipeline.scaler)!==null&&text(pipeline.scaler)!=='standard'
      ||text(pipeline.selection)!==null&&text(pipeline.selection)!=='anova'
      ||numberValue(pipeline.k_features)!==null&&numberValue(pipeline.k_features)!==12
      ||numberValue(pipeline.pca_components)!==null&&numberValue(pipeline.pca_components)!==4
      ||stringList(pipeline.log_features).length>0
      ||Array.isArray(pipeline.ratios)&&pipeline.ratios.length>0
      ||text(quantum.backend)!==null&&text(quantum.backend)!=='statevector'
      ||numberValue(quantum.qubits)!==null&&numberValue(quantum.qubits)!==4
      ||numberValue(quantum.shots)!==null&&numberValue(quantum.shots)!==1024
      ||numberValue(quantum.feature_map_reps)!==null&&numberValue(quantum.feature_map_reps)!==1
      ||numberValue(quantum.ansatz_reps)!==null&&numberValue(quantum.ansatz_reps)!==1
      ||text(quantum.optimizer)!==null&&text(quantum.optimizer)!=='COBYLA'
      ||numberValue(hybrid.quantum_layers)!==null&&numberValue(hybrid.quantum_layers)!==2
      ||models.some(model=>!['logistic_regression','svm','random_forest'].includes(model))
    );
    if(!changedConfiguration)return null;
    const safeDestination=destination.startsWith('/')&&!destination.startsWith('//')?destination:'/';
    const metadata:ResearchMetadata={
      source:'guest_session',
      research_stage:safeDestination.split('?')[0],
      models,
      selected_feature_count:Array.isArray(draft.features)?draft.features.length:0,
      seed:numberValue(draft.seed),
      test_size:numberValue(draft.test_size),
      cv_folds:numberValue(draft.cv_folds),
      max_samples:numberValue(draft.max_samples),
      duplicate_policy:text(draft.duplicate_policy),
      threshold_strategy:text(draft.threshold_strategy),
      calibration:text(draft.calibration),
      imputer:text(pipeline.imputer),
      scaler:text(pipeline.scaler),
      feature_selection:text(pipeline.selection),
      selected_feature_limit:numberValue(pipeline.k_features),
      pca_components:numberValue(pipeline.pca_components),
      angle_scaling:typeof pipeline.angle_scaling==='boolean'?pipeline.angle_scaling:null,
      log_feature_count:Array.isArray(pipeline.log_features)?pipeline.log_features.length:0,
      ratio_count:Array.isArray(pipeline.ratios)?pipeline.ratios.length:0,
      quantum_backend:text(quantum.backend),
      quantum_qubits:numberValue(quantum.qubits),
      quantum_shots:numberValue(quantum.shots),
      quantum_optimizer:text(quantum.optimizer),
      quantum_feature_map_reps:numberValue(quantum.feature_map_reps),
      quantum_ansatz_reps:numberValue(quantum.ansatz_reps),
      hybrid_backend:text(hybrid.backend),
      hybrid_qubits:numberValue(hybrid.qubits),
      hybrid_layers:numberValue(hybrid.quantum_layers),
      verified_demo:Boolean(demo.active),
    };
    return {migrationId,destination:safeDestination,datasetId,experimentId,metadata};
  }catch{return null}
}

export function createGuestMigration(destination:string):GuestMigrationSnapshot|null{
  const candidate=inspectMigratableGuestState(destination);
  if(!candidate)return null;
  const existing=readGuestMigration();
  if(existing&&existing.migrationId===candidate.migrationId)return existing;
  const snapshot:GuestMigrationSnapshot={
    version:1,
    migrationId:candidate.migrationId,
    status:'pending',
    createdAt:new Date().toISOString(),
    destination:candidate.destination,
    datasetId:candidate.datasetId,
    experimentId:candidate.experimentId,
    metadata:candidate.metadata,
    error:null,
  };
  writeGuestMigration(snapshot);
  return snapshot;
}

export function readGuestMigration():GuestMigrationSnapshot|null{
  try{
    const value=JSON.parse(sessionStorage.getItem(MIGRATION_KEY)||'null') as GuestMigrationSnapshot|null;
    if(!value||value.version!==1||!value.migrationId||!value.destination)return null;
    return value.status==='importing'?{...value,status:'pending'}:value;
  }catch{return null}
}

export function writeGuestMigration(snapshot:GuestMigrationSnapshot){
  try{sessionStorage.setItem(MIGRATION_KEY,JSON.stringify(snapshot))}catch{}
}

export function clearGuestMigration(){
  try{
    sessionStorage.removeItem(MIGRATION_KEY);
    sessionStorage.removeItem(ACTIVE_GUEST_SESSION_KEY);
  }catch{}
}

export function guestMigrationActivity(snapshot:GuestMigrationSnapshot):NewResearchActivity{
  return {
    activityType:'session',
    title:'Guest research session saved',
    status:'imported',
    occurredAt:snapshot.createdAt,
    route:snapshot.destination,
    referenceId:snapshot.experimentId,
    experimentId:snapshot.experimentId,
    datasetId:snapshot.datasetId,
    metadata:snapshot.metadata,
    idempotencyKey:`guest-session:${snapshot.migrationId}`,
  };
}
