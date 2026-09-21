export type EnvironmentId = 'research' | 'data-lab' | 'model-lab' | 'quantum-lab' | 'research-studio';

export type NavigationItem = {
  path: string;
  label: string;
  number: string;
};

export type EnvironmentNavigation = {
  id: EnvironmentId;
  name: string;
  context: string;
  description: string;
  items: NavigationItem[];
};

export const environments: EnvironmentNavigation[] = [
  {id: 'research', name: 'Research', context: 'Overview', description: 'High-level research workspace and project overview.', items: [{path: '/', label: 'Overview', number: '01'}]},
  {id: 'data-lab', name: 'Data Lab', context: 'Dataset preparation', description: 'Dataset inspection and preparation.', items: [
    {path: '/datasets', label: 'Datasets', number: '02'}, {path: '/quality', label: 'Data quality', number: '03'}, {path: '/preprocessing', label: 'Preprocessing', number: '04'}, {path: '/features', label: 'Feature selection', number: '05'}, {path: '/pca', label: 'PCA / dimensions', number: '06'},
  ]},
  {id: 'model-lab', name: 'Model Lab', context: 'Model evaluation', description: 'Classical and hybrid model experimentation and evaluation.', items: [
    {path: '/training', label: 'Training', number: '07'}, {path: '/comparison', label: 'Model comparison', number: '08'}, {path: '/explainability', label: 'Explainability', number: '10'}, {path: '/prediction', label: 'Research prediction', number: '11'},
  ]},
  {id: 'quantum-lab', name: 'Quantum Lab', context: 'Quantum research', description: 'Quantum-specific research functionality already present in Q-Health.', items: [{path: '/quantum', label: 'Quantum circuit', number: '09'}]},
  {id: 'research-studio', name: 'Research Studio', context: 'Experiment tracking', description: 'Experiment tracking and research workflow.', items: [{path: '/experiments', label: 'Experiments', number: '12'}]},
];

export function isNavigationItemActive(path: string, pathname: string) {
  return path === '/' ? pathname === '/' : pathname === path || pathname.startsWith(`${path}/`);
}

export function getEnvironmentForPath(pathname: string) {
  return environments.find(environment => environment.items.some(item => isNavigationItemActive(item.path, pathname))) ?? environments[0];
}

export function getNavigationItemForPath(pathname: string) {
  return getEnvironmentForPath(pathname).items.find(item => isNavigationItemActive(item.path, pathname));
}
