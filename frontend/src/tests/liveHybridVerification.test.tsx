import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach,beforeEach,describe,expect,it,vi,type MockInstance} from 'vitest';
import {LiveHybridVerification} from '../components/LiveHybridVerification';
import {ApiError,ApiTransportError,qh} from '../lib/api';
import type {HybridRuntimeCheck,HybridRuntimeVerification} from '../types/qhealth';

const ALL_PASS_CHECKS:Record<string,HybridRuntimeCheck>={
  pennylane_import:{status:'PASS',detail:'PennyLane imported successfully.'},
  pytorch_import:{status:'PASS',detail:'PyTorch imported successfully.'},
  quantum_device_initialization:{status:'PASS',detail:'PennyLane default.qubit initialized successfully.'},
  preprocessing_and_feature_reduction:{status:'PASS',detail:'Existing preprocessing produced a 4-component representation for the 4-qubit hybrid model.'},
  hybrid_training:{status:'PASS',detail:'Real hybrid CV training and final fitting completed.'},
  quantum_forward_pass:{status:'PASS',detail:'Quantum layer returned 4 expectation values per sample.'},
  trainable_quantum_parameters:{status:'PASS',detail:'Recorded quantum parameters changed between initialization and the final optimizer step.'},
  positive_class_probability:{status:'PASS',detail:'The real PyTorch output head produced a finite positive-class probability.'},
  sensitivity_first_threshold:{status:'PASS',detail:'Prediction used the existing target_sensitivity operating-point logic.'},
  shap_explainability:{status:'PASS',detail:'SHAP evaluated the real hybrid positive-class output for one held-out case.'},
  artifact_save:{status:'PASS',detail:'Existing HMAC-protected model artifact save completed.'},
  artifact_reload:{status:'PASS',detail:'Saved hybrid artifact reloaded into a rebuilt PennyLane runtime and produced a valid probability.'},
};

function verifiedFixture():HybridRuntimeVerification{
  return {
    status:'VERIFIED',
    verified:true,
    verification_kind:'live_runtime',
    dataset:'Early Stage Diabetes Risk Prediction',
    model_type:'hybrid_pennylane_torch',
    framework:'PennyLane',
    classical_framework:'PyTorch',
    execution:'local PennyLane quantum simulation',
    backend:'default.qubit',
    real_hardware:false,
    checks:ALL_PASS_CHECKS,
    configuration:{qubits:4,quantum_layers:2,hidden_dimensions:[8,4],epochs:10,batch_size:16,sample_cap:200,cv_folds:3,seed:42},
    prediction:{positive_class_probability:0.83,predicted_positive_class:1,operating_threshold:0.62,threshold_source:'out_of_fold_validation',threshold_strategy:'target_sensitivity',target_sensitivity:0.9},
    quantum:{expectation_value_dimension:4,quantum_parameters_changed:true},
    artifact:{saved:true,reloaded:true},
    shap:{explained_case_count:1,background_count:120,output_semantics:'final positive-class probability'},
    verified_at:'2026-10-05T10:00:00Z',
    scientific_status:'Verified live hybrid runtime using local quantum simulation; not clinical validation and not evidence of quantum advantage.',
  };
}

function failedFixture():HybridRuntimeVerification{
  return {
    status:'FAILED',
    verified:false,
    verification_kind:'live_runtime',
    dataset:'Early Stage Diabetes Risk Prediction',
    model_type:'hybrid_pennylane_torch',
    framework:'PennyLane',
    classical_framework:'PyTorch',
    execution:'local PennyLane quantum simulation',
    backend:'default.qubit',
    real_hardware:false,
    checks:{
      pennylane_import:{status:'PASS',detail:'PennyLane imported successfully.'},
      pytorch_import:{status:'FAIL',detail:'PyTorch is not installed in the backend environment.'},
    },
    error:'The live hybrid path cannot execute because PyTorch is unavailable.',
    verified_at:'2026-10-05T10:02:00Z',
    scientific_status:'Research prototype runtime verification; not clinical validation and not evidence of quantum advantage.',
  };
}

function view(){
  return render(<MemoryRouter><LiveHybridVerification datasetName="Early Stage Diabetes Risk Prediction" hybridDetailPath="/experiments/exp1"/></MemoryRouter>);
}

describe('LiveHybridVerification',()=>{
  let mockRun:MockInstance<(force?:boolean)=>Promise<HybridRuntimeVerification>>;

  beforeEach(()=>{
    mockRun=vi.spyOn(qh,'hybridRuntimeVerification');
  });

  afterEach(()=>{
    vi.restoreAllMocks();
  });

  it('shows the initial NOT RUN state and does not call the backend on mount',()=>{
    view();
    expect(screen.getByText('NOT RUN')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/run live verification/i})).toBeEnabled();
    expect(mockRun).not.toHaveBeenCalled();
  });

  it('shows a running state, disables the button, then renders the verified result',async()=>{
    let resolveRun:(value:HybridRuntimeVerification)=>void=()=>undefined;
    mockRun.mockImplementation(()=>new Promise<HybridRuntimeVerification>(resolve=>{resolveRun=resolve;}));
    view();
    fireEvent.click(screen.getByRole('button',{name:/run live verification/i}));
    expect(screen.getByText(/RUNNING LIVE VERIFICATION/i)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/running/i})).toBeDisabled();

    resolveRun(verifiedFixture());
    await waitFor(()=>{
      expect(screen.getAllByText('LIVE HYBRID VERIFIED').length).toBeGreaterThan(0);
    });
    expect(screen.queryByText(/RUNNING LIVE VERIFICATION/i)).not.toBeInTheDocument();
  });

  it('renders every backend check, the real probability, threshold, SHAP and artifact reload',()=>{
    mockRun.mockResolvedValue(verifiedFixture());
    view();
    fireEvent.click(screen.getByRole('button',{name:/run live verification/i}));
    return waitFor(()=>{
      expect(screen.getAllByText('LIVE HYBRID VERIFIED').length).toBeGreaterThan(0);
      expect(screen.getAllByText('PASS').length).toBe(14);
      expect(screen.getByText('PennyLane import')).toBeInTheDocument();
      expect(screen.getByText('PyTorch import')).toBeInTheDocument();
      expect(screen.getByText('Quantum device initialization')).toBeInTheDocument();
      expect(screen.getByText('Preprocessing / feature reduction')).toBeInTheDocument();
      expect(screen.getByText('Hybrid training')).toBeInTheDocument();
      expect(screen.getByText('Quantum forward pass')).toBeInTheDocument();
      expect(screen.getByText('Trainable quantum parameters')).toBeInTheDocument();
      expect(screen.getByText('Positive-class probability')).toBeInTheDocument();
      expect(screen.getByText('Sensitivity-first threshold')).toBeInTheDocument();
      expect(screen.getByText('SHAP explainability')).toBeInTheDocument();
      expect(screen.getAllByText('Artifact save').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Artifact reload').length).toBeGreaterThan(0);
      expect(screen.getByText('83%')).toBeInTheDocument();
      expect(screen.getByText('0.62')).toBeInTheDocument();
      expect(screen.getByText('out_of_fold_validation')).toBeInTheDocument();
      expect(screen.getByText('final positive-class probability')).toBeInTheDocument();
      expect(screen.getByText('Last live verification')).toBeInTheDocument();
    });
  });

  it('shows the failed result with the failed check, safe error and retry without fake success',()=>{
    mockRun.mockResolvedValue(failedFixture());
    view();
    fireEvent.click(screen.getByRole('button',{name:/run live verification/i}));
    return waitFor(()=>{
      expect(screen.getAllByText('LIVE HYBRID VERIFICATION FAILED').length).toBeGreaterThan(0);
      expect(screen.getByText('The live hybrid path cannot execute because PyTorch is unavailable.')).toBeInTheDocument();
      expect(screen.getByText('PyTorch is not installed in the backend environment.')).toBeInTheDocument();
      expect(screen.getByText(/Verified Demo remains available/i)).toBeInTheDocument();
      expect(screen.getByRole('button',{name:/re-verify live runtime/i})).toBeEnabled();
      expect(screen.queryByText('LIVE HYBRID VERIFIED')).not.toBeInTheDocument();
      expect(screen.queryByText('NOT RUN')).not.toBeInTheDocument();
    });
  });

  it('distinguishes a transport failure from a backend verification failure',()=>{
    mockRun.mockRejectedValue(new ApiTransportError('Unable to reach the Q-Health backend while requesting /hybrid/runtime-verification.'));
    view();
    fireEvent.click(screen.getByRole('button',{name:/run live verification/i}));
    return waitFor(()=>{
      expect(screen.getByText(/Unable to reach live verifier/i)).toBeInTheDocument();
      expect(screen.queryByText('LIVE HYBRID VERIFICATION FAILED')).not.toBeInTheDocument();
      expect(screen.queryByText('LIVE HYBRID VERIFIED')).not.toBeInTheDocument();
    });
  });

  it('distinguishes an API error from a backend verification result',()=>{
    mockRun.mockRejectedValue(new ApiError('Not authorized',{status:401,code:'unauthorized'}));
    view();
    fireEvent.click(screen.getByRole('button',{name:/run live verification/i}));
    return waitFor(()=>{
      expect(screen.getByText(/The backend verifier endpoint returned an error/i)).toBeInTheDocument();
      expect(screen.queryByText('LIVE HYBRID VERIFICATION FAILED')).not.toBeInTheDocument();
    });
  });
});

describe('qh.hybridRuntimeVerification API contract',()=>{
  afterEach(()=>{
    vi.unstubAllGlobals();
  });

  it('requests /api/hybrid/runtime-verification and appends force=true only for reruns',async()=>{
    const fetchMock=vi.fn(async(_input:RequestInfo|URL,_init?:RequestInit)=>new Response(JSON.stringify({status:'VERIFIED',verified:true}),{status:200,headers:{'Content-Type':'application/json'}}));
    vi.stubGlobal('fetch',fetchMock);
    await qh.hybridRuntimeVerification();
    await qh.hybridRuntimeVerification(true);
    const urls=fetchMock.mock.calls.map(call=>String(call[0]));
    expect(urls[0]).toBe('/api/hybrid/runtime-verification');
    expect(urls[1]).toBe('/api/hybrid/runtime-verification?force=true');
  });
});
