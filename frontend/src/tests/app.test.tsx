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
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({
  setSessionToken:vi.fn(),
  api:{get:vi.fn(()=>Promise.resolve([])),post:vi.fn(()=>Promise.resolve({})),remove:vi.fn(()=>Promise.resolve(undefined))},
  qh:{
    health:vi.fn(()=>Promise.resolve({status:'ok',version:'test',mode:'local',authentication_required:false,quantum:{available:false,runtime_verified:false,execution:'local simulation'},disclaimer:'Research only'})),
    systemStatus:vi.fn(()=>Promise.resolve({status:'ok',version:'test',mode:'local',database_available:true,storage_available:true,quantum:{available:false,runtime_verified:false,execution:'local simulation'},supported_models:{classical:[],quantum:[]},jobs:{queued:0,running:0,active:0}})),
    summary:vi.fn(()=>Promise.resolve({counts:{datasets:0,experiments:0,ready_models:0,active_jobs:0},recent_experiments:[],disclaimer:'Research only'})),
    jobs:vi.fn(()=>Promise.resolve([])),
    models:vi.fn(()=>Promise.resolve([])),
    experiments:vi.fn(()=>Promise.resolve([])),
    datasets:vi.fn(()=>Promise.resolve([])),
    datasetLibrary:vi.fn(()=>Promise.resolve([])),
    registerBuiltIn:vi.fn(()=>Promise.resolve({})),
    inspectDataset:vi.fn(()=>Promise.resolve({})),
    upload:vi.fn(()=>Promise.resolve({})),
    capabilities:vi.fn(()=>Promise.resolve({available:false,runtime_verified:false,execution:'Quantum runtime unavailable'})),
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
    recommended_duplicate_policy:'reject' as const,origin:'built_in' as const,dataset_status:'available' as const,
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
    {...libraryItem,slug:'cleveland-heart-disease',name:'Heart Disease — Cleveland',domain:'cardiovascular',target:'heart_disease',positive_label:'present',negative_label:'absent',row_count:303,feature_count:13,class_labels:['absent','present']},
    {...libraryItem,slug:'chronic-kidney-disease',name:'Chronic Kidney Disease',domain:'nephrology',target:'ckd_status',positive_label:'ckd',negative_label:'not_ckd',row_count:400,feature_count:24,class_labels:['ckd','not_ckd']},
    {...libraryItem,slug:'ilpd-liver',name:'ILPD Liver Patient Dataset',domain:'hepatology',target:'liver_disease',positive_label:'present',negative_label:'absent',row_count:583,feature_count:10,class_labels:['absent','present'],recommended_duplicate_policy:'drop_exact' as const},
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

  it('shows truthful not-yet-run readiness and supports next/previous stage navigation',async()=>{
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>expect(screen.getAllByText('NOT YET RUN').length).toBeGreaterThan(0));
    expect(screen.getByText('Step 1 of 10')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/Next/i}));
    expect(screen.getByText('Step 2 of 10')).toBeInTheDocument();
    expect(screen.getByRole('link',{name:/Open current stage/i})).toHaveAttribute('href','/datasets');
    fireEvent.click(screen.getByRole('button',{name:/Previous/i}));
    expect(screen.getByText('Step 1 of 10')).toBeInTheDocument();
  });

  it.each([
    {
      label:'does not use a ready model from a different experiment',
      modelExperimentId:'experiment-b',
      expectedReady:false,
    },
    {
      label:'accepts a ready model from the completed experiment',
      modelExperimentId:'experiment-a',
      expectedReady:true,
    },
  ])('$label',async({modelExperimentId,expectedReady})=>{
    vi.mocked(qh.summary).mockResolvedValue({
      counts:{datasets:1,experiments:1,ready_models:1,active_jobs:0},
      recent_experiments:[],
      disclaimer:'Research only',
    });
    vi.mocked(qh.experiments).mockResolvedValue([
      {id:'experiment-a',status:'succeeded'},
    ] as Awaited<ReturnType<typeof qh.experiments>>);
    vi.mocked(qh.models).mockResolvedValue([
      {id:'model-1',experiment_id:modelExperimentId,status:'ready'},
    ] as Awaited<ReturnType<typeof qh.models>>);

    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>{
      const dependentSteps=Array.from(document.querySelectorAll('.demo-step')).slice(6,9);
      expect(dependentSteps).toHaveLength(3);
      if(expectedReady){
        dependentSteps.forEach(step=>expect(step.textContent).toContain('READY'));
      }else{
        dependentSteps.forEach(step=>expect(step.textContent).toContain('NOT YET RUN'));
        dependentSteps.forEach(step=>expect(step.textContent).not.toMatch(/\bREADY\b/));
      }
    });
  });

  it('surfaces backend errors instead of failing silently',async()=>{
    vi.mocked(qh.summary).mockRejectedValueOnce(new Error('Backend unavailable'));
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>expect(screen.getByText('Backend unavailable')).toBeInTheDocument());
  });
});
