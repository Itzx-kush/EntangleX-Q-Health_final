import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import App from '../App';
import {ResearchShell} from '../components/ResearchShell';
import {DraftProvider} from '../hooks/useDraft';
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
});

describe('research shell navigation and commands',()=>{
  it('marks the active route and redirects unknown routes to overview',async()=>{
    renderWithProviders(<ResearchShell><div>Shell content</div></ResearchShell>,['/datasets']);
    expect(screen.getByRole('link',{name:/Datasets/i})).toHaveClass('active');

    renderWithProviders(<App/>,['/not-a-real-route']);
    await waitFor(()=>expect(screen.getByRole('heading',{name:/Overview/i})).toBeInTheDocument());
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

  it('surfaces backend errors instead of failing silently',async()=>{
    vi.mocked(qh.summary).mockRejectedValueOnce(new Error('Backend unavailable'));
    renderWithProviders(<ResearchShell><DemoCenter/></ResearchShell>,['/demo']);
    await waitFor(()=>expect(screen.getByText('Backend unavailable')).toBeInTheDocument());
  });
});
