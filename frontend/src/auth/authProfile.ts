import type {User,UserIdentity} from '@supabase/supabase-js';

export type OAuthProvider='google'|'github';

export type AuthProfile={
  provider:OAuthProvider|null;
  displayName:string|null;
  username:string|null;
  email:string|null;
  avatarUrl:string|null;
  connectedProviders:OAuthProvider[];
};

function text(source:Record<string,unknown>|undefined,...keys:string[]){
  for(const key of keys){
    const value=source?.[key];
    if(typeof value==='string'&&value.trim())return value.trim();
  }
  return null;
}

function supportedProvider(value:string|undefined):OAuthProvider|null{
  return value==='google'||value==='github'?value:null;
}

function identityData(identity:UserIdentity|undefined){
  return identity?.identity_data as Record<string,unknown>|undefined;
}

function identityTime(identity:UserIdentity){
  const value=identity.last_sign_in_at||identity.updated_at||identity.created_at;
  const timestamp=value?Date.parse(value):Number.NaN;
  return Number.isNaN(timestamp)?0:timestamp;
}

export function resolveActiveProvider(
  user:User,
  identities:UserIdentity[],
  requestedProvider:OAuthProvider|null,
):OAuthProvider|null{
  const available=identities
    .map(identity=>supportedProvider(identity.provider))
    .filter((provider):provider is OAuthProvider=>Boolean(provider));
  if(requestedProvider&&available.includes(requestedProvider))return requestedProvider;

  const mostRecent=[...identities]
    .filter(identity=>supportedProvider(identity.provider))
    .sort((left,right)=>identityTime(right)-identityTime(left))[0];
  const recentProvider=supportedProvider(mostRecent?.provider);
  if(recentProvider&&identityTime(mostRecent)>0)return recentProvider;

  const metadataProvider=supportedProvider(
    typeof user.app_metadata?.provider==='string'?user.app_metadata.provider:undefined,
  );
  if(metadataProvider&&available.includes(metadataProvider))return metadataProvider;
  return available[0]||null;
}

export function buildAuthProfile(
  user:User,
  identities:UserIdentity[],
  requestedProvider:OAuthProvider|null,
):AuthProfile{
  const provider=resolveActiveProvider(user,identities,requestedProvider);
  const identity=identities.find(candidate=>candidate.provider===provider);
  const providerData=identityData(identity);
  const userData=user.user_metadata as Record<string,unknown>|undefined;
  const username=provider==='github'
    ? text(providerData,'user_name','username','preferred_username','nickname')
    : text(providerData,'preferred_username','user_name','username','nickname');
  const displayName=provider==='github'
    ? username||text(providerData,'name','full_name')
    : text(providerData,'full_name','name')||username;
  const fallbackName=text(userData,'full_name','name','preferred_username','user_name','username','nickname');
  const avatarUrl=text(providerData,'avatar_url','picture')
    ||text(userData,'avatar_url','picture');
  const connectedProviders=Array.from(new Set(
    identities
      .map(candidate=>supportedProvider(candidate.provider))
      .filter((candidate):candidate is OAuthProvider=>Boolean(candidate)),
  ));

  return {
    provider,
    displayName:displayName||fallbackName||user.email?.split('@')[0]||null,
    username,
    email:user.email||null,
    avatarUrl,
    connectedProviders,
  };
}