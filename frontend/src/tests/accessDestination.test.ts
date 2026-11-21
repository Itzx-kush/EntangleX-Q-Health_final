import {afterEach,describe,expect,it} from 'vitest';
import {oauthDestination,restoreOAuthAnchor} from '../auth/returnDestination';
afterEach(()=>{sessionStorage.clear();history.replaceState(null,'','/')});
describe('OAuth return destination',()=>{
  it('preserves a nested route, a query and the bookmarked panel across the provider callback',()=>{
    const path='/experiments/abc?mode=research';
    expect(oauthDestination(location.origin+path+'&code=transient#diagnostics')).toBe(location.origin+path);
    history.replaceState(null,'',path);restoreOAuthAnchor();
    expect(location.hash).toBe('#diagnostics');expect(sessionStorage.getItem('qhealth-oauth-anchor')).toBeNull();
  });
  it('does not restore a different route or retain a callback fragment',()=>{
    oauthDestination(location.origin+'/demo#active');history.replaceState(null,'','/quantum');restoreOAuthAnchor();
    expect(location.hash).toBe('');oauthDestination(location.origin+'/demo#access_token=example');
    expect(sessionStorage.getItem('qhealth-oauth-anchor')).toBeNull();
  });
});
