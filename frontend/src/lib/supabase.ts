import {createClient, type SupabaseClient} from '@supabase/supabase-js';

const supabaseUrl=(import.meta.env.VITE_SUPABASE_URL as string|undefined)?.trim();
const supabaseAnonKey=(import.meta.env.VITE_SUPABASE_ANON_KEY as string|undefined)?.trim();

function isValidHttpUrl(value:string|undefined){
  if(!value)return false;
  try{
    const url=new URL(value);
    return url.protocol==='https:'||url.hostname==='localhost'||url.hostname==='127.0.0.1';
  }catch{
    return false;
  }
}

export const supabaseConfigurationError=!supabaseUrl||!supabaseAnonKey
  ? 'Account sign-in is not configured for this deployment. You can still continue without signing in.'
  : !isValidHttpUrl(supabaseUrl)
    ? 'The Supabase URL for this deployment is invalid. You can still continue without signing in.'
    : null;

export const supabase:SupabaseClient|null=supabaseConfigurationError
  ? null
  : createClient(supabaseUrl!,supabaseAnonKey!,{
      auth:{
        flowType:'pkce',
        persistSession:true,
        autoRefreshToken:true,
        detectSessionInUrl:true,
      },
    });
