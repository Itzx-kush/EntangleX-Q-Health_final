import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {DraftProvider} from '../hooks/useDraft';
import {Datasets} from '../pages/ResearchPagesCore';
import {qh} from '../lib/api';

const dataset={id:'dataset-1',name:'Pima Indians Diabetes',sha256:'a'.repeat(64),created_at:'2026-01-01T00:00:00Z',provenance:{name:'Pima Indians Diabetes',domain:'endocrinology',source:'UCI',source_url:'https://example.invalid',version:'1',target:'outcome',positive_label:'1',negative_label:'0',features:['glucose','outcome'],numeric_features:['glucose'],categorical_features:[],row_count:768,feature_count:1,class_distribution:{'1':268,'0':500},target_classes:['0','1'],is_demo:true,dataset_hash:'a'.repeat(64),license:'CC BY 4.0'},quality:{blockers:[],warnings:[],missing_values:{glucose:0},infinite_values:{glucose:0},duplicate_rows:0,duplicate_feature_rows:0,suspiciously_predictive_features:[],identifier_features:[],highly_correlated_pairs:[],distributions:[],scope:'',row_count:768,feature_count:1,class_distribution:{'1':268,'0':500},minority_fraction:.35,class_imbalance:false,constant_features:[],low_variance_features:[],invalid_numeric_values:''}} as any;
const library=[{slug:'pima-diabetes',name:'Pima Indians Diabetes',domain:'endocrinology',description:'benchmark',source:'UCI',source_url:'https://example.invalid',version:'1',license:'CC BY 4.0',task:'binary_classification',target:'outcome',positive_label:'1',negative_label:'0',rows:768,features:8,numeric_feature_count:8,categorical_feature_count:0,filename:'pima.csv',is_demo:true,dataset_hash:'a'.repeat(64),hash_algorithm:'sha256',hash_scope:'exact'}];
const suggestedMetadata={name:'Fixture Dataset',name_source:'filename',target:'target',target_confidence:.95,target_source:'inspection.target_candidates[0]',target_classes_source:'inspection.target_candidates[0].class_distribution',target_classes:['positive','negative'],target_class_distribution:{positive:12,negative:12},positive_label:'positive',positive_label_confidence:.95,positive_label_source:'semantic_label_rule',negative_label:'negative',negative_label_source:'remaining_binary_class',version:'upload-snapshot-test',version_source:'generated_snapshot',domain:'biomedical',domain_source:'fallback_biomedical',source:'User-provided',source_source:'default_user_upload'};
const initialInspection={suggested_metadata:suggestedMetadata,metadata_warnings:[],row_count:24,column_count:3,column_names:['glucose','group','target'],numeric_columns:['glucose'],categorical_columns:['group','target'],boolean_columns:[],datetime_like_columns:[],unsupported_columns:[],missing_values:{glucose:0,group:0,target:0},infinite_values:{glucose:0},duplicate_rows:0,duplicate_feature_rows:0,constant_features:[],low_variance_features:[],high_cardinality_categorical_features:[],identifier_like_columns:[],empty_columns:[],possible_target_columns:['target'],target_candidates:[{column:'target',confidence:.95,reasons:['target-like column'],class_count:2,class_distribution:{positive:12,negative:12}}],target:null,target_classes:[],class_distribution:{},schema_consistent:true,suspicious_target_proxy_columns:[],transformations_applied:[],compatibility:{status:'BLOCKED',checks:[{code:'target_selection',status:'BLOCKED',message:'Select a target column.'}],blockers:['Select a target column.'],warnings:[]},file_format:'csv',filename:'fixture.csv',file_size_bytes:100};
const readyInspection={...initialInspection,target:'target',target_classes:['negative','positive'],class_distribution:{positive:12,negative:12},compatibility:{status:'READY',checks:[{code:'binary_target',status:'PASS',message:'Target contains exactly two observed classes.'}],blockers:[],warnings:[]}};

vi.mock('../lib/api',()=>({
  api:{remove:vi.fn(()=>Promise.resolve(undefined))},
  qh:{
    datasets:vi.fn(()=>Promise.resolve([])),datasetLibrary:vi.fn(()=>Promise.resolve(library)),useLibraryDataset:vi.fn(()=>Promise.resolve(dataset)),
    inspect:vi.fn((form:FormData)=>{
     const requestedTarget=form.get('target');
     if(requestedTarget==='target')return Promise.resolve(readyInspection);
     if(requestedTarget)return Promise.resolve({...initialInspection,target:String(requestedTarget),compatibility:{status:'BLOCKED',checks:[{code:'positive_label',status:'BLOCKED',message:'Select a positive class.'}],blockers:['Select a positive class.'],warnings:[]}});
     return Promise.resolve(initialInspection);
    }),
    register:vi.fn(()=>Promise.resolve(dataset)),
  },
}));

function renderLab(){
 const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
 return render(<QueryClientProvider client={client}><MemoryRouter><DraftProvider><Datasets/></DraftProvider></MemoryRouter></QueryClientProvider>);
}

beforeEach(()=>vi.clearAllMocks());

describe('Dataset Lab library and inspector',()=>{
 it('renders the curated library and selects a built-in dataset',async()=>{
  renderLab();
  expect(await screen.findByText('Pima Indians Diabetes')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Use dataset'}));
  await waitFor(()=>expect(qh.useLibraryDataset).toHaveBeenCalledWith('pima-diabetes',expect.anything()));
 });

 it('synchronizes an auto-detected target with compatibility',async()=>{
  renderLab();
  const file=new File(['glucose,group,target\n1,A,positive\n'], 'fixture.csv', {type:'text/csv'});
  fireEvent.change(document.querySelector('input[type="file"]')!,{target:{files:[file]}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect dataset'}));
  await screen.findByText('Potential target columns');
  expect(screen.getByText('AUTO-DETECTED DATASET PROFILE')).toBeInTheDocument();
  await waitFor(()=>expect(screen.getByText('READY')).toBeInTheDocument());
  expect(qh.inspect).toHaveBeenCalledTimes(2);
  const compatibilityRequest=vi.mocked(qh.inspect).mock.calls[1][0] as FormData;
  expect(compatibilityRequest.get('target')).toBe('target');
  expect(compatibilityRequest.get('positive_label')).toBe('positive');
 });

 it('recomputes compatibility when the target changes and clears it for a new file',async()=>{
  renderLab();
  const input=document.querySelector('input[type="file"]')!;
  const first=new File(['glucose,group,target\n1,A,positive\n'], 'first.csv', {type:'text/csv'});
  fireEvent.change(input,{target:{files:[first]}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect dataset'}));
  await waitFor(()=>expect(screen.getByText('READY')).toBeInTheDocument());

  fireEvent.change(screen.getByRole('combobox',{name:/Target column/i}),{target:{value:'group'}});
  await waitFor(()=>expect(screen.getByText('BLOCKED')).toBeInTheDocument());
  const targetChangeRequest=vi.mocked(qh.inspect).mock.calls.at(-1)?.[0] as FormData;
  expect(targetChangeRequest.get('target')).toBe('group');

  const second=new File(['glucose,group,target\n2,B,negative\n'], 'second.csv', {type:'text/csv'});
  fireEvent.change(input,{target:{files:[second]}});
  expect(screen.queryByText('AUTO-DETECTED DATASET PROFILE')).not.toBeInTheDocument();
  expect(screen.queryByText('BLOCKED')).not.toBeInTheDocument();
 });

 it('clears inspection state when the selected file is removed',async()=>{
  renderLab();
  const input=document.querySelector('input[type="file"]')!;
  const file=new File(['glucose,group,target\n1,A,positive\n'], 'fixture.csv', {type:'text/csv'});
  fireEvent.change(input,{target:{files:[file]}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect dataset'}));
  await waitFor(()=>expect(screen.getByText('AUTO-DETECTED DATASET PROFILE')).toBeInTheDocument());
  fireEvent.change(input,{target:{files:[]}});
  expect(screen.queryByText('AUTO-DETECTED DATASET PROFILE')).not.toBeInTheDocument();
  expect(screen.queryByText('READY')).not.toBeInTheDocument();
 });

 it('keeps user upload inspection usable when the benchmark library fails',async()=>{
  vi.mocked(qh.datasetLibrary).mockRejectedValueOnce(new Error('A curated benchmark asset is unavailable · 685c2397-7031-4ae4-bcc4-849201e2608e'));
  renderLab();
  expect(await screen.findByText(/A curated benchmark asset is unavailable/)).toBeInTheDocument();
  const file=new File(['glucose,group,target\n1,A,positive\n'], 'fixture.csv', {type:'text/csv'});
  fireEvent.change(document.querySelector('input[type="file"]')!,{target:{files:[file]}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect dataset'}));
  expect(await screen.findByText('AUTO-DETECTED DATASET PROFILE')).toBeInTheDocument();
 });

 it('rejects an incomplete inspection response without creating registration state',async()=>{
  vi.mocked(qh.inspect).mockResolvedValueOnce({} as any);
  renderLab();
  const file=new File(['glucose,target\n1,positive\n'], 'fixture.csv', {type:'text/csv'});
  fireEvent.change(document.querySelector('input[type="file"]')!,{target:{files:[file]}});
  fireEvent.click(screen.getByRole('button',{name:'Inspect dataset'}));
  expect(await screen.findByText(/Dataset inspection response is incomplete/)).toBeInTheDocument();
  expect(screen.queryByText('AUTO-DETECTED DATASET PROFILE')).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Register inspected dataset'})).toBeDisabled();
 });
});
