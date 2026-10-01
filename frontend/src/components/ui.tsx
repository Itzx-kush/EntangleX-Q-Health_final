import type {ButtonHTMLAttributes,InputHTMLAttributes,ReactNode,SelectHTMLAttributes,TextareaHTMLAttributes} from 'react';
import {cn} from '../lib/utils';
import {ClickSpark} from './reactbits';
import {TremorBadge,TremorCard} from './TremorUI';

export function Button({className='',variant='primary',type='button',...props}:{variant?:'primary'|'outline'|'ghost'}&ButtonHTMLAttributes<HTMLButtonElement>){return <ClickSpark><button type={type} className={cn('btn',variant==='primary'?'btn-primary':variant==='outline'?'btn-outline':'btn-ghost',className)} {...props}/></ClickSpark>;}
export function LinkButton({children,to,className='',variant='primary'}:{children:ReactNode;to:string;className?:string;variant?:'primary'|'outline'|'ghost'}){return <a href={to} className={cn('btn',variant==='primary'?'btn-primary':variant==='outline'?'btn-outline':'btn-ghost',className)}>{children}</a>;}
export function Input(props:InputHTMLAttributes<HTMLInputElement>){return <input className="input" {...props}/>;}
export function Select(props:SelectHTMLAttributes<HTMLSelectElement>){return <select className="select" {...props}/>;}
export function Textarea(props:TextareaHTMLAttributes<HTMLTextAreaElement>){return <textarea className="textarea" {...props}/>;}
export function Card({children,className='',title,description}:{children:ReactNode;className?:string;title?:string;description?:string}){return <TremorCard className={className} title={title} description={description}>{children}</TremorCard>;}
export function Badge({children,tone='blue'}:{children:ReactNode;tone?:'blue'|'green'|'amber'|'red'|'purple'}){return <TremorBadge tone={tone}>{children}</TremorBadge>;}
