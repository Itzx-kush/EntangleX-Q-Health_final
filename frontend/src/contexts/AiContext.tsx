import {createContext,useCallback,useContext,useState,type ReactNode} from 'react';
import {qh} from '../lib/api';

export type Message={role:'user'|'model';content:string};

type AiContextValue={
  messages:Message[];
  input:string;
  loading:boolean;
  error:string|null;
  isPopupOpen:boolean;
  setInput:(value:string)=>void;
  setPopupOpen:(open:boolean)=>void;
  handleSend:(text:string)=>Promise<void>;
  clearChat:()=>void;
};

const AiContext=createContext<AiContextValue|undefined>(undefined);

export function AiProvider({children}:{children:ReactNode}){
  const [messages,setMessages]=useState<Message[]>([]);
  const [input,setInput]=useState('');
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [isPopupOpen,setPopupOpen]=useState(false);

  const clearChat=useCallback(()=>{
    setMessages([]);
    setError(null);
    setInput('');
  },[]);

  const handleSend=useCallback(async(text:string)=>{
    const trimmed=text.trim();
    if(!trimmed||loading)return;

    const conversation=messages.slice(-10);
    setInput('');
    setError(null);
    setMessages(prev=>[...prev,{role:'user',content:trimmed}]);
    setLoading(true);

    try{
      const response=await qh.aiChat({message:trimmed,conversation});
      setMessages(prev=>[...prev,{role:'model',content:response.reply}]);
    }catch(error){
      console.error('AI Chat Error:',error);
      setMessages(prev=>prev.slice(0,-1));
      setError(error instanceof Error?error.message:'AI Assistant is temporarily unavailable.');
    }finally{
      setLoading(false);
    }
  },[messages,loading]);

  return <AiContext.Provider value={{messages,input,loading,error,isPopupOpen,setInput,setPopupOpen,handleSend,clearChat}}>
    {children}
  </AiContext.Provider>;
}

export function useAi(){
  const context=useContext(AiContext);
  if(!context)throw new Error('useAi must be used within an AiProvider');
  return context;
}
