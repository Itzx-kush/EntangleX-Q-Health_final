import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {ResearchReportSection} from '../pages/ResearchPagesStudio';
import {ResearchReportsPage} from '../research/ResearchReportsPage';
import {useAuth} from '../auth/AuthProvider';
import {qh} from '../lib/api';
import type {SavedResearchReport} from '../types/qhealth';

vi.mock('../auth/AuthProvider',()=>({useAuth:vi.fn()}));
vi.mock('../lib/api',()=>({qh:{
  savedResearchReports:vi.fn(),downloadSavedResearchReport:vi.fn(),deleteSavedResearchReport:vi.fn(),
}}));

const report:SavedResearchReport={
  saved_report_id:'11111111-1111-4111-8111-111111111111',title:'EntangleX Q-Health Research Experiment Report',
  experiment_id:'22222222-2222-4222-8222-222222222222',experiment_name:'Persisted experiment',dataset_name:'Verified dataset',
  report_version:'1',evidence_package_id:'33333333-3333-4333-8333-333333333333',evidence_package_fingerprint:'f'.repeat(64),
  report_artifact_id:null,report_fingerprint:'a'.repeat(64),integrity_hash:'b'.repeat(64),generated_at:'2026-10-04T07:00:00Z',
  saved_at:'2026-10-04T07:05:00Z',size_bytes:12345,content_type:'application/pdf',status:'active',
  primary_result:{model:'Random Forest',metric:'roc_auc',value:.91},
};

function wrapper(children:React.ReactNode){
  const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
  return render(<MemoryRouter><QueryClientProvider client={client}>{children}</QueryClientProvider></MemoryRouter>);
}

beforeEach(()=>{
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({session:{access_token:'session-token'},isAuthenticated:true,leaveGuestMode:vi.fn()} as any);
});

describe('Research Report section',()=>{
  const base={id:report.experiment_id,savedLoading:false,pdfBusy:false,pdfSuccess:false,saveBusy:false,saveSuccess:false,onDownload:vi.fn(),onSave:vi.fn(),onSignIn:vi.fn()};

  it('keeps guest PDF download available and does not expose save',()=>{
    const onDownload=vi.fn(),onSignIn=vi.fn();
    wrapper(<ResearchReportSection {...base} isAuthenticated={false} onDownload={onDownload} onSignIn={onSignIn}/>);
    fireEvent.click(screen.getByRole('button',{name:'Download PDF Report'}));
    expect(onDownload).toHaveBeenCalledOnce();
    expect(screen.queryByRole('button',{name:'Save to My Research'})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Sign in to save'}));
    expect(onSignIn).toHaveBeenCalledOnce();
  });

  it('supports authenticated save, loading, success, saved, and safe error states',()=>{
    const onSave=vi.fn();
    const view=wrapper(<ResearchReportSection {...base} isAuthenticated onSave={onSave}/>);
    fireEvent.click(screen.getByRole('button',{name:'Save to My Research'}));
    expect(onSave).toHaveBeenCalledOnce();
    view.rerender(<MemoryRouter><QueryClientProvider client={new QueryClient()}><ResearchReportSection {...base} isAuthenticated saveBusy onSave={onSave}/></QueryClientProvider></MemoryRouter>);
    expect(screen.getByRole('button',{name:'Saving…'})).toBeDisabled();
    view.rerender(<MemoryRouter><QueryClientProvider client={new QueryClient()}><ResearchReportSection {...base} isAuthenticated saveSuccess savedReport={report} error="Storage is temporarily unavailable."/></QueryClientProvider></MemoryRouter>);
    expect(screen.getByText('Research report saved to My Research.')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Saved to My Research'})).toBeDisabled();
    expect(screen.getByText('Storage is temporarily unavailable.')).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'View saved report'})).toHaveAttribute('href',`/my-research/reports/${report.saved_report_id}`);
  });
});

describe('My Research Reports page',()=>{
  it('renders the authenticated empty state without treating it as an error',async()=>{
    vi.mocked(qh.savedResearchReports).mockResolvedValue([]);
    wrapper(<ResearchReportsPage/>);
    expect(await screen.findByText('No saved research reports yet.')).toBeInTheDocument();
    expect(screen.getByText(/Complete an experiment and save its research report/)).toBeInTheDocument();
  });

  it('renders metadata and supports download, open, details, and confirmed delete',async()=>{
    vi.mocked(qh.savedResearchReports).mockResolvedValueOnce([report]).mockResolvedValue([]);
    vi.mocked(qh.downloadSavedResearchReport).mockResolvedValue(undefined);
    vi.mocked(qh.deleteSavedResearchReport).mockResolvedValue({saved_report_id:report.saved_report_id,status:'deleted'});
    vi.spyOn(window,'confirm').mockReturnValue(true);
    wrapper(<ResearchReportsPage/>);
    expect(await screen.findByText(report.title)).toBeInTheDocument();
    expect(screen.getByText(/Random Forest/)).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'Open Experiment'})).toHaveAttribute('href',`/experiments/${report.experiment_id}`);
    expect(screen.getByRole('link',{name:'View Details'})).toHaveAttribute('href',`/my-research/reports/${report.saved_report_id}`);
    fireEvent.click(screen.getByRole('button',{name:'Download PDF'}));
    await waitFor(()=>expect(qh.downloadSavedResearchReport).toHaveBeenCalledWith(report.saved_report_id,report.experiment_id,'session-token'));
    fireEvent.click(screen.getByRole('button',{name:'Delete'}));
    await waitFor(()=>expect(qh.deleteSavedResearchReport).toHaveBeenCalledWith(report.saved_report_id,'session-token'));
    expect(await screen.findByText('No saved research reports yet.')).toBeInTheDocument();
  });

  it('separates guest and authenticated error behavior',async()=>{
    vi.mocked(useAuth).mockReturnValue({session:null,isAuthenticated:false,leaveGuestMode:vi.fn()} as any);
    const guest=wrapper(<ResearchReportsPage/>);
    expect(screen.getByText('Guest mode is active')).toBeInTheDocument();
    expect(qh.savedResearchReports).not.toHaveBeenCalled();
    guest.unmount();

    vi.mocked(useAuth).mockReturnValue({session:{access_token:'session-token'},isAuthenticated:true,leaveGuestMode:vi.fn()} as any);
    vi.mocked(qh.savedResearchReports).mockRejectedValue(new Error('Private library unavailable.'));
    wrapper(<ResearchReportsPage/>);
    expect(await screen.findByText('Saved reports unavailable')).toBeInTheDocument();
    expect(screen.getByText('Private library unavailable.')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Retry'})).toBeInTheDocument();
  });
});
