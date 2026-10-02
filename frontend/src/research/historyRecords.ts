import type {Circuit,Explanation,Experiment,ModelRecord,Prediction,QuantumConfig} from '../types/qhealth';
import {modelLabels} from '../utils/format';
import type {NewResearchActivity} from './historyTypes';

export function experimentActivity(experiment:Experiment):NewResearchActivity{
  return {
    activityType:'experiment',
    title:'Training experiment created',
    status:experiment.status,
    occurredAt:experiment.created_at,
    route:`/experiments/${encodeURIComponent(experiment.id)}`,
    referenceId:experiment.id,
    experimentId:experiment.id,
    datasetId:experiment.dataset_id,
    metadata:{
      models:experiment.config.models,
      seed:experiment.config.seed,
      parent_id:experiment.parent_id,
    },
    idempotencyKey:`experiment:${experiment.id}`,
  };
}

export function predictionActivity(prediction:Prediction,model:ModelRecord):NewResearchActivity{
  const first=prediction.predictions[0];
  return {
    activityType:'prediction',
    title:`Research prediction · ${modelLabels[model.model_type]}`,
    status:'completed',
    route:'/prediction',
    experimentId:model.experiment_id,
    modelId:model.id,
    datasetId:model.dataset_id,
    metadata:{
      model_type:model.model_type,
      probability_status:prediction.probability_status,
      predicted_class:first?.predicted_class||null,
      research_risk_category:first?.research_risk_category||null,
      sample_count:prediction.predictions.length,
      local_explanation:Boolean(prediction.explanation||prediction.influence),
    },
  };
}

export function explanationActivity(explanation:Explanation,model:ModelRecord):NewResearchActivity{
  return {
    activityType:'explanation',
    title:explanation.result.title||`Explanation · ${modelLabels[model.model_type]}`,
    status:'available',
    occurredAt:explanation.created_at,
    route:'/explainability',
    referenceId:explanation.id,
    experimentId:model.experiment_id,
    modelId:model.id,
    datasetId:model.dataset_id,
    method:explanation.method,
    metadata:{
      model_type:model.model_type,
      scope:explanation.result.scope,
      sample_count:explanation.result.sample_count,
      explanation_level:explanation.result.explanation_level||null,
    },
    idempotencyKey:`explanation:${explanation.id}`,
  };
}

export function quantumActivity({circuit,configuration,datasetId,model}:{circuit:Circuit;configuration?:QuantumConfig;datasetId:string|null;model?:ModelRecord}):NewResearchActivity{
  return {
    activityType:'quantum',
    title:model?`Fitted circuit · ${modelLabels[model.model_type]}`:`${circuit.model_type.toUpperCase()} circuit generated`,
    status:circuit.execution_kind||'configured',
    route:'/quantum',
    referenceId:model?.id||null,
    experimentId:model?.experiment_id||null,
    modelId:model?.id||null,
    datasetId:model?.dataset_id||datasetId,
    metadata:{
      model_type:circuit.model_type,
      backend:circuit.backend,
      execution_kind:circuit.execution_kind,
      qubits:circuit.qubits,
      logical_depth:circuit.logical_depth,
      parameter_count:circuit.parameter_count,
      ...(configuration?{
        optimizer:configuration.optimizer,
        shots:configuration.shots,
        feature_map_reps:configuration.feature_map_reps,
        ansatz_reps:configuration.ansatz_reps,
        entanglement:configuration.entanglement,
      }:{})
    },
  };
}
