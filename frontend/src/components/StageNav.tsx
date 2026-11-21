import {Link} from 'react-router-dom';

export const stages=[['Data','/datasets'],['Quality','/quality'],['Preprocess','/preprocessing'],['Features','/features'],['PCA','/pca'],['Train','/training'],['Compare','/comparison'],['Robustness','/robustness'],['Explain','/explainability'],['Predict','/prediction'],['Experiments','/experiments']] as const;
export function StageNav({current}:{current:string}) {
  return <details className="stage-disclosure"><summary>Research pathway</summary><nav aria-label="Research pathway">
    {stages.map(([label,path])=><Link key={path} to={path} aria-current={current===path?'page':undefined}>{label}</Link>)}
  </nav></details>;
}
