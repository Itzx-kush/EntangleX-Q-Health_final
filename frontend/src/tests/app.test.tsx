import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import App from '../App';
import {ResearchShell} from '../components/ResearchShell';
import {ThemeToggle} from '../components/ThemeToggle';
import {DraftProvider} from '../hooks/useDraft';
import {Datasets} from '../pages/ResearchPagesCore';
import {DemoCenter,SettingsPage} from '../pages/ResearchPagesSystem';
import {Comparison,PredictionPage,Quantum,Robustness,Training} from '../pages/ResearchPagesModels';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({
  setSessionToken:vi.fn(),
  api:{get:vi.fn(()=>Promise.resolve([])),post:vi.fn(()=>Promise.resolve({})),remove:vi.fn(()=>Promise.resolve(undefined))},
  qh:{
    alignment:vi.fn(()=>Promise.resolve({contract_version:'2026-09-30',models:[{model_id:'logistic_regression',display_name:'Logistic Regression',category:'classical',implementation_status:'AVAILABLE',executable:true},{model_id:'svm',display_name:'SVM',category:'classical',implementation_status:'AVAILABLE',executable:true},{model_id:'random_forest',display_name:'Random Forest',category:'classical',implementation_status:'AVAILABLE',executable:true},{model_id:'vqc',display_name:'VQC',category:'quantum',implementation_status:'AVAILABLE',executable:true},{model_id:'qsvc',display_name:'QSVC',category:'quantum',implementation_status:'AVAILABLE',executable:true},{model_id:'qnn',display_name:'QNN',category:'quantum',implementation_status:'AVAILABLE',executable:true},{model_id:'hybrid_pennylane_torch',display_name:'PennyLane + PyTorch Hybrid',category:'hybrid quantum-classical',implementation_status:'AVAILABLE',executable:true}],frameworks:{},showcase:{id:'early-stage-diabetes',display_name:'Early Stage Diabetes Risk Prediction',label:'Featured SIH demonstration',featured_dataset_slug:'early-stage-diabetes',disease_domain:'endocrinology',target:'diabetes_status',positive_class:'positive',dataset_hash:'hash',research_only_disclaimer:'Research benchmark only.',recommended_models:[]},flagship_experiment_preset:{id:'sih-diabetes-demonstration',display_name:'SIH Diabetes Demonstration',dataset_slug:'early-stage-diabetes',models:[],auto_start_training:false,threshold_strategy:'target_sensitivity',evidence_requirements:[]},flagship_architecture:{model_id:'hybrid_pennylane_torch',status:'IMPLEMENTED',stages:['Classical preprocessing','PennyLane quantum circuit','PyTorch classical output head','SHAP explanation']}})),
    health:vi.fn(()=>Promise.resolve({status:'ok',version:'test',mode:'local',authentication_required:false,quantum:{available:false,runtime_verified:false,execution:'local simulation'},disclaimer:'Research only'})),
    systemStatus:vi.fn(()=>Promise.resolve({status:'ok',version:'test',mode:'local',database_available:true,storage_available:true,quantum:{available:false,runtime_verified:false,execution:'local simulation'},model_capabilities:[],supported_models:{classical:[],quantum:[],qiskit_quantum:[],pennylane_hybrid:[]},jobs:{queued:0,running:0,active:0}})),
    summary:vi.fn(()=>Promise.resolve({counts:{datasets:0,experiments:0,ready_models:0,active_jobs:0},recent_experiments:[],disclaimer:'Research only'})),
    jobs:vi.fn(()=>Promise.resolve([])),
    models:vi.fn(()=>Promise.resolve([])),
    experiments:vi.fn(()=>Promise.resolve([])),
    datasets:vi.fn(()=>Promise.resolve([])),
    datasetLibrary:vi.fn(()=>Promise.resolve([])),
    registerBuiltIn:vi.fn(()=>Promise.resolve({})),
    dataset:vi.fn(()=>Promise.resolve({})),
    demo:vi.fn(()=>Promise.resolve({})),
    inspectDataset:vi.fn(()=>Promise.resolve({})),
    upload:vi.fn(()=>Promise.resolve({})),
    capabilities:vi.fn(()=>Promise.resolve({available:false,runtime_verified:false,execution:'Quantum runtime unavailable'})),
    resourcePolicy:vi.fn(()=>Promise.resolve({})),
    resourceAdvisor:vi.fn(()=>Promise.resolve({})),
    createJob:vi.fn(()=>Promise.resolve({})),
    comparison:vi.fn(()=>Promise.resolve({})),
    robustness:vi.fn(()=>Promise.resolve({experiment_id:'',dataset_id:'',sample_count:0,model_count:0,condition_count:0,results:[],limitations:[]})),
    robustnessHistory:vi.fn(()=>Promise.resolve([])),
    explanations:vi.fn(()=>Promise.resolve([])),
    explain:vi.fn(()=>Promise.resolve({})),
    schema:vi.fn(()=>Promise.resolve({model_id:'',features:[],positive_label:'positive',negative_label:'negative'})),
    sample:vi.fn(()=>Promise.resolve({features:{},sample:'Sample',source:'Public benchmark'})),
    predict:vi.fn(()=>Promise.resolve({})),
  },
}));

function renderWithProviders(ui:React.ReactNode,initialEntries=['/']){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}});
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={initialEntries}><DraftProvider>{ui}</DraftProvider></MemoryRouter></QueryClientProvider>);
}

beforeEach(()=>{
  localStorage.clear();
  vi.clearAllMocks();
  document.documentElement.className='';
  document.documentElement.removeAttribute('data-theme');
});

describe('medical dataset library',()=>{
  const libraryItem={
    slug:'wdbc',name:'Breast Cancer Wisconsin Diagnostic',domain:'oncology',description:'Diagnostic benchmark',
    source:'UCI Machine Learning Repository',source_url:'https://doi.org/10.24432/C5DW2B',version:'snapshot',
    license:'CC BY 4.0',license_url:'https://creativecommons.org/licenses/by/4.0/',attribution:'Wolberg et al.',
    target:'diagnosis',target_type:'binary_classification' as const,positive_label:'malignant',negative_label:'benign',
    row_count:569,feature_count:30,class_labels:['benign','malignant'],sha256:'a'.repeat(64),normalization:[],
    recommended_duplicate_policy:'reject' as const,origin:'built_in' as const,dataset_status:'available' as const,demo_readiness:{status:'ready' as const,instant_demo_available:true,artifact_version:'sih-verified-demo-v1',experiment_id:'experiment-a',model_ids:['model-a'],verified_dataset_hash:'a'.repeat(64),verified_artifact_manifest_hash:'b'.repeat(64)},
  };
  const inspection=(target='diagnosis')=>({
    filename:'medical.csv',sha256:'b'.repeat(64),row_count:20,column_count:3,columns:['age','diagnosis','outcome'],
    schema:[{name:'age',type:'number',missing_count:0,unique_count:20},{name:'diagnosis',type:'string',missing_count:0,unique_count:2},{name:'outcome',type:'string',missing_count:0,unique_count:2}],
    detected_target:target,target_type:'binary_classification',confidence_score:.95,confidence:'high' as const,
    selection_method:target==='diagnosis'?'automatic':'manual_override',class_labels:['benign','malignant'],
    class_distribution:{benign:10,malignant:10},positive_label:'malignant',positive_label_confidence:.95,
    positive_label_reason:'Semantic pair',requires_manual_target:false,requires_positive_label:false,
    heuristic_notice:'Scores are deterministic heuristic rankings, not calibrated probabilities.',candidates:[],
  });
  const libraryItems=[
    libraryItem,
    {...libraryItem,slug:'early-stage-diabetes',name:'Early Stage Diabetes Risk Prediction',domain:'endocrinology',target:'diabetes_status',positive_label:'positive',negative_label:'negative',row_count:520,feature_count:16,class_labels:['negative','positive'],recommended_duplicate_policy:'drop_exact' as const},
    {...libraryItem,demo_readiness:{status:'requires_processing' as const,instant_demo_available:false,artifact_version:null,experiment_id:null,model_ids:[],verified_dataset_hash:null,verified_artifact_manifest_hash:null},slug:'cleveland-heart-disease',name:'Heart Disease — Cleveland',domain:'cardiovascular',target:'heart_disease',positive_label:'present',negative_label:'absent',row_count:303,feature_count:13,class_labels:['absent','present']},
    {...libraryItem,demo_readiness:{status:'requires_processing' as const,instant_demo_available:false,artifact_version:null,experiment_id:null,model_ids:[],verified_dataset_hash:null,verified_artifact_manifest_hash:null},slug:'chronic-kidney-disease',name:'Chronic Kidney Disease',domain:'nephrology',target:'ckd_status',positive_label:'ckd',negative_label:'not_ckd',row_count:400,feature_count:24,class_labels:['ckd','not_ckd']},
    {...libraryItem,demo_readiness:{status:'requires_processing' as const,instant_demo_available:false,artifact_version:null,experiment_id:null,model_ids:[],verified_dataset_hash:null,verified_artifact_manifest_hash:null},slug:'ilpd-liver',name:'ILPD Liver Patient Dataset',domain:'hepatology',target:'liver_disease',positive_label:'present',negative_label:'absent',row_count:583,feature_count:10,class_labels:['absent','present'],recommended_duplicate_policy:'drop_exact' as const},
  ];
  const registeredDataset=(item:typeof libraryItem)=>({
    id:`dataset-${item.slug}`,name:item.name,sha256:item.sha256,created_at:new Date().toISOString(),
    provenance:{name:item.name,domain:item.domain,source:item.source,source_url:item.source_url,version:'snapshot',target:item.target,positive_label:item.positive_label,negative_label:item.negative_label,features:[],numeric_features:[],categorical_features:[],row_count:item.row_count,feature_count:item.feature_count,class_distribution:{},target_classes:item.class_labels,is_demo:false,dataset_hash:item.sha256,license:'CC BY 4.0',origin:'built_in' as const,recommended_duplicate_policy:item.recommended_duplicate_policy},
    quality:{} as never,
  });

  it('discovers and registers a built-in dataset without changing routes',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({pipeline:{log_features:['old_feature'],ratios:[{name:'old_ratio',numerator:'a',denominator:'b'}]}}));
    vi.mocked(qh.datasetLibrary).mockResolvedValue([libraryItem]);
    vi.mocked(qh.registerBuiltIn).mockResolvedValue(registeredDataset(libraryItem));
    renderWithProviders(<Datasets/>,['/datasets']);
    await waitFor(()=>expect(screen.getByText('Breast Cancer Wisconsin Diagnostic')).toBeInTheDocument());
    expect(screen.getByText('Medical Dataset Library')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Use Dataset'}));
    await waitFor(()=>expect(qh.registerBuiltIn).toHaveBeenCalledWith('wdbc'));
    await waitFor(()=>{
      const draft=JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}');
      expect(draft.dataset_id).toBe('dataset-wdbc');
      expect(draft.pipeline.log_features).toEqual([]);
      expect(draft.pipeline.ratios).toEqual([]);
    });
  });

  it('switches through all five datasets with isolated duplicate policy and feature state',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({models:['qsvc'],pipeline:{log_features:['old_feature'],ratios:[{name:'old_ratio',numerator:'a',denominator:'b'}]}}));
    vi.mocked(qh.datasetLibrary).mockResolvedValue(libraryItems);
    vi.mocked(qh.registerBuiltIn).mockImplementation(async slug=>registeredDataset(libraryItems.find(item=>item.slug===slug) as typeof libraryItem));
    renderWithProviders(<Datasets/>,['/datasets']);
    await screen.findByText(libraryItems[0].name);
    for(const item of libraryItems){
      const article=screen.getByText(item.name).closest('article');
      expect(article).not.toBeNull();
      fireEvent.click(within(article as HTMLElement).getByRole('button',{name:'Use Dataset'}));
      await waitFor(()=>{
        const draft=JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}');
        expect(draft.dataset_id).toBe(`dataset-${item.slug}`);
        expect(draft.duplicate_policy).toBe(item.recommended_duplicate_policy);
        expect(draft.pipeline.log_features).toEqual([]);
        expect(draft.pipeline.ratios).toEqual([]);
        expect(draft.models).toEqual(['qsvc']);
      });
    }
    expect(qh.registerBuiltIn).toHaveBeenCalledTimes(5);
  });

  it('clears an active deleted dataset instead of retaining a stale ID',async()=>{
    const dataset=registeredDataset(libraryItem);
    vi.mocked(qh.datasetLibrary).mockResolvedValue([]);
    vi.mocked(qh.datasets).mockResolvedValue([dataset]);
    vi.spyOn(window,'confirm').mockReturnValue(true);
    renderWithProviders(<Datasets/>,['/datasets']);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Select'})).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button',{name:'Select'}));
    await waitFor(()=>expect(JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}').dataset_id).toBe(dataset.id));
    fireEvent.click(screen.getByRole('button',{name:/Delete dataset/i}));
    await waitFor(()=>expect(JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}').dataset_id).toBe(''));
  });

  it('restores the active registered dataset from persisted state after remount',async()=>{
    const dataset=registeredDataset(libraryItem);
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:dataset.id}));
    vi.mocked(qh.datasetLibrary).mockResolvedValue([]);
    vi.mocked(qh.datasets).mockResolvedValue([dataset]);
    renderWithProviders(<Datasets/>,['/datasets']);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Selected'})).toBeInTheDocument());
  });

  it('inspects an upload and supports manual target override',async()=>{
    vi.mocked(qh.datasetLibrary).mockResolvedValue([]);
    vi.mocked(qh.inspectDataset).mockImplementation(async form=>inspection(String(form.get('target')||'diagnosis')));
    renderWithProviders(<Datasets/>,['/datasets']);
    const file=new File(['age,diagnosis,outcome\\n20,benign,no\\n21,malignant,yes\\n'],'medical.csv',{type:'text/csv'});
    fireEvent.change(screen.getByLabelText('CSV file'),{target:{files:[file]}});
    fireEvent.click(screen.getByRole('button',{name:/Detect Target/i}));
    await waitFor(()=>expect(screen.getByText('AUTOMATIC TARGET ANALYSIS')).toBeInTheDocument());
    expect(screen.getAllByText('diagnosis').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText(/Target column/),{target:{value:'outcome'}});
    await waitFor(()=>expect(vi.mocked(qh.inspectDataset).mock.calls.length).toBeGreaterThan(1));
    const latest=vi.mocked(qh.inspectDataset).mock.calls.at(-1)?.[0];
    expect(latest?.get('target')).toBe('outcome');
  });
});

describe('research shell navigation and commands',()=>{
  it('marks the active route and redirects unknown routes to overview',async()=>{
    const activeRoute=renderWithProviders(<ResearchShell><div>Shell content</div></ResearchShell>,['/datasets']);
    expect(activeRoute.getByRole('link',{name:/Datasets/i})).toHaveClass('active');
    activeRoute.unmount();

    const fallbackRoute=renderWithProviders(<App/>,['/not-a-real-route']);
    await waitFor(()=>expect(fallbackRoute.getByRole('heading',{name:/Overview/i})).toBeInTheDocument());
  });

  it('renders a discoverable header theme toggle and persists the chosen theme',async()=>{
    renderWithProviders(<ResearchShell><ThemeToggle/><div>Shell content</div></ResearchShell>);
    const toggle=await waitFor(()=>screen.getByRole('button',{name:/Switch to dark theme/i}));
    fireEvent.click(toggle);
    await waitFor(()=>expect(screen.getByRole('button',{name:/Switch to light theme/i})).toBeInTheDocument());
    expect(localStorage.getItem('qhealth-theme')).toBe('dark');
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('opens the command palette, searches, activates with Enter, and closes with Escape',async()=>{
    renderWithProviders(<ResearchShell><div>Shell content</div></ResearchShell>);
    fireEvent.click(screen.getByRole('button',{name:/Open command palette/i}));
    const dialog=screen.getByRole('dialog',{name:/Command palette/i});
    expect(dialog).toBeInTheDocument();
    const input=screen.getByRole('textbox',{name:/Search commands/i});
    fireEvent.change(input,{target:{value:'Training'}});
    fireEvent.keyDown(window,{key:'Enter'});
    await waitFor(()=>expect(screen.getByRole('link',{name:/Training/i})).toHaveClass('active'));

    fireEvent.click(screen.getByRole('button',{name:/Open command palette/i}));
    expect(screen.getByRole('dialog',{name:/Command palette/i})).toBeInTheDocument();
    fireEvent.keyDown(window,{key:'Escape'});
    expect(screen.queryByRole('dialog',{name:/Command palette/i})).not.toBeInTheDocument();
  });

  it('opens and closes the mobile navigation drawer',()=>{
    renderWithProviders(<ResearchShell><div>Shell content</div></ResearchShell>);
    fireEvent.click(screen.getByRole('button',{name:/Open navigation/i}));
    expect(screen.getAllByRole('button',{name:/Close navigation/i})).toHaveLength(2);
    fireEvent.click(screen.getAllByRole('button',{name:/Close navigation/i})[0]);
    expect(screen.getAllByRole('button',{name:/Close navigation/i})).toHaveLength(1);
    expect(document.querySelector('.navigation-scrim')).not.toBeInTheDocument();
  });
});

describe('settings and Demo Center readiness',()=>{
  it('persists theme, density, motion, and inspector preferences',()=>{
    renderWithProviders(<ResearchShell><SettingsPage/></ResearchShell>,['/settings']);
    fireEvent.click(screen.getByRole('button',{name:/Deep research/i}));
    fireEvent.change(screen.getByLabelText('Density'),{target:{value:'compact'}});
    fireEvent.change(screen.getByLabelText('Motion'),{target:{value:'reduced'}});
    fireEvent.click(screen.getByRole('checkbox',{name:/Show context inspector/i}));
    expect(localStorage.getItem('qhealth-theme')).toBe('dark');
    expect(localStorage.getItem('qhealth-density')).toBe('compact');
    expect(localStorage.getItem('qhealth-motion')).toBe('reduced');
    expect(localStorage.getItem('qhealth-inspector')).toBe('hidden');
  });

  const demoLibraryItem={
    slug:'wdbc',name:'Breast Cancer Wisconsin Diagnostic',domain:'oncology',description:'Diagnostic benchmark',
    source:'UCI Machine Learning Repository',source_url:'https://doi.org/10.24432/C5DW2B',version:'snapshot',
    license:'CC BY 4.0',license_url:'https://creativecommons.org/licenses/by/4.0/',attribution:'Wolberg et al.',
    target:'diagnosis',target_type:'binary_classification' as const,positive_label:'malignant',negative_label:'benign',
    row_count:569,feature_count:30,class_labels:['benign','malignant'],sha256:'a'.repeat(64),normalization:[],
    recommended_duplicate_policy:'reject' as const,origin:'built_in' as const,dataset_status:'available' as const,demo_readiness:{status:'ready' as const,instant_demo_available:true,artifact_version:'sih-verified-demo-v1',experiment_id:'experiment-a',model_ids:['model-a'],verified_dataset_hash:'a'.repeat(64),verified_artifact_manifest_hash:'b'.repeat(64)},
  };
  const demoDataset={
    id:'dataset-a',name:demoLibraryItem.name,sha256:demoLibraryItem.sha256,created_at:'2026-09-29T00:00:00Z',
    provenance:{name:demoLibraryItem.name,domain:demoLibraryItem.domain,source:demoLibraryItem.source,source_url:demoLibraryItem.source_url,version:'snapshot',target:'diagnosis',positive_label:'malignant',negative_label:'benign',features:[],numeric_features:[],categorical_features:[],row_count:569,feature_count:30,class_distribution:{benign:357,malignant:212},target_classes:['benign','malignant'],is_demo:false,dataset_hash:demoLibraryItem.sha256,license:'CC BY 4.0',origin:'built_in' as const,library_slug:'wdbc',recommended_duplicate_policy:'reject' as const},
    quality:{} as never,
  };
  const currentExperiment={
    id:'experiment-a',dataset_id:demoDataset.id,parent_id:null,status:'succeeded',
    config:{models:['logistic_regression','svm']},summary:{},created_at:'2026-09-29T00:00:00Z',
  } as Awaited<ReturnType<typeof qh.experiments>>[number];
  const readyModel=(id:string,experimentId:string,datasetId:string,modelType:'logistic_regression'|'svm'='logistic_regression')=>({
    id,experiment_id:experimentId,dataset_id:datasetId,model_type:modelType,status:'ready',
    details:{},metrics:{},created_at:'2026-09-29T00:00:00Z',
  } as Awaited<ReturnType<typeof qh.models>>[number]);

  it('loads with a truthful no-dataset state and verified route actions',async()=>{
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>expect(screen.getByText(/No dataset is selected/)).toBeInTheDocument());
    expect(document.querySelector('[data-stage="dataset"]')?.textContent).toContain('NOT STARTED');
    expect(document.querySelector('[data-stage="quality"]')?.textContent).toContain('BLOCKED');
    expect(document.querySelector('[data-stage="training"]')?.textContent).toContain('BLOCKED');
    const routes={dataset:'/datasets',quality:'/quality',preprocessing:'/preprocessing',features:'/features',pca:'/pca',training:'/training',quantum:'/quantum',comparison:'/comparison',robustness:'/robustness',explainability:'/explainability',prediction:'/prediction',report:'/experiments'};
    Object.entries(routes).forEach(([stage,path])=>
      expect(document.querySelector(`[data-stage="${stage}"] a`)).toHaveAttribute('href',path)
    );
    expect(screen.getByText('Step 1 of 12')).toBeInTheDocument();
    screen.getAllByRole('link',{name:'Choose Dataset'}).forEach(link=>
      expect(link).toHaveAttribute('href','/datasets')
    );
    fireEvent.click(screen.getByRole('button',{name:/Next/i}));
    expect(screen.getByText('Step 2 of 12')).toBeInTheDocument();
    screen.getAllByRole('link',{name:'Open Data Quality'}).forEach(link=>
      expect(link).toHaveAttribute('href','/quality')
    );
    fireEvent.click(screen.getByRole('button',{name:/Previous/i}));
    expect(screen.getByText('Step 1 of 12')).toBeInTheDocument();
  });

  it('selects a library dataset through the existing API and displays backend metadata',async()=>{
    vi.mocked(qh.datasetLibrary).mockResolvedValue([demoLibraryItem]);
    vi.mocked(qh.registerBuiltIn).mockResolvedValue(demoDataset);
    vi.mocked(qh.dataset).mockResolvedValue(demoDataset);
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    fireEvent.click(await screen.findByRole('button',{name:'Use Dataset'}));
    await waitFor(()=>expect(qh.registerBuiltIn).toHaveBeenCalledWith('wdbc'));
    await waitFor(()=>expect(JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}').dataset_id).toBe(demoDataset.id));
    const currentCard=screen.getByRole('heading',{name:'Current dataset'}).closest('.glass-card');
    expect(currentCard).not.toBeNull();
    expect(within(currentCard as HTMLElement).getByText(demoDataset.name)).toBeInTheDocument();
    expect(within(currentCard as HTMLElement).getByText('diagnosis')).toBeInTheDocument();
    expect(within(currentCard as HTMLElement).getByText('benign / malignant')).toBeInTheDocument();
    expect(document.querySelector('[data-stage="quality"]')?.textContent).toContain('READY');
    expect(qh.demo).not.toHaveBeenCalled();
  });

  it('does not use a ready model from another experiment for the active dataset',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:demoDataset.id}));
    vi.mocked(qh.dataset).mockResolvedValue(demoDataset);
    vi.mocked(qh.experiments).mockResolvedValue([currentExperiment]);
    vi.mocked(qh.models).mockResolvedValue([readyModel('model-b','experiment-b','dataset-b')]);
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>{
      expect(document.querySelector('[data-stage="training"]')?.textContent).toContain('BLOCKED');
      expect(document.querySelector('[data-stage="comparison"]')?.textContent).toContain('BLOCKED');
      expect(document.querySelector('[data-stage="robustness"]')?.textContent).toContain('BLOCKED');
      expect(document.querySelector('[data-stage="explainability"]')?.textContent).toContain('BLOCKED');
      expect(document.querySelector('[data-stage="prediction"]')?.textContent).toContain('BLOCKED');
      expect(document.querySelector('[data-stage="report"]')?.textContent).toContain('BLOCKED');
    });
  });

  it('recognizes ready models only from the current completed experiment',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:demoDataset.id}));
    vi.mocked(qh.dataset).mockResolvedValue(demoDataset);
    vi.mocked(qh.experiments).mockResolvedValue([currentExperiment]);
    vi.mocked(qh.models).mockResolvedValue([
      readyModel('model-a1',currentExperiment.id,demoDataset.id),
      readyModel('model-a2',currentExperiment.id,demoDataset.id,'svm'),
    ]);
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>{
      expect(document.querySelector('[data-stage="training"]')?.textContent).toContain('COMPLETED');
      expect(document.querySelector('[data-stage="comparison"]')?.textContent).toContain('READY');
      expect(document.querySelector('[data-stage="robustness"]')?.textContent).toContain('READY');
      expect(document.querySelector('[data-stage="explainability"]')?.textContent).toContain('READY');
      expect(document.querySelector('[data-stage="prediction"]')?.textContent).toContain('READY');
      expect(document.querySelector('[data-stage="report"]')?.textContent).toContain('READY');
    });
    screen.getAllByRole('link',{name:'View Experiment'}).forEach(link=>
      expect(link).toHaveAttribute('href','/experiments/experiment-a')
    );
  });

  it('surfaces backend errors instead of failing silently',async()=>{
    vi.mocked(qh.health).mockRejectedValueOnce(new Error('Backend unavailable'));
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>expect(screen.getAllByText('Backend unavailable').length).toBeGreaterThan(0));
  });
});

describe('operating-point and evidence UX',()=>{
  const metricRecord={accuracy:.8,precision:.75,recall:.7,sensitivity:.7,specificity:.9,f1:.72,roc_auc:.82,true_positive:7,true_negative:9,false_positive:1,false_negative:3,confusion_matrix:[[9,1],[3,7]],sample_count:20,roc_curve:{fpr:[0,1],tpr:[0,1],thresholds:[null,.5]},undefined_metrics:[]};
  const operatingPoint={selection_strategy:'target_sensitivity' as const,target_sensitivity:.95,target_specificity:null,selected_threshold:.42,threshold_units:'positive_class_probability',threshold_feasible:true,threshold_source:'out_of_fold_validation',validation_metrics:{threshold:.42,sensitivity:.95,specificity:.8,precision:.85,recall:.95,f1:.9,accuracy:.87,roc_auc:.91},holdout_metrics:{sensitivity:.7,specificity:.9},number_of_oof_samples:80,cv_fold_count:3,curve:[{threshold:.2,sensitivity:1,specificity:.4,precision:.6,recall:1,f1:.75,accuracy:.7,roc_auc:.91},{threshold:.42,sensitivity:.95,specificity:.8,precision:.85,recall:.95,f1:.9,accuracy:.87,roc_auc:.91}],interpretation:'Research operating point; not a clinically validated screening cutoff.'};
  const timings={final_training_seconds:1,cv_total_seconds:2,cv_fold_seconds:[1,1],test_inference_seconds:.2,test_inference_seconds_per_sample:.01};
  const experiment={id:'experiment-active',dataset_id:'dataset-active',parent_id:null,status:'succeeded',config:{models:['logistic_regression','qnn']},summary:{},created_at:'2026-09-30T00:00:00Z'} as Awaited<ReturnType<typeof qh.experiments>>[number];
  const model=(id:string,type:'logistic_regression'|'qnn',dataset='dataset-active',experimentId='experiment-active')=>({id,experiment_id:experimentId,dataset_id:dataset,model_type:type,status:'ready',details:{},metrics:{test:metricRecord,training:metricRecord,validation:{folds:[metricRecord],summary:Object.fromEntries(['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'].map(name=>[name,{mean:.8,std:.1,valid_folds:3}])) as never,std_definition:'sample'},timing:timings,calibration:{},operating_point:operatingPoint},created_at:'2026-09-30T00:00:00Z'}) as Awaited<ReturnType<typeof qh.models>>[number];

  it('switches between fixed and sensitivity-first operating-point controls',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({threshold_strategy:'target_sensitivity',target_sensitivity:.95}));
    renderWithProviders(<Training/>,['/training']);
    expect(screen.getByLabelText('Operating point')).toHaveValue('target_sensitivity');
    expect(screen.getByLabelText(/Target sensitivity/)).toHaveValue(.95);
    expect(screen.queryByLabelText('Fixed research threshold')).not.toBeInTheDocument();
    expect(screen.getByText(/not a clinically validated screening cutoff/i)).toBeInTheDocument();
  });

  it('renders threshold evidence, quantum resources, costs and truthful limitations',async()=>{
    vi.mocked(qh.experiments).mockResolvedValue([experiment]);
    const classical=model('classical-model','logistic_regression');
    const quantum=model('quantum-model','qnn');
    vi.mocked(qh.comparison).mockResolvedValue({
      experiment_id:experiment.id,dataset_id:experiment.dataset_id,models:[classical,quantum],split:{split_hash:'split'},comparison_fingerprint:'fingerprint',
      conclusion:'All completed pairs are shown.',
      limitations:['Benchmark only'],
      pairs:[{
        benchmark_type:'fair_controlled_diabetes_benchmark', quantum_model:quantum.id,classical_model:classical.id,quantum_type:'qnn',classical_type:'logistic_regression',
        performance:Object.fromEntries(['accuracy','precision','recall','sensitivity','specificity','f1','roc_auc'].map(name=>[name,{classical:.8,quantum:.7,delta_quantum_minus_classical:-.1}])) as never,
        computational_cost:{classical:{final_training_seconds:1,cv_total_seconds:2,cv_mean_fold_seconds:1,test_inference_seconds:.2,test_inference_seconds_per_sample:.01},quantum:{final_training_seconds:4,cv_total_seconds:8,cv_mean_fold_seconds:4,test_inference_seconds:.4,test_inference_seconds_per_sample:.02},deltas_quantum_minus_classical:{final_training_seconds:3,cv_total_seconds:6,cv_mean_fold_seconds:3,test_inference_seconds:.2,test_inference_seconds_per_sample:.01},semantics:'Measured runtime only.'},
        quantum_resources:{backend:'aer',execution_kind:'finite-shot local quantum simulation',qubits:2,shots:128,logical_depth:7,gate_counts:{cx:2},total_parameter_count:6,trainable_parameter_count:4,optimizer:'COBYLA',optimizer_objective_evaluations:5,noise_probability:0,real_hardware:false,resource_semantics:'Logical resources; not hardware cost.'},
        fairness:{dataset_id:'dataset-active',dataset_hash:'a'.repeat(64),target:'Early Stage Diabetes Risk Prediction',experiment_id:experiment.id,split_hash:'split',common_sample_count:100,source_sample_count:120,same_sample_budget:true,preprocessing_fingerprint:'fingerprint',cv_fold_count:3,seed:42,test_size:.25,target_sensitivity:.8,threshold_strategy:'target_sensitivity',controlled_comparison:true,status:'CONTROLLED COMPARISON',split_match:true,common_representation:{pca_components:2,hybrid_qubits:2,selected_feature_count:2}},
        operating_points:{classical:operatingPoint,quantum:operatingPoint},robustness:{status:'not_evaluated',note:'Not implemented'},conclusion:'The classical model produced higher sensitivity. No general quantum advantage established.',limitations:['benchmark evidence only','no clinical validation','simulator-only','no general quantum advantage established'],test_metric_delta_quantum_minus_classical:{accuracy:-.1,precision:-.1,recall:-.1,sensitivity:-.1,specificity:-.1,f1:-.1,roc_auc:-.1},final_training_seconds_delta:3,
      }],
    });
    renderWithProviders(<Comparison/>,['/comparison']);
    expect(await screen.findByText('Controlled classical vs hybrid evidence')).toBeInTheDocument();
    expect(screen.getByText('CONTROLLED DIABETES BENCHMARK')).toBeInTheDocument();
    expect(screen.getAllByText('CONTROLLED COMPARISON').length).toBeGreaterThan(0);
    expect(screen.getByText('HYBRID EXECUTION CONTEXT')).toBeInTheDocument();
    expect(screen.getByText(/Same sample budget = true/i)).toBeInTheDocument();
    expect(screen.getByText('Observed difference (Hybrid − Classical)')).toBeInTheDocument();
    expect(screen.getAllByText(/no general quantum advantage established/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Selected research threshold: 0.4200/i)).toBeInTheDocument();
    expect(screen.getByText('Validation, holdout, and runtime')).toBeInTheDocument();
  });

  it('shows an infeasible target without inventing a threshold',async()=>{
    const infeasibleModel=model('classical-model','logistic_regression');
    infeasibleModel.metrics.operating_point={...operatingPoint,threshold_feasible:false,selected_threshold:null,validation_metrics:null,infeasible_reason:'Target sensitivity is not achievable on the validation folds under the current model configuration.'};
    vi.mocked(qh.experiments).mockResolvedValue([experiment]);
    vi.mocked(qh.comparison).mockResolvedValue({experiment_id:experiment.id,dataset_id:experiment.dataset_id,models:[infeasibleModel],pairs:[],split:{},comparison_fingerprint:'fingerprint',conclusion:'No pair',limitations:[]});
    renderWithProviders(<Comparison/>,['/comparison']);
    expect(await screen.findByText(/Target sensitivity is not achievable/)).toBeInTheDocument();
    expect(screen.queryByText(/Selected research threshold: 0/)).not.toBeInTheDocument();
  });

  it('defaults prediction to active context and preserves all-model historical mode',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:'dataset-active'}));
    vi.mocked(qh.experiments).mockResolvedValue([experiment,{...experiment,id:'experiment-old',dataset_id:'dataset-old',created_at:'2026-09-01T00:00:00Z'}]);
    vi.mocked(qh.models).mockResolvedValue([model('active-model','logistic_regression'),model('historical-model','logistic_regression','dataset-old','experiment-old')]);
    renderWithProviders(<PredictionPage/>,['/prediction']);
    const selector=await screen.findByLabelText('Registered model');
    await waitFor(()=>expect(within(selector).getAllByRole('option')).toHaveLength(2));
    fireEvent.change(screen.getByLabelText('Prediction model scope'),{target:{value:'all'}});
    await waitFor(()=>expect(within(selector).getAllByRole('option')).toHaveLength(3));
    expect(screen.getByRole('option',{name:/historic/i})).toBeInTheDocument();
  });

  it('runs and renders neutral paired robustness evidence',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({dataset_id:'dataset-active'}));
    const classical=model('classical-model','logistic_regression');
    const quantum=model('quantum-model','qnn');
    vi.mocked(qh.experiments).mockResolvedValue([experiment]);
    vi.mocked(qh.models).mockResolvedValue([classical,quantum]);
    const evidence=(id:string,type:'logistic_regression'|'qnn',delta:number)=>({
      id:`result-${id}`,status:'evaluated',reason:null,experiment_id:experiment.id,dataset_id:experiment.dataset_id,dataset_hash:'a'.repeat(64),split_hash:'split',
      model_id:id,model_type:type,perturbation_type:'missingness',perturbation_level:.05,random_seed:42,sample_count:20,
      baseline_metrics:metricRecord,perturbed_metrics:{...metricRecord,accuracy:.8+delta,sensitivity:.7+delta,specificity:.9+delta,f1:.72+delta,roc_auc:.82+delta},
      degradation_delta:{accuracy:delta,precision:delta,recall:delta,sensitivity:delta,specificity:delta,f1:delta,roc_auc:delta},
      relative_degradation:{accuracy:delta,precision:delta,recall:delta,sensitivity:delta,specificity:delta,f1:delta,roc_auc:delta},
      undefined_metrics:{},threshold_used:.42,threshold_source:'out_of_fold_validation',preprocessing_context:{},perturbation_metadata:{changed_cells:3},
      execution_timing:{baseline_inference_seconds:.01,perturbed_inference_seconds:.01},limitations:['Research evaluation only'],reproducibility_metadata:{perturbation_fingerprint:'same'},
    });
    vi.mocked(qh.robustness).mockResolvedValue({experiment_id:experiment.id,dataset_id:experiment.dataset_id,sample_count:20,model_count:2,condition_count:2,results:[evidence(classical.id,'logistic_regression',-.05),evidence(quantum.id,'qnn',-.1)] as never,limitations:['No ranking']});
    renderWithProviders(<Robustness/>,['/robustness']);
    expect(await screen.findByText('Robustness Lab')).toBeInTheDocument();
    await waitFor(()=>expect(screen.getByLabelText('Robustness experiment')).toHaveValue(experiment.id));
    fireEvent.change(screen.getByLabelText('Classical robustness model'),{target:{value:classical.id}});
    fireEvent.change(screen.getByLabelText('Quantum robustness model'),{target:{value:quantum.id}});
    fireEvent.change(screen.getByLabelText('Perturbation scenario'),{target:{value:'gaussian_noise'}});
    expect(screen.getByLabelText('Perturbation level')).toHaveValue('0.05');
    fireEvent.click(screen.getByRole('button',{name:'Run robustness condition'}));
    expect(await screen.findByText('Observed degradation under controlled perturbation')).toBeInTheDocument();
    expect(screen.getAllByText(/perturbed − baseline/i).length).toBeGreaterThan(0);
    expect(screen.getByText('Paired observed differences')).toBeInTheDocument();
    expect(screen.getByText(/not a winner or advantage claim/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Winner$/i)).not.toBeInTheDocument();
  });

  it('renders an explicit not-applicable robustness condition',async()=>{
    vi.mocked(qh.experiments).mockResolvedValue([experiment]);
    const classical=model('classical-model','logistic_regression');
    vi.mocked(qh.models).mockResolvedValue([classical]);
    vi.mocked(qh.robustness).mockResolvedValue({experiment_id:experiment.id,dataset_id:experiment.dataset_id,sample_count:20,model_count:1,condition_count:1,results:[{
      id:'result-na',status:'not_applicable',reason:'No categorical feature with at least two observed training categories is available.',experiment_id:experiment.id,dataset_id:experiment.dataset_id,dataset_hash:'a'.repeat(64),split_hash:'split',
      model_id:classical.id,model_type:'logistic_regression',perturbation_type:'categorical',perturbation_level:.05,random_seed:42,sample_count:20,baseline_metrics:metricRecord,perturbed_metrics:null,
      degradation_delta:{accuracy:null,precision:null,recall:null,sensitivity:null,specificity:null,f1:null,roc_auc:null},relative_degradation:{accuracy:null,precision:null,recall:null,sensitivity:null,specificity:null,f1:null,roc_auc:null},undefined_metrics:{accuracy:'undefined'},threshold_used:.5,threshold_source:'configured_fixed_threshold',preprocessing_context:{},perturbation_metadata:null,execution_timing:{baseline_inference_seconds:.01,perturbed_inference_seconds:null},limitations:[],reproducibility_metadata:{},
    }] as never,limitations:[]});
    renderWithProviders(<Robustness/>,['/robustness']);
    await waitFor(()=>expect(screen.getByLabelText('Robustness experiment')).toHaveValue(experiment.id));
    fireEvent.change(screen.getByLabelText('Classical robustness model'),{target:{value:classical.id}});
    fireEvent.change(screen.getByLabelText('Perturbation scenario'),{target:{value:'categorical'}});
    fireEvent.click(screen.getByRole('button',{name:'Run robustness condition'}));
    expect(await screen.findByText(/not applicable:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/No categorical feature/).length).toBeGreaterThan(0);
  });
});

describe('quantum resource advisor',()=>{
  const recommendedQuantum={backend:'aer' as const,qubits:4,feature_map_reps:1,ansatz_reps:1,entanglement:'full' as const,optimizer:'SPSA' as const,maxiter:30,shots:1024,noise_probability:.05};
  const advisorResponse={
    requested_configuration:{model_type:'qnn' as const,quantum:{...recommendedQuantum,qubits:8,feature_map_reps:3,ansatz_reps:3,maxiter:300,shots:16384},feature_dimension:8,sample_count:300,dataset_id:null,experiment_id:null},
    resource_profile:{logical_qubits:8,feature_dimension:8,feature_map_repetitions:3,ansatz_repetitions:3,entanglement:'full',logical_depth:null,gate_count:null,parameter_count:null,circuit_complexity:'high',optimizer:'SPSA',optimizer_iteration_budget:300,optimization_workload:'high',backend:'aer',execution_kind:'finite-shot local Aer simulation',shots_per_circuit_evaluation:16384,measurement_workload:'high',noise_probability:.05,noise_mode:'density-matrix simulator path',sample_count:300,bounded_quantum_sample_cap:256,sample_workload:'high',structural_metadata_status:'Not guessed',hardware_execution:false},
    budget_status:{status:'exceeds_budget' as const,reasons:['qubits exceeds bounded limit']},
    budget_policy:{version:'bounded-simulator-resource-policy-v1',scope:'local',schema_bounds:{},bounded_prototype_limits:{},near_budget_fraction:.75,safe_baseline:{},recommendation_order:[],semantics:'Explicit engineering guardrails; not a runtime prediction.'},
    recommendation:{available:true,configuration:{model_type:'qnn' as const,quantum:recommendedQuantum,feature_dimension:4,sample_count:160,dataset_id:null,experiment_id:null},changes:[{field:'shots',from:16384,to:1024,reason:'Reduces finite-shot measurement workload.'},{field:'qubits',from:8,to:4,reason:'Keeps PCA equal to qubits.'}],rationale:'Deterministic policy order.',valid:true,policy_version:'bounded-simulator-resource-policy-v1'},
    historical_evidence:{matched_runs:2,median_training_seconds:12,min_training_seconds:10,max_training_seconds:14,measured_fields:['final_training_seconds'],matching_policy:'Exact model, backend, and qubits.',runs:[],limitations:[]},
    limitations:['Hardware execution is not available in the current verified configuration.'],
  };

  it('renders exceeded budget, measured history, changes, and applies only after explicit action',async()=>{
    localStorage.setItem('qhealth-tictac-draft',JSON.stringify({quantum:{...advisorResponse.requested_configuration.quantum},pipeline:{pca_components:8},max_samples:300}));
    vi.mocked(qh.resourceAdvisor).mockResolvedValue(advisorResponse as never);
    renderWithProviders(<Quantum/>,['/quantum']);
    expect(screen.getByText('Quantum Resource Advisor')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Quantum advisor model'),{target:{value:'qnn'}});
    fireEvent.click(screen.getByRole('button',{name:'Analyze resource profile'}));
    expect(await screen.findByText('EXCEEDS BUDGET')).toBeInTheDocument();
    expect(screen.getByText('16384')).toBeInTheDocument();
    expect(screen.getByText('1024')).toBeInTheDocument();
    expect(screen.getByText('Observed historical runs')).toBeInTheDocument();
    expect(screen.getByText('12.000 s')).toBeInTheDocument();
    expect(screen.getByText(/Hardware execution is not available/)).toBeInTheDocument();
    let persisted=JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}');
    expect(persisted.quantum.qubits).toBe(8);
    fireEvent.click(screen.getByRole('button',{name:'Apply recommended configuration'}));
    await waitFor(()=>{
      persisted=JSON.parse(localStorage.getItem('qhealth-tictac-draft')||'{}');
      expect(persisted.quantum.qubits).toBe(4);
      expect(persisted.pipeline.pca_components).toBe(4);
      expect(persisted.max_samples).toBe(160);
    });
  });

  it('shows the truthful no-history and within-budget states',async()=>{
    vi.mocked(qh.resourceAdvisor).mockResolvedValue({
      ...advisorResponse,
      budget_status:{status:'within_budget',reasons:['Every dimension is within policy.']},
      recommendation:{...advisorResponse.recommendation,available:false,configuration:null,changes:[],rationale:'Already within policy.'},
      historical_evidence:{...advisorResponse.historical_evidence,matched_runs:0,median_training_seconds:null,min_training_seconds:null,max_training_seconds:null},
    } as never);
    renderWithProviders(<Quantum/>,['/quantum']);
    fireEvent.click(screen.getByRole('button',{name:'Analyze resource profile'}));
    expect(await screen.findByText('WITHIN BUDGET')).toBeInTheDocument();
    expect(screen.getByText(/Insufficient historical evidence/)).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Apply recommended configuration'})).not.toBeInTheDocument();
    expect(screen.queryByText(/Estimated runtime:/i)).not.toBeInTheDocument();
  });
});
