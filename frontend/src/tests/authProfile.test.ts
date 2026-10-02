import {describe,expect,it} from 'vitest';
import type {User,UserIdentity} from '@supabase/supabase-js';
import {buildAuthProfile,resolveActiveProvider} from '../auth/authProfile';

function user(overrides:Partial<User>={}):User{
  return {
    id:'user-1',
    app_metadata:{provider:'google'},
    user_metadata:{full_name:'Google Name',avatar_url:'https://example.com/google.png'},
    aud:'authenticated',
    created_at:'2026-01-01T00:00:00Z',
    email:'account@example.com',
    ...overrides,
  } as User;
}

function identity(provider:'google'|'github',data:Record<string,unknown>,lastSignIn:string):UserIdentity{
  return {
    id:`${provider}-1`,
    identity_id:`${provider}-identity-1`,
    user_id:'user-1',
    identity_data:data,
    provider,
    created_at:'2026-01-01T00:00:00Z',
    updated_at:lastSignIn,
    last_sign_in_at:lastSignIn,
  };
}

describe('provider-aware auth profile',()=>{
  const google=identity('google',{full_name:'Google Name',avatar_url:'https://example.com/google.png'},'2026-01-02T00:00:00Z');
  const github=identity('github',{user_name:'octocat',name:'GitHub Name',avatar_url:'https://example.com/github.png'},'2026-01-03T00:00:00Z');

  it('uses the requested linked provider without replacing the canonical email',()=>{
    const profile=buildAuthProfile(user(),[google,github],'github');
    expect(profile).toMatchObject({
      provider:'github',
      displayName:'octocat',
      username:'octocat',
      email:'account@example.com',
      avatarUrl:'https://example.com/github.png',
      connectedProviders:['google','github'],
    });
  });

  it('restores the most recently used linked identity when no redirect marker remains',()=>{
    expect(resolveActiveProvider(user(),[google,github],null)).toBe('github');
  });

  it('keeps Google profile data for a Google login',()=>{
    const profile=buildAuthProfile(user(),[google,github],'google');
    expect(profile.provider).toBe('google');
    expect(profile.displayName).toBe('Google Name');
    expect(profile.avatarUrl).toBe('https://example.com/google.png');
  });

  it('falls back safely when GitHub has no username or avatar',()=>{
    const sparseGitHub=identity('github',{name:'Fallback Name'},'2026-01-03T00:00:00Z');
    const profile=buildAuthProfile(user({user_metadata:{}}),[sparseGitHub],'github');
    expect(profile.displayName).toBe('Fallback Name');
    expect(profile.username).toBeNull();
    expect(profile.avatarUrl).toBeNull();
  });
});