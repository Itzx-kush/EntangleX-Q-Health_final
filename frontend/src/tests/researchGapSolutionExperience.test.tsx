import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {ResearchGapSolutionExperience} from '../components/ResearchGapSolutionExperience';

function view(extra?:{datasetName?:string;hybridDetailPath?:string}){
  return render(
    <MemoryRouter>
      <ResearchGapSolutionExperience datasetName={extra?.datasetName} hybridDetailPath={extra?.hybridDetailPath}/>
    </MemoryRouter>
  );
}

describe('ResearchGapSolutionExperience narrative',()=>{
  it('renders the research gap and our-solution framing',()=>{
    view();
    expect(screen.getByRole('heading',{name:/research gap.*our solution/i})).toBeInTheDocument();
    expect(screen.getByText(/Hybrid QML is difficult to evaluate meaningfully/)).toBeInTheDocument();
    expect(screen.getByText(/Quantum models need classical controls/)).toBeInTheDocument();
    expect(screen.getByText('OUR SOLUTION — ENTANGLEX Q-HEALTH')).toBeInTheDocument();
    expect(screen.getByText('7-model controlled comparison')).toBeInTheDocument();
    expect(screen.getByText('Sensitivity-first evaluation')).toBeInTheDocument();
    expect(screen.getByText('SHAP explainability')).toBeInTheDocument();
    expect(screen.getByText('Provenance / reproducibility')).toBeInTheDocument();
  });

  it('frames the contribution as integration, with what-is-not-novel honesty',()=>{
    view();
    expect(screen.getByText('OUR CONTRIBUTION')).toBeInTheDocument();
    expect(screen.getByText(/combines hybrid QML, controlled cross-family benchmarking/i)).toBeInTheDocument();
    expect(screen.getByText(/A contribution statement, not a universal novelty claim/i)).toBeInTheDocument();
    expect(screen.getByText('BUILT ON ESTABLISHED METHODS')).toBeInTheDocument();
    expect(screen.getByText(/Qiskit-based quantum models, PennyLane, PyTorch, SHAP/i)).toBeInTheDocument();
  });

  it('renders the what-we-add matrix and research flow with actual model families',()=>{
    view();
    expect(screen.getByText('WHAT WE ADD')).toBeInTheDocument();
    expect(screen.getByText('Logistic Regression · SVM · Random Forest')).toBeInTheDocument();
    expect(screen.getByText('VQC · QSVC · QNN')).toBeInTheDocument();
    expect(screen.getByText('RESEARCH-TO-PRODUCT FLOW')).toBeInTheDocument();
    expect(screen.getByText('HYBRID IMPLEMENTATION')).toBeInTheDocument();
    expect(screen.getByText('RESEARCH INSIGHT')).toBeInTheDocument();
  });

  it('links to connected workflows and the scientific boundary',()=>{
    view();
    expect(screen.getByRole('link',{name:/View Controlled Comparison/i})).toHaveAttribute('href','/comparison');
    expect(screen.getByRole('link',{name:/Explainability/i})).toHaveAttribute('href','/explainability');
    expect(screen.getByRole('button',{name:/View Hybrid Architecture/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Why Hybrid/})).toBeInTheDocument();
    expect(screen.getByText(/no clinical validation, clinical diagnosis, real quantum hardware, or quantum advantage/i)).toBeInTheDocument();
  });
});
