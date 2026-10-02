import {createContext,useCallback,useContext,useEffect,useMemo,useState,type ReactNode} from 'react';
import type {AuthError,Session,User} from '@supabase/supabase-js';
import {supabase,supabaseConfigurationError} from '../lib/supabase';
import {ensureActiveGuestSession} from './guestSession';

const GUEST_MODE_KEY='qhealth-access-mode';
const AUTH_QUERY_KEYS=['code','error','error_code','error_description'];

type AuthContextValue={
  user:User|null;
  session:Session|null;
  isAuthenticated:boolean;
  isGuest:boolean;
  loading:boolean;
  signingOut:boolean;
  isConfigured:boolean;
  error:string|null;
  signInWithGoogle:()=>Promise<void>;
  signInWithGitHub:()=>Promise<void>;
  signOut:()=>Promise<void>;
  continueAsGuest:()=>void;
  leaveGuestMode:()=>void;
  clearError:()=>void;
};

const AuthContext=createContext<AuthContextValue|null>(null);
const FALLBACK_AUTH:AuthContextValue={
  user:null,
  session:null,
  isAuthenticated:false,
  isGuest:true,
  loading:false,
  signingOut:false,
  isConfigured:false,
  error:null,
  signInWithGoogle:async()=>{},
  signInWithGitHub:async()=>{},
  signOut:async()=>{},
  continueAsGuest:()=>{},
  leaveGuestMode:()=>{},
  clearError:()=>{},
};

function readGuestMode(){
  try{return localStorage.getItem(GUEST_MODE_KEY)==='guest'}catch{return false}
}

function oauthErrorFromUrl(){
  const query=new URLSearchParams(window.location.search);
  const hash=new URLSearchParams(window.location.hash.replace(/^#/,''));
  const description=query.get('error_description')||hash.get('error_description');
  const code=query.get('error')||hash.get('error');
  if(!description&&!code)return null;
  return decodeURIComponent((description||code||'Account sign-in was not completed.').replace(/\+/g,' '));
}

function cleanOAuthUrl(includeCode=true){
  const url=new URL(window.location.href);
  let changed=false;
  AUTH_QUERY_KEYS.forEach(key=>{
    if(key==='code'&&!includeCode)return;
    if(url.searchParams.has(key)){url.searchParams.delete(key);changed=true}
  });
  if(/(^#|&)access_token=|(^#|&)error=/.test(url.hash)){
    url.hash='';
    changed=true;
  }
  if(changed)window.history.replaceState(window.history.state,'',`${url.pathname}${url.search}${url.hash}`);
}

function authMessage(error:unknown,fallback:string){
  if(error instanceof Error&&error.message)return error.message;
  const authError=error as Partial<AuthError>|null;
  return authError?.message||fallback;
}

export function AuthProvider({children}:{children:ReactNode}){
  const [session,setSession]=useState<Session|null>(null);
  const [isGuest,setIsGuest]=useState(readGuestMode);
  const [loading,setLoading]=useState(true);
  const [signingOut,setSigningOut]=useState(false);
  const [error,setError]=useState<string|null>(()=>oauthErrorFromUrl());

  useEffect(()=>{
    if(oauthErrorFromUrl())cleanOAuthUrl(false);
    if(!supabase){
      setLoading(false);
      return;
    }

    let active=true;
    const {data:{subscription}}=supabase.auth.onAuthStateChange((_event,nextSession)=>{
      if(!active)return;
      setSession(nextSession);
      setSigningOut(false);
      if(nextSession){
        setError(null);
        setIsGuest(false);
        try{localStorage.removeItem(GUEST_MODE_KEY)}catch{}
      }
      setLoading(false);
    });

    supabase.auth.getSession()
      .then(({data,error:sessionError})=>{
        if(!active)return;
        if(sessionError)setError(authMessage(sessionError,'We could not restore your research session.'));
        setSession(data.session);
        if(data.session){
          setIsGuest(false);
          try{localStorage.removeItem(GUEST_MODE_KEY)}catch{}
        }
      })
      .catch(sessionError=>{
        if(active)setError(authMessage(sessionError,'We could not restore your research session. Check your connection and try again.'));
      })
      .finally(()=>{
        cleanOAuthUrl();
        if(active)setLoading(false);
      });

    return()=>{active=false;subscription.unsubscribe()};
  },[]);

  const signInWithOAuth=useCallback(async(provider:'google'|'github')=>{
    setError(null);
    if(!supabase){
      setError(supabaseConfigurationError);
      return;
    }
    try{
      const redirectUrl=new URL(window.location.href);
      AUTH_QUERY_KEYS.forEach(key=>redirectUrl.searchParams.delete(key));
      redirectUrl.hash='';
      const {error:signInError}=await supabase.auth.signInWithOAuth({
        provider,
        options:{
          redirectTo:redirectUrl.toString(),
          ...(provider==='google'?{queryParams:{prompt:'select_account'}}:{}),
        },
      });
      if(signInError)setError(authMessage(signInError,`${provider==='google'?'Google':'GitHub'} sign-in could not be started.`));
    }catch(signInError){
      setError(authMessage(signInError,`${provider==='google'?'Google':'GitHub'} sign-in could not be started. Check your connection and try again.`));
    }
  },[]);
  const signInWithGoogle=useCallback(()=>signInWithOAuth('google'),[signInWithOAuth]);
  const signInWithGitHub=useCallback(()=>signInWithOAuth('github'),[signInWithOAuth]);

  const signOut=useCallback(async()=>{
    setError(null);
    setSigningOut(true);
    try{
      const {error:signOutError}=supabase?await supabase.auth.signOut():{error:null};
      if(signOutError){
        setError(authMessage(signOutError,'Sign out could not be completed.'));
        setSigningOut(false);
        return;
      }
      setSession(null);
      setIsGuest(false);
      try{localStorage.removeItem(GUEST_MODE_KEY)}catch{}
    }catch(signOutError){
      setError(authMessage(signOutError,'Sign out could not be completed.'));
      setSigningOut(false);
    }
  },[]);

  const continueAsGuest=useCallback(()=>{
    try{localStorage.setItem(GUEST_MODE_KEY,'guest')}catch{}
    ensureActiveGuestSession();
    setIsGuest(true);
    setError(null);
  },[]);

  const leaveGuestMode=useCallback(()=>{
    try{localStorage.removeItem(GUEST_MODE_KEY)}catch{}
    setIsGuest(false);
  },[]);
  const clearError=useCallback(()=>setError(null),[]);

  const value=useMemo<AuthContextValue>(()=>({
    user:session?.user??null,
    session,
    isAuthenticated:Boolean(session),
    isGuest,
    loading,
    signingOut,
    isConfigured:!supabaseConfigurationError,
    error,
    signInWithGoogle,
    signInWithGitHub,
    signOut,
    continueAsGuest,
    leaveGuestMode,
    clearError,
  }),[session,isGuest,loading,signingOut,error,signInWithGoogle,signInWithGitHub,signOut,continueAsGuest,leaveGuestMode,clearError]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(){
  return useContext(AuthContext)||FALLBACK_AUTH;
}
