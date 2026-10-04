import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Download,FileText,FlaskConical,LogIn,RefreshCw,Trash2} from 'lucide-react';
import {Link,useNavigate,useParams} from 'react-router-dom';
import {useAuth} from '../auth/AuthProvider';
import {qh} from '../lib/api';
import type {SavedResearchReport} from '../types/qhealth';
import {dateTime,metric,shortId} from '../utils/format';
import {Button,Card} from '../components/ui';
import {EmptyState,ErrorBanner,Loading,MetricCard,Notice,PageHeader,StatusBadge} from '../components/Shared';

function resultSummary(report:SavedResearchReport){
  const result=report.primary_result;
  return result?`${result.model} · ${result.metric.replaceAll('_',' ').toUpperCase()} ${metric(result.value)}`:'Primary result not recorded';
}

export function ResearchReportsPage(){
  const {session,isAuthenticated,leaveGuestMode}=useAuth();
  const token=session?.access_token||'';
  const queryClient=useQueryClient();
  const reports=useQuery({queryKey:['saved-research-reports'],queryFn:()=>qh.savedResearchReports(token),enabled:Boolean(isAuthenticated&&token),retry:false});
  const remove=useMutation({
    mutationFn:(report:SavedResearchReport)=>qh.deleteSavedResearchReport(report.saved_report_id,token),
    onSuccess:()=>queryClient.invalidateQueries({queryKey:['saved-research-reports']}),
  });
  const download=useMutation({mutationFn:(report:SavedResearchReport)=>qh.downloadSavedResearchReport(report.saved_report_id,report.experiment_id,token)});
  const confirmDelete=(report:SavedResearchReport)=>{
    if(window.confirm('Delete this saved research report?\n\nThis removes the saved copy from My Research. The original experiment and research evidence remain intact.'))remove.mutate(report);
  };

  if(!isAuthenticated)return <div><PageHeader eyebrow="Personal research" title="My Research Reports" description="Private saved reports are available only after sign-in."/><Card title="Guest mode is active" description="PDF download from Experiment Detail remains available without an account."><Button onClick={leaveGuestMode}><LogIn size={14}/>Sign in with Google or GitHub</Button></Card></div>;
  return <div>
    <PageHeader eyebrow="Personal research" title="My Research Reports" description="Persistent, private PDF research artifacts linked to their canonical experiments." actions={<Link className="btn btn-outline" to="/my-research">Research activity</Link>}/>
    <ErrorBanner error={(reports.error as Error)?.message||(remove.error as Error)?.message||(download.error as Error)?.message}/>
    {reports.isLoading?<Loading/>:reports.isError?<Card title="Saved reports unavailable" description="The private research library could not be loaded."><Button variant="outline" onClick={()=>reports.refetch()}><RefreshCw size={14}/>Retry</Button></Card>:reports.data?.length?<div className="grid gap-5 lg:grid-cols-2">{reports.data.map(report=><Card key={report.saved_report_id} title={report.title} description={resultSummary(report)}>
      <div className="flex flex-wrap gap-2"><StatusBadge value={report.status}/><span className="mono text-xs muted">v{report.report_version} · {shortId(report.saved_report_id)}</span></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2"><MetricCard label="EXPERIMENT" value={report.experiment_name||shortId(report.experiment_id)} detail={report.dataset_name||'Dataset not recorded'}/><MetricCard label="SAVED" value={dateTime(report.saved_at)} detail={`Generated ${dateTime(report.generated_at)}`}/></div>
      <p className="mt-3 break-all text-xs muted">Evidence package: {report.evidence_package_fingerprint?`${report.evidence_package_fingerprint.slice(0,16)}…`:report.evidence_package_id?shortId(report.evidence_package_id):'Not recorded'} · Report fingerprint: {report.report_fingerprint.slice(0,16)}…</p>
      <div className="mt-4 flex flex-wrap gap-2"><Link className="btn btn-outline" to={`/experiments/${report.experiment_id}`}><FlaskConical size={13}/>Open Experiment</Link><Button variant="outline" disabled={download.isPending} onClick={()=>download.mutate(report)}><Download size={13}/>Download PDF</Button><Link className="btn btn-outline" to={`/my-research/reports/${report.saved_report_id}`}><FileText size={13}/>View Details</Link><Button variant="ghost" disabled={remove.isPending} onClick={()=>confirmDelete(report)}><Trash2 size={13}/>Delete</Button></div>
    </Card>)}</div>:<EmptyState title="No saved research reports yet.">Complete an experiment and save its research report to keep a persistent copy in My Research.</EmptyState>}
  </div>;
}

export function ResearchReportDetailPage(){
  const {savedReportId=''}=useParams();
  const navigate=useNavigate();
  const {session,isAuthenticated,leaveGuestMode}=useAuth();
  const token=session?.access_token||'';
  const queryClient=useQueryClient();
  const report=useQuery({queryKey:['saved-research-report',savedReportId],queryFn:()=>qh.savedResearchReport(savedReportId,token),enabled:Boolean(isAuthenticated&&token&&savedReportId),retry:false});
  const download=useMutation({mutationFn:(value:SavedResearchReport)=>qh.downloadSavedResearchReport(value.saved_report_id,value.experiment_id,token)});
  const remove=useMutation({mutationFn:(value:SavedResearchReport)=>qh.deleteSavedResearchReport(value.saved_report_id,token),onSuccess:async()=>{await queryClient.invalidateQueries({queryKey:['saved-research-reports']});navigate('/my-research/reports')}});
  if(!isAuthenticated)return <div><PageHeader eyebrow="Personal research" title="Research Report" description="Sign in to view this private saved artifact."/><Button onClick={leaveGuestMode}><LogIn size={14}/>Sign in with Google or GitHub</Button></div>;
  if(report.isLoading)return <Loading/>;
  if(report.isError||!report.data)return <div><PageHeader eyebrow="Personal research" title="Research Report" description="This saved artifact is unavailable for the current account."/><ErrorBanner error={(report.error as Error)?.message}/><Link className="btn btn-outline" to="/my-research/reports">Back to reports</Link></div>;
  const value=report.data;
  const confirmDelete=()=>{if(window.confirm('Delete this saved research report?\n\nThis removes the saved copy from My Research. The original experiment and research evidence remain intact.'))remove.mutate(value)};
  return <div><PageHeader eyebrow="Personal research" title="Research Report" description="Private saved-artifact details; the canonical experiment remains the scientific source of truth." actions={<Link className="btn btn-outline" to="/my-research/reports">All reports</Link>}/><ErrorBanner error={(download.error as Error)?.message||(remove.error as Error)?.message}/><Card title={value.title} description={resultSummary(value)}>
    <div className="grid gap-4 md:grid-cols-2"><MetricCard label="EXPERIMENT" value={value.experiment_name||shortId(value.experiment_id)} detail={value.experiment_id}/><MetricCard label="DATASET" value={value.dataset_name||'Not recorded'} detail="Snapshot at save time"/><MetricCard label="GENERATED" value={dateTime(value.generated_at)} detail={`Report version ${value.report_version}`}/><MetricCard label="SAVED" value={dateTime(value.saved_at)} detail={`${value.size_bytes.toLocaleString()} bytes`}/></div>
    <div className="mt-4 space-y-2 break-all text-xs"><p><strong>Evidence package:</strong> {value.evidence_package_id||'Not recorded'}</p><p><strong>Evidence-package fingerprint:</strong> {value.evidence_package_fingerprint||'Not recorded'}</p><p><strong>Report fingerprint:</strong> {value.report_fingerprint}</p><p><strong>Integrity SHA-256:</strong> {value.integrity_hash}</p></div>
    <Notice tone="blue">This saved copy does not modify the original experiment, evidence package, dataset, models, or scientific results.</Notice>
    <div className="mt-4 flex flex-wrap gap-2"><Button disabled={download.isPending} onClick={()=>download.mutate(value)}><Download size={14}/>Download PDF</Button><Link className="btn btn-outline" to={`/experiments/${value.experiment_id}`}><FlaskConical size={13}/>Open Experiment</Link><Button variant="ghost" disabled={remove.isPending} onClick={confirmDelete}><Trash2 size={13}/>Delete Saved Report</Button></div>
  </Card></div>;
}
