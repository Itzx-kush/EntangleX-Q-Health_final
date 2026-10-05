import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {WhyHybridExperience} from '../components/WhyHybridExperience';

function view(extra?:{datasetName?:string;hybridDetailPath?:string}){
  return render(
    <MemoryRouter>
      <WhyHybridExperience datasetName={extra?.datasetName} hybridDetailPath={extra?.hybridDetailPath}/>
    </MemoryRouter>
  );
}

describe('WhyHybridExperience rationale',()=>{
  it('renders the three model families with the actual EntangleX models',()=>{
    view();
    expect(screen.getByRole('heading',{name:/why hybrid\?/i})).toBeInTheDocument();
    expect(screen.getByText('Classical')).toBeInTheDocument();
    expect(screen.getByText('Quantum')).toBeInTheDocument();
    expect(screen.getByText('Hybrid')).toBeInTheDocument();
    expect(screen.getByText('Logistic Regression')).toBeInTheDocument();
    expect(screen.getByText('SVM')).toBeInTheDocument();
    expect(screen.getByText('Random Forest')).toBeInTheDocument();
    expect(screen.getByText('VQC')).toBeInTheDocument();
    expect(screen.getByText('QSVC')).toBeInTheDocument();
    expect(screen.getByText('QNN')).toBeInTheDocument();
    expect(screen.getByText('PennyLane + PyTorch Hybrid')).toBeInTheDocument();
  });

  it('frames the hybrid rationale as a hypothesis and an honesty boundary',()=>{
    view();
    expect(screen.getByText(/RESEARCH HYPOTHESIS/)).toBeInTheDocument();
    expect(screen.getByText(/trainable quantum representation integrated into a classical ML pipeline/i)).toBeInTheDocument();
    expect(screen.getByText(/Compare classical, quantum, and hybrid models/i)).toBeInTheDocument();
    expect(screen.getByText('WHAT WE DO NOT CLAIM')).toBeInTheDocument();
    expect(screen.getByText('No assumed quantum advantage')).toBeInTheDocument();
    expect(screen.getByText('No real quantum hardware execution')).toBeInTheDocument();
    expect(screen.getByText('No clinical validation')).toBeInTheDocument();
  });

  it('exposes the research flow and the layer-by-layer architecture matrix',()=>{
    view();
    expect(screen.getByText('CLASSICAL PREPROCESSING')).toBeInTheDocument();
    expect(screen.getByText('QUANTUM TRANSFORMATION')).toBeInTheDocument();
    expect(screen.getByText('CLASSICAL OUTPUT HEAD')).toBeInTheDocument();
    expect(screen.getByText('Classical preprocessing')).toBeInTheDocument();
    expect(screen.getByText('Quantum layer')).toBeInTheDocument();
    expect(screen.getByText('PyTorch head')).toBeInTheDocument();
    expect(screen.getByText('SHAP')).toBeInTheDocument();
  });

  it('links to the existing comparison and explainability experiences',()=>{
    view();
    expect(screen.getByRole('link',{name:/View 7-Model Comparison/i})).toHaveAttribute('href','/comparison');
    expect(screen.getByRole('link',{name:/Explainability/i})).toHaveAttribute('href','/explainability');
  });
});
