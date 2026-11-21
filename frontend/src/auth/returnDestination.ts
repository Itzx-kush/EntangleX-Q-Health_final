const key='qhealth-oauth-anchor';

export function oauthDestination(href:string) {
  const url=new URL(href);
  for(const param of ['code','error','error_code','error_description']) url.searchParams.delete(param);
  // OAuth providers own the callback fragment. Only remember a normal in-page anchor.
  try {
    sessionStorage.removeItem(key);
    if(/^#[\w-]+$/.test(url.hash)) sessionStorage.setItem(key,JSON.stringify([url.pathname+url.search,url.hash]));
  } catch { /* The route and query also travel in the provider redirect. */ }
  url.hash='';
  return url.toString();
}
export function restoreOAuthAnchor() {
  try {
    const raw=sessionStorage.getItem(key);
    if(!raw)return;
    sessionStorage.removeItem(key);
    const [path,hash]=JSON.parse(raw);
    if(path!==location.pathname+location.search || !/^#[\w-]+$/.test(hash) || location.hash)return;
    history.replaceState(history.state,'',path+hash);
    window.dispatchEvent(new PopStateEvent('popstate'));
  } catch { /* An expired tab preference has no bearing on the restored session. */ }
}
