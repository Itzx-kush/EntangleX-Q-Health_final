import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {DraftProvider} from '../hooks/ExperimentDraft';
import Experiments from '../pages/Experiments';
import ExperimentDetail from '../pages/ExperimentDetail';
const experiment = {id: 'experiment-123', dataset_id: 'dataset-456', parent_id: null, status: 'succeeded', config: {models: ['logistic_regression'], seed: 42}, summary: {split_hash: 'split-123'}, created_at: '2026-01-01T00:00:00Z'};
function response(body: unknown): Response {return {ok: true, json: async () => body} as Response;}
describe('Research Studio environment', () => {
  beforeEach(() => {localStorage.clear(); vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([experiment])));});
  afterEach(() => {vi.unstubAllGlobals(); localStorage.clear();});
  it('renders the registry with real experiment data, search, and filters', async () => {render(<MemoryRouter><DraftProvider><Experiments/></DraftProvider></MemoryRouter>); await waitFor(() => expect(screen.getAllByText(/experime/).length).toBeGreaterThan(0)); expect(screen.getByRole('navigation', {name: 'Research Studio workflow'})).toBeInTheDocument(); expect(screen.getByRole('textbox', {name: 'Search experiments'})).toBeInTheDocument(); expect(screen.getByRole('link', {name: /Open Model Lab/})).toHaveAttribute('href', '/training'); fireEvent.change(screen.getByRole('textbox', {name: 'Search experiments'}), {target: {value: 'no-match'}}); expect(screen.getByText(/No experiments match/)).toBeInTheDocument();});
  it('shows a truthful empty registry state', async () => {vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response([]))); render(<MemoryRouter><DraftProvider><Experiments/></DraftProvider></MemoryRouter>); await waitFor(() => expect(screen.getByText(/No experiments are registered/)).toBeInTheDocument()); expect(screen.getByRole('link', {name: /Start in Model Lab/})).toHaveAttribute('href', '/training');});
  it('renders real experiment detail and related research links', async () => {const detail = {experiment, models: [], jobs: []}; vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(detail))); render(<MemoryRouter initialEntries={['/experiments/experiment-123']}><DraftProvider><ExperimentDetail/></DraftProvider></MemoryRouter>); await waitFor(() => expect(screen.getByText(/split-123/)).toBeInTheDocument()); expect(screen.getByRole('link', {name: /All experiments/})).toHaveAttribute('href', '/experiments'); expect(screen.getAllByRole('link', {name: /Quantum Lab/}).find(link => link.getAttribute('href') === '/quantum')).toBeInTheDocument(); expect(screen.getByText(/No model records are available/)).toBeInTheDocument();});
});
