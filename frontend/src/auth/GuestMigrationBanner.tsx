import {CheckCircle2,History,RefreshCw,X} from 'lucide-react';
import {Link} from 'react-router-dom';
import {Button} from '../components/ui';
import {useGuestMigration} from './GuestMigrationProvider';

export function GuestMigrationBanner(){
  const {migration,retryMigration,dismissMigration}=useGuestMigration();
  if(!migration||!['importing','completed','failed'].includes(migration.status))return null;

  if(migration.status==='importing')return <div className="guest-migration-banner is-importing" role="status" aria-live="polite" aria-busy="true">
    <RefreshCw size={17} className="guest-migration-spinner" aria-hidden="true"/>
    <div><strong>Adding your research to your account…</strong><span>Your guest session remains available until saving is confirmed.</span></div>
  </div>;

  if(migration.status==='failed')return <div className="guest-migration-banner is-failed" role="alert">
    <History size={17} aria-hidden="true"/>
    <div><strong>Your research session is still available.</strong><span>We couldn’t save it to your account yet. {migration.error}</span></div>
    <Button variant="outline" onClick={retryMigration}><RefreshCw size={14}/>Retry</Button>
  </div>;

  return <div className="guest-migration-banner is-complete" role="status" aria-live="polite">
    <CheckCircle2 size={17} aria-hidden="true"/>
    <div><strong>Your research has been saved to your account.</strong><span>The imported session is available in My Research.</span></div>
    <Link className="btn btn-outline" to="/my-research">Open My Research</Link>
    <button type="button" className="guest-migration-dismiss" onClick={dismissMigration} aria-label="Dismiss migration confirmation"><X size={15}/></button>
  </div>;
}