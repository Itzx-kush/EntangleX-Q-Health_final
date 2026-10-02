import {useEffect,useState} from 'react';
import type {User} from '@supabase/supabase-js';

function metadataText(user:User|undefined,key:string){
  const value=user?.user_metadata?.[key];
  return typeof value==='string'&&value.trim()?value.trim():null;
}

export function accountName(user:User|undefined|null){
  if(!user)return 'Guest researcher';
  return metadataText(user,'full_name')
    ||metadataText(user,'name')
    ||metadataText(user,'preferred_username')
    ||user.email?.split('@')[0]
    ||'EntangleX account';
}

export function accountEmail(user:User|undefined|null){
  return user?.email||'Email unavailable';
}

export function accountAvatarUrl(user:User|undefined|null){
  if(!user)return null;
  return metadataText(user,'avatar_url')||metadataText(user,'picture');
}

export function accountInitials(user:User|undefined|null){
  const parts=accountName(user).split(/\s+/).filter(Boolean);
  return (parts.length>1?`${parts[0][0]}${parts.at(-1)?.[0]||''}`:parts[0]?.slice(0,2)||'EX').toUpperCase();
}

export function accountProvider(user:User|undefined|null){
  const provider=user?.app_metadata?.provider;
  return typeof provider==='string'&&provider?provider[0].toUpperCase()+provider.slice(1):'Google';
}

export function AccountAvatar({user,size='medium'}:{user:User|undefined|null;size?:'small'|'medium'|'large'}){
  const source=accountAvatarUrl(user);
  const [failed,setFailed]=useState(false);
  useEffect(()=>setFailed(false),[source]);
  const label=`${accountName(user)} profile`;
  return <span className={`account-avatar account-avatar-${size}`} aria-label={label} role="img">
    {source&&!failed
      ? <img src={source} alt="" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>
      : <span aria-hidden="true">{accountInitials(user)}</span>}
  </span>;
}
