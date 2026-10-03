import {fireEvent,render,screen} from '@testing-library/react';
import {describe,expect,it,vi} from 'vitest';
import {ResearchTraceability} from '../pages/ResearchPagesStudio';
import type {TraceabilityEvidence} from '../types/qhealth';

const base:TraceabilityEvidence={
  dataset:{id:'dataset-12345678',name:'Diabetes benchmark',domain:'biomedical',source:'Recorded source',positive_class:'positive',sha256:'a'.repeat(64),created_at:'2026-01-01T00:00:00Z',version:{id:'version-12345678',label:'v1',content_sha256:'b'.repeat(64),schema_fingerprint:'c'.repeat(64),created_at:'2026-01-01T00:00:00Z'}},
  experiment:{id:'experiment-12345678',name:'Comparison',status:'completed',created_at:'2026-01-01T00:00:00Z',parent_id:null,configuration_fingerprint:'d'.repeat(64),configuration:{model_families:['logistic_regression'],random_seed:42,test_size:.2,cv_folds:5,sample_budget:100,preprocessing:{scaler:'standard'},feature_configuration:{selection:'anova'},threshold_strategy:'target_sensitivity'}},
  run:{id:'run-12345678',status:'completed',created_at:'2026-01-01T00:00:00Z',started_at:'2026-01-01T00:00:00Z',completed_at:'2026-01-01T00:01:00Z',duration_seconds:60,reproducibility_status:'CONFIGURATION_RECORDED',reproducibility_metadata:{seed:42},job:{id:'job-12345678',status:'succeeded',started_at:'2026-01-01T00:00:00Z',completed_at:'2026-01-01T00:01:00Z'}},
  models:[{id:'model-12345678',run_id:'run-12345678',model_family:'logistic_regression',status:'ready',artifact_hash:'e'.repeat(64),artifact_ids:['artifact-12345678']}],
  artifacts:[{id:'artifact-12345678',type:'model',name:'Model',run_id:'run-12345678',model_id:'model-12345678',integrity_hash:'f'.repeat(64),hash_algorithm:'sha256',storage_status:'recorded',immutable:true}],
  evidence:{html_report_available:true,json_report_available:true,package_count:1,latest_package_id:'package-12345678'},
  audit:{events_recorded:true,description:'Integrity-linked audit records'},
  reproducibility:{status:'RECORDED',recorded_fields:['dataset_hash'],label:'Reproducibility metadata recorded',claim:'Recorded metadata only.'},
};

describe('ResearchTraceability',()=>{
  it('renders the complete recorded chain and secure report actions',()=>{
    render(<ResearchTraceability value={base} onReport={vi.fn()}/>);
    expect(screen.getByText('WHAT PRODUCED THIS RESULT?')).toBeInTheDocument();
    expect(screen.getByText('REPRODUCIBILITY METADATA RECORDED')).toBeInTheDocument();
    expect(screen.getByText('✓ HTML report available')).toBeInTheDocument();
    expect(screen.getByText('✓ Integrity-linked audit records')).toBeInTheDocument();
  });

  it('renders rerun and missing evidence states without fabrication',()=>{
    const partial:TraceabilityEvidence={...base,
      experiment:{...base.experiment,parent_id:'parent-12345678',configuration_fingerprint:null},
      run:null,models:[],artifacts:[],
      evidence:{html_report_available:false,json_report_available:false,package_count:0,latest_package_id:null},
      audit:{events_recorded:false,description:'Audit events not recorded'},
      reproducibility:{status:'PARTIAL',recorded_fields:['dataset_hash'],label:'Partial reproducibility metadata',claim:'Recorded metadata only.'},
    };
    render(<ResearchTraceability value={partial} onReport={vi.fn()}/>);
    expect(screen.getByText(/Rerun of parent/)).toBeInTheDocument();
    expect(screen.getByText('— Artifact not available')).toBeInTheDocument();
    expect(screen.getByText('— HTML report not available')).toBeInTheDocument();
    expect(screen.getByText('— Audit events not recorded')).toBeInTheDocument();
  });

  it('expands exact recorded metadata on request',()=>{
    render(<ResearchTraceability value={base} onReport={vi.fn()}/>);
    fireEvent.click(screen.getByRole('button',{name:'Detailed traceability'}));
    expect(screen.getByText('Exact recorded traceability metadata')).toBeInTheDocument();
  });
});