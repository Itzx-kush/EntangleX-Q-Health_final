import {ValueBars} from './Charts';
import {ChartValues} from './ChartValues';
import {Card} from './ui';

type Fitted = {pca_explained_variance?:number[]; pca_loadings?:number[][]; selected_features?:string[];
  output_features?:string[]; selection_scores?:{feature:string;score:number|null;selected:boolean}[]};
export function PipelineEvidence({stage,fitted}:{stage:'pca'|'features'|'preprocessing';fitted:Fitted}) {
  const names=fitted.selected_features??[];
  if (stage==='pca') {
    const variance=fitted.pca_explained_variance??[];
    const loadings=fitted.pca_loadings??[];
    return <Card title="Variance by principal component" description="Percentage of training variance explained by each fitted component.">
      {variance.length?<ValueBars items={variance.flatMap((v,i)=>Number.isFinite(v)?[{name:fitted.output_features?.[i]??'PC'+(i+1),value:v*100}]:[])} unit="%"/>:<p className="muted">Component variance was not recorded.</p>}
      {names.length>0&&loadings.length>0&&loadings.every(row=>row.length===names.length)&&<ChartValues label="Signed component loadings" columns={['Selected feature',...loadings.map((_,i)=>'PC'+(i+1))]} rows={names.map((name,j)=>[name,...loadings.map(row=>row[j])])}/>}
    </Card>;
  }
  if (stage==='features'&&fitted.selection_scores?.length) return <Card title="Training feature selection" description="Recorded scores and selection decisions for the fitted representation.">
    <ChartValues label="Feature scores and selection" columns={['Feature','Score','Retained']} rows={fitted.selection_scores.map(item=>[item.feature,item.score,item.selected?'Yes':'No'])}/>
  </Card>;
  return null;
}
