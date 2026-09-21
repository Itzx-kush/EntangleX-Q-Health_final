import {ChevronRight, Home} from 'lucide-react';
import {Link} from 'react-router-dom';
import {getEnvironmentForPath, getNavigationItemForPath} from '../navigation';

export function WorkspaceContext({pathname}: {pathname: string}) {
  const environment = getEnvironmentForPath(pathname);
  const page = getNavigationItemForPath(pathname);
  return <div className="workspace-context-bar" aria-label="Current workspace location">
    <div className="workspace-breadcrumbs" aria-label="Breadcrumb">
      <Link to="/" aria-label="Research workspace"><Home size={13} aria-hidden="true"/><span>Research workspace</span></Link>
      <ChevronRight size={13} aria-hidden="true"/>
      <span className="workspace-breadcrumb-environment">{environment.name}</span>
      {page && <><ChevronRight size={13} aria-hidden="true"/><span aria-current="page">{page.label}</span></>}
    </div>
    <div className="workspace-context-description"><span>{environment.context}</span>{page?.description && <><span className="context-description-rule"/><span>{page.description}</span></>}</div>
  </div>;
}
