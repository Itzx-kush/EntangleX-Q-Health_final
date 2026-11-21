import {useId, useState} from 'react';
import {Link} from 'react-router-dom';
import {Moon, Sun, Monitor, RotateCcw, LogIn} from 'lucide-react';
import {useAuth} from '../auth/AuthProvider';
import {useGuestMigration} from '../auth/GuestMigrationProvider';
import {AccountAvatar, accountEmail, accountName} from '../auth/AccountIdentity';
import {defaultAppearance, updateAppearance, usePreferences, type Appearance} from '../lib/appearance';
import {setSessionToken} from '../lib/api';
import {useQueryClient} from '@tanstack/react-query';
import {PageHeader} from './Shared';
import {Button} from './ui';

function PreferenceSelect<K extends 'sidebar'|'layout'|'density'|'motion'>({field, title, help, options, value}: {
  field: K; title: string; help: string; options: [Appearance[K], string][]; value: Appearance[K];
}) {
  const id = useId();
  return <div className="preference-row"><label htmlFor={id}><strong>{title}</strong><small id={id+'-help'}>{help}</small></label>
    <select className="select" aria-label={title} id={id} aria-describedby={id+'-help'} value={value} onChange={e => updateAppearance({[field]: e.target.value})}>
      {options.map(([key, label]) => <option value={key} key={key}>{label}</option>)}
    </select></div>;
}
const themes = [
  {id:'research', label:'Research light', Icon:Sun}, {id:'dark', label:'Deep research', Icon:Moon}, {id:'system', label:'System', Icon:Monitor},
] as const;
export function SettingsPanel() {
  const prefs = usePreferences();
  const {user, isAuthenticated, signingOut, signOut} = useAuth();
  const {beginUpgrade, hasMigratableState} = useGuestMigration();
  const [token, setToken] = useState('');
  const [notice, setNotice] = useState('');
  const client = useQueryClient();
  return <div className="preference-page">
    <PageHeader eyebrow="Workspace" title="Settings" description="Set up your reading surface, navigation and account."/>
    <section className="preference-panel"><h2>Appearance</h2><p>Choose a theme for this browser. System follows your device.</p>
      <div className="theme-gallery">{themes.map(({id,label,Icon}) => <button key={id} type="button" className="theme-tile" aria-pressed={prefs.theme===id} onClick={()=>updateAppearance({theme:id})}>
        <span aria-hidden="true" className={'theme-sample sample-'+id}><i/><b/><em/></span>
        <span><Icon size={16}/>{label}</span></button>)}</div>
    </section>
    <section className="preference-panel"><h2>Workspace layout</h2>
      <PreferenceSelect field="sidebar" title="Sidebar" help="Choose the frame around your navigation." value={prefs.sidebar} options={[[ 'sidebar','Standard'],['inset','Inset'],['floating','Floating']]}/>
      <PreferenceSelect field="layout" title="Layout" help="Keep labels visible, collapse to icons or open navigation on demand." value={prefs.layout} options={[[ 'default','Full navigation'],['icon','Icons only'],['offcanvas','Off-canvas']]}/>
      <PreferenceSelect field="density" title="Density" help="Adjust spacing in tables and workspace panels." value={prefs.density} options={[[ 'comfortable','Comfortable'],['compact','Compact']]}/>
      <label className="preference-row"><span><strong>Show context inspector</strong><small>View connection, registry and job activity alongside your work.</small></span><input type="checkbox" checked={prefs.inspector} onChange={e=>updateAppearance({inspector:e.target.checked})}/></label>
    </section>
    <section className="preference-panel"><h2>Motion and accessibility</h2>
      <PreferenceSelect field="motion" title="Motion" help="Device requests for reduced motion always take priority." value={prefs.motion} options={[[ 'full','Full motion'],['reduced','Reduced motion']]}/>
      <div className="preference-row"><span><strong>Appearance defaults</strong><small>Restore this browser’s theme, layout, density and motion preferences.</small></span><Button variant="outline" onClick={()=>{updateAppearance(defaultAppearance);setNotice('Appearance preferences reset.')}}><RotateCcw size={15}/>Reset appearance</Button></div>
    </section>
    <section className="preference-panel"><h2>Account and access</h2><div className="preference-row">
      <div className="profile-name">{isAuthenticated?<AccountAvatar user={user} size="medium"/>:<LogIn size={22}/>}<div><strong>{isAuthenticated?accountName(user):'Guest research workspace'}</strong><small>{isAuthenticated?accountEmail(user):'Sign in to keep eligible activity in your personal workspace.'}</small></div></div>
      {isAuthenticated?<div className="flex flex-wrap gap-2"><Link to="/account" className="btn btn-outline">My account</Link><Link to="/my-research" className="btn btn-outline">My Research</Link><Button variant="ghost" disabled={signingOut} onClick={()=>void signOut()}>Sign out</Button></div>:<Button variant="outline" onClick={beginUpgrade}>{hasMigratableState?'Sign in to save':'Go to sign in'}</Button>}
    </div></section>
    <section className="preference-panel"><h2>Connection</h2><form onSubmit={e=>{e.preventDefault();setSessionToken(token);setToken('');void client.invalidateQueries();setNotice('Connection token applied to this session.')}}>
      <label className="field"><span>Optional local API token</span><small>The token is held in memory for this session.</small><input className="input" type="password" autoComplete="off" value={token} onChange={e=>setToken(e.target.value)}/></label><Button variant="outline" type="submit">Apply connection token</Button></form>
    </section><p className="preference-notice" role="status">{notice}</p>
  </div>;
}
