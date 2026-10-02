import {CalendarClock,CheckCircle2,Github,KeyRound,LogIn,LogOut,Palette,ShieldCheck,UserRound} from 'lucide-react';
import {Link} from 'react-router-dom';
import {AccountAvatar,accountEmail,accountName,accountProvider} from '../auth/AccountIdentity';
import {useAuth} from '../auth/AuthProvider';
import {useGuestMigration} from '../auth/GuestMigrationProvider';
import {PageHeader} from '../components/Shared';
import {Badge,Button,Card} from '../components/ui';
import {RecentResearchPreview} from '../research/ResearchHistoryPage';

function dateLabel(value:string|undefined){
  if(!value)return 'Unavailable';
  const date=new Date(value);
  return Number.isNaN(date.getTime())?'Unavailable':new Intl.DateTimeFormat(undefined,{dateStyle:'medium'}).format(date);
}

export function AccountPage(){
  const {user,profile,isAuthenticated,error,signingOut,signOut}=useAuth();
  const {beginUpgrade,hasMigratableState}=useGuestMigration();

  if(!isAuthenticated)return <div>
    <PageHeader eyebrow="Workspace identity" title="Guest research workspace" description="You are using the full current EntangleX research prototype without an account."/>
    <div className="account-guest-panel">
      <div className="account-guest-icon"><UserRound size={24}/></div>
      <div><h2>Guest mode is active</h2><p>Your current prototype workflow remains available. Sign in when you want to establish a personal EntangleX identity; persistent research records are not enabled yet.</p></div>
      <Button onClick={beginUpgrade}><LogIn size={15}/>{hasMigratableState?'Sign in to save this work':'Go to sign in'}</Button>
    </div>
  </div>;

  const theme=localStorage.getItem('qhealth-theme')==='dark'?'Deep research':'Research light';
  const density=localStorage.getItem('qhealth-density')==='compact'?'Compact':'Comfortable';
  const motion=localStorage.getItem('qhealth-motion')==='reduced'?'Reduced':'Full';

  return <div className="account-page">
    <PageHeader
      eyebrow="Personal workspace"
      title="My account"
      description="Your authenticated EntangleX identity, session status, and local workspace preferences."
      actions={<Button variant="outline" disabled={signingOut} onClick={()=>void signOut()}><LogOut size={15}/>{signingOut?'Signing out…':'Sign out'}</Button>}
    />

    {error&&<div className="account-page-error" role="alert"><ShieldCheck size={17}/><span><strong>Account action unavailable</strong>{error}</span></div>}

    <section className="account-identity-panel" aria-labelledby="account-identity-title">
      <AccountAvatar user={user} profile={profile} size="large"/>
      <div className="account-identity-copy">
        <span className="account-kicker">Authenticated identity</span>
        <h2 id="account-identity-title">{accountName(user,profile)}</h2>
        <p>{accountEmail(user,profile)}</p>
        <div><Badge tone="green">Signed in</Badge><Badge tone="blue">{profile?.provider==='github'&&<Github size={12}/>} {accountProvider(user,profile)}</Badge></div>
      </div>
      <div className="account-session-seal"><CheckCircle2 size={20}/><span><strong>Session active</strong><small>Managed securely by Supabase Auth</small></span></div>
    </section>

    <div className="account-content-grid">
      <Card title="Account identity" description="Information supplied by your active authenticated account.">
        <dl className="account-details">
          <div><dt><UserRound size={15}/>Display name</dt><dd>{accountName(user,profile)}</dd></div>
          {profile?.username&&<div><dt>{profile.provider==='github'?<Github size={15}/>:<UserRound size={15}/>}Provider username</dt><dd>@{profile.username.replace(/^@/,'')}</dd></div>}
          <div><dt><KeyRound size={15}/>Email</dt><dd>{accountEmail(user,profile)}</dd></div>
          <div><dt>{profile?.provider==='github'?<Github size={15}/>:<ShieldCheck size={15}/>}Authentication provider</dt><dd>{accountProvider(user,profile)}</dd></div>
          <div><dt><ShieldCheck size={15}/>Connected accounts</dt><dd>{profile?.connectedProviders.length?profile.connectedProviders.map(provider=>provider==='github'?'GitHub':'Google').join(' · '):accountProvider(user,profile)}</dd></div>
          <div><dt><CalendarClock size={15}/>Account established</dt><dd>{dateLabel(user?.created_at)}</dd></div>
        </dl>
        <details className="account-technical-details">
          <summary>Technical account details</summary>
          <div><span>EntangleX user ID</span><code>{user?.id}</code></div>
          <div><span>Email verification</span><strong>{user?.email_confirmed_at?'Verified':'Not reported'}</strong></div>
        </details>
      </Card>

      <Card title="Interface preferences" description="These settings remain local to this browser.">
        <div className="account-preference-list">
          <div><Palette size={16}/><span><strong>Theme</strong><small>{theme}</small></span></div>
          <div><span className="account-density-icon" aria-hidden="true">Aa</span><span><strong>Density</strong><small>{density}</small></span></div>
          <div><span className="account-motion-icon" aria-hidden="true">↝</span><span><strong>Motion</strong><small>{motion}</small></span></div>
        </div>
        <Link className="btn btn-outline mt-4" to="/settings">Open workspace preferences</Link>
      </Card>
    </div>

    <section className="account-research-section">
      <div className="account-research-heading"><div><span className="account-kicker">My Research</span><h2>Recent activity</h2><p>Meaningful research actions saved privately to this authenticated workspace.</p></div><Link className="btn btn-outline" to="/my-research">Open My Research</Link></div>
      <RecentResearchPreview/>
    </section>

    <section className="account-foundation-note">
      <div><span className="account-kicker">Workspace foundation</span><h2>Your account is ready for the next research layer.</h2></div>
      <p>Research history and user-owned records are not stored in this phase. The existing EntangleX backend remains the source of truth for current research workflows.</p>
    </section>
  </div>;
}
