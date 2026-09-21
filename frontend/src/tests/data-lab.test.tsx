import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import type {ReactNode} from 'react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {DraftProvider} from '../hooks/ExperimentDraft';
import Datasets from '../pages/Datasets';
import Quality from '../pages/Quality';
import Preprocessing from '../pages/Preprocessing';
import FeatureSelection from '../pages/FeatureSelection';
import PCA from '../pages/PCA';

const quality = {scope: 'all features', row_count: 569, feature_count: 30, class_distribution: {benign: 357, malignant: 212}, minority_fraction: 0.37, class_imbalance: false, missing_values: {radius: 0}, infinite_values: {radius: 0}, duplicate_rows: 0, duplicate_feature_rows: 0, constant_features: [], low_variance_features: [], suspiciously_predictive_features: [], identifier_features: [], highly_correlated_pairs: [], warnings: [], blockers: [], distributions: [], invalid_numeric_values: 'No invalid numeric values detected.'};
const dataset = {id: 'dataset-123', name: 'Wisconsin benchmark', sha256: 'abc123', created_at: '2026-01-01T00:00:00Z', quality, provenance: {name: 'Wisconsin benchmark', domain: 'biomedical', source: 'public benchmark', source_url: null, version: '1', target: 'diagnosis', positive_label: 'malignant', negative_label: 'benign', features: ['radius'], numeric_features: ['radius'], categorical_features: [], row_count: 569, feature_count: 30, class_distribution: {benign: 357, malignant: 212}, target_classes: ['benign', 'malignant'], is_demo: true, dataset_hash: 'abc123', license: null}};
function response(body: unknown): Response {return {ok: true, json: async () => body} as Response;}
function renderPage(page: ReactNode, path = '/') {return render(<MemoryRouter initialEntries={[path]}><DraftProvider>{page}</DraftProvider></MemoryRouter>);}

describe('Data Lab research workspace', () => {
  beforeEach(() => {localStorage.clear(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([])));});
  afterEach(() => {vi.unstubAllGlobals(); localStorage.clear();});

  it('renders one route-aware workflow across all five Data Lab areas', async () => {
    renderPage(<Preprocessing/>, '/preprocessing');
    expect(screen.getByRole('heading', {level: 1, name: 'Preprocessing'})).toBeInTheDocument();
    expect(screen.getByRole('navigation', {name: 'Data Lab workflow'})).toBeInTheDocument();
    for (const label of ['Datasets', 'Data quality', 'Preprocessing', 'Feature selection', 'PCA / dimensions']) expect(screen.getByRole('link', {name: new RegExp(label)})).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Continue to Model Lab/})).toHaveAttribute('href', '/training');
    expect(screen.getByRole('link', {name: /Data quality/})).toHaveAttribute('href', '/quality');
    await waitFor(() => expect(screen.getByText(/No preprocessing result yet/)).toBeInTheDocument());
  });

  it('presents actual registry values and honest raw-preview boundaries', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([dataset])));
    renderPage(<Datasets/>, '/datasets');
    await waitFor(() => expect(screen.getByText('Wisconsin benchmark')).toBeInTheDocument());
    expect(screen.getByText('569 / 30')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: 'Select'}));
    expect(screen.getByText(/Raw records are not exposed/)).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Review data quality/})).toHaveAttribute('href', '/quality');
  });

  it('keeps the Datasets loading state visible while the real request is pending', () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise<Response>(() => undefined)));
    renderPage(<Datasets/>, '/datasets');
    expect(screen.getByText(/Loading registered datasets/)).toBeInTheDocument();
  });

  it('surfaces a registry error instead of silently presenting an empty dataset', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Registry unavailable')));
    renderPage(<Datasets/>, '/datasets');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Registry unavailable'));
    expect(screen.queryByText('569 / 30')).not.toBeInTheDocument();
  });

  it('shows an honest empty quality state when no dataset is selected', async () => {
    renderPage(<Quality/>, '/quality');
    await waitFor(() => expect(screen.getByText(/Select a dataset to inspect its quality/)).toBeInTheDocument());
    expect(screen.getByRole('heading', {name: 'Data quality'})).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Preprocessing/})).toHaveAttribute('href', '/preprocessing');
  });

  it('renders the real quality response for the selected dataset', async () => {
    localStorage.setItem('qhealth-config-v1', JSON.stringify({dataset_id: 'dataset-123'}));
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => String(input).endsWith('/datasets/dataset-123') ? Promise.resolve(response(dataset)) : Promise.resolve(response([dataset]))));
    renderPage(<Quality/>, '/quality');
    await waitFor(() => expect(screen.getByText('569')).toBeInTheDocument());
    expect(screen.getByText('Quality gates')).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Continue to preprocessing/})).toHaveAttribute('href', '/preprocessing');
  });

  it('keeps preparation controls labelled and exposes truthful no-result states', async () => {
    renderPage(<Preprocessing/>, '/preprocessing');
    expect(screen.getByLabelText('Numeric missing-value strategy')).toBeInTheDocument();
    expect(screen.getByLabelText('Scaling')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/No preprocessing result yet/)).toBeInTheDocument());
  });

  it('renders feature-selection and PCA configuration without synthetic results', async () => {
    const {unmount} = renderPage(<FeatureSelection/>, '/features');
    expect(screen.getByRole('heading', {name: 'Feature selection'})).toBeInTheDocument();
    expect(screen.getByLabelText('Method')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/No feature-selection output yet/)).toBeInTheDocument());
    unmount();
    renderPage(<PCA/>, '/pca');
    expect(screen.getByRole('heading', {name: 'PCA / dimensions'})).toBeInTheDocument();
    expect(screen.getByText('PCA components')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/No PCA result yet/)).toBeInTheDocument());
  });
});
