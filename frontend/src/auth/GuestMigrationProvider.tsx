import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useQueryClient} from '@tanstack/react-query';
import {useLocation,useNavigate} from 'react-router-dom';
import {useAuth} from './AuthProvider';
import {
  createGuestMigration,
  clearGuestMigration,
  guestMigrationActivity,
  inspectMigratableGuestState,
  readGuestMigration,
  writeGuestMigration,
  type GuestMigrationSnapshot,
} from './guestSession';
import {insertResearchActivity} from '../research/historyService';

type GuestMigrationContextValue={
  migration:GuestMigrationSnapshot|null;
  hasMigratableState:boolean;
  beginUpgrade:()=>void;
  retryMigration:()=>void;
  continueGuestSession:()=>void;
  dismissMigration:()=>void;
};

const GuestMigrationContext=createContext<GuestMigrationContextValue|null>(null);
const FALLBACK_GUEST_MIGRATION:GuestMigrationContextValue={
  migration:null,
  hasMigratableState:false,
  beginUpgrade:()=>{},
  retryMigration:()=>{},
  continueGuestSession:()=>{},
  dismissMigration:()=>{},
};

export function GuestMigrationProvider({children}:{children:ReactNode}){
  const {user,isAuthenticated,isGuest,isConfigured,leaveGuestMode,continueAsGuest}=useAuth();
  const location=useLocation();
  const navigate=useNavigate();
  const queryClient=useQueryClient();
  const [migration,setMigration]=useState<GuestMigrationSnapshot|null>(readGuestMigration);
  const [hasMigratableState,setHasMigratableState]=useState(false);
  const activeImport=useRef<string|null>(null);
  const destination=`${location.pathname}${location.search}`;

  const refreshGuestState=useCallback(()=>{
    setMigration(readGuestMigration());
    setHasMigratableState(Boolean(inspectMigratableGuestState(destination)));
  },[destination]);

  useEffect(()=>{
    refreshGuestState();
    const onStorage=(event:StorageEvent)=>{
      if(!event.key||event.key.startsWith('qhealth-'))refreshGuestState();
    };
    window.addEventListener('storage',onStorage);
    window.addEventListener('qhealth-guest-state-changed',refreshGuestState);
    return()=>{
      window.removeEventListener('storage',onStorage);
      window.removeEventListener('qhealth-guest-state-changed',refreshGuestState);
    };
  },[refreshGuestState]);

  const beginUpgrade=useCallback(()=>{
    const snapshot=createGuestMigration(destination);
    setMigration(snapshot);
    leaveGuestMode();
  },[destination,leaveGuestMode]);

  const continueGuestSession=useCallback(()=>{
    continueAsGuest();
    const pending=readGuestMigration();
    if(pending)setMigration(pending);
  },[continueAsGuest]);

  const retryMigration=useCallback(()=>{
    const current=readGuestMigration();
    if(!current)return;
    const pending={...current,status:'pending' as const,error:null};
    writeGuestMigration(pending);
    setMigration(pending);
  },[]);

  const dismissMigration=useCallback(()=>{
    clearGuestMigration();
    setMigration(null);
  },[]);

  useEffect(()=>{
    const current=readGuestMigration();
    if(!isAuthenticated||!user||!current||current.status!=='pending')return;
    if(activeImport.current===current.migrationId)return;
    if(!isConfigured){
      const failed={...current,status:'failed' as const,error:'Research persistence is not configured for this deployment.'};
      writeGuestMigration(failed);
      setMigration(failed);
      return;
    }

    activeImport.current=current.migrationId;
    const importing={...current,status:'importing' as const,error:null};
    writeGuestMigration(importing);
    setMigration(importing);

    insertResearchActivity(guestMigrationActivity(current))
      .then(()=>{
        const completed={...current,status:'completed' as const,error:null};
        writeGuestMigration(completed);
        setMigration(completed);
        void queryClient.invalidateQueries({queryKey:['research-history',user.id]});
        const target=current.destination;
        if(`${location.pathname}${location.search}`!==target)navigate(target,{replace:true});
      })
      .catch(error=>{
        const failed={
          ...current,
          status:'failed' as const,
          error:error instanceof Error?error.message:'Your research could not be saved to your account yet.',
        };
        writeGuestMigration(failed);
        setMigration(failed);
      })
      .finally(()=>{activeImport.current=null});
  },[isAuthenticated,user,isConfigured,queryClient,navigate,location.pathname,location.search,migration?.status]);

  const value=useMemo<GuestMigrationContextValue>(()=>({
    migration,
    hasMigratableState:isGuest&&hasMigratableState,
    beginUpgrade,
    retryMigration,
    continueGuestSession,
    dismissMigration,
  }),[migration,isGuest,hasMigratableState,beginUpgrade,retryMigration,continueGuestSession,dismissMigration]);

  return <GuestMigrationContext.Provider value={value}>{children}</GuestMigrationContext.Provider>;
}

export function useGuestMigration(){
  return useContext(GuestMigrationContext)||FALLBACK_GUEST_MIGRATION;
}