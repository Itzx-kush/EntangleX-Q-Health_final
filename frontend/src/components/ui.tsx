import type {ButtonHTMLAttributes,InputHTMLAttributes,ReactNode,SelectHTMLAttributes,TextareaHTMLAttributes} from 'react';
import {cn} from '../lib/utils';
import {ClickSpark,SpotlightPanel} from './reactbits';

export function Button({className='',variant='primary',...props}:{variant?:'primary'|'outline'|'ghost'}&ButtonHTMLAttributes<HTMLButtonElement>){return <ClickSpark><button className={cn('btn',variant==='primary'?'btn-primary':variant==='outline'?'btn-outline':'btn-ghost',className)} {...props}/></ClickSpark>;}
export function LinkButton({children,to,className='',variant='primary'}:{children:ReactNode;to:string;className?:string;variant?:'primary'|'outline'|'ghost'}){return <a href={to} className={cn('btn',variant==='primary'?'btn-primary':variant==='outline'?'btn-outline':'btn-ghost',className)}>{children}</a>;}
export function Input(props:InputHTMLAttributes<HTMLInputElement>){return <input className="input" {...props}/>;}
export function Select(props:SelectHTMLAttributes<HTMLSelectElement>){return <select className="select" {...props}/>;}
export function Textarea(props:TextareaHTMLAttributes<HTMLTextAreaElement>){return <textarea className="textarea" {...props}/>;}
export function Card({children,className='',title,description}:{children:ReactNode;className?:string;title?:string;description?:string}){return <SpotlightPanel className={cn('glass-card p-5',className)}>{title&&<div className="mb-4"><h2 className="section-title">{title}</h2>{description&&<p className="section-copy mt-1">{description}</p>}</div>}{children}</SpotlightPanel>;}
export function Badge({children,tone='blue'}:{children:ReactNode;tone?:'blue'|'green'|'amber'|'red'|'purple'}){return <span className={`badge badge-${tone}`}>{children}</span>;}
