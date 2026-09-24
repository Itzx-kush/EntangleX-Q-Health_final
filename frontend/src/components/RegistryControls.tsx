import {Button} from './ui';

export function RegistryControls({page,pages,total,setPage}:{page:number;pages:number;total:number;setPage:(page:number)=>void}){
  return <div className="mt-4 flex items-center justify-between gap-3 text-xs muted" aria-label="Registry pagination"><span>{total} matching records · page {page+1} of {pages}</span><div className="flex gap-2"><Button variant="outline" disabled={page===0} onClick={()=>setPage(page-1)}>Previous</Button><Button variant="outline" disabled={page>=pages-1} onClick={()=>setPage(page+1)}>Next</Button></div></div>;
}