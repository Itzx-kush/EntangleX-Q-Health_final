import {afterEach, expect, it, vi} from 'vitest';
import {api, setSessionToken} from '../services/api';
afterEach(() => {vi.unstubAllGlobals(); setSessionToken('');});
it('sends an in-memory token without browser persistence', async () => {
  const generatedToken = crypto.randomUUID();
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({status: 'ok'}), {status: 200, headers: {'Content-Type': 'application/json'}}));
  vi.stubGlobal('fetch', fetcher);
  const stored = {...localStorage};
  setSessionToken(generatedToken);
  await api.get('/health');
  expect(new Headers(fetcher.mock.calls[0][1].headers).get('Authorization')).toBe(`Bearer ${generatedToken}`);
  expect({...localStorage}).toEqual(stored);
});
