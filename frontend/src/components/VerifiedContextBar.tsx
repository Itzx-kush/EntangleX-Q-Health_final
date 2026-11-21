import {useFlagshipData} from '../hooks/useVerifiedDemo';

export function VerifiedContextBar() {
  const {context,item,payload,verified}=useFlagshipData(true);
  if(!context.active)return null;
  const dataset=payload?.dataset.name||item?.name||(verified.isError?'Dataset unavailable':'Loading dataset…');
  const mode=payload?.verified?'Verified · precomputed':verified.isError?'Evidence unavailable':'Checking evidence';
  return <section className="verified-summary-bar" aria-label="Active verified demonstration context">
    <details><summary><span>{mode}</span><strong>{dataset}</strong></summary>
      <dl><div><dt>Experiment</dt><dd>{payload?.experiment.name||'SIH demonstration'}</dd></div>
        <div><dt>Recorded models</dt><dd>{payload?.models.length??item?.demo_readiness.model_ids.length??'—'}</dd></div></dl>
    </details>
    <button type="button" onClick={context.deactivate}>Exit demo</button>
  </section>;
}
