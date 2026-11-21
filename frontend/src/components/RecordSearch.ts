import {useQuery} from '@tanstack/react-query';
import {qh} from '../lib/api';
import {modelLabels, shortId} from '../utils/format';

export function useRecordSearch(query: string) {
  const needle = query.trim().toLowerCase();
  const enabled = needle.length >= 2;
  const datasets = useQuery({queryKey: ['datasets'], queryFn: qh.datasets, enabled, staleTime: 30000});
  const models = useQuery({queryKey: ['models'], queryFn: qh.models, enabled, staleTime: 30000});
  const experiments = useQuery({queryKey: ['experiments'], queryFn: qh.experiments, enabled, staleTime: 30000});
  if (!enabled) return [];
  return [
    ...(datasets.data ?? []).map(row => ({label: row.name, id: row.id, hint: 'Dataset', path: '/datasets'})),
    ...(models.data ?? []).map(row => ({label: modelLabels[row.model_type] + ' · ' + shortId(row.id), id: row.id, hint: 'Model', path: '/comparison'})),
    ...(experiments.data ?? []).map(row => ({label: 'Experiment ' + shortId(row.id), id: row.id, hint: row.status, path: '/experiments/' + row.id})),
  ].filter(row => [row.label, row.id, row.hint].join(' ').toLowerCase().includes(needle)).slice(0, 12);
}
