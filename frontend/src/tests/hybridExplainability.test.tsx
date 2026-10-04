import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import type {ReactNode} from 'react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {DraftProvider} from '../hooks/useDraft';
import {Explainability,PredictionPage} from '../pages/ResearchPagesModels';
import {qh} from '../lib/api';

const hybrid={id:'hybrid-model-1234',experiment_id:'experiment-1',dataset_id:'dataset-1',model_type:'hybrid_pennylane_torch',status:'ready',details:{},metrics:{},created_at:'2026-09-30T00:00:00Z'};
const experiment={id:'experiment-1',dataset_id:'dataset-1',parent_id:null,status:'succeeded',config:{models:['hybrid_pennylane_torch']},summary:{},created_at:'2026-09-30T00:00:00Z'};
const globalExplanation={id:'explanation-1',model_id:hybrid.id,method:'shap',created_at:'2026-09-30T00:00:00Z',result:{title:'Global Hybrid SHAP',scope:'Bounded held-out cases',sample_count:2,units:'Mean absolute SHAP contribution across explained cases to the final positive-class probability.',influence:[{feature:'age',magnitude:.08,signed_mean:.04,direction:'toward_positive'}],elapsed_seconds:.1,limitations:['SHAP does not establish biological causation.'],method_display:'SHAP — Final Hybrid Output',model_type:'hybrid_pennylane_torch',model_display_name:'PennyLane + PyTorch Hybrid',output_semantics:'final positive-class probability',explanation_level:'global_dataset',background_sample_count:20,explained_case_count:2}};
const localExplanation={method:'shap',method_display:'SHAP — Final Hybrid Output',scope:'local_case',model_type:'hybrid_pennylane_torch',model_display_name:'PennyLane + PyTorch Hybrid',output_semantics:'final positive-class probability',prediction_context:{probability_positive:.73,operating_threshold:.48,threshold_source:'out_of_fold_validation',predicted_class:'positive',positive_label:'positive',negative_label:'negative',research_risk_category:'HIGH',base_value:.52},contributions:[{feature:'polyuria',original_value:'Yes',contribution:.12,signed_mean:.12,magnitude:.12,absolute_contribution:.12,direction:'toward_positive',interpretation:"Increased the model's final positive-class probability."},{feature:'age',original_value:52,contribution:-.05,signed_mean:-.05,magnitude:.05,absolute_contribution:.05,direction:'toward_negative',interpretation:"Decreased the model's final positive-class probability."}],background_source:'training partition only',background_sample_count:20,explained_case_count:1,limitations:["SHAP describes how input features influenced this model's final prediction; it does not establish biological or clinical causation."]};

vi.mock('../lib/api',()=>({qh:{
 models:vi.fn(()=>Promise.resolve([hybrid])),experiments:vi.fn(()=>Promise.resolve([experiment])),dataset:vi.fn(()=>Promise.resolve({id:'dataset-1',name:'Research dataset',sha256:'hash-1',provenance:{row_count:20,feature_count:2},quality:{},created_at:'2026-09-30T00:00:00Z'})),
 explanations:vi.fn(()=>Promise.resolve([globalExplanation])),explain:vi.fn(()=>Promise.resolve(globalExplanation)),
 schema:vi.fn(()=>Promise.resolve({model_id:hybrid.id,features:[{name:'age',type:'number',nullable:true},{name:'polyuria',type:'string',nullable:true}],positive_label:'positive',negative_label:'negative'})),
 sample:vi.fn(()=>Promise.resolve({features:{age:52,polyuria:'Yes'},sample:'Public benchmark sample',source:'UCI'})),
 predict:vi.fn(()=>Promise.resolve({model_id:hybrid.id,model_type:'hybrid_pennylane_torch',positive_label:'positive',negative_label:'negative',probability_status:'uncalibrated model probability',decision_rule:'Positive model probability >= 0.48',operating_threshold:.48,threshold_source:'out_of_fold_validation',risk_thresholds:[.33,.66],predictions:[{sample:'Sample #1',predicted_class:'positive',probability_positive:.73,decision_score:null,research_risk_category:'HIGH'}],influence:localExplanation.contributions,explanation:localExplanation,limitations:localExplanation.limitations,disclaimer:'Research only'})),
}}));

function renderPage(page:ReactNode){localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:'dataset-1'}));return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}><MemoryRouter><DraftProvider>{page}</DraftProvider></MemoryRouter></QueryClientProvider>)}

describe('hybrid SHAP presentation',()=>{
 beforeEach(()=>{localStorage.clear();vi.clearAllMocks()});
 it('shows SHAP as the actual hybrid method and labels global importance accurately',async()=>{
  renderPage(<Explainability/>);
  const modelSelect=await screen.findByLabelText('Registered model');
  await within(modelSelect).findByRole('option',{name:/PennyLane \+ PyTorch Hybrid/i});
  fireEvent.change(modelSelect,{target:{value:hybrid.id}});
  await waitFor(()=>expect(screen.getByLabelText('Explanation method')).toHaveValue('shap'));
  const method=screen.getByLabelText('Explanation method');
  expect(within(method).getByRole('option',{name:'SHAP — Final Hybrid Output'})).toBeInTheDocument();
  expect(screen.getByText(/Explains contribution to the final PennyLane \+ PyTorch positive-class probability/i)).toBeInTheDocument();
  expect(await screen.findByText('GLOBAL / DATASET-LEVEL')).toBeInTheDocument();
  expect(screen.getAllByText(/Mean absolute SHAP contribution across explained cases/i).length).toBeGreaterThan(0);
  expect(method).not.toHaveValue('permutation');
 });
 it('answers why the exact case was flagged with probability, threshold, directions, values, and limitation',async()=>{
  renderPage(<PredictionPage/>);
  fireEvent.change(await screen.findByLabelText('Registered model'),{target:{value:hybrid.id}});
  await screen.findByText('age');
  fireEvent.change(screen.getByLabelText('age'),{target:{value:'52'}});
  fireEvent.change(screen.getByLabelText('polyuria'),{target:{value:'Yes'}});
  fireEvent.click(screen.getByRole('button',{name:'Generate research prediction'}));
  expect(await screen.findByText(/Research use only — not a clinical diagnosis/i)).toBeInTheDocument();
  expect(screen.getByText('Research model output')).toBeInTheDocument();
  expect(screen.getAllByText('Positive-class model probability').length).toBeGreaterThan(0);
  expect(screen.getByText('Decision score')).toBeInTheDocument();
  expect(screen.getByText('Research risk category')).toBeInTheDocument();
  expect(screen.getByRole('heading',{name:'Post-hoc model explanation',level:3})).toBeInTheDocument();
  expect(screen.getByText('SHAP — Final Hybrid Output')).toBeInTheDocument();
    expect(screen.getAllByText('73.0%').length).toBeGreaterThan(0);
  expect(screen.getByText('0.4800')).toBeInTheDocument();
  expect(screen.getByText('Pushed toward positive class')).toBeInTheDocument();
  expect(screen.getByText('Pushed toward negative class')).toBeInTheDocument();
  expect(screen.getByText('Original value: Yes')).toBeInTheDocument();
  expect(screen.getByText('+0.1200')).toBeInTheDocument();
  expect(screen.getByText('-0.0500')).toBeInTheDocument();
  expect(screen.getAllByText(/does not establish biological or clinical causation/i).length).toBeGreaterThan(0);
 });
 it('keeps decision scores distinct when model probability is unavailable',async()=>{
  vi.mocked(qh.predict).mockResolvedValueOnce({model_id:hybrid.id,model_type:'hybrid_pennylane_torch',positive_label:'positive',negative_label:'negative',probability_status:'Decision score only; no model probability or risk category is available.',decision_rule:'Positive decision score >= 0',operating_threshold:0,threshold_source:'estimator_default',risk_thresholds:[.33,.66],predictions:[{sample:'Sample #1',predicted_class:'positive',probability_positive:null,decision_score:1.2345,research_risk_category:null}],influence:null,explanation:null,limitations:[],disclaimer:'Research only'});
  renderPage(<PredictionPage/>);
  fireEvent.change(await screen.findByLabelText('Registered model'),{target:{value:hybrid.id}});
  await screen.findByText('age');
  fireEvent.change(screen.getByLabelText('age'),{target:{value:'52'}});
  fireEvent.click(screen.getByRole('button',{name:'Generate research prediction'}));
  expect(await screen.findByText('Not available for this estimator')).toBeInTheDocument();
  expect(screen.getByText('1.2345')).toBeInTheDocument();
  expect(screen.getByText('Not assigned')).toBeInTheDocument();
  expect(screen.queryByText('123.5%')).not.toBeInTheDocument();
 });
});
