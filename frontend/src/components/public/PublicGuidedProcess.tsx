import {useEffect, useState} from 'react';
import {ChoiceTabs} from '../ChoiceTabs';

const stages = [
  {id: 'stage-01', label: 'Prepare', title: 'Data preparation & quality control', detail: 'Inspect missing values, target classes and the dataset fingerprint before fitting a transformation.', items: ['Schema and missingness', 'Dataset provenance', 'Partition isolation']},
  {id: 'stage-02', label: 'Represent', title: 'Feature engineering & selection', detail: 'Trace the features selected on training data and the representation supplied to each model.', items: ['Feature selection', 'Training-only transforms', 'Quantum input width']},
  {id: 'stage-03', label: 'Model', title: 'Hybrid VQC modelling', detail: 'Follow a sample from angle encoding through the trainable circuit and classical output head. Compare it with the registered classical and quantum models.', items: ['Feature encoding', 'Variational layers', 'Classical readout']},
  {id: 'stage-04', label: 'Evaluate', title: 'Controlled evaluation & validation', detail: 'Inspect held-out performance, valid cross-validation folds and perturbation results alongside their experimental conditions.', items: ['Held-out scores', 'Robustness evidence', 'Research report']},
];
function selectedFromHash() {
  return stages.find(stage => '#' + stage.id === window.location.hash)?.id || stages[0].id;
}
export function PublicGuidedProcess() {
  const [selection, setSelection] = useState(selectedFromHash);
  useEffect(() => {
    const sync = () => {
      if (stages.some(stage => '#' + stage.id === window.location.hash)) setSelection(selectedFromHash());
    };
    window.addEventListener('hashchange', sync);
    return () => window.removeEventListener('hashchange', sync);
  }, []);
  const stage = stages.find(item => item.id === selection)!;
  return <section id="guided-process" className="method-section"><div className="qx-wrap qx-section">
    <p className="qx-kicker">Methodology</p><h2>From sample to evidence</h2>
    <ChoiceTabs prefix="method" items={stages} label="Research methodology" value={selection} onChange={setSelection}/>
    <div id="method-panel" className="method-panel" role="tabpanel" aria-labelledby={'method-tab-' + selection}>
      <div><span className="method-number">{String(stages.indexOf(stage) + 1).padStart(2, '0')}</span><h3 id={stage.id}>{stage.title}</h3><p>{stage.detail}</p></div>
      <ul>{stage.items.map(item => <li key={item}>{item}</li>)}</ul>
    </div>
  </div></section>;
}
