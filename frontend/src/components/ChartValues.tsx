import {useState} from 'react';

type Cell = string | number | null | undefined;
export function ChartValues({columns,rows,label='Chart values'}:{columns:string[];rows:Cell[][];label?:string}) {
  const [open,setOpen]=useState(false);
  return <details className="chart-values" onToggle={event=>setOpen(event.currentTarget.open)}>
    <summary>{label}</summary>{open&&<div className="table-wrap" tabIndex={0} role="region" aria-label={label}>
      <table className="data-table"><caption className="sr-only">{label}</caption><thead><tr>{columns.map(name=><th key={name} scope="col">{name}</th>)}</tr></thead>
        <tbody>{rows.map((row,i)=><tr key={i}>{row.map((value,j)=>j===0?<th scope="row" key={j}>{value??'—'}</th>:<td key={j}>{value??'—'}</td>)}</tr>)}</tbody>
      </table></div>}</details>;
}
