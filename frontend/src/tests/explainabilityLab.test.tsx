import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {ExplainabilityResearchLab} from '../components/ExplainabilityResearchLab';
import type {Dataset,Experiment,ModelRecord,VerifiedEvidencePackage} from '../types/qhealth';

const model={id:'hybrid-1',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'hybrid_pennylane_torch',status:'ready',created_at:'2026-01-01T00:00:00Z',details:{quantum:{framework:'PennyLane',classical_framework:'PyTorch',execution_kind:'local simulation',real_hardware:false}},metrics:{}} as ModelRecord;
const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'succeeded',config:{},summary:{},created_at:'2026-01-01T00:00:00Z'} as unknown as Experiment;
const dataset={id:'dataset-1',name:'Verified research dataset',sha256:'dataset-hash',provenance:{row_count:20,feature_count:2},quality:{},created_at:'2026-01-01T00:00:00Z'} as unknown as Dataset;
const verified={method:'SHAP permutation explainer',model_id:model.id,model_ids:[model.id],output_path:'research output',global_summary:[{feature:'polyuria',mean_absolute_shap:.18,mean_signed_shap:.12},{feature:'age',mean_absolute_shap:.08,mean_signed_shap:-.04}],local:{case_id:'heldout-row-1',method:'shap',method_display:'SHAP — Final Hybrid Output',scope:'local_case',model_type:'hybrid_pennylane_torch',model_display_name:'PennyLane + PyTorch Hybrid',output_semantics:'final positive-class probability',prediction_context:{probability_positive:.73,operating_threshold:.48,threshold_source:'out_of_fold_validation',predicted_class:'positive',positive_label:'positive',negative_label:'negative',research_risk_category:'research_flagged',base_value:.52},contributions:[{feature:'polyuria',original_value:'Yes',contribution:.12,magnitude:.12,direction:'toward_positive',interpretation:'Increased the model output.'},{feature:'age',original_value:52,contribution:-.05,magnitude:.05,direction:'toward_negative',interpretation:'Decreased the model output.'}],background_source:'training partition only',background_sample_count:20,explained_case_count:1,limitations:['Post-hoc model behavior; not causation.']}} as unknown as VerifiedEvidencePackage['evidence']['explainability'];

describe('ExplainabilityResearchLab',()=>{
 it('separates verified global and local evidence with input values and signed contributions',()=>{
  render(<MemoryRouter><ExplainabilityResearchLab model={model} models={[model]} experiment={experiment} dataset={dataset} verified={verified} mode="verified"/></MemoryRouter>);
  expect(screen.getByText('Explainability overview')).toBeInTheDocument();
  expect(screen.getByText('Global feature influence')).toBeInTheDocument();
  expect(screen.getAllByText('GLOBAL / DATASET-LEVEL').length).toBeGreaterThan(0);
  expect(screen.getAllByText('LOCAL / CASE-LEVEL').length).toBeGreaterThan(0);
  expect(screen.getByText('Explained input profile')).toBeInTheDocument();
  expect(screen.getAllByText('Yes').length).toBeGreaterThan(0);
  expect(screen.getByText('+0.1200')).toBeInTheDocument();
  expect(screen.getByText('-0.0500')).toBeInTheDocument();
  expect(screen.getByText(/polyuria had the largest persisted global/i)).toBeInTheDocument();
  expect(screen.getAllByText(/does not establish medical causation/i).length).toBeGreaterThan(0);
 });

 it('shows truthful missing states instead of another model explanation',()=>{
  render(<MemoryRouter><ExplainabilityResearchLab model={model} models={[model]} experiment={experiment} dataset={dataset} records={[]} mode="live" onModelChange={()=>undefined}/></MemoryRouter>);
  expect(screen.getByText(/Global explainability evidence is not available for this model/i)).toBeInTheDocument();
  expect(screen.getByText(/Local explanation evidence is not recorded for this model/i)).toBeInTheDocument();
  expect(screen.getAllByText('NOT AVAILABLE').length).toBeGreaterThan(0);
  expect(screen.queryByText('+0.1200')).not.toBeInTheDocument();
 });
});
