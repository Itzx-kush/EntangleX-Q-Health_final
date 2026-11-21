import {fireEvent,render,screen,within} from '@testing-library/react';
import {describe,expect,it} from 'vitest';
import {ModelMetricBars} from '../components/Charts';
import {connectionState} from '../lib/connection';
import {defaultAppearance,readAppearance,updateAppearance} from '../lib/appearance';
import type {ModelRecord} from '../types/qhealth';

describe('Workspace evidence',()=>{
  it('uses the legend swatch for each of the seven bars, preserving an absent score',()=>{
    const kinds=['logistic_regression','random_forest','svm','qnn','qsvc','vqc','hybrid_pennylane_torch'] as const;
    const models=kinds.map((model_type,i)=>({id:String(i),model_type,metrics:{test:{roc_auc:i===0?null:.3+i/10}}})) as ModelRecord[];
    render(<ModelMetricBars models={models} metricName="roc_auc"/>);
    const figure=screen.getByRole('figure');const legend=within(figure).getByRole('list',{name:'Model families'});
    for(const row of figure.querySelectorAll('[data-family]')){
      const bar=row.querySelector<HTMLElement>('.bar-track i');
      if(!bar){expect(row).toHaveTextContent('—');continue;}
      const swatch=within(legend).getByText(row.getAttribute('data-family')!).querySelector('i')!;
      expect(bar.style.backgroundColor).toBe(swatch.style.backgroundColor);expect(bar.style.backgroundColor).not.toBe('');
    }
  });
  it('separates pending, partial service and a confirmed connection',()=>{
    const pending={isError:false,isFetching:true,failureCount:0};
    expect(connectionState(pending,pending).label).toBe('Connecting');
    expect(connectionState({...pending,data:{}},{...pending,data:{database_available:false}}).label).toBe('Partial availability');
    expect(connectionState({...pending,data:{}},{...pending,data:{database_available:true}}).label).toBe('Connected');
    expect(connectionState({...pending,failureCount:1},pending).label).toBe('Retrying');
    expect(connectionState({...pending,isError:true,isFetching:false},{...pending,isError:true,isFetching:false}).label).toBe('Unavailable');
  });
  it('reads the legacy theme and restores preferences without touching research storage',()=>{
    localStorage.clear();localStorage.setItem('qhealth-tictac-theme','dark');localStorage.setItem('qhealth-verified-demo-context','experiment');
    expect(readAppearance().theme).toBe('dark');
    updateAppearance({layout:'icon',inspector:true});expect(readAppearance().inspector).toBe(true);
    updateAppearance(defaultAppearance);expect(readAppearance()).toEqual(defaultAppearance);expect(localStorage.getItem('qhealth-verified-demo-context')).toBe('experiment');
  });
});
