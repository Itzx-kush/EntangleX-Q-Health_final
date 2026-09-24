import {useEffect,useRef} from 'react';

/** Keep keyboard focus inside an open dialog and restore its trigger on close. */
export function useDialogFocus<T extends HTMLElement>(){
  const ref=useRef<T>(null);
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null;
    const node=ref.current;
    if(!node)return;
    const selector='button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]';
    const controls=()=>Array.from(node.querySelectorAll<HTMLElement>(selector));
    controls()[0]?.focus();
    const trap=(event:KeyboardEvent)=>{
      if(event.key!=='Tab')return;
      const items=controls();
      const first=items[0],last=items.at(-1);
      if(!first){event.preventDefault();return;}
      if(event.shiftKey&&(document.activeElement===first||!node.contains(document.activeElement))){
        event.preventDefault();last?.focus();
      }else if(!event.shiftKey&&(document.activeElement===last||!node.contains(document.activeElement))){
        event.preventDefault();first.focus();
      }
    };
    document.addEventListener('keydown',trap);
    return()=>{document.removeEventListener('keydown',trap);if(previous?.isConnected)previous.focus();};
  },[]);
  return ref;
}