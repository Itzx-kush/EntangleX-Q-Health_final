import {ExampleCircuit} from './ExampleCircuit';
import {useState} from 'react';
import {ChevronDown, Code2} from 'lucide-react';
import {ChoiceTabs} from '../ChoiceTabs';
import {CopyButton} from '../CopyButton';
import {previewPreset, previewTabs, type PreviewKind, type RegisterWidth} from './previewPresets';

export function PublicResearchDemonstration() {
  const [kind, setKind] = useState<PreviewKind>('hybrid-vqc');
  const [width, setWidth] = useState<RegisterWidth>(4);
  const preset = previewPreset(kind, width);
  return <section id="interactive-demo" className="qx-wrap qx-section">
    <div className="qx-section-heading"><div><p className="qx-kicker">Interactive preview</p><h2>Open the workbench</h2></div>
      <p>Explore an example, change the register and inspect the code behind the output.</p></div>
    <div className="preview-frame">
      <ChoiceTabs label="Research workflow options" prefix="preview" items={previewTabs} value={kind} onChange={setKind}/>
      <div id="preview-panel" role="tabpanel" aria-labelledby={'preview-tab-' + kind}>
        <div className="preview-grid">
          <div className="preview-config">
            <p className="qx-kicker">Configuration</p><h3>{preset.summary}</h3><p>{preset.detail}</p>
            {kind !== 'classical-baseline' && <fieldset className="register-picker"><legend>Register width</legend>{([2, 4] as const).map(n =>
              <button key={n} aria-pressed={width === n} onClick={() => setWidth(n)}>{n}Q</button>)}</fieldset>}
            {kind!=='classical-baseline'&&<ExampleCircuit kind={kind} width={width}/>}
            <dl className="preview-stats">{preset.stats.map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
          </div>
          <div className="preview-output"><h3>{preset.chart}</h3>
            <div className={'preview-bars ' + (preset.values.length > 8 ? 'many' : '')}>
              {preset.values.map(item => <div key={item.label}><span>{item.label}</span><i aria-hidden="true"><b style={{width: (item.value * 100) + '%'}}/></i><strong>{(item.value * 100).toFixed(1)}%</strong></div>)}
            </div>
            <p role="note" aria-label="Scientific evidence disclosure">Illustrative sample · independent of the verified benchmark and live quantum jobs.</p>
          </div>
        </div>
        <details className="preview-code"><summary><Code2 size={17}/> Inspect example code <ChevronDown size={16}/></summary><div><CopyButton label="Copy code sample" value={preset.code}/><pre tabIndex={0}><code>{preset.code}</code></pre></div></details>
      </div>
    </div>
  </section>;
}
