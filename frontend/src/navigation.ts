import type {LucideIcon} from 'lucide-react';
import {Activity, BarChart3, Brain, Database, FlaskConical, Gauge, Microscope, Orbit, Settings2} from 'lucide-react';

export type EnvironmentId = 'research' | 'data-lab' | 'model-lab' | 'quantum-lab' | 'research-studio';

export type NavigationItem = {
  path: string;
  label: string;
  number: string;
  description: string;
  icon: LucideIcon;
};

export type EnvironmentNavigation = {
  id: EnvironmentId;
  name: string;
  context: string;
  description: string;
  icon: LucideIcon;
  items: NavigationItem[];
};

export const environments: EnvironmentNavigation[] = [
  {id: 'research', name: 'Research', context: 'Overview', description: 'High-level research workspace and project overview.', icon: Activity, items: [
    {path: '/', label: 'Overview', number: '01', description: 'Research workspace overview.', icon: Activity},
  ]},
  {id: 'data-lab', name: 'Data Lab', context: 'Dataset preparation', description: 'Dataset inspection and preparation.', icon: Database, items: [
    {path: '/datasets', label: 'Datasets', number: '02', description: 'Manage benchmark and user-provided datasets.', icon: Database},
    {path: '/quality', label: 'Data quality', number: '03', description: 'Inspect data quality and provenance.', icon: Gauge},
    {path: '/preprocessing', label: 'Preprocessing', number: '04', description: 'Configure leakage-safe preprocessing.', icon: Settings2},
    {path: '/features', label: 'Feature selection', number: '05', description: 'Select reproducible model inputs.', icon: Microscope},
    {path: '/pca', label: 'PCA / dimensions', number: '06', description: 'Reduce and inspect feature dimensions.', icon: BarChart3},
  ]},
  {id: 'model-lab', name: 'Model Lab', context: 'Model evaluation', description: 'Classical and hybrid model experimentation and evaluation.', icon: Brain, items: [
    {path: '/training', label: 'Training', number: '07', description: 'Run controlled model training experiments.', icon: Brain},
    {path: '/comparison', label: 'Model comparison', number: '08', description: 'Compare measured model results.', icon: BarChart3},
    {path: '/explainability', label: 'Explainability', number: '10', description: 'Inspect model explanations and provenance.', icon: Microscope},
    {path: '/prediction', label: 'Research prediction', number: '11', description: 'Use completed models for research prediction.', icon: Activity},
  ]},
  {id: 'quantum-lab', name: 'Quantum Lab', context: 'Quantum research', description: 'Quantum-specific research functionality already present in Q-Health.', icon: Orbit, items: [
    {path: '/quantum', label: 'Quantum circuit', number: '09', description: 'Inspect quantum circuit configuration.', icon: Orbit},
  ]},
  {id: 'research-studio', name: 'Research Studio', context: 'Experiment tracking', description: 'Experiment tracking and research workflow.', icon: FlaskConical, items: [
    {path: '/experiments', label: 'Experiments', number: '12', description: 'Review tracked research experiments.', icon: FlaskConical},
  ]},
];

export const navigationItems = environments.flatMap(environment => environment.items.map(item => ({...item, environmentId: environment.id, environmentName: environment.name})));

export function isNavigationItemActive(path: string, pathname: string) {
  return path === '/' ? pathname === '/' : pathname === path || pathname.startsWith(`${path}/`);
}

export function getEnvironmentForPath(pathname: string) {
  return environments.find(environment => environment.items.some(item => isNavigationItemActive(item.path, pathname))) ?? environments[0];
}

export function getNavigationItemForPath(pathname: string) {
  return getEnvironmentForPath(pathname).items.find(item => isNavigationItemActive(item.path, pathname));
}
