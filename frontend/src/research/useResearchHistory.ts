import {useCallback,useState} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {toast} from 'sonner';
import {useAuth} from '../auth/AuthProvider';
import {fetchResearchHistory,insertResearchActivity} from './historyService';
import type {NewResearchActivity,ResearchHistoryFilter} from './historyTypes';

export function useResearchHistory(filter:ResearchHistoryFilter='all',page=0,pageSize=20){
  const {user,isAuthenticated,isConfigured}=useAuth();
  return useQuery({
    queryKey:['research-history',user?.id,filter,page,pageSize],
    queryFn:()=>fetchResearchHistory(user!.id,{filter,page,pageSize}),
    enabled:Boolean(isAuthenticated&&isConfigured&&user),
    staleTime:30_000,
  });
}

export function useResearchRecorder(){
  const {user,isAuthenticated,isConfigured}=useAuth();
  const queryClient=useQueryClient();
  const [warning,setWarning]=useState<string|null>(null);

  const record=useCallback(async(activity:NewResearchActivity)=>{
    if(!isAuthenticated||!isConfigured||!user)return null;
    try{
      const saved=await insertResearchActivity(activity);
      setWarning(null);
      await queryClient.invalidateQueries({queryKey:['research-history',user.id]});
      return saved;
    }catch(error){
      const message=error instanceof Error?error.message:'Research history could not be saved.';
      setWarning(message);
      toast.warning('Research completed, but history saving is temporarily unavailable.',{description:message});
      return null;
    }
  },[isAuthenticated,isConfigured,user,queryClient]);

  return {record,warning,clearWarning:()=>setWarning(null)};
}
