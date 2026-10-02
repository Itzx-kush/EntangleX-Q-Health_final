import {useEffect,useState} from 'react';
import type {User} from '@supabase/supabase-js';
import type {AuthProfile} from './authProfile';

function metadataText(user:User|undefined,key:string){
  const value=user?.user_metadata?.[key];
  return typeof value==='string'&&value.trim()?value.trim():null;
}

export function accountName(user:User|undefined|null,profile?:AuthProfile|null){
  if(!user)return 'Guest researcher';
  return profile?.displayName
    ||metadataText(user,'full_name')
    ||metadataText(user,'name')
    ||metadataText(user,'preferred_username')
    ||user.email?.split('@')[0]
    ||'EntangleX account';
}

export function accountEmail(user:User|undefined|null,profile?:AuthProfile|null){
  return profile?.email||user?.email||'Email unavailable';
}

export function accountAvatarUrl(user:User|undefined|null,profile?:AuthProfile|null){
  if(!user)return null;
  return profile?.avatarUrl||metadataText(user,'avatar_url')||metadataText(user,'picture');
}

export function accountInitials(user:User|undefined|null,profile?:AuthProfile|null){
  const parts=accountName(user,profile).split(/\s+/).filter(Boolean);
  return (parts.length>1?`${parts[0][0]}${parts.at(-1)?.[0]||''}`:parts[0]?.slice(0,2)||'EX').toUpperCase();
}

export function accountProvider(user:User|undefined|null,profile?:AuthProfile|null){
  if(profile?.provider)return profile.provider==='github'?'GitHub':'Google';
  const provider=user?.app_metadata?.provider;
  return typeof provider==='string'&&provider?provider[0].toUpperCase()+provider.slice(1):'Google';
}

export function AccountAvatar({user,profile,size='medium'}:{user:User|undefined|null;profile?:AuthProfile|null;size?:'small'|'medium'|'large'}){
  const source=accountAvatarUrl(user,profile);
  const [failed,setFailed]=useState(false);
  useEffect(()=>setFailed(false),[source]);
  const label=`${accountName(user,profile)} profile`;
  return <span className={`account-avatar account-avatar-${size}`} aria-label={label} role="img">
    {source&&!failed
      ? <img src={source} alt="" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>
      : <span aria-hidden="true">{accountInitials(user,profile)}</span>}
  </span>;
}
