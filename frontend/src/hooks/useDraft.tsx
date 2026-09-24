import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import type {PipelineConfig,QuantumConfig,TrainingConfig} from '../types/qhealth';

export const defaultDraft:TrainingConfig={
  dataset_id:'',features:null,models:['logistic_regression','svm','random_forest'],
  pipeline:{imputer:'median',scaler:'standard',outlier_strategy:'none',lower_quantile:.01,upper_quantile:.99,log_features:[],ratios:[],selection:'anova',k_features:12,variance_threshold:0,pca_components:4,pca_whiten:false,angle_scaling:true},
  quantum:{backend:'statevector',qubits:4,feature_map_reps:1,ansatz_reps:1,entanglement:'linear',optimizer:'COBYLA',maxiter:30,shots:1024,noise_probability:0},
  parameters:{logistic_c:1,svm_c:1,svm_kernel:'rbf',forest_trees:100,forest_max_depth:null,class_weight:null},
  seed:42,test_size:.2,cv_folds:3,max_samples:160,duplicate_policy:'reject',probability_threshold:.5,calibration:'none',calibration_folds:3
};
type Ctx={draft:TrainingConfig;update:(patch:Partial<TrainingConfig>)=>void;pipeline:(patch:Partial<PipelineConfig>)=>void;quantum:(patch:Partial<QuantumConfig>)=>void;reset:()=>void};
const DraftContext=createContext<Ctx|null>(null);
export function DraftProvider({children}:{children:ReactNode}){
  const [draft,setDraft]=useState<TrainingConfig>(()=>{try{const raw=localStorage.getItem('qhealth-tictac-draft');if(raw){const v=JSON.parse(raw) as Partial<TrainingConfig>;return {...defaultDraft,...v,pipeline:{...defaultDraft.pipeline,...v.pipeline},quantum:{...defaultDraft.quantum,...v.quantum},parameters:{...defaultDraft.parameters,...v.parameters}}}}catch{}return defaultDraft});
  useEffect(()=>{try{localStorage.setItem('qhealth-tictac-draft',JSON.stringify(draft))}catch{}},[draft]);
  return <DraftContext.Provider value={{draft,update:p=>setDraft(v=>({...v,...p})),pipeline:p=>setDraft(v=>({...v,pipeline:{...v.pipeline,...p}})),quantum:p=>setDraft(v=>({...v,quantum:{...v.quantum,...p}})),reset:()=>setDraft(defaultDraft)}}>{children}</DraftContext.Provider>;
}
export function useDraft(){const v=useContext(DraftContext);if(!v)throw new Error('DraftProvider missing');return v;}
