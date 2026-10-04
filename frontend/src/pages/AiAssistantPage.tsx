import {useEffect,useRef} from 'react';
import {AlertCircle,Bot,Loader2,MessageSquare,RefreshCcw,Send,User} from 'lucide-react';
import {Button} from '../components/ui';
import {useAi} from '../contexts/AiContext';

export const EXAMPLE_PROMPTS=[
  'What is EntangleX Q-Health?',
  'How does the hybrid quantum-classical model work?',
  'Explain the VQC workflow.',
  'What is the role of PCA in this prototype?'
];

function renderAssistantText(text:string){
  return text.split('\n').map((line,index)=>{
    const trimmed=line.trim();
    if(!trimmed)return <div key={index} className="h-2"/>;
    if(trimmed.startsWith('- ')){
      return <div key={index} className="flex gap-2 text-sm leading-relaxed my-1"><span className="text-primary">•</span><span>{trimmed.slice(2)}</span></div>;
    }
    return <p key={index} className="text-sm leading-relaxed mb-1">{line}</p>;
  });
}

export function AiAssistantPage(){
  const {messages,input,loading,error,setInput,handleSend,clearChat}=useAi();
  const endRef=useRef<HTMLDivElement>(null);
  const textareaRef=useRef<HTMLTextAreaElement>(null);

  useEffect(()=>{if(messages.length)endRef.current?.scrollIntoView({behavior:'smooth'});},[messages,loading]);

  const onKeyDown=(event:React.KeyboardEvent<HTMLTextAreaElement>)=>{
    if(event.key==='Enter'&&!event.shiftKey){
      event.preventDefault();
      void handleSend(input);
    }
  };

  const onInput=(event:React.ChangeEvent<HTMLTextAreaElement>)=>{
    setInput(event.target.value);
    event.target.style.height='auto';
    event.target.style.height=`${Math.min(event.target.scrollHeight,200)}px`;
  };

  return <div className="layer3-final-workspace layer3-ai-workspace flex flex-col h-[calc(100vh-4rem)] max-w-4xl mx-auto w-full p-4 md:p-6 lg:p-8">
    <div className="flex items-center justify-between mb-6 pb-4 border-b border-border">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2 text-foreground"><Bot className="text-primary w-7 h-7"/>EntangleX AI Assistant</h1>
        <p className="text-sm text-muted-foreground mt-1">Your prototype-aware research assistant.</p>
      </div>
      {messages.length>0&&<Button variant="outline" onClick={()=>{if(window.confirm('Clear current conversation?'))clearChat();}} className="flex items-center gap-2 py-1.5 px-3">
        <RefreshCcw size={16}/><span className="hidden sm:inline">New conversation</span>
      </Button>}
    </div>

    <div className="flex-1 overflow-y-auto mb-4 space-y-6 pr-2 scrollbar-thin">
      {!messages.length?<div className="flex flex-col items-center justify-center h-full text-center space-y-8 animate-in fade-in zoom-in duration-500">
        <div className="bg-primary/10 p-4 rounded-full"><MessageSquare className="w-12 h-12 text-primary"/></div>
        <div className="max-w-md">
          <h2 className="text-xl font-semibold mb-2">How can I help you?</h2>
          <p className="text-muted-foreground mb-6">Ask about the EntangleX Q-Health architecture, quantum workflow, models, evidence, and how to use the platform.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {EXAMPLE_PROMPTS.map(prompt=><button key={prompt} onClick={()=>void handleSend(prompt)} className="text-left text-sm bg-card border border-border hover:border-primary hover:bg-accent/50 text-foreground transition-colors px-3 py-2 rounded-md shadow-sm">{prompt}</button>)}
          </div>
        </div>
      </div>:<div className="space-y-6 pb-4">
        {messages.map((message,index)=><div key={index} className={`flex gap-4 ${message.role==='user'?'justify-end':'justify-start'}`}>
          {message.role==='model'&&<div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0"><Bot size={18} className="text-primary"/></div>}
          <div className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3.5 shadow-sm ${message.role==='user'?'bg-primary text-primary-foreground rounded-tr-sm':'bg-card border border-border text-card-foreground rounded-tl-sm'}`}>
            {message.role==='user'?<div className="whitespace-pre-wrap text-sm md:text-base">{message.content}</div>:renderAssistantText(message.content)}
          </div>
          {message.role==='user'&&<div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0"><User size={18} className="text-secondary-foreground"/></div>}
        </div>)}
        {loading&&<div className="flex gap-4 justify-start"><div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0"><Bot size={18} className="text-primary"/></div><div className="bg-card border border-border rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm flex items-center gap-2 text-muted-foreground"><Loader2 className="w-4 h-4 animate-spin text-primary"/><span className="text-sm">Thinking...</span></div></div>}
        <div ref={endRef}/>
      </div>}
    </div>

    {error&&<div className="flex gap-4 justify-center mb-4"><div className="bg-destructive/10 border border-destructive/20 text-destructive rounded-lg px-4 py-3 text-sm flex items-center gap-2 max-w-md w-full"><AlertCircle size={18} className="shrink-0"/><p>{error}</p></div></div>}

    <div className="bg-card border border-border rounded-xl shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all p-2 flex items-end gap-2">
      <textarea ref={textareaRef} value={input} onChange={onInput} onKeyDown={onKeyDown} placeholder="Ask about EntangleX Q-Health..." className="flex-1 max-h-48 min-h-[44px] bg-transparent resize-none border-0 focus:ring-0 p-2 text-foreground text-sm md:text-base scrollbar-thin outline-none" disabled={loading} rows={1} maxLength={2000}/>
      <Button onClick={()=>void handleSend(input)} disabled={!input.trim()||loading} className="shrink-0 h-10 w-10 flex items-center justify-center p-0 rounded-lg mb-0.5"><Send size={18}/></Button>
    </div>
    <p className="text-xs text-muted-foreground text-center mt-2">The AI Assistant may produce inaccurate information. Always verify scientific facts.</p>
  </div>;
}
