import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import type {ReactNode} from 'react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ModelCardPanel} from '../components/ModelCardPanel';
import {CalibrationLaboratory} from '../pages/CalibrationLaboratory';
import {ThresholdAnalysis} from '../pages/ThresholdAnalysis';
import {QuantumDiagnostics} from '../pages/QuantumDiagnostics';
import {qh} from '../lib/api';

vi.mock('../lib/api',()=>({qh:{
  modelCard:vi.fn(), calibration_preflight:vi.fn(), create_calibration_study:vi.fn(),
  calibration_study:vi.fn(), threshold_preflight:vi.fn(), create_threshold_study:vi.fn(),
  threshold_study:vi.fn(), quantum_diagnostics_preflight:vi.fn(),
  quantum_diagnostics_by_run:vi.fn(), create_quantum_diagnostics:vi.fn(),
}}));

const model={id:'11111111-1111-4111-8111-111111111111',experiment_id:'22222222-2222-4222-8222-222222222222',dataset_id:'33333333-3333-4333-8333-333333333333',model_type:'logistic_regression',status:'ready',details:{},metrics:{},created_at:'2026-10-03T00:00:00Z'} as any;
const quantum={...model,id:'44444444-4444-4444-8444-444444444444',model_type:'vqc'};

function renderEvidence(node:ReactNode){
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}})}>{node}</QueryClientProvider>);
}

describe('research evidence integrations',()=>{
  beforeEach(()=>vi.clearAllMocks());

  it('renders a canonical Model Card while disclosing unavailable evidence',async()=>{
    vi.mocked(qh.modelCard).mockResolvedValue({
      schema_version:'model_card_v1',card_id:'card-1',generated_at:'2026-10-03T00:00:00Z',card_status:'COMPLETE_WITH_LIMITATIONS',
      model_identity:{model_id:model.id},task:{condition_task_status:'not_configured'},data:{dataset_id:model.dataset_id},training:{},model:{},
      evaluation:{status:'available'},multi_seed_evidence:{status:'not_available'},calibration:{status:'not_available'},threshold:{status:'not_available'},
      robustness:{status:'not_available'},external_validation:{status:'not_available'},distribution_shift:{status:'not_available'},group_validation:{status:'not_applicable'},quantum:{status:'not_applicable'},
      provenance:{source_context:{type:'verified_demo_experiment'}},reproducibility:{status:'verified_precomputed_package'},artifact:{artifact_id:'artifact-1'},
      limitations:[{category:'research_use',description:'Research only'}],evidence_gaps:[{category:'calibration',status:'not_available',description:'No study'}],
    } as any);
    renderEvidence(<ModelCardPanel model={model}/>);
    expect(await screen.findByText('COMPLETE WITH LIMITATIONS')).toBeInTheDocument();
    expect(screen.getAllByText('NOT AVAILABLE').length).toBeGreaterThan(0);
    expect(screen.getByText('RESEARCH EVALUATION ONLY')).toBeInTheDocument();
  });

  it('runs calibration and renders computed metrics, while blocking an infeasible model',async()=>{
    vi.mocked(qh.calibration_preflight).mockResolvedValue({feasible:true,limitations:[],method_support:{none:true,sigmoid:true,isotonic:true,temperature_scaling:true},source_context_type:'verified_demo_experiment'});
    vi.mocked(qh.create_calibration_study).mockResolvedValue({id:'cal-1',status:'created'});
    vi.mocked(qh.calibration_study).mockResolvedValue({id:'cal-1',status:'completed',metrics:{brier_score:.12,log_loss:.3,expected_calibration_error:.04,maximum_calibration_error:.08},curves:{reliability_curve:[]},summary:{},limitations:[],provenance:{type:'verified_demo_experiment'}});
    const {unmount}=renderEvidence(<CalibrationLaboratory model={model}/>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Evaluate'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Evaluate'}));
    expect(await screen.findByText('0.1200')).toBeInTheDocument();
    unmount();

    vi.mocked(qh.calibration_preflight).mockResolvedValue({feasible:false,limitations:['Calibration is not applicable to quantum-family models.'],method_support:{none:false},source_context_type:'verified_demo_experiment'});
    renderEvidence(<CalibrationLaboratory model={quantum}/>);
    expect(await screen.findByText(/not applicable to quantum-family models/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Evaluate'})).toBeDisabled();
  });

  it('runs controlled threshold analysis and renders the frozen operating point',async()=>{
    vi.mocked(qh.threshold_preflight).mockResolvedValue({feasible:true,limitations:[],method_support:{dedicated_split:true},source_context_type:'verified_demo_experiment'});
    vi.mocked(qh.create_threshold_study).mockResolvedValue({id:'threshold-1',status:'created'});
    vi.mocked(qh.threshold_study).mockResolvedValue({id:'threshold-1',status:'completed',results:{feasible:true,selected_operating_point:{threshold:.42,sensitivity:.9,specificity:.8,f1:.85,tp:9,tn:8,fp:2,fn:1},sweep:[]},curves:{},summary:{},limitations:[],configuration:{selection_protocol:'dedicated_split'},provenance:{type:'verified_demo_experiment'}});
    renderEvidence(<ThresholdAnalysis model={model}/>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Evaluate'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Evaluate'}));
    expect(await screen.findByText('0.4200')).toBeInTheDocument();
    expect(screen.getByText('9')).toBeInTheDocument();
  });

  it('generates diagnostics without reload and shows classical not-applicable state',async()=>{
    const report={id:'diag-1',experiment_id:quantum.experiment_id,model_record_id:quantum.id,model_type:'vqc',status:'completed',created_at:'2026-10-03T00:00:00Z',model_configuration:{},feature_encoding:{qubit_count:4,mapping_strategy:'ZZFeatureMap',dimensionality_reduction:'pca',original_features:4},circuit_structure:{ansatz:'RealAmplitudes',entanglement_pattern:'linear',depth:3,parameterized_gates:8},resource_profile:{},optimizer_profile:{},training_profile:{},execution_profile:{backend:'statevector',execution_mode:'local_simulator'},stability_profile:{},noise_profile:{noise_enabled:false},warnings:[],limitations:['Loss curve history unavailable'],configuration_fingerprint:'fp',provenance:{type:'verified_demo_experiment'}};
    vi.mocked(qh.quantum_diagnostics_preflight).mockResolvedValue({feasible:true,limitations:[],warnings:[],unsupported_fields:[]});
    vi.mocked(qh.quantum_diagnostics_by_run).mockRejectedValue(new Error('No diagnostics report exists for this model.'));
    vi.mocked(qh.create_quantum_diagnostics).mockResolvedValue(report);
    const {unmount}=renderEvidence(<QuantumDiagnostics model={quantum}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Generate Diagnostics'}));
    expect(await screen.findByText('ZZFeatureMap')).toBeInTheDocument();
    unmount();

    vi.mocked(qh.quantum_diagnostics_preflight).mockResolvedValue({feasible:false,limitations:['Classical models do not support quantum diagnostics.'],warnings:[],unsupported_fields:[]});
    vi.mocked(qh.quantum_diagnostics_by_run).mockRejectedValue(new Error('No report'));
    renderEvidence(<QuantumDiagnostics model={model}/>);
    expect(await screen.findByText(/Classical models do not support quantum diagnostics/i)).toBeInTheDocument();
  });
});