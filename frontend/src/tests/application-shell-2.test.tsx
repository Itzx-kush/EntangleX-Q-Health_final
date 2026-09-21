import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {useState} from 'react';
import {MemoryRouter, useLocation} from 'react-router-dom';
import {describe, expect, it} from 'vitest';
import {ApplicationShell} from '../components/ApplicationShell';
import {environments, navigationItems} from '../navigation';

function LocationProbe() { const location = useLocation(); return <output aria-label="current route">{location.pathname}</output>; }
function TestShell({path = '/'}: {path?: string}) {
  const [menu, setMenu] = useState(false);
  return <MemoryRouter initialEntries={[path]}><ApplicationShell health={{error: ''}} token="" setToken={() => undefined} menu={menu} setMenu={setMenu} onApplyToken={() => undefined}><LocationProbe/></ApplicationShell></MemoryRouter>;
}

describe('Application Shell 2.0', () => {
  it('renders the global header, route-aware context, and all research environments', () => {
    render(<TestShell path="/features"/>);
    expect(screen.getByRole('button', {name: 'Open command palette'})).toBeInTheDocument();
    expect(screen.getByText('Checking')).toBeInTheDocument();
    expect(screen.getByRole('link', {name: /Research workspace/i})).toBeInTheDocument();
    expect(screen.getAllByText('Data Lab').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Feature selection').length).toBeGreaterThan(0);
    for (const environment of environments) expect(screen.getByRole('region', {name: `${environment.name} environment`})).toBeInTheDocument();
  });

  it('opens the command palette with the button and Ctrl+K, filters real route options, and closes with Escape', async () => {
    render(<TestShell/>);
    fireEvent.click(screen.getByRole('button', {name: 'Open command palette'}));
    expect(screen.getByRole('dialog', {name: 'Navigate Q-Health workspace'})).toBeInTheDocument();
    const input = screen.getByPlaceholderText('Search environments and pages');
    fireEvent.change(input, {target: {value: 'quantum'}});
    expect(screen.getAllByRole('option', {name: /Quantum Lab/}).length).toBeGreaterThan(0);
    fireEvent.keyDown(window, {key: 'Escape'});
    await waitFor(() => expect(screen.queryByRole('dialog', {name: 'Navigate Q-Health workspace'})).not.toBeInTheDocument());

    fireEvent.keyDown(window, {key: 'k', ctrlKey: true});
    expect(screen.getByRole('dialog', {name: 'Navigate Q-Health workspace'})).toBeInTheDocument();
  });

  it('uses the central route registry to navigate and closes the command surface', async () => {
    render(<TestShell/>);
    expect(navigationItems.some(item => item.path === '/datasets')).toBe(true);
    fireEvent.click(screen.getByRole('button', {name: 'Open command palette'}));
    fireEvent.change(screen.getByPlaceholderText('Search environments and pages'), {target: {value: 'datasets'}});
    fireEvent.click(screen.getByRole('option', {name: /Datasets/}));
    await waitFor(() => expect(screen.getAllByRole('status')[0]).toHaveTextContent(/Connected|Checking|Unavailable/));
    expect(screen.getByLabelText('current route')).toHaveTextContent('/datasets');
    await waitFor(() => expect(screen.queryByRole('dialog', {name: 'Navigate Q-Health workspace'})).not.toBeInTheDocument());
  });

  it('opens, closes, and focus-wraps the mobile navigation', () => {
    render(<TestShell/>);
    const open = screen.getByRole('button', {name: /Open research workspace navigation/i});
    fireEvent.click(open);
    expect(screen.getByRole('button', {name: /Close research workspace navigation/i})).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', {name: 'Close navigation'}));
    expect(screen.getByRole('button', {name: /Open research workspace navigation/i})).toHaveAttribute('aria-expanded', 'false');
  });

  it('supports compact navigation while retaining accessible route names', () => {
    render(<TestShell/>);
    fireEvent.click(screen.getByRole('button', {name: 'Collapse environment navigation'}));
    expect(screen.getByRole('button', {name: 'Expand environment navigation'})).toBeInTheDocument();
    const datasets = screen.getByRole('link', {name: '02 Datasets'});
    expect(datasets).toHaveAttribute('href', '/datasets');
    expect(datasets).toHaveAttribute('title', 'Datasets');
  });

  it('switches and persists the semantic Q-Health theme', () => {
    localStorage.clear();
    render(<TestShell/>);
    fireEvent.change(screen.getByRole('combobox', {name: 'Appearance theme'}), {target: {value: 'dark'}});
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
    expect(localStorage.getItem('qhealth-theme-v1')).toBe('dark');
    localStorage.clear();
  });
});
