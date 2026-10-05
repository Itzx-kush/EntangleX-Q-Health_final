import {render,screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe,expect,it} from 'vitest';
import {ResearchBasisExperience} from '../components/ResearchBasisExperience';

function view(extra?:{datasetName?:string;hybridDetailPath?:string}){
  return render(
    <MemoryRouter>
      <ResearchBasisExperience datasetName={extra?.datasetName} hybridDetailPath={extra?.hybridDetailPath}/>
    </MemoryRouter>
  );
}

describe('ResearchBasisExperience',()=>{
  it('renders the research basis, themes, and verified reference cards',()=>{
    view();
    expect(screen.getByRole('heading',{name:/research basis.*verified references/i})).toBeInTheDocument();
    expect(screen.getAllByText('Quantum ML').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Hybrid QML').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Healthcare QML').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Explainability').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Quantum circuit learning')).toBeInTheDocument();
    expect(screen.getByText('A Unified Approach to Interpreting Model Predictions')).toBeInTheDocument();
    expect(screen.getByText(/Biamonte, J\./)).toBeInTheDocument();
    expect(screen.getByText(/Lundberg, S\.M\./)).toBeInTheDocument();
  });

  it('distinguishes established methods from EntangleX integration',()=>{
    view();
    expect(screen.getByText('ESTABLISHED METHODS')).toBeInTheDocument();
    expect(screen.getByText('ENTANGLEX INTEGRATION')).toBeInTheDocument();
    expect(screen.getByText('WHAT IS OUR CONTRIBUTION?')).toBeInTheDocument();
    expect(screen.getByText('WHAT IS NOT OUR CLAIM?')).toBeInTheDocument();
    expect(screen.getByText(/We do not claim to have invented QML, SHAP, PennyLane, PyTorch/i)).toBeInTheDocument();
  });

  it('renders literature boundary and future-work sections',()=>{
    view();
    expect(screen.getByText('WHAT THE LITERATURE SUPPORTS')).toBeInTheDocument();
    expect(screen.getByText('WHAT THE LITERATURE DOES NOT PROVE')).toBeInTheDocument();
    expect(screen.getByText('FUTURE WORK — NOT CURRENT CAPABILITIES')).toBeInTheDocument();
    expect(screen.getByText('Real quantum hardware evaluation')).toBeInTheDocument();
    expect(screen.getByText(/local quantum simulation, research prototype/i)).toBeInTheDocument();
  });

  it('exposes nine verified external links plus internal workflow links',()=>{
    view();
    const external=screen.getAllByRole('link').filter(link=>link.getAttribute('target')==='_blank');
    expect(external.length).toBe(9);
    const hrefs=external.map(link=>link.getAttribute('href'));
    expect(hrefs).toContain('https://www.nature.com/articles/nature23474');
    expect(hrefs).toContain('https://doi.org/10.1080/00107514.2014.964942');
    expect(hrefs).toContain('https://link.aps.org/doi/10.1103/PhysRevA.98.032309');
    expect(hrefs).toContain('https://pubmed.ncbi.nlm.nih.gov/30385997/');
    expect(hrefs).toContain('https://arxiv.org/abs/2301.09106');
    expect(hrefs).toContain('https://proceedings.neurips.cc/paper/2017/hash/8a20a8621978632d76c43dfd28b67767-Abstract.html');
    expect(screen.getByRole('link',{name:/View 7-Model Comparison/i})).toHaveAttribute('href','/comparison');
    expect(screen.getByRole('link',{name:/View SHAP Evidence/i})).toHaveAttribute('href','/explainability');
    expect(screen.getByRole('button',{name:/View Hybrid Architecture/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Why Hybrid/})).toBeInTheDocument();
  });
});
