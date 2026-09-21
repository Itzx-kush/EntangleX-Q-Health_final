import React from 'react';
import {fireEvent, render, screen, waitFor, within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {ApplicationShell} from '../components/ApplicationShell';
import {Dialog, Drawer, ErrorState, IconButton, LoadingState, SuccessState, Tabs, Toast, Tooltip, Button} from '../components/Primitives';
import Dashboard from '../pages/Dashboard';

beforeEach(() => { vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Backend unavailable'))); });

describe('Q-Health UI foundation', () => {
  it('renders accessible button and icon button controls', () => {
    render(<><Button>Run workflow</Button><IconButton label="Refresh workspace">↻</IconButton></>);
    expect(screen.getByRole('button', {name: 'Run workflow'})).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Refresh workspace'})).toBeInTheDocument();
  });

  it('exposes tooltip content to assistive technology', () => {
    render(<Tooltip label="Measured backend state"><button>State</button></Tooltip>);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Measured backend state');
  });

  it('exposes active tab semantics', () => {
    render(<Tabs items={[{value: 'a', label: 'Summary'}, {value: 'b', label: 'Details'}]} value="a" onChange={() => undefined}/>);
    expect(screen.getByRole('tab', {name: 'Summary'})).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', {name: 'Details'})).toHaveAttribute('aria-selected', 'false');
  });

  it('opens, closes, and Escape-closes a dialog', async () => {
    function Fixture() { const [open, setOpen] = React.useState(false); return <><button onClick={() => setOpen(true)}>Open dialog</button><Dialog open={open} onClose={() => setOpen(false)} title="Research details"><p>Details</p></Dialog></>; }
    render(<Fixture/>);
    fireEvent.click(screen.getByRole('button', {name: 'Open dialog'}));
    expect(screen.getByRole('dialog', {name: 'Research details'})).toBeInTheDocument();
    fireEvent.keyDown(window, {key: 'Escape'});
    await waitFor(() => expect(screen.queryByRole('dialog', {name: 'Research details'})).not.toBeInTheDocument());
  });

  it('opens and closes a drawer', async () => {
    function Fixture() { const [open, setOpen] = React.useState(false); return <><button onClick={() => setOpen(true)}>Open drawer</button><Drawer open={open} onClose={() => setOpen(false)} title="Filters"><p>Filters</p></Drawer></>; }
    render(<Fixture/>);
    fireEvent.click(screen.getByRole('button', {name: 'Open drawer'}));
    expect(screen.getByRole('dialog', {name: 'Filters'})).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole('dialog', {name: 'Filters'})).getByRole('button', {name: 'Close drawer'}));
    await waitFor(() => expect(screen.queryByRole('dialog', {name: 'Filters'})).not.toBeInTheDocument());
  });

  it('renders real frontend states with semantic status roles', () => {
    render(<><LoadingState>Loading records</LoadingState><ErrorState>Request failed</ErrorState><SuccessState>Saved</SuccessState><Toast message="Copied" onDismiss={() => undefined}/></>);
    expect(screen.getByText('Loading records')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Request failed');
    expect(screen.getAllByRole('status').some(node => node.textContent?.includes('Saved'))).toBe(true);
    expect(screen.getByText('Copied')).toBeInTheDocument();
  });

  it('renders the existing shell, navigation, routes, and foundation dashboard without fabricating data', async () => {
    function Fixture() { return <MemoryRouter initialEntries={['/']}><ApplicationShell health={{error: ''}} token="" setToken={() => undefined} menu={false} setMenu={() => undefined} onApplyToken={() => undefined}><Dashboard/></ApplicationShell></MemoryRouter>; }
    render(<Fixture/>);
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('navigation', {name: 'Research environments'})).toBeInTheDocument();
    expect(screen.getByRole('heading', {name: /traceable path/i})).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Backend unavailable/)).toBeInTheDocument());
  });
});
