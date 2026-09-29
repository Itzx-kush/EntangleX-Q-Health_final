import type {Experiment,Job,ModelRecord} from '../types/qhealth';

export type DemoStageKey =
  | 'dataset'
  | 'quality'
  | 'preprocessing'
  | 'features'
  | 'pca'
  | 'training'
  | 'quantum'
  | 'comparison'
  | 'explainability'
  | 'prediction'
  | 'report';

export type DemoStageStatus =
  | 'NOT STARTED'
  | 'READY'
  | 'IN PROGRESS'
  | 'COMPLETED'
  | 'BLOCKED'
  | 'UNAVAILABLE';

export interface DemoState {
  currentExperiment:Experiment|null;
  currentModels:ModelRecord[];
  readyModels:ModelRecord[];
  currentJob:Job|null;
  stages:Record<DemoStageKey,DemoStageStatus>;
}

const terminalSuccess=new Set(['succeeded','completed','partial']);
const activeStates=new Set(['queued','running','cancel_requested']);
const terminalFailure=new Set(['failed','cancelled','interrupted']);

/**
 * Derive judge-facing readiness from relationships already persisted by the backend.
 * The latest experiment for the active dataset is authoritative; records from another
 * dataset or an older experiment never unlock its downstream stages.
 */
export function deriveDemoState(
  datasetId:string,
  experiments:Experiment[]=[],
  models:ModelRecord[]=[],
  jobs:Job[]=[],
  quantumAvailable:boolean|undefined,
):DemoState{
  const currentExperiment=datasetId
    ? experiments
      .filter(experiment=>experiment.dataset_id===datasetId)
      .reduce<Experiment|null>(
        (latest,experiment)=>!latest||experiment.created_at>latest.created_at?experiment:latest,
        null,
      )
    : null;
  const currentModels=currentExperiment
    ? models.filter(model=>
      model.dataset_id===datasetId&&model.experiment_id===currentExperiment.id
    )
    : [];
  const readyModels=currentModels.filter(model=>model.status==='ready');
  const currentJobs=currentExperiment
    ? jobs.filter(job=>job.experiment_id===currentExperiment.id)
    : [];
  const currentJob=currentJobs[0]||null;
  const hasDataset=Boolean(datasetId);
  const inProgress=Boolean(
    currentExperiment&&(
      activeStates.has(currentExperiment.status)||
      currentJobs.some(job=>activeStates.has(job.status))
    )
  );
  const terminallyFinished=Boolean(
    currentExperiment&&terminalSuccess.has(currentExperiment.status)
  );
  const completed=Boolean(terminallyFinished&&readyModels.length);
  const failed=Boolean(
    currentExperiment&&
    terminalFailure.has(currentExperiment.status)
  );
  const quantumCompleted=readyModels.some(model=>
    ['vqc','qsvc','qnn'].includes(model.model_type)
  );

  const datasetDependent:DemoStageStatus=hasDataset?'READY':'BLOCKED';
  const modelDependent:DemoStageStatus=completed?'READY':'BLOCKED';
  const training:DemoStageStatus=!hasDataset
    ? 'BLOCKED'
    : inProgress
      ? 'IN PROGRESS'
      : completed
        ? 'COMPLETED'
        : failed||terminallyFinished
          ? 'BLOCKED'
          : 'READY';
  const quantum:DemoStageStatus=!hasDataset
    ? 'BLOCKED'
    : quantumCompleted
      ? 'COMPLETED'
      : quantumAvailable===false
        ? 'UNAVAILABLE'
        : quantumAvailable
          ? 'READY'
          : 'NOT STARTED';

  return {
    currentExperiment,
    currentModels,
    readyModels,
    currentJob,
    stages:{
      dataset:hasDataset?'READY':'NOT STARTED',
      quality:datasetDependent,
      preprocessing:datasetDependent,
      features:datasetDependent,
      pca:datasetDependent,
      training,
      quantum,
      comparison:completed&&readyModels.length>=2?'READY':'BLOCKED',
      explainability:modelDependent,
      prediction:modelDependent,
      report:completed?'READY':'BLOCKED',
    },
  };
}