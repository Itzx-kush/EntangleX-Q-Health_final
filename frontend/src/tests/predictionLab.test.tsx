import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {ResearchPredictionLab,type CrossModelPrediction} from '../components/ResearchPredictionLab';
import type {Dataset,Experiment,ModelRecord,Prediction,VerifiedPredictionCase} from '../types/qhealth';

const classical={id:'model-classical',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'random_forest',status:'ready',details:{},metrics:{test:{roc_auc:.91}},created_at:'2026-10-01T00:00:00Z'} as ModelRecord;
const quantum={id:'model-quantum',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'qsvc',status:'ready',details:{quantum:{execution_kind:'local_simulation'}},metrics:{test:{roc_auc:.86}},created_at:'2026-10-01T00:00:00Z'} as ModelRecord;
const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'succeeded',config:{models:['random_forest','qsvc'],threshold_strategy:'fixed'},summary:{},created_at:'2026-10-01T00:00:00Z'} as Experiment;
const dataset={id:'dataset-1',name:'Research dataset',sha256:'sha-1',provenance:{row_count:40,feature_count:2},quality:{},created_at:'2026-10-01T00:00:00Z'} as Dataset;
const prediction=(model:ModelRecord,predicted_class:string,probability:number):Prediction=>({model_id:model.id,model_type:model.model_type,positive_label:'positive',negative_label:'negative',probability_status:'uncalibrated model probability',decision_rule:'Positive probability >= 0.5',operating_threshold:.5,threshold_source:'configured_research_threshold',risk_thresholds:[.33,.66],predictions:[{sample:'Sample #1',predicted_class,probability_positive:probability,decision_score:null,research_risk_category:'MODERATE'}],influence:null,explanation:null,limitations:[],disclaimer:'Research only'});

function renderLab(node:React.ReactNode){return render(<MemoryRouter>{node}</MemoryRouter>)}

describe('ResearchPredictionLab',()=>{
 it('presents a verified representative case without implying a live request',()=>{
  const verifiedCase={case_id:'CASE-001',case_label:'flagged',model_id:classical.id,model_type:classical.model_type,row_index:1,input:{age:52,polyuria:'Yes'},probability_positive:.73,threshold:.5,threshold_source:'verified_package',predicted_class:'positive'} as VerifiedPredictionCase;
  renderLab(<ResearchPredictionLab mode="verified" model={classical} models={[classical]} experiment={experiment} dataset={dataset} verifiedCases={[verifiedCase]}/>);
  expect(screen.getByText('Verified / precomputed')).toBeInTheDocument();
  expect(screen.getByText(/Research use only — not a clinical diagnosis/i)).toBeInTheDocument();
  expect(screen.getAllByText('CASE-001').length).toBeGreaterThan(0);
  expect(screen.getByText('age')).toBeInTheDocument();
  expect(screen.getAllByText('73.0%').length).toBeGreaterThan(0);
  expect(screen.getByText(/Cross-model comparison is not fabricated/i)).toBeInTheDocument();
 });

 it('reports same-input model disagreement from returned outputs only',()=>{
  const crossResults:CrossModelPrediction[]=[{model:classical,prediction:prediction(classical,'positive',.73)},{model:quantum,prediction:prediction(quantum,'negative',.42)}];
  renderLab(<ResearchPredictionLab mode="live" model={classical} models={[classical,quantum]} experiment={experiment} dataset={dataset} input={{age:52,polyuria:'Yes'}} prediction={prediction(classical,'positive',.73)} crossResults={crossResults} sameInputVerified/>);
  expect(screen.getByText('SAME INPUT VERIFIED')).toBeInTheDocument();
  expect(screen.getByText(/Model disagreement detected/i)).toBeInTheDocument();
  expect(screen.getAllByText('1 / 2 models',{exact:true})).toHaveLength(2);
  expect(screen.getByText('CLASSICAL')).toBeInTheDocument();
  expect(screen.getByText('QUANTUM')).toBeInTheDocument();
  expect(screen.getByText(/agreement is not truth or clinical evidence/i)).toBeInTheDocument();
 });
});
