import {describe,expect,it} from 'vitest';
import {deriveDemoState} from '../lib/demoState';
import type {Experiment,Job,ModelRecord} from '../types/qhealth';

const experiment=(id:string,datasetId:string,status='succeeded',createdAt='2026-09-29T00:00:00Z'):Experiment=>({
  id,
  dataset_id:datasetId,
  parent_id:null,
  status,
  config:{dataset_id:datasetId,models:['logistic_regression'],pipeline:{} as never,quantum:{} as never,hybrid:{} as never,parameters:{} as never,seed:17,test_size:.2,cv_folds:2,max_samples:80,duplicate_policy:'reject',probability_threshold:.5,threshold_strategy:'fixed',target_sensitivity:.95,calibration:'none',calibration_folds:3,features:null},
  summary:{},
  created_at:createdAt,
});

const model=(id:string,experimentId:string,datasetId:string,status='ready',modelType:'logistic_regression'|'svm'='logistic_regression'):ModelRecord=>({
  id,
  experiment_id:experimentId,
  dataset_id:datasetId,
  model_type:modelType,
  status,
  details:{},
  metrics:{},
  created_at:'2026-09-29T00:00:00Z',
});

const job=(experimentId:string,status='running'):Job=>({
  id:`job-${experimentId}`,
  experiment_id:experimentId,
  status,
  progress:40,
  state:'Training',
  errors:[],
  created_at:'2026-09-29T00:00:00Z',
  updated_at:'2026-09-29T00:00:00Z',
});

describe('SIH Demo Center state matrix',()=>{
  it('blocks dataset-dependent stages when no dataset is active',()=>{
    const state=deriveDemoState('',[],[],[],true);
    expect(state.stages).toMatchObject({
      dataset:'NOT STARTED',
      quality:'BLOCKED',
      preprocessing:'BLOCKED',
      training:'BLOCKED',
      comparison:'BLOCKED',
      robustness:'BLOCKED',
      explainability:'BLOCKED',
      prediction:'BLOCKED',
      report:'BLOCKED',
    });
  });

  it('makes configuration stages ready without claiming they executed',()=>{
    const state=deriveDemoState('dataset-a',[],[],[],true);
    expect(state.stages.dataset).toBe('READY');
    expect(state.stages.quality).toBe('READY');
    expect(state.stages.preprocessing).toBe('READY');
    expect(state.stages.features).toBe('READY');
    expect(state.stages.pca).toBe('READY');
    expect(state.stages.training).toBe('READY');
    expect(state.stages.comparison).toBe('BLOCKED');
    expect(state.stages.robustness).toBe('BLOCKED');
  });

  it('reports a current-dataset active job as in progress',()=>{
    const current=experiment('experiment-a','dataset-a','running');
    const state=deriveDemoState('dataset-a',[current],[],[job(current.id)],true);
    expect(state.currentExperiment?.id).toBe(current.id);
    expect(state.stages.training).toBe('IN PROGRESS');
    expect(state.stages.report).toBe('BLOCKED');
  });

  it('does not use a ready model from another experiment or dataset',()=>{
    const current=experiment('experiment-a','dataset-a');
    const foreign=model('model-b','experiment-b','dataset-b');
    const state=deriveDemoState('dataset-a',[current],[foreign],[],true);
    expect(state.readyModels).toHaveLength(0);
    expect(state.stages.training).toBe('BLOCKED');
    expect(state.stages.comparison).toBe('BLOCKED');
    expect(state.stages.robustness).toBe('BLOCKED');
    expect(state.stages.explainability).toBe('BLOCKED');
    expect(state.stages.prediction).toBe('BLOCKED');
    expect(state.stages.report).toBe('BLOCKED');
  });

  it('uses the latest experiment for the active dataset instead of an older success',()=>{
    const older=experiment('experiment-old','dataset-a','succeeded','2026-09-28T00:00:00Z');
    const latest=experiment('experiment-new','dataset-a','running','2026-09-29T00:00:00Z');
    const olderModel=model('model-old',older.id,'dataset-a');
    const state=deriveDemoState('dataset-a',[older,latest],[olderModel],[job(latest.id)],true);
    expect(state.currentExperiment?.id).toBe(latest.id);
    expect(state.readyModels).toHaveLength(0);
    expect(state.stages.training).toBe('IN PROGRESS');
    expect(state.stages.explainability).toBe('BLOCKED');
  });

  it('recognizes only models from the current completed experiment',()=>{
    const current=experiment('experiment-a','dataset-a');
    const first=model('model-a1',current.id,'dataset-a');
    const second=model('model-a2',current.id,'dataset-a','ready','svm');
    const state=deriveDemoState('dataset-a',[current],[first,second],[],true);
    expect(state.stages.training).toBe('COMPLETED');
    expect(state.stages.comparison).toBe('READY');
    expect(state.stages.robustness).toBe('READY');
    expect(state.stages.explainability).toBe('READY');
    expect(state.stages.prediction).toBe('READY');
    expect(state.stages.report).toBe('READY');
  });

  it('drops stale experiment and model relationships when the dataset changes',()=>{
    const oldExperiment=experiment('experiment-a','dataset-a');
    const oldModel=model('model-a',oldExperiment.id,'dataset-a');
    const state=deriveDemoState('dataset-b',[oldExperiment],[oldModel],[],true);
    expect(state.currentExperiment).toBeNull();
    expect(state.readyModels).toHaveLength(0);
    expect(state.stages.training).toBe('READY');
    expect(state.stages.explainability).toBe('BLOCKED');
  });
});