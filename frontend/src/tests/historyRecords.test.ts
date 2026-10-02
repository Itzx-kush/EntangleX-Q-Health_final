import {describe,expect,it} from 'vitest';
import {experimentActivity,explanationActivity,predictionActivity,quantumActivity} from '../research/historyRecords';
import type {Circuit,Experiment,Explanation,ModelRecord,Prediction,QuantumConfig} from '../types/qhealth';

const model={id:'model-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'qsvc',status:'ready',details:{},metrics:{},created_at:'2026-10-02T10:00:00Z'} satisfies ModelRecord;

describe('research history metadata boundaries',()=>{
  it('uses stable backend experiment identity for idempotency',()=>{
    const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'queued',config:{models:['qsvc'],seed:7} as Experiment['config'],summary:{},created_at:'2026-10-02T10:00:00Z'} satisfies Experiment;
    const activity=experimentActivity(experiment);
    expect(activity.idempotencyKey).toBe('experiment:experiment-1');
    expect(activity.occurredAt).toBe(experiment.created_at);
    expect(activity.route).toBe('/experiments/experiment-1');
  });

  it('stores prediction metadata without raw sample inputs or full result payloads',()=>{
    const prediction={model_id:'model-1',model_type:'qsvc',positive_label:'yes',negative_label:'no',probability_status:'available',decision_rule:'fixed',operating_threshold:.5,threshold_source:'configured',risk_thresholds:[.33,.66],predictions:[{sample:'sample-1',predicted_class:'yes',probability_positive:.72,decision_score:.4,research_risk_category:'elevated'}],influence:null,explanation:null,limitations:[],disclaimer:'research only'} satisfies Prediction;
    const activity=predictionActivity(prediction,model);
    expect(activity.metadata).toMatchObject({predicted_class:'yes',sample_count:1});
    expect(JSON.stringify(activity)).not.toContain('probability_positive');
    expect(JSON.stringify(activity)).not.toContain('sample-1');
  });

  it('uses stable explanation IDs and backend timestamps',()=>{
    const explanation={id:'explanation-1',model_id:'model-1',method:'perturbation',created_at:'2026-10-02T11:00:00Z',result:{title:'Measured influence',scope:'global',sample_count:8,units:'score',influence:[],elapsed_seconds:1,limitations:[]}} satisfies Explanation;
    const activity=explanationActivity(explanation,model);
    expect(activity.idempotencyKey).toBe('explanation:explanation-1');
    expect(activity.occurredAt).toBe(explanation.created_at);
  });

  it('records simulator terminology and bounded quantum configuration metadata',()=>{
    const circuit={model_type:'qsvc',execution_kind:'simulated',backend:'aer',qubits:4,logical_depth:12,parameter_count:8,gate_counts:{h:4},text:'omitted from history',gates:[],limitation:'research only'} satisfies Circuit;
    const configuration={backend:'aer',qubits:4,feature_map_reps:2,ansatz_reps:2,entanglement:'linear',optimizer:'COBYLA',maxiter:50,shots:1024,noise_probability:0} satisfies QuantumConfig;
    const activity=quantumActivity({circuit,configuration,datasetId:'dataset-1'});
    expect(activity.status).toBe('simulated');
    expect(activity.metadata).toMatchObject({backend:'aer',qubits:4,shots:1024});
    expect(JSON.stringify(activity)).not.toContain('omitted from history');
  });
});
