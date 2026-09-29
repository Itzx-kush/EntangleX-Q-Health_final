import {describe,expect,it} from 'vitest';
import {resolveApiBase} from '../lib/api';

describe('production API base configuration',()=>{
  it('preserves the same-origin /api default for local and proxy deployments',()=>{
    expect(resolveApiBase(undefined,false)).toBe('/api');
    expect(resolveApiBase('/api/',true)).toBe('/api');
  });

  it('accepts the configured Render HTTPS backend and removes trailing slashes',()=>{
    expect(resolveApiBase('https://entanglex-q-health-api.onrender.com/api/',true))
      .toBe('https://entanglex-q-health-api.onrender.com/api');
  });

  it('fails a production build configuration that targets localhost or insecure cross-origin HTTP',()=>{
    expect(()=>resolveApiBase('http://localhost:8000/api',true)).toThrow(/must not target localhost/i);
    expect(()=>resolveApiBase('http://api.example.test/api',true)).toThrow(/must use HTTPS/i);
  });
});
