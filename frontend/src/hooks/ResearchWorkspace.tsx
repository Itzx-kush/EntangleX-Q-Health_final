import {createContext, useContext, useEffect, useMemo, useState, type ReactNode} from 'react';
import {useLocation} from 'react-router-dom';
import {api} from '../services/api';
import {useLoad} from './useLoad';
import {useDraft} from './ExperimentDraft';
import type {Dataset, Experiment, Job} from '../types';

type WorkflowStage = 'data' | 'quality' | 'preprocess' | 'features' | 'pca' | 'train' | 'evaluate' | 'explain' | 'predict' | 'experiment';
type WorkspaceState = {
  dataset?: Dataset;
  experiment?: Experiment;
  job?: Job;
  selectedModelLabel?: string;
  stage: WorkflowStage;
  focusMode: boolean;
  immersionMode: boolean;
  setFocusMode: (value: boolean) => void;
  setImmersionMode: (value: boolean) => void;
  datasetsLoading: boolean;
  jobs: Job[];
  experiments: Experiment[];
};

const emptyWorkspace: WorkspaceState = {
  stage: 'data', focusMode: false, immersionMode: false, setFocusMode: () => undefined, setImmersionMode: () => undefined,
  datasetsLoading: false, jobs: [], experiments: [],
};
const Context = createContext<WorkspaceState>(emptyWorkspace);

const stageForPath: Array<[string, WorkflowStage]> = [
  ['/datasets', 'data'], ['/quality', 'quality'], ['/preprocessing', 'preprocess'],
  ['/features', 'features'], ['/pca', 'pca'], ['/training', 'train'],
  ['/comparison', 'evaluate'], ['/explainability', 'explain'], ['/prediction', 'predict'],
  ['/experiments', 'experiment'], ['/quantum', 'experiment'],
];

function stageFor(pathname: string): WorkflowStage {
  return stageForPath.find(([path]) => pathname === path || pathname.startsWith(`${path}/`))?.[1] ?? 'data';
}

export function ResearchWorkspaceProvider({children}: {children: ReactNode}) {
  const {pathname} = useLocation();
  const {draft} = useDraft();
  const datasets = useLoad(() => api.get<Dataset[]>('/datasets'), [], 15000);
  const jobs = useLoad(() => api.get<Job[]>('/training/jobs'), [], 5000);
  const experiments = useLoad(() => api.get<Experiment[]>('/experiments'), [], 10000);
  const [focusMode, setFocusMode] = useState(false);
  const [immersionMode, setImmersionMode] = useState(false);
  const [selectedExperimentId, setSelectedExperimentId] = useState(() => sessionStorage.getItem('qhealth-current-experiment') || '');

  const dataset = datasets.data?.find(item => item.id === draft.dataset_id);
  const experiment = useMemo(() => {
    const routeMatch = pathname.match(/^\/experiments\/([^/]+)/);
    const id = routeMatch?.[1] || selectedExperimentId;
    return experiments.data?.find(item => item.id === id);
  }, [experiments.data, pathname, selectedExperimentId]);
  const job = useMemo(() => {
    const related = jobs.data?.filter(item => item.experiment_id === experiment?.id) ?? [];
    return related.find(item => ['running', 'queued'].includes(item.status)) || related[0] || jobs.data?.find(item => ['running', 'queued'].includes(item.status));
  }, [experiment?.id, jobs.data]);

  useEffect(() => {
    if (experiment?.id) { setSelectedExperimentId(experiment.id); sessionStorage.setItem('qhealth-current-experiment', experiment.id); }
  }, [experiment?.id]);
  useEffect(() => {
    if (job?.experiment_id && job.experiment_id !== selectedExperimentId) {
      setSelectedExperimentId(job.experiment_id);
      sessionStorage.setItem('qhealth-current-experiment', job.experiment_id);
    }
  }, [job?.experiment_id, selectedExperimentId]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && focusMode) setFocusMode(false);
      if (event.key === 'Escape' && immersionMode) setImmersionMode(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [focusMode, immersionMode]);

  return <Context.Provider value={{
    dataset, experiment, job, stage: stageFor(pathname), focusMode, immersionMode,
    selectedModelLabel: draft.models[0],
    setFocusMode, setImmersionMode, datasetsLoading: datasets.loading, jobs: jobs.data ?? [], experiments: experiments.data ?? [],
  }}>{children}</Context.Provider>;
}

export function useResearchWorkspace() {
  return useContext(Context);
}