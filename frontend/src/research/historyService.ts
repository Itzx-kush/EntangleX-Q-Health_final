import {supabase} from '../lib/supabase';
import type {NewResearchActivity,ResearchActivity,ResearchHistoryFilter,ResearchHistoryPage} from './historyTypes';

const TABLE='research_activity';

function requireSupabase(){
  if(!supabase)throw new Error('Research history is not configured for this deployment.');
  return supabase;
}

function historyError(error:{message?:string;code?:string}|null,fallback:string){
  if(!error)return fallback;
  if(error.code==='42P01'||error.message?.includes('research_activity')){
    return 'Research history setup is incomplete. Apply the Supabase research activity migration and retry.';
  }
  return error.message||fallback;
}

export async function fetchResearchHistory(userId:string,{filter='all',page=0,pageSize=20}:{filter?:ResearchHistoryFilter;page?:number;pageSize?:number}={}):Promise<ResearchHistoryPage>{
  const client=requireSupabase();
  const start=page*pageSize;
  let query=client.from(TABLE)
    .select('*',{count:'exact'})
    .eq('user_id',userId)
    .order('occurred_at',{ascending:false})
    .range(start,start+pageSize-1);
  if(filter!=='all')query=query.eq('activity_type',filter);
  const {data,error,count}=await query;
  if(error)throw new Error(historyError(error,'Research history could not be loaded.'));
  return {records:(data||[]) as ResearchActivity[],total:count||0};
}

export async function insertResearchActivity(activity:NewResearchActivity):Promise<ResearchActivity>{
  const client=requireSupabase();
  const row={
    activity_type:activity.activityType,
    title:activity.title,
    status:activity.status??null,
    ...(activity.occurredAt?{occurred_at:activity.occurredAt}:{}),
    route:activity.route,
    reference_id:activity.referenceId??null,
    experiment_id:activity.experimentId??null,
    model_id:activity.modelId??null,
    dataset_id:activity.datasetId??null,
    method:activity.method??null,
    metadata:activity.metadata||{},
    idempotency_key:activity.idempotencyKey??null,
  };
  let query=client.from(TABLE);
  const response=activity.idempotencyKey
    ? await query.upsert(row,{onConflict:'user_id,idempotency_key',ignoreDuplicates:true}).select().maybeSingle()
    : await query.insert(row).select().single();
  if(response.error)throw new Error(historyError(response.error,'This research activity could not be saved.'));
  if(response.data)return response.data as ResearchActivity;

  const existing=await client.from(TABLE)
    .select('*')
    .eq('idempotency_key',activity.idempotencyKey!)
    .limit(1)
    .single();
  if(existing.error)throw new Error(historyError(existing.error,'This research activity could not be confirmed.'));
  return existing.data as ResearchActivity;
}
