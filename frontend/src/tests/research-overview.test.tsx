import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import Dashboard from '../pages/Dashboard';

type Summary = {counts: Record<string, number>; recent_experiments: Array<{id: string; dataset_id: string; parent_id: null; status: string; config: Record<string, unknown>; summary: Record<string, unknown>; created_at: string}>};
const summary: Summary = {counts: {datasets: 3, experiments: 4, ready_models: 2, active_jobs: 1}, recent_experiments: [{id: 'experiment-123456', dataset_id: 'dataset-123456', parent_id: null, status: 'succeeded', config: {}, summary: {}, created_at: '2026-01-01T12:00:00Z'}]};
function response(body: unknown): Response { return {ok: true, json: async () => body} as Response; }
function renderOverview() { return render(<MemoryRouter><Dashboard/></MemoryRouter>); }

describe('Research Overview flagship workspace', () => {
  beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(summary))); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('renders the research hero, briefing, pipeline, capabilities, and real summary values', async () => {
    renderOverview();
    expect(screen.getByRole('heading', {level: 1, name: /traceable path/i})).toBeInTheDocument();
    expect(screen.getByRole('heading', {name: /workspace snapshot/i})).toBeInTheDocument();
    expect(screen.getByRole('heading', {name: /measured path from data/i})).toBeInTheDocument();
    expect(screen.getByRole('heading', {name: /choose the next workspace/i})).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
    expect(screen.getByText('succeeded')).toBeInTheDocument();
    expect(screen.getByText(/Only experiments returned by the backend/)).toBeInTheDocument();
  });

  it('exposes real entry points for every research environment', async () => {
    renderOverview();
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
    expect(screen.getByRole('link', {name: 'Open Data Lab'})).toHaveAttribute('href', '/datasets');
    expect(screen.getByRole('link', {name: 'Open Model Lab'})).toHaveAttribute('href', '/training');
    expect(screen.getByRole('link', {name: 'Open Quantum Lab'})).toHaveAttribute('href', '/quantum');
    expect(screen.getAllByRole('link', {name: 'Open Research Studio'}).find(link => link.getAttribute('href') === '/experiments')).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Open Model comparison/})).toHaveAttribute('href', '/comparison');
  });

  it('keeps the layout honest during loading', () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => new Promise<Response>(() => undefined)));
    renderOverview();
    expect(screen.getByLabelText('Loading recent research activity')).toBeInTheDocument();
    expect(screen.getAllByText('Loading summary').length).toBeGreaterThan(0);
  });

  it('renders the backend error and retries the real summary request', async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new Error('Summary request failed'));
    vi.stubGlobal('fetch', fetchMock);
    renderOverview();
    await waitFor(() => expect(screen.getByText(/Research summary unavailable/)).toBeInTheDocument());
    fetchMock.mockResolvedValueOnce(response(summary));
    fireEvent.click(screen.getByRole('button', {name: 'Retry summary'}));
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument());
  });

  it('shows a useful empty state when the backend returns no recent experiments', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({...summary, counts: {datasets: 0, experiments: 0, ready_models: 0, active_jobs: 0}, recent_experiments: []})));
    renderOverview();
    await waitFor(() => expect(screen.getByText('No research activity available')).toBeInTheDocument());
    expect(screen.getAllByRole('link', {name: /Open Data Lab/}).find(link => link.getAttribute('href') === '/datasets')).toBeInTheDocument();
  });

  it('does not turn absent backend fields into scientific claims', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({counts: {datasets: 2}, recent_experiments: []})));
    renderOverview();
    await waitFor(() => expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0));
    expect(screen.queryByText(/accuracy|precision|recall|quantum advantage/i)).not.toBeInTheDocument();
  });
});
