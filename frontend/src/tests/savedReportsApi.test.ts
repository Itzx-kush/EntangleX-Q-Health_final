import {afterEach,describe,expect,it,vi} from 'vitest';
import {qh} from '../lib/api';

afterEach(()=>vi.unstubAllGlobals());

describe('saved research report API contract',()=>{
  it('sends the Supabase access token to the authenticated saved-report request',async()=>{
    const fetchMock=vi.fn().mockResolvedValue(new Response('[]',{status:200,headers:{'Content-Type':'application/json'}}));
    vi.stubGlobal('fetch',fetchMock);
    await qh.savedResearchReports('supabase-session-token','experiment-1');
    const [url,options]=fetchMock.mock.calls[0];
    expect(String(url)).toContain('/me/research-reports?experiment_id=experiment-1');
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer supabase-session-token');
  });

  it('sends only the experiment identifier when saving',async()=>{
    const fetchMock=vi.fn().mockResolvedValue(new Response('{}',{status:201,headers:{'Content-Type':'application/json'}}));
    vi.stubGlobal('fetch',fetchMock);
    await qh.saveResearchReport('experiment-1','supabase-session-token');
    const [,options]=fetchMock.mock.calls[0];
    expect(options.method).toBe('POST');
    expect(JSON.parse(options.body)).toEqual({experiment_id:'experiment-1'});
    expect(options.body).not.toContain('user_id');
  });
});
