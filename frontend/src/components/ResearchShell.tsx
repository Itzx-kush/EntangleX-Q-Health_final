import {useEffect,useMemo,useState,type ReactNode} from 'react';
import {NavLink,useLocation,useNavigate} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {
  Activity,Atom,BarChart3,Brain,ChevronLeft,ChevronRight,Command,Database,
  FlaskConical,LayoutDashboard,Menu,PanelRight,PlayCircle,Search,Settings2,
  ShieldCheck,SlidersHorizontal,X,Zap
} from 'lucide-react';
import {qh,setSessionToken} from '../lib/api';
import {Badge,Button} from './ui';
import {SearchBar} from './SearchBar';
import {StatusBadge} from './Shared';
import {AmbientBackground} from './reactbits';
import type {Health,Job,SystemStatus} from '../types/qhealth';

type NavEntry={label:string;path:string;icon:typeof Activity};
type NavGroup={label:string;items:NavEntry[]};
type SummaryData={counts:{datasets:number;experiments:number;ready_models:number;active_jobs:number}};
type ThemeMode='research'|'dark'|'system';
type SidebarVariant='sidebar'|'floating'|'inset';
type LayoutMode='default'|'icon'|'offcanvas';
type UiSettings={
  theme:ThemeMode;
  sidebar:SidebarVariant;
  layout:LayoutMode;
  density:'comfortable'|'compact';
  motion:'full'|'reduced';
};

const navGroups:NavGroup[]=[
  {label:'Research',items:[
    {label:'Overview',path:'/',icon:LayoutDashboard},
    {label:'Datasets',path:'/datasets',icon:Database},
    {label:'Data quality',path:'/quality',icon:ShieldCheck},
    {label:'Preprocessing',path:'/preprocessing',icon:SlidersHorizontal},
    {label:'Feature selection',path:'/features',icon:BarChart3},
    {label:'PCA / dimensions',path:'/pca',icon:BarChart3},
  ]},
  {label:'Modeling',items:[
    {label:'Training',path:'/training',icon:PlayCircle},
    {label:'Comparison',path:'/comparison',icon:BarChart3},
    {label:'Quantum Lab',path:'/quantum',icon:Atom},
  ]},
  {label:'Interpretation',items:[
    {label:'Explainability',path:'/explainability',icon:Brain},
    {label:'Research prediction',path:'/prediction',icon:Zap},
  ]},
  {label:'Experiments',items:[
    {label:'Experiment registry',path:'/experiments',icon:FlaskConical},
  ]},
];

const pageNames:Record<string,string>=Object.fromEntries(
  navGroups.flatMap(group=>group.items.map(item=>[item.path,item.label]))
);

function readSettings():UiSettings{
  const storedTheme=localStorage.getItem('qhealth-theme')||localStorage.getItem('qhealth-tictac-theme')||'research';
  const storedSidebar=localStorage.getItem('qhealth-sidebar-variant')||'inset';
  const storedLayout=localStorage.getItem('qhealth-layout')||'default';
  return {
    theme:(['research','dark','system'].includes(storedTheme)?storedTheme:'research') as ThemeMode,
    sidebar:(['sidebar','floating','inset'].includes(storedSidebar)?storedSidebar:'inset') as SidebarVariant,
    layout:(['default','icon','offcanvas'].includes(storedLayout)?storedLayout:'default') as LayoutMode,
    density:(localStorage.getItem('qhealth-density')||'comfortable') as 'comfortable'|'compact',
    motion:(localStorage.getItem('qhealth-motion')||'full') as 'full'|'reduced',
  };
}

function SettingsPopover({token,setToken,onApply,onClose}:{token:string;setToken:(v:string)=>void;onApply:()=>void;onClose:()=>void}){
  return <div className="shell-popover settings-panel" role="dialog" aria-label="Connection settings">
    <div className="flex items-start justify-between gap-3"><div><p className="eyebrow">Connection</p><h2 className="section-title mt-1">Session settings</h2></div><button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close settings"><X size={15}/></button></div>
    <label className="field mt-4"><span>Optional local API token</span><input className="input" type="password" value={token} onChange={e=>setToken(e.target.value)} placeholder="Bearer token"/><small>Kept in memory only. Never stored in local storage.</small></label>
    <Button className="mt-3 w-full" onClick={onApply}>Apply connection token</Button>
    <NavLink className="btn btn-outline mt-2 w-full" to="/settings" onClick={onClose}><Settings2 size={14}/>Open settings center</NavLink>
  </div>;
}

function CommandPalette({onClose}:{onClose:()=>void}){
  const navigate=useNavigate(); const [query,setQuery]=useState(''); const [activeIndex,setActiveIndex]=useState(0);
  const applyLocal=(key:string,value:string)=>{localStorage.setItem(key,value);window.dispatchEvent(new Event('qhealth-settings-changed'));onClose()};
  const commands=[
    {label:'Open Overview',hint:'Navigation',run:()=>navigate('/')},
    {label:'Open Datasets',hint:'Navigation',run:()=>navigate('/datasets')},
    {label:'Open Training',hint:'Navigation',run:()=>navigate('/training')},
    {label:'Open Comparison',hint:'Navigation',run:()=>navigate('/comparison')},
    {label:'Open Quantum Lab',hint:'Navigation',run:()=>navigate('/quantum')},
    {label:'Open Explainability',hint:'Navigation',run:()=>navigate('/explainability')},
    {label:'Open Research Prediction',hint:'Navigation',run:()=>navigate('/prediction')},
    {label:'Open Experiments',hint:'Navigation',run:()=>navigate('/experiments')},
    {label:'Launch SIH Demo',hint:'Presentation',run:()=>navigate('/demo')},
    {label:'Open Settings',hint:'Workspace',run:()=>navigate('/settings')},
    {label:'Use research light theme',hint:'Appearance',run:()=>applyLocal('qhealth-theme','research')},
    {label:'Use deep research theme',hint:'Appearance',run:()=>applyLocal('qhealth-theme','dark')},
    {label:'Use compact density',hint:'Layout',run:()=>applyLocal('qhealth-density','compact')},
    {label:'Use comfortable density',hint:'Layout',run:()=>applyLocal('qhealth-density','comfortable')},
    {label:'Show context inspector',hint:'Workspace',run:()=>applyLocal('qhealth-inspector','visible')},
    {label:'Hide context inspector',hint:'Workspace',run:()=>applyLocal('qhealth-inspector','hidden')},
  ];
  const filtered=commands.filter(command=>command.label.toLowerCase().includes(query.toLowerCase())||command.hint.toLowerCase().includes(query.toLowerCase()));
  useEffect(()=>setActiveIndex(0),[query]);
  useEffect(()=>{const handler=(e:KeyboardEvent)=>{if(e.key==='ArrowDown'){e.preventDefault();setActiveIndex(i=>Math.min(i+1,Math.max(filtered.length-1,0)))}else if(e.key==='ArrowUp'){e.preventDefault();setActiveIndex(i=>Math.max(i-1,0))}else if(e.key==='Enter'&&filtered[activeIndex]){e.preventDefault();filtered[activeIndex].run();onClose()} };window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)},[activeIndex,filtered,onClose]);
  return <div className="command-overlay" role="presentation" onMouseDown={onClose}>
    <div className="command-dialog" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={e=>e.stopPropagation()}>
      <div className="command-search"><Search size={17}/><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search actions and research areas…" aria-label="Search commands"/><kbd>ESC</kbd></div>
      <div className="command-list" role="listbox" aria-label="Available commands">{filtered.map((command,index)=><button key={command.label} role="option" aria-selected={activeIndex===index} className={activeIndex===index?'is-highlighted':''} onMouseEnter={()=>setActiveIndex(index)} onClick={()=>{command.run();onClose()}}><span className="command-icon"><Command size={14}/></span><span className="min-w-0 flex-1"><strong className="block">{command.label}</strong><small className="muted">{command.hint}</small></span><ChevronRight size={14} className="ml-auto muted"/></button>)}{!filtered.length&&<p className="p-6 text-center text-sm muted">No command matches this search.</p>}</div>
      <div className="command-footer"><span><kbd>↑↓</kbd> Navigate</span><span><kbd>Enter</kbd> Open</span><span><kbd>Esc</kbd> Close</span></div>
    </div>
  </div>;
}

function ConfigDrawer({prefs,onChange,onReset,onClose}:{prefs:UiSettings;onChange:(patch:Partial<UiSettings>)=>void;onReset:()=>void;onClose:()=>void}){
  const choice=(label:string,active:boolean,patch:Partial<UiSettings>)=>
    <button type="button" className={'config-choice '+(active?'is-active':'')} onClick={()=>onChange(patch)} aria-pressed={active}>{label}</button>;
  return <div className="config-overlay" role="presentation" onMouseDown={onClose}>
    <aside className="config-drawer" role="dialog" aria-modal="true" aria-label="Theme and layout settings" onMouseDown={e=>e.stopPropagation()}>
      <div className="config-drawer-head">
        <div><p className="eyebrow">Workspace</p><h2>Theme &amp; layout</h2><p className="muted">Customize the research shell without changing the research workflow.</p></div>
        <button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close theme and layout"><X size={15}/></button>
      </div>
      <div className="config-section"><p className="config-title">Theme</p><div className="config-choice-grid">
        {choice('Research light',prefs.theme==='research',{theme:'research'})}
        {choice('Deep research',prefs.theme==='dark',{theme:'dark'})}
        {choice('System',prefs.theme==='system',{theme:'system'})}
      </div></div>
      <div className="config-section"><p className="config-title">Sidebar</p><div className="config-choice-grid">
        {choice('Standard',prefs.sidebar==='sidebar',{sidebar:'sidebar'})}
        {choice('Floating',prefs.sidebar==='floating',{sidebar:'floating'})}
        {choice('Inset',prefs.sidebar==='inset',{sidebar:'inset'})}
      </div></div>
      <div className="config-section"><p className="config-title">Layout</p><div className="config-choice-grid">
        {choice('Default',prefs.layout==='default',{layout:'default'})}
        {choice('Compact',prefs.layout==='icon',{layout:'icon'})}
        {choice('Off-canvas',prefs.layout==='offcanvas',{layout:'offcanvas'})}
      </div></div>
      <div className="config-section"><p className="config-title">Density</p><div className="config-choice-grid">
        {choice('Comfortable',prefs.density==='comfortable',{density:'comfortable'})}
        {choice('Compact',prefs.density==='compact',{density:'compact'})}
      </div></div>
      <div className="config-section"><p className="config-title">Motion</p><div className="config-choice-grid">
        {choice('Full',prefs.motion==='full',{motion:'full'})}
        {choice('Reduced',prefs.motion==='reduced',{motion:'reduced'})}
      </div></div>
      <div className="config-drawer-actions">
        <button className="btn btn-outline" onClick={onReset}>Reset</button>
        <button className="btn btn-primary" onClick={onClose}>Done</button>
      </div>
    </aside>
  </div>;
}

function ContextInspector({summary,health,status,jobs,visible,onClose}:{summary:SummaryData|undefined;health:Health|undefined;status:SystemStatus|undefined;jobs:Job[]|undefined;visible:boolean;onClose:()=>void}){
  if(!visible)return null;
  const active=(jobs||[]).filter(job=>['queued','running','cancel_requested'].includes(job.status));
  return <aside className="context-inspector" aria-label="Research context inspector">
    <div className="inspector-head"><div><p className="eyebrow">Live context</p><h2>Workspace state</h2></div><button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close context inspector"><X size={15}/></button></div>
    <div className="inspector-card"><div className="inspector-label"><Activity size={13}/> System status</div><div className="inspector-status"><span className={'status-dot '+(health?'is-live':'is-offline')}/><strong>{health?'Backend connected':'Backend unavailable'}</strong></div><p className="inspector-copy">{health?.mode||'Start the FastAPI service to load live research state.'}</p></div>
    <div className="inspector-card"><div className="inspector-label"><Database size={13}/> Registry</div><dl className="inspector-facts"><div><dt>Datasets</dt><dd>{summary?.counts.datasets??'—'}</dd></div><div><dt>Experiments</dt><dd>{summary?.counts.experiments??'—'}</dd></div><div><dt>Ready models</dt><dd>{summary?.counts.ready_models??'—'}</dd></div><div><dt>Storage</dt><dd>{status?.storage_available?'Ready':'Not reported'}</dd></div></dl></div>
    <div className="inspector-card"><div className="inspector-label"><Zap size={13}/> Quantum boundary</div><div className="inspector-status"><Badge tone={health?.quantum.available?'purple':'amber'}>{health?.quantum.available?'Available':'Not available'}</Badge></div><p className="inspector-copy">{health?.quantum.execution||'Capability is reported by the backend, not assumed by the UI.'}</p></div>
    <div className="inspector-card"><div className="inspector-label"><PlayCircle size={13}/> Active jobs <span className="ml-auto">{active.length}</span></div>{active.length?<ul className="inspector-jobs">{active.slice(0,4).map(job=><li key={job.id}><StatusBadge value={job.status}/><span>{job.state}</span></li>)}</ul>:<p className="inspector-copy">No queued or running jobs.</p>}</div>
    <p className="inspector-note"><ShieldCheck size={13}/> Metrics, status and quantum availability are shown only when returned by the live backend.</p>
  </aside>;
}

export function ResearchShell({children}:{children:ReactNode}){
  const {pathname}=useLocation();
  const [mobile,setMobile]=useState(false); const [palette,setPalette]=useState(false); const [settings,setSettings]=useState(false); const [config,setConfig]=useState(false);
  const [showInspector,setShowInspector]=useState(()=>localStorage.getItem('qhealth-inspector')!=='hidden');
  const [token,setToken]=useState(''); const [uiSettings,setUiSettings]=useState<UiSettings>(readSettings);
  const summary=useQuery({queryKey:['summary'],queryFn:qh.summary,refetchInterval:10000});
  const health=useQuery({queryKey:['health'],queryFn:qh.health,refetchInterval:15000});
  const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:10000});
  const status=useQuery({queryKey:['system-status'],queryFn:qh.systemStatus,refetchInterval:15000});
  const title=pageNames[pathname]|| (pathname.startsWith('/experiments/')?'Experiment detail':'Research workspace');
  const isActiveGroup=useMemo(()=>navGroups.find(group=>group.items.some(item=>item.path===pathname))?.label,[pathname]);

  useEffect(()=>{
    const resolved=uiSettings.theme==='system'
      ? (window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'research')
      : uiSettings.theme;
    document.documentElement.classList.toggle('dark',resolved==='dark');
    document.documentElement.dataset.theme=uiSettings.theme;
    document.documentElement.dataset.density=uiSettings.density;
    document.documentElement.dataset.motion=uiSettings.motion;
    document.documentElement.dataset.sidebar=uiSettings.sidebar;
    document.documentElement.dataset.layout=uiSettings.layout;
    localStorage.setItem('qhealth-theme',uiSettings.theme);
    localStorage.setItem('qhealth-sidebar-variant',uiSettings.sidebar);
    localStorage.setItem('qhealth-layout',uiSettings.layout);
    localStorage.setItem('qhealth-density',uiSettings.density);
    localStorage.setItem('qhealth-motion',uiSettings.motion);
  },[uiSettings]);

  useEffect(()=>{const handler=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setPalette(true)}if(e.key==='Escape'){setPalette(false);setSettings(false)}};window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)},[]);
  useEffect(()=>{const handler=()=>setUiSettings(readSettings());window.addEventListener('qhealth-settings-changed',handler);return()=>window.removeEventListener('qhealth-settings-changed',handler)},[]);
  useEffect(()=>{setMobile(false);setSettings(false)},[pathname]);
  const updatePrefs=(patch:Partial<UiSettings>)=>setUiSettings(prev=>({...prev,...patch}));
  const resetPrefs=()=>setUiSettings({theme:'research',sidebar:'inset',layout:'default',density:'comfortable',motion:'full'});

  return <div className={'research-shell '+(uiSettings.layout==='icon'?'is-collapsed ':'')+(uiSettings.layout==='offcanvas'?'is-offcanvas':'')}>
    <AmbientBackground/>
    <aside className={'research-sidebar variant-'+uiSettings.sidebar+' '+(uiSettings.layout==='icon'?'is-collapsed ':'')+(mobile?'is-mobile-open ':'')+(uiSettings.layout==='offcanvas'?'is-offcanvas':'')} aria-label="Primary navigation">
      <div className="sidebar-brand"><NavLink to="/" className="brand-mark" aria-label="Q-Health overview"><img src="/entanglex-mark.svg" alt="" aria-hidden="true"/></NavLink><div className="brand-copy"><img src="/entanglex-logo-dark.svg" alt="EntangleX"/><span>Q-HEALTH</span></div><button className="sidebar-close btn btn-ghost" onClick={()=>setMobile(false)} aria-label="Close navigation"><X size={16}/></button></div>
      <div className="sidebar-context"><span className="context-kicker">Research workspace</span><strong>SIH 2026 · PS 26139</strong><span>Hybrid biomedical ML</span></div>
      <nav className="sidebar-nav">{navGroups.map(group=><div className={'sidebar-group '+(isActiveGroup===group.label?'is-current':'')} key={group.label}><p className="sidebar-label">{group.label}</p>{group.items.map(({label,path,icon:Icon})=><NavLink key={path} end={path==='/'||path==='/experiments'} to={path} className={({isActive})=>'sidebar-link '+(isActive?'active':'')} title={uiSettings.layout==='icon'?label:undefined}><Icon size={16}/><span>{label}</span>{path==='/quantum'&&<span className="sidebar-pulse"/>}</NavLink>)}</div>)}<div className="sidebar-group sidebar-special"><p className="sidebar-label">Presentation</p><NavLink to="/demo" className={({isActive})=>'sidebar-link demo-link '+(isActive?'active':'')}><PlayCircle size={16}/><span>SIH Demo Center</span></NavLink></div></nav>
      <div className="sidebar-bottom"><button className="sidebar-link" onClick={()=>setPalette(true)}><Command size={16}/><span>Command palette</span><kbd>⌘K</kbd></button><NavLink to="/settings" className="sidebar-link"><Settings2 size={16}/><span>Settings</span></NavLink><button className="sidebar-link" onClick={()=>setConfig(true)}><Settings2 size={16}/><span>Theme & Layout</span></button><button className="collapse-button" onClick={()=>updatePrefs({layout:uiSettings.layout==='icon'?'default':'icon'})} aria-label={uiSettings.layout==='icon'?'Expand sidebar':'Collapse sidebar'}>{uiSettings.layout==='icon'?<ChevronRight size={15}/>:<><ChevronLeft size={15}/><span>Collapse sidebar</span></>}</button></div>
    </aside>
    {mobile&&<button className="navigation-scrim" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
    <div className="research-workspace">
      <header className="research-topbar"><div className="topbar-left"><button className="mobile-menu btn btn-ghost" onClick={()=>setMobile(true)} aria-label="Open navigation"><Menu size={18}/></button><div><p className="topbar-kicker">{isActiveGroup||'Research'} <span>/</span> EntangleX workspace</p><h1>{title}</h1></div></div><div className="topbar-actions"><SearchBar compact/><button className="command-trigger" onClick={()=>setPalette(true)} aria-label="Open command palette"><Command size={15}/><span>Search commands</span><kbd>⌘K</kbd></button><span className={'connection-indicator '+(health.data?'is-live':'') }><span className="status-dot"/><span>{health.data?'Connected':'Offline'}</span></span><button className="icon-button" onClick={()=>setShowInspector(v=>{const next=!v;localStorage.setItem('qhealth-inspector',next?'visible':'hidden');return next})} aria-label={showInspector?'Hide context inspector':'Show context inspector'}><PanelRight size={16}/></button><button className="icon-button" onClick={()=>setConfig(true)} aria-label="Open theme settings"><Settings2 size={16}/></button>{settings&&<SettingsPopover token={token} setToken={setToken} onApply={()=>{setSessionToken(token);setSettings(false)}} onClose={()=>setSettings(false)}/>}</div></header>
      <div className="research-context-bar"><div className="breadcrumbs"><span>Workspace</span><ChevronRight size={13}/><strong>{title}</strong></div><div className="context-actions"><span className="context-chip"><span className="status-dot is-live"/> Research prototype</span><NavLink className="context-demo-link" to="/demo"><PlayCircle size={13}/> Presentation mode</NavLink></div></div>
      <div className={'research-body '+(!showInspector?'inspector-closed':'')}><main className="research-main">{children}<div className="bottom-status"><span><span className={'status-dot '+(health.data?'is-live':'is-offline')}/>{health.data?'Backend connected':'Backend unavailable'}</span><span>Quantum: {health.data?.quantum.available?'available':'not reported'}</span><span>Jobs: {status.data?.jobs.active??summary.data?.counts.active_jobs??'—'} active</span><span className="ml-auto">Research prototype · no clinical diagnosis</span></div></main><ContextInspector summary={summary.data} health={health.data} status={status.data} jobs={jobs.data} visible={showInspector} onClose={()=>setShowInspector(false)}/></div>
      <footer className="research-footer"><span>EntangleX Q-Health · Hybrid quantum–classical research platform</span><span>Measured outputs only · <NavLink to="/settings">Settings</NavLink></span></footer>
    </div>
    {palette&&<CommandPalette onClose={()=>setPalette(false)}/>}
    {config&&<ConfigDrawer prefs={uiSettings} onChange={patch=>updatePrefs(patch)} onReset={resetPrefs} onClose={()=>setConfig(false)}/>}
  </div>;
}