import {ThemeToggle} from './ThemeToggle';
import {useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {NavLink,useLocation,useNavigate} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {
  Activity,Atom,BarChart3,Brain,Bot,ChevronLeft,ChevronRight,Command,Database,
  FlaskConical,History,KeyRound,LayoutDashboard,Menu,MoreHorizontal,PanelRight,PlayCircle,Search,Settings2,
  ShieldCheck,SlidersHorizontal,UserRound,X,Zap
} from 'lucide-react';
import {qh,setSessionToken} from '../lib/api';
import {Badge,Button} from './ui';
import {useRecordSearch} from './RecordSearch';
import {Brand} from './Brand';
import {connectionState} from '../lib/connection';
import {useDialogFocus} from '../hooks/useDialogFocus';
import {defaultAppearance, updateAppearance, useAppearance, type Appearance as UiSettings} from '../lib/appearance';
import {StatusBadge} from './Shared';
import type {Health,Job,SystemStatus} from '../types/qhealth';
import {VerifiedContextBar} from './VerifiedContextBar';
import {AccountMenu} from '../auth/AccountMenu';
import {useAuth} from '../auth/AuthProvider';
import {GuestMigrationBanner} from '../auth/GuestMigrationBanner';
import {useAi} from '../contexts/AiContext';

type NavEntry={label:string;path:string;icon:typeof Activity};
type NavGroup={label:string;items:NavEntry[]};
type SummaryData={counts:{datasets:number;experiments:number;ready_models:number;active_jobs:number}};
const navGroups:NavGroup[]=[
  {label:'Research',items:[
    {label:'Overview',path:'/',icon:LayoutDashboard},
    {label:'Datasets',path:'/datasets',icon:Database},
    {label:'Data quality',path:'/quality',icon:ShieldCheck},
  ]},
  {label:'Pipeline',items:[
    {label:'Preprocessing',path:'/preprocessing',icon:SlidersHorizontal},
    {label:'Feature selection',path:'/features',icon:BarChart3},
    {label:'PCA / dimensions',path:'/pca',icon:BarChart3},
  ]},
  {label:'Modeling',items:[
    {label:'Training',path:'/training',icon:PlayCircle},
    {label:'Comparison',path:'/comparison',icon:BarChart3},
    {label:'Robustness Lab',path:'/robustness',icon:ShieldCheck},
  ]},
  {label:'Quantum',items:[
    {label:'Quantum Lab',path:'/quantum',icon:Atom},
  ]},
  {label:'Interpretation',items:[
    {label:'Explainability',path:'/explainability',icon:Brain},
    {label:'Research prediction',path:'/prediction',icon:Zap},
  ]},
  {label:'Studio',items:[
    {label:'AI Assistant',path:'/ai',icon:Bot},
    {label:'Experiment registry',path:'/experiments',icon:FlaskConical},
    {label:'SIH Demo Center',path:'/demo',icon:PlayCircle},
  ]},
  {label:'Systems',items:[
    {label:'Redis Lab',path:'/redis',icon:Database},
  ]},
];

const pageNames:Record<string,string>=Object.fromEntries(
  navGroups.flatMap(group=>group.items.map(item=>[item.path,item.label]))
);
pageNames['/account']='My account';
pageNames['/my-research']='My Research';
pageNames['/settings']='Settings';
pageNames['/my-research/reports']='Saved reports';

const navByPath=(path:string)=>navGroups.flatMap(group=>group.items).find(item=>item.path===path)!;
const mobilePrimaryNav:NavEntry[]=[navByPath('/'),navByPath('/datasets'),navByPath('/quantum'),navByPath('/experiments')];

export const isMac = typeof navigator !== 'undefined' && /mac/i.test(navigator.userAgent || '');
export const shortcutLabel = isMac ? '⌘K' : 'Ctrl+K';

function SettingsPopover({token,setToken,onApply,onClose}:{token:string;setToken:(v:string)=>void;onApply:()=>void;onClose:()=>void}){
  const focus = useDialogFocus<HTMLDivElement>();
  return <div ref={focus} className="shell-popover settings-panel" role="dialog" aria-label="Connection settings">
    <div className="flex items-start justify-between gap-3"><div><p className="eyebrow">Connection</p><h2 className="section-title mt-1">Session settings</h2></div><button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close settings"><X size={15}/></button></div>
    <label className="field mt-4"><span>Optional local API token</span><input className="input" type="password" value={token} onChange={e=>setToken(e.target.value)} placeholder="Bearer token"/><small>Kept in memory only. Never stored in local storage.</small></label>
    <Button className="mt-3 w-full" onClick={onApply}>Apply connection token</Button>
    <NavLink className="btn btn-outline mt-2 w-full" to="/settings" onClick={onClose}><Settings2 size={14}/>Open settings center</NavLink>
  </div>;
}

function fuzzyMatch(query:string,value:string){
  if(!query)return true;
  let cursor=0;
  for(const character of query.toLowerCase()){
    cursor=value.toLowerCase().indexOf(character,cursor);
    if(cursor===-1)return false;
    cursor+=1;
  }
  return true;
}

function CommandPalette({onClose}:{onClose:()=>void}){
  const navigate=useNavigate(); const [query,setQuery]=useState(''); const [activeIndex,setActiveIndex]=useState(0);
  const {isAuthenticated}=useAuth();
  const inputRef=useRef<HTMLInputElement|null>(null);
  const dialogRef=useRef<HTMLDivElement|null>(null);
  const previousFocusRef=useRef<HTMLElement|null>(null);
  const applyLocal=(key:string,value:string)=>{localStorage.setItem(key,value);window.dispatchEvent(new Event('qhealth-settings-changed'));onClose()};
  const toggleLocal=(key:string,on:string,off:string)=>applyLocal(key,localStorage.getItem(key)===on?off:on);
  const commands=useMemo(()=>[
    ...navGroups.flatMap(group=>group.items.map(item=>({label:`Open ${item.label}`,hint:'Navigation',keywords:[group.label,item.label],run:()=>navigate(item.path)}))),
    {label:'Launch SIH Demo',hint:'Navigation',keywords:['presentation','demo'],run:()=>navigate('/demo')},
    ...(isAuthenticated?[{label:'Open My Account',hint:'Account',keywords:['profile'],run:()=>navigate('/account')}]:[]),
    ...(isAuthenticated?[{label:'Open My Research',hint:'Account',keywords:['history','reports'],run:()=>navigate('/my-research')}]:[]),
    {label:'Open Settings',hint:'Workspace',keywords:['preferences','appearance'],run:()=>navigate('/settings')},
    {label:'Toggle sidebar',hint:'Workspace',keywords:['navigation','collapse'],run:()=>toggleLocal('qhealth-layout','icon','default')},
    {label:'Toggle compact density',hint:'Workspace',keywords:['spacing'],run:()=>toggleLocal('qhealth-density','compact','comfortable')},
    {label:'Toggle reduced motion',hint:'Workspace',keywords:['accessibility','motion'],run:()=>toggleLocal('qhealth-motion','reduced','full')},
    {label:'Toggle light / dark theme',hint:'Workspace',keywords:['appearance','theme'],run:()=>toggleLocal('qhealth-theme','dark','research')},
    {label:'Show context inspector',hint:'Workspace',keywords:['live status','jobs'],run:()=>applyLocal('qhealth-inspector','visible')},
    {label:'Hide context inspector',hint:'Workspace',keywords:['live status','jobs'],run:()=>applyLocal('qhealth-inspector','hidden')},
  ],[isAuthenticated,navigate]);
  const records = useRecordSearch(query);
  const filtered = [...commands.filter(command => fuzzyMatch(query, [command.label, command.hint, ...command.keywords].join(' '))),
    ...records.map(record => ({...record, run: () => navigate(record.path)}))];
  useEffect(()=>setActiveIndex(0),[query]);
  useEffect(()=>{
    previousFocusRef.current=document.activeElement instanceof HTMLElement?document.activeElement:null;
    inputRef.current?.focus();
    return()=>previousFocusRef.current?.focus({preventScroll:true});
  },[]);
  useEffect(()=>{
    const active=dialogRef.current?.querySelector<HTMLElement>(`#command-option-${activeIndex}`);
    active?.scrollIntoView?.({block:'nearest'});
  },[activeIndex]);
  useEffect(()=>{const handler=(e:KeyboardEvent)=>{
    if(e.key==='Tab'){
      const focusable=dialogRef.current?.querySelectorAll<HTMLElement>('button,input,[href],select,textarea,[tabindex]:not([tabindex="-1"])');
      if(!focusable?.length)return;
      const first=focusable[0]; const last=focusable[focusable.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
      return;
    }
    if(e.key==='ArrowDown'){e.preventDefault();setActiveIndex(i=>Math.min(i+1,Math.max(filtered.length-1,0)))}
    else if(e.key==='ArrowUp'){e.preventDefault();setActiveIndex(i=>Math.max(i-1,0))}
    else if(e.key==='Enter'&&filtered[activeIndex]){e.preventDefault();filtered[activeIndex].run();onClose()}
  };window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)},[activeIndex,filtered,onClose]);
  return <div className="command-overlay" role="presentation" onMouseDown={onClose}>
    <div ref={dialogRef} className="command-dialog" role="dialog" aria-modal="true" aria-label="Command palette" onMouseDown={e=>e.stopPropagation()}>
      <div className="command-search"><Search size={17}/><input ref={inputRef} autoFocus value={query} onChange={e=>setQuery(e.target.value)} role="combobox" aria-expanded="true" placeholder="Search pages, actions and records…" aria-label="Search commands" aria-controls="command-results" aria-activedescendant={filtered[activeIndex]?`command-option-${activeIndex}`:undefined}/><kbd>ESC</kbd></div>
      <div id="command-results" className="command-list" role="listbox" aria-label="Available commands">{filtered.map((command,index)=><div className="command-entry" role="presentation" key={command.hint + command.label + ('id' in command ? command.id : '')}>{(index===0||filtered[index-1]?.hint!==command.hint)&&<p className="command-group-label">{command.hint}</p>}<button id={`command-option-${index}`} role="option" aria-selected={activeIndex===index} className={activeIndex===index?'is-highlighted':''} onMouseEnter={()=>setActiveIndex(index)} onClick={()=>{command.run();onClose()}}><span className="command-icon"><Command size={14}/></span><span className="min-w-0 flex-1"><strong className="block">{command.label}</strong><small className="muted">{command.hint}</small></span><ChevronRight size={14} className="ml-auto muted"/></button></div>)}{!filtered.length&&<p className="p-6 text-center text-sm muted">No command matches this search.</p>}</div>
      <div className="command-footer"><span><kbd>↑↓</kbd> Navigate</span><span><kbd>Enter</kbd> Open</span><span><kbd>Esc</kbd> Close</span></div>
    </div>
  </div>;
}

function ConfigDrawer({prefs,onChange,onReset,onClose}:{prefs:UiSettings;onChange:(patch:Partial<UiSettings>)=>void;onReset:()=>void;onClose:()=>void}){
  const focus = useDialogFocus<HTMLElement>();
  const choice=(label:string,active:boolean,patch:Partial<UiSettings>)=>
    <button type="button" className={'config-choice '+(active?'is-selected':'')} onClick={()=>onChange(patch)} aria-pressed={active}>{label}</button>;
  return <div className="config-overlay" role="presentation" onMouseDown={onClose}>
    <aside ref={focus} className="config-drawer" role="dialog" aria-modal="true" aria-label="Theme and layout settings" onMouseDown={e=>e.stopPropagation()}>
      <div className="config-drawer-head">
        <div><p className="eyebrow">Workspace</p><h2>Theme &amp; layout</h2><p className="muted">Customize the research shell without changing the research workflow.</p></div>
        <button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close theme and layout"><X size={15}/></button>
      </div>
      <div className="config-section"><p className="config-section-title">Theme</p><div className="config-choice-grid">
        {choice('Research light',prefs.theme==='research',{theme:'research'})}
        {choice('Deep research',prefs.theme==='dark',{theme:'dark'})}
        {choice('System',prefs.theme==='system',{theme:'system'})}
      </div></div>
      <div className="config-section"><p className="config-section-title">Sidebar</p><div className="config-choice-grid">
        {choice('Standard',prefs.sidebar==='sidebar',{sidebar:'sidebar'})}
        {choice('Floating',prefs.sidebar==='floating',{sidebar:'floating'})}
        {choice('Inset',prefs.sidebar==='inset',{sidebar:'inset'})}
      </div></div>
      <div className="config-section"><p className="config-section-title">Layout</p><div className="config-choice-grid">
        {choice('Default',prefs.layout==='default',{layout:'default'})}
        {choice('Compact',prefs.layout==='icon',{layout:'icon'})}
        {choice('Off-canvas',prefs.layout==='offcanvas',{layout:'offcanvas'})}
      </div></div>
      <div className="config-section"><p className="config-section-title">Density</p><div className="config-choice-grid">
        {choice('Comfortable',prefs.density==='comfortable',{density:'comfortable'})}
        {choice('Compact',prefs.density==='compact',{density:'compact'})}
      </div></div>
      <div className="config-section"><p className="config-section-title">Motion</p><div className="config-choice-grid">
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

function ContextInspector({summary,health,status,jobs,connection,retry,visible,onClose}:{connection:ReturnType<typeof connectionState>;retry:()=>void;summary:SummaryData|undefined;health:Health|undefined;status:SystemStatus|undefined;jobs:Job[]|undefined;visible:boolean;onClose:()=>void}){
  if(!visible)return null;
  const active=(jobs||[]).filter(job=>['queued','running','cancel_requested'].includes(job.status));
  return <aside className="context-inspector" aria-label="Research context inspector">
    <div className="inspector-head"><div><p className="eyebrow">Live context</p><h2>Workspace state</h2></div><button className="btn btn-ghost px-2" onClick={onClose} aria-label="Close context inspector"><X size={15}/></button></div>
    <div className="inspector-card"><div className="inspector-label"><Activity size={13}/> System status</div><div className="inspector-status"><span className={'status-dot '+('is-'+connection.tone)}/><strong>{connection.label}</strong></div><p className="inspector-copy">{connection.detail}</p>{connection.tone!=='live'&&<Button variant="outline" onClick={retry}>Retry connection</Button>}</div>
    <div className="inspector-card"><div className="inspector-label"><Database size={13}/> Registry</div><dl className="inspector-facts"><div><dt>Datasets</dt><dd>{summary?.counts.datasets??'—'}</dd></div><div><dt>Experiments</dt><dd>{summary?.counts.experiments??'—'}</dd></div><div><dt>Ready models</dt><dd>{summary?.counts.ready_models??'—'}</dd></div><div><dt>Storage</dt><dd>{status?.storage_available?'Ready':'Not reported'}</dd></div></dl></div>
    <div className="inspector-card"><div className="inspector-label"><Zap size={13}/> Quantum boundary</div><div className="inspector-status"><Badge tone={health?.quantum?.available?'purple':'amber'}>{health?.quantum?.available?'Available':health?'Unavailable':'Not reported'}</Badge></div><p className="inspector-copy">{health?.quantum?.execution||'Capability is reported by the backend, not assumed by the UI.'}</p></div>
    <div className="inspector-card"><div className="inspector-label"><PlayCircle size={13}/> Active jobs <span className="ml-auto">{jobs ? active.length : '—'}</span></div>{active.length?<ul className="inspector-jobs">{active.slice(0,4).map(job=><li key={job.id}><StatusBadge value={job.status}/><span>{job.state}</span></li>)}</ul>:<p className="inspector-copy">{jobs?'No queued or running jobs.':'Job activity has not been reported.'}</p>}</div>
    <p className="inspector-note"><ShieldCheck size={13}/> Metrics, status and quantum availability are shown only when returned by the live backend.</p>
  </aside>;
}

function MobileBottomNavigation({onMore}:{onMore:()=>void}){
  return <nav className="mobile-bottom-nav" aria-label="Mobile navigation">
    <div className="mobile-bottom-nav-inner">
      {mobilePrimaryNav.map(({label,path,icon:Icon})=><NavLink key={path} end={path==='/'||path==='/experiments'} to={path} className={({isActive})=>'mobile-nav-link '+(isActive?'active':'')} aria-label={label}>
        <Icon size={18}/><span>{label==='Quantum Lab'?'Quantum':label}</span>
      </NavLink>)}
      <button className="mobile-nav-link" type="button" onClick={onMore} aria-label="Open more navigation">
        <MoreHorizontal size={18}/><span>More</span>
      </button>
    </div>
  </nav>;
}

function MobileMoreSheet({onClose}:{onClose:()=>void}){
  const {isAuthenticated}=useAuth();
  const focus = useDialogFocus<HTMLElement>();
  return <div className="mobile-more-overlay" role="presentation" onMouseDown={onClose}>
    <aside ref={focus} className="mobile-more-sheet" role="dialog" aria-modal="true" aria-labelledby="mobile-more-title" onMouseDown={e=>e.stopPropagation()}>
      <div className="mobile-more-head">
        <div><p className="eyebrow">EntangleX Q-Health</p><h2 id="mobile-more-title">Research navigation</h2><p className="muted">Open any existing workspace route.</p></div>
        <button className="btn btn-ghost px-2" type="button" onClick={onClose} aria-label="Close more navigation"><X size={17}/></button>
      </div>
      <nav className="mobile-more-groups">
        {navGroups.map(group=><div className="mobile-more-group" key={group.label}>
          <p className="sidebar-label">{group.label}</p>
          {group.items.map(({label,path,icon:Icon})=><NavLink key={path} end={path==='/'||path==='/experiments'} to={path} onClick={onClose} className={({isActive})=>'mobile-more-link '+(isActive?'active':'')}>
            <Icon size={16}/><span>{label}</span><ChevronRight size={14} className="ml-auto"/>
          </NavLink>)}
        </div>)}
        <div className="mobile-more-group">
          <p className="sidebar-label">Workspace</p>
          {isAuthenticated&&<NavLink to="/my-research" onClick={onClose} className={({isActive})=>'mobile-more-link '+(isActive?'active':'')}><History size={16}/><span>My Research</span><ChevronRight size={14} className="ml-auto"/></NavLink>}
          {isAuthenticated&&<NavLink to="/account" onClick={onClose} className={({isActive})=>'mobile-more-link '+(isActive?'active':'')}><UserRound size={16}/><span>My account</span><ChevronRight size={14} className="ml-auto"/></NavLink>}
          <NavLink to="/settings" onClick={onClose} className={({isActive})=>'mobile-more-link '+(isActive?'active':'')}><Settings2 size={16}/><span>Settings</span><ChevronRight size={14} className="ml-auto"/></NavLink>
        </div>
      </nav>
    </aside>
  </div>;
}

export function ResearchShell({children}:{children:ReactNode}){
  const {pathname}=useLocation();
  const {isAuthenticated}=useAuth();
  const {setPopupOpen}=useAi();
  const [mobile,setMobile]=useState(false); const [mobileMore,setMobileMore]=useState(false); const [palette,setPalette]=useState(false); const [settings,setSettings]=useState(false); const [config,setConfig]=useState(false);
  const [isMobileViewport,setIsMobileViewport]=useState(false);
  const uiSettings=useAppearance();
  const showInspector=uiSettings.inspector;
  const setShowInspector=(inspector:boolean)=>updateAppearance({inspector});
  const [token,setToken]=useState('');
  const sidebarFocus=useDialogFocus<HTMLElement>(mobile);
  const summary=useQuery({queryKey:['summary'],queryFn:qh.summary,refetchInterval:10000});
  const health=useQuery({queryKey:['health'],queryFn:qh.health,refetchInterval:15000});
  const jobs=useQuery({queryKey:['jobs'],queryFn:qh.jobs,refetchInterval:10000});
  const status=useQuery({queryKey:['system-status'],queryFn:qh.systemStatus,refetchInterval:15000});
  const connection=connectionState(health,status);
  const retryConnection=()=>{void health.refetch();void status.refetch();void jobs.refetch();void summary.refetch()};
  const title=pageNames[pathname]|| (pathname.startsWith('/experiments/')?'Experiment detail':pathname.startsWith('/my-research/reports/')?'Saved report':'Research workspace');
  const isActiveGroup=useMemo(()=>navGroups.find(group=>group.items.some(item=>item.path===pathname))?.label,[pathname]);

  useEffect(()=>{const handler=(e:KeyboardEvent)=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();setPalette(true)}if(e.key==='Escape'){setPalette(false);setSettings(false);setConfig(false);setMobileMore(false);setMobile(false)}};window.addEventListener('keydown',handler);return()=>window.removeEventListener('keydown',handler)},[]);
  useEffect(()=>{
    if(!window.matchMedia)return;
    const media=window.matchMedia('(max-width: 767px)');
    const update=()=>setIsMobileViewport(media.matches);
    update();
    media.addEventListener?.('change',update);
    return()=>media.removeEventListener?.('change',update);
  },[]);
  useEffect(()=>{setMobile(false);setMobileMore(false);setSettings(false)},[pathname]);
  useEffect(()=>{
    if(mobile||mobileMore||palette||config){
      const prev=document.body.style.overflow;
      document.body.style.overflow='hidden';
      return()=>{document.body.style.overflow=prev;};
    }
  },[mobile,mobileMore,palette,config]);
  const updatePrefs=updateAppearance;
  const resetPrefs=()=>updateAppearance(defaultAppearance);
  const isLayer3Analysis = ['/datasets','/quality','/preprocessing','/features','/pca'].includes(pathname);

  return <div className={'research-shell '+(uiSettings.layout==='icon'?'is-collapsed ':'')+(uiSettings.layout==='offcanvas'?'is-offcanvas':'')}>
    <a className="qx-skip" href="#workspace-content">Skip to research content</a>
    <aside ref={sidebarFocus}
      className={'research-sidebar variant-'+uiSettings.sidebar+' '+(uiSettings.layout==='icon'?'is-collapsed ':'')+(mobile?'is-mobile-open ':'')+(uiSettings.layout==='offcanvas'?'is-offcanvas':'')}
      aria-label="Primary navigation"
      role={mobile ? "dialog" : undefined}
      aria-modal={mobile ? true : undefined}
    >
      <div className="sidebar-brand"><NavLink to="/" aria-label="EntangleX Q-Health Overview"><Brand/></NavLink><button className="sidebar-close btn btn-ghost" onClick={()=>setMobile(false)} aria-label="Close navigation"><X size={16}/></button></div>
      <nav className="sidebar-nav" aria-label="Research workspace navigation">{navGroups.map(group=><div className={'sidebar-group '+(isActiveGroup===group.label?'is-current':'')} key={group.label}><p className="sidebar-label">{group.label}</p>{group.items.map(({label,path,icon:Icon})=><NavLink key={path} end={path==='/'||path==='/experiments'} to={path} aria-label={label} title={label} className={({isActive})=>'sidebar-link '+(isActive?'active is-active':'')}><Icon size={16} aria-hidden="true"/><span>{label}</span></NavLink>)}</div>)}</nav>
      <div className="sidebar-bottom"><p className="sidebar-label workspace-label">Workspace</p>{isAuthenticated&&<NavLink to="/my-research" aria-label="My Research" title="My Research" className={({isActive})=>'sidebar-link '+(isActive?'active is-active':'')}><History size={16} aria-hidden="true"/><span>My Research</span></NavLink>}{isAuthenticated&&<NavLink to="/account" aria-label="My account" title="My account" className={({isActive})=>'sidebar-link '+(isActive?'active':'')}><UserRound size={16} aria-hidden="true"/><span>My account</span></NavLink>}<NavLink to="/settings" aria-label="Settings" title="Settings" className={({isActive})=>'sidebar-link '+(isActive?'active':'')}><Settings2 size={16} aria-hidden="true"/><span>Settings</span></NavLink><button className="collapse-button" onClick={()=>updatePrefs({layout:uiSettings.layout==='icon'?'default':'icon'})} aria-label={uiSettings.layout==='icon'?'Expand sidebar':'Collapse sidebar'}>{uiSettings.layout==='icon'?<ChevronRight size={15}/>:<><ChevronLeft size={15}/><span>Collapse sidebar</span></>}</button></div>
    </aside>
    {mobile&&<button className="navigation-scrim" tabIndex={-1} aria-hidden="true" onClick={()=>setMobile(false)}/>}
      <div className="research-workspace">
      <header className="research-topbar"><div className="topbar-left"><NavLink to="/" className="mobile-brand-mark" aria-label="EntangleX Q-Health Overview"><img src="/entanglex-mark.svg" alt="" aria-hidden="true"/></NavLink><button className="mobile-menu btn btn-ghost" onClick={()=>{if(isMobileViewport)setMobileMore(true);else setMobile(v=>!v)}} aria-label={mobile||mobileMore?"Close navigation":"Open navigation"} aria-expanded={mobile||mobileMore}><Menu size={18} aria-hidden="true"/></button><div><p className="topbar-kicker">{isActiveGroup||'Research'} <span>/</span> {isAuthenticated?'Personal workspace':'Guest research'}</p><strong className="workspace-location">{title}</strong></div></div><div className="topbar-actions"><button className="command-trigger" onClick={()=>setPalette(true)} aria-keyshortcuts="Control+k Meta+k" title="Search workspace"><Command size={15} aria-hidden="true"/><span>Search workspace</span><kbd>{shortcutLabel}</kbd><b className="sr-only">Open command palette</b></button><button className="icon-button" onClick={()=>setPopupOpen(true)} aria-label="Open EntangleX AI Assistant" title="Open EntangleX AI Assistant"><Bot size={16} aria-hidden="true"/></button><button className={'connection-indicator is-'+connection.tone} title={connection.detail} onClick={()=>setShowInspector(!showInspector)} aria-label={connection.label+' · '+(showInspector?'Hide context inspector':'Show context inspector')} aria-expanded={showInspector}><span className="status-dot"/><span>{connection.label}</span></button><button className="icon-button" onClick={()=>setSettings(true)} aria-label="Connection settings" title="Connection settings"><KeyRound size={16} aria-hidden="true"/></button><button className="icon-button" onClick={()=>setConfig(true)} aria-label="Open theme and layout settings"><Settings2 size={16} aria-hidden="true"/></button><ThemeToggle/><AccountMenu/>{settings&&<SettingsPopover token={token} setToken={setToken} onApply={()=>{setSessionToken(token);setToken('');setSettings(false);retryConnection()}} onClose={()=>setSettings(false)}/>}</div></header>
      <div className={'research-body '+(isLayer3Analysis?'layer3-analytic-workspace ':'')+(!showInspector?'inspector-closed':'')}><main id="workspace-content" tabIndex={-1} className="research-main"><VerifiedContextBar/><GuestMigrationBanner/>{children}</main><ContextInspector summary={summary.data} health={health.data} status={status.data} jobs={jobs.data} connection={connection} retry={retryConnection} visible={showInspector} onClose={()=>setShowInspector(false)}/></div>
      <footer className="research-footer"><span>EntangleX Q-Health · Hybrid quantum–classical research platform</span><span>Research use only · <NavLink to="/settings">Settings</NavLink></span></footer>
    </div>
    {isMobileViewport&&<MobileBottomNavigation onMore={()=>setMobileMore(true)}/>}
    {palette&&<CommandPalette onClose={()=>setPalette(false)}/>}
    {config&&<ConfigDrawer prefs={uiSettings} onChange={patch=>updatePrefs(patch)} onReset={resetPrefs} onClose={()=>setConfig(false)}/>}
    {isMobileViewport&&mobileMore&&<MobileMoreSheet onClose={()=>setMobileMore(false)}/>}
  </div>;
}
