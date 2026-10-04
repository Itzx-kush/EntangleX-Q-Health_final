import {fireEvent,render,screen} from '@testing-library/react';
import {describe,expect,it} from 'vitest';
import {DiagnosticEvidence} from '../components/DiagnosticEvidence';
import type {Experiment,MetricName,ModelRecord} from '../types/qhealth';

const metricNames:MetricName[]=['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'];
const completeMetrics={accuracy:.8,precision:.75,recall:.9,sensitivity:.9,specificity:.7,f1:.82,roc_auc:.91,true_positive:9,true_negative:7,false_positive:3,false_negative:1,confusion_matrix:[[7,3],[1,9]],sample_count:20,roc_curve:{fpr:[0,.2,1],tpr:[0,.9,1],thresholds:[null,.5,0]},undefined_metrics:[]};
const summary=Object.fromEntries(metricNames.map(name=>[name,{mean:name==='roc_auc'?.88:.78,std:.02,valid_folds:2}])) as Record<MetricName,{mean:number;std:number;valid_folds:number}>;
const fold=(roc_auc:number)=>({...completeMetrics,roc_auc});
const models=[
 {id:'model-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'random_forest',status:'ready',created_at:'2026-01-01',details:{},metrics:{test:completeMetrics,validation:{folds:[fold(.86),fold(.9)],summary,std_definition:'sample standard deviation across folds; not a confidence interval'},timing:{final_training_seconds:1.2,cv_total_seconds:2.4,cv_fold_seconds:[1.1,1.3],test_inference_seconds:.02,test_inference_seconds_per_sample:.001},calibration:{method:'none',brier_score:.18,reliability_curve:{mean_probability:[.2,.8],observed_positive_fraction:[.1,.9]},clinical_calibration:false,interpretation:'Research diagnostics only.'},operating_point:{selection_strategy:'target_sensitivity',target_sensitivity:.9,target_specificity:null,selected_threshold:.42,threshold_units:'probability',threshold_feasible:true,threshold_source:'out-of-fold validation',validation_metrics:{threshold:.42,sensitivity:.9,specificity:.7,precision:.75,recall:.9,f1:.82,accuracy:.8,roc_auc:.88},holdout_metrics:{sensitivity:.9,specificity:.7,roc_auc:.91},number_of_oof_samples:40,cv_fold_count:2,curve:[{threshold:.3,sensitivity:.95,specificity:.6,precision:.7,recall:.95,f1:.8,accuracy:.76,roc_auc:.88},{threshold:.42,sensitivity:.9,specificity:.7,precision:.75,recall:.9,f1:.82,accuracy:.8,roc_auc:.88}],interpretation:'Persisted validation operating point.'}}},
 {id:'model-2',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'svm',status:'ready',created_at:'2026-01-01',details:{},metrics:{}}
] as unknown as ModelRecord[];
const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'succeeded',created_at:'2026-01-01',summary:{},config:{calibration:'none',cv_folds:2}} as unknown as Experiment;

describe('DiagnosticEvidence',()=>{
 it('presents persisted confusion, CV, threshold, calibration, and runtime evidence',()=>{
  render(<DiagnosticEvidence experiment={experiment} models={models} mode="live"/>);
  expect(screen.getByText('Diagnostic Evidence')).toBeInTheDocument();
  expect(screen.getByText('FALSE POSITIVE')).toBeInTheDocument();
  expect(screen.getByText('3')).toBeInTheDocument();
  expect(screen.getAllByText('Not performed').length).toBeGreaterThan(0);
  expect(screen.getByText(/out-of-fold validation evidence/i)).toBeInTheDocument();
  expect(screen.getByText(/false positives and 1 false negatives/i)).toBeInTheDocument();
 });

 it('switches locally to a partial legacy model without fabricating evidence',()=>{
  render(<DiagnosticEvidence experiment={experiment} models={models} mode="verified"/>);
  fireEvent.change(screen.getByLabelText('Model diagnostic selector'),{target:{value:'model-2'}});
  expect(screen.getByText(/No confusion-matrix values are reconstructed/i)).toBeInTheDocument();
  expect(screen.getByText(/Cross-validation evidence is not available/i)).toBeInTheDocument();
  expect(screen.getAllByText(/Operating-point evidence was not evaluated/i).length).toBeGreaterThan(0);
  expect(screen.getAllByText('NOT AVAILABLE').length).toBeGreaterThan(0);
 });
});
