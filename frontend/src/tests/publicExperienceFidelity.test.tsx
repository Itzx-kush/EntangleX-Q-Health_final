import {afterEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {PublicExperience} from '../components/PublicExperience';
import {PublicHeader} from '../components/public/PublicHeader';
import {PublicGuidedProcess} from '../components/public/PublicGuidedProcess';
import {PublicResearchDemonstration} from '../components/public/PublicResearchDemonstration';
import {exampleProbabilities, previewPreset} from '../components/public/previewPresets';

afterEach(()=>{vi.unstubAllGlobals();window.history.replaceState(null,'','/')});
describe('Public research experience',()=>{
  it('renders the message and entry points without waiting for animation',()=>{
    vi.stubGlobal('matchMedia',()=>({matches:true,addEventListener(){},removeEventListener(){}}));
    render(<PublicExperience onRequestAccess={()=>{}}/>);
    expect(screen.getByRole('heading',{level:1})).toHaveTextContent('One dataset.Two paths.');
    expect(screen.getByRole('button',{name:'Open verified SIH demo'})).toBeVisible();
    expect(screen.getByRole('link',{name:'Try interactive preview'})).toHaveAttribute('href','#interactive-demo');
  });
  it('routes demo and account entry separately and keeps public bookmarks',()=>{
    const request=vi.fn();
    render(<PublicExperience onRequestAccess={request}/>);
    fireEvent.click(screen.getByRole('button',{name:'Open verified SIH demo'})); expect(request).toHaveBeenLastCalledWith('/demo');
    fireEvent.click(screen.getByRole('button',{name:'Sign in'})); expect(request).toHaveBeenLastCalledWith('/');
    for(const id of ['interactive-demo','technical-stack','guided-process','about','demonstration'])expect(document.getElementById(id)).toBeInTheDocument();
  });
  it('closes the mobile navigation on Escape, outside press and link selection',()=>{
    render(<PublicHeader onRequestAccess={()=>{}}/>);
    const toggle=screen.getByRole('button',{name:'Open navigation menu'});
    fireEvent.click(toggle);expect(toggle).toHaveAttribute('aria-expanded','true');
    fireEvent.keyDown(window,{key:'Escape'});expect(toggle).toHaveFocus();
    fireEvent.click(toggle);fireEvent.pointerDown(document.body);expect(toggle).toHaveAttribute('aria-expanded','false');
    fireEvent.click(toggle);fireEvent.click(screen.getByRole('link',{name:'Methodology'}));expect(toggle).toHaveAttribute('aria-expanded','false');
  });
  it('links both branches of the signature diagram to their explanations',()=>{
    render(<PublicExperience onRequestAccess={()=>{}}/>);
    const classical=screen.getByRole('button',{name:'Classical'});
    fireEvent.click(classical);expect(classical).toHaveAttribute('aria-pressed','true');
    fireEvent.click(screen.getByRole('button',{name:'Quantum'}));expect(classical).toHaveAttribute('aria-pressed','false');
  });
  it('restores a legacy methodology bookmark and supports roving keyboard selection',()=>{
    window.history.replaceState(null,'','/#stage-03');
    render(<PublicGuidedProcess/>);
    const tab=screen.getByRole('tab',{name:'Model'});expect(tab).toHaveAttribute('aria-selected','true');
    fireEvent.keyDown(tab,{key:'End'});expect(screen.getByRole('tab',{name:'Evaluate'})).toHaveFocus();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Controlled evaluation');
    fireEvent.keyDown(screen.getByRole('tab',{name:'Evaluate'}),{key:'Home'});
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Data preparation');
  });
  it.each([2,4] as const)('keeps the %i-qubit code, register, circuit and calculated distribution synchronized',n=>{
    render(<PublicResearchDemonstration/>);
    fireEvent.click(screen.getByRole('button',{name:n+'Q'}));
    const panel=screen.getByRole('tabpanel');
    expect(within(panel).getByRole('img',{name:'hybrid-vqc circuit on '+n+' qubits'})).toBeInTheDocument();
    expect(panel.querySelector('code')).toHaveTextContent('width = '+n);
    expect(panel).toHaveTextContent(n+' qubits');expect(panel.querySelectorAll('.preview-bars>div')).toHaveLength(2**n);
    const rows=exampleProbabilities(n);
    expect(rows.reduce((sum,row)=>sum+row.value,0)).toBeCloseTo(1,12);
    expect(rows[0].value).toBeCloseTo([Math.PI/3,Math.PI/4,Math.PI/6,Math.PI/5].slice(0,n).reduce((p,x)=>p*Math.cos(x/2)**2,1),12);
  });
  it('computes kernel overlaps for the displayed width and keeps illustrative output distinct',()=>{
    render(<PublicResearchDemonstration/>);
    const first=screen.getByRole('tab',{name:'Hybrid VQC'});fireEvent.keyDown(first,{key:'End'});
    expect(screen.getByRole('tab',{name:'Quantum kernel'})).toHaveFocus();
    fireEvent.click(screen.getByRole('button',{name:'2Q'}));
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Calculated example overlaps');
    expect(previewPreset('quantum-kernel',2).values[0].value).toBe(1);
    expect(previewPreset('quantum-kernel',2).values.at(-1)?.value).not.toBe(previewPreset('quantum-kernel',4).values.at(-1)?.value);
    expect(screen.getByRole('note')).toHaveTextContent('Illustrative sample');
  });
  it('names real estimators and features used by the classical example',()=>{
    render(<PublicResearchDemonstration/>);fireEvent.click(screen.getByRole('tab',{name:'Classical baseline'}));
    const panel=screen.getByRole('tabpanel');
    for(const name of ['GradientBoostingClassifier','RandomForestClassifier','StratifiedKFold','early-stage-diabetes','Polyuria','Polydipsia','Age','Alopecia'])expect(panel).toHaveTextContent(name);
    expect(panel).not.toHaveTextContent(/XGBoost|BMI|from entanglex/);
    expect(within(panel).queryByRole('group',{name:'Register width'})).not.toBeInTheDocument();
  });
  it('confirms clipboard success only after resolution and handles rejection',async()=>{
    const writeText=vi.fn().mockRejectedValueOnce(new Error('denied')).mockResolvedValueOnce(undefined);
    Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText}});
    render(<PublicResearchDemonstration/>);fireEvent.click(screen.getByText('Inspect example code'));
    const copy=screen.getByRole('button',{name:'Copy code sample'});fireEvent.click(copy);
    await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent('manually'));expect(copy).not.toHaveTextContent('Copied');
    fireEvent.click(copy);await waitFor(()=>expect(copy).toHaveTextContent('Copied'));
    expect(writeText).toHaveBeenCalledWith(previewPreset('hybrid-vqc',4).code);
  });
});
