import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import type {ReactNode} from 'react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {DraftProvider} from '../hooks/ExperimentDraft';
import Training from '../pages/Training';
import Comparison from '../pages/Comparison';
import Explainability from '../pages/Explainability';
import Prediction from '../pages/Prediction';

const experiment = {id: 'experiment-123', dataset_id: 'dataset-123', parent_id: null, status: 'succeeded', config: {}, summary: {}, created_at: '2026-01-01T00:00:00Z'};
const metricSet = {sensitivity: .8, specificity: .75, roc_auc: .82, f1: .78, accuracy: .79, precision: .77, recall: .8, true_positive: 8, true_negative: 7, false_positive: 2, false_negative: 2, confusion_matrix: [[7, 2], [2, 8]], sample_count: 19, roc_curve: {fpr: [0, .2, 1], tpr: [0, .8, 1], thresholds: [1, .5, 0]}, undefined_metrics: []};
const model = {id: 'model-123', experiment_id: 'experiment-123', dataset_id: 'dataset-123', model_type: 'logistic_regression', status: 'ready', details: {}, metrics: {training: metricSet, test: metricSet, validation: {folds: [], summary: Object.fromEntries(['sensitivity', 'specificity', 'roc_auc', 'f1', 'accuracy', 'precision', 'recall'].map(key => [key, {mean: .8, std: .03, valid_folds: 3}])), std_definition: 'sample'}, timing: {final_training_seconds: .2, cv_total_seconds: .5, test_inference_seconds: .01, test_inference_seconds_per_sample: .001}, calibration: {}}, created_at: '2026-01-01T00:00:00Z'};
function response(body: unknown): Response {return {ok: true, json: async () => body} as Response;}
function renderPage(page: ReactNode, path = '/') {return render(<MemoryRouter initialEntries={[path]}><DraftProvider>{page}</DraftProvider></MemoryRouter>);}

describe('Model Lab experimentation workspace', () => {
  beforeEach(() => {localStorage.clear(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([])));});
  afterEach(() => {vi.unstubAllGlobals(); localStorage.clear();});

  it('renders the shared workflow with valid active-stage routes', async () => {
    renderPage(<Training/>, '/training');
    expect(screen.getByRole('heading', {level: 1, name: 'Training'})).toBeInTheDocument();
    const workflow = screen.getByRole('navigation', {name: 'Model Lab workflow'});
    expect(workflow).toBeInTheDocument();
    for (const label of ['Training', 'Model comparison', 'Explainability', 'Research prediction']) expect(screen.getByRole('link', {name: new RegExp(label)})).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Quantum Lab/})).toHaveAttribute('href', '/quantum');
    await waitFor(() => expect(screen.getByText(/No training jobs have been submitted/)).toBeInTheDocument());
  });

  it('renders supported model options and labelled training controls', () => {
    renderPage(<Training/>, '/training');
    for (const label of ['Logistic Regression', 'SVM', 'Random Forest', 'VQC', 'QSVC', 'QNN']) expect(screen.getByText(label)).toBeInTheDocument();
    expect(screen.getByText('Partitions and evaluation')).toBeInTheDocument();
    expect(screen.getByText('Quantum configuration')).toBeInTheDocument();
    expect(screen.getAllByRole('button', {name: /Create training experiment/}).length).toBeGreaterThan(0);
  });

  it('renders measured comparison data without inventing a ranking', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => String(input).endsWith('/experiments') ? Promise.resolve(response([experiment])) : Promise.resolve(response({experiment_id: experiment.id, models: [model], pairs: [], split: {}, comparison_fingerprint: 'split-123', conclusion: 'Measured comparison returned by the backend.', limitations: []}))));
    renderPage(<Comparison/>, '/comparison');
    await waitFor(() => expect(screen.getByText('Measured comparison returned by the backend.')).toBeInTheDocument());
    expect(screen.getByRole('table', {name: /Measured model comparison/})).toBeInTheDocument();
    expect(screen.getAllByText('Logistic Regression').length).toBeGreaterThan(0);
    expect(screen.getByRole('img', {name: /receiver operating characteristic/i})).toBeInTheDocument();
  });

  it('keeps explainability and prediction honest when no model is selected', async () => {
    renderPage(<Explainability/>, '/explainability');
    expect(screen.getByText(/No explanation has been calculated/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('No model selected')).toBeInTheDocument());
    const {unmount} = renderPage(<Prediction/>, '/prediction');
    expect(screen.getByText(/No input schema loaded/)).toBeInTheDocument();
    expect(screen.getByRole('button', {name: /Generate research prediction/})).toBeDisabled();
    unmount();
  });

  it('renders a real explanation and prediction response when backend data is returned', async () => {
    const explanation = {id: 'explanation-123', model_id: model.id, method: 'permutation', created_at: '2026-01-01T00:00:00Z', result: {title: 'Measured permutation influence', scope: 'Held-out sample subset', sample_count: 4, units: 'ROC-AUC decrease', elapsed_seconds: .4, influence: [{feature: 'marker_a', magnitude: .12}], limitations: []}};
    const schema = {model_id: model.id, features: [{name: 'marker_a', type: 'number', nullable: true}], positive_label: 'positive', negative_label: 'negative'};
    const prediction = {model_id: model.id, model_type: 'logistic_regression', positive_label: 'positive', negative_label: 'negative', probability_status: 'Measured probability', decision_rule: 'Configured threshold', risk_thresholds: [.33, .66], predictions: [{sample: 'sample-1', predicted_class: 'positive', probability_positive: .72, decision_score: .44, research_risk_category: 'high'}], influence: null, limitations: [], disclaimer: 'Research prototype'};
    const fetchMock = vi.fn().mockImplementation((input: RequestInfo | URL) => {const url = String(input); if (url.endsWith('/models')) return Promise.resolve(response([model])); if (url.endsWith(`/models/${model.id}`)) return Promise.resolve(response(model)); if (url.endsWith(`/models/${model.id}/explanations`)) return Promise.resolve(response([explanation])); if (url.endsWith(`/models/${model.id}/input-schema`)) return Promise.resolve(response(schema)); if (url.endsWith(`/models/${model.id}/predict`)) return Promise.resolve(response(prediction)); return Promise.resolve(response([]));});
    vi.stubGlobal('fetch', fetchMock);
    const explanationView = renderPage(<Explainability/>, '/explainability');
    const modelSelect = await screen.findByRole('combobox', {name: 'Registered model'});
    fireEvent.change(modelSelect, {target: {value: model.id}});
    await waitFor(() => expect(screen.getByText('Measured permutation influence')).toBeInTheDocument());
    expect(screen.getByRole('img', {name: /feature influence/i})).toBeInTheDocument();
    explanationView.unmount();
    renderPage(<Prediction/>, '/prediction');
    const predictionSelect = await screen.findByRole('combobox', {name: 'Registered model'});
    fireEvent.change(predictionSelect, {target: {value: model.id}});
    await waitFor(() => expect(screen.getByText('Anonymous sample')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', {name: /Generate research prediction/}));
    await waitFor(() => expect(screen.getByText('Predicted class: positive')).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalled();
  });
});
