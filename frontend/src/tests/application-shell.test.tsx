import {fireEvent, render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe, expect, it} from 'vitest';
import {useState} from 'react';
import {ApplicationShell} from '../components/ApplicationShell';
import {environments} from '../navigation';

function TestShell({path = '/'}: {path?: string}) {
  const [menu, setMenu] = useState(false);
  return <MemoryRouter initialEntries={[path]}><ApplicationShell health={{error: ''}} token="" setToken={() => undefined} menu={menu} setMenu={setMenu} onApplyToken={() => undefined}><p>Shell content</p></ApplicationShell></MemoryRouter>;
}

describe('environment-based application shell', () => {
  it('renders all five research environments', () => {
    render(<TestShell/>);
    for (const environment of environments) expect(screen.getByRole('region', {name: `${environment.name} environment`})).toBeInTheDocument();
  });

  it.each([
    ['/', 'Research', 'Overview'], ['/datasets', 'Data Lab', 'Datasets'], ['/quality', 'Data Lab', 'Data quality'], ['/preprocessing', 'Data Lab', 'Preprocessing'], ['/features', 'Data Lab', 'Feature selection'], ['/pca', 'Data Lab', 'PCA / dimensions'],
    ['/training', 'Model Lab', 'Training'], ['/comparison', 'Model Lab', 'Model comparison'], ['/explainability', 'Model Lab', 'Explainability'], ['/prediction', 'Model Lab', 'Research prediction'], ['/quantum', 'Quantum Lab', 'Quantum circuit'], ['/experiments', 'Research Studio', 'Experiments'], ['/experiments/exp-123', 'Research Studio', 'Experiments'],
  ])('marks %s as %s / %s', (path, environment, page) => {
    render(<TestShell path={path}/>);
    expect(screen.getByRole('region', {name: `${environment} environment`})).toHaveAttribute('data-active', 'true');
    expect(screen.getByRole('link', {name: new RegExp(`^\\d+ ${page}$`)})).toHaveAttribute('aria-current', 'page');
  });

  it('keeps every existing navigation link mapped to its existing URL', () => {
    render(<TestShell/>);
    for (const environment of environments) for (const item of environment.items) {
      expect(screen.getByRole('link', {name: new RegExp(item.label, 'i')})).toHaveAttribute('href', item.path);
    }
  });

  it('opens, closes, and keyboard-closes the mobile navigation', () => {
    render(<TestShell/>);
    const menuButton = screen.getByRole('button', {name: /open research workspace navigation/i});
    expect(menuButton).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(menuButton);
    expect(screen.getByRole('button', {name: /close research workspace navigation/i})).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(window, {key: 'Escape'});
    expect(screen.getByRole('button', {name: /open research workspace navigation/i})).toHaveAttribute('aria-expanded', 'false');
  });

  it('closes the mobile navigation when a route is selected', () => {
    render(<TestShell/>);
    fireEvent.click(screen.getByRole('button', {name: /open research workspace navigation/i}));
    fireEvent.click(screen.getByRole('link', {name: /Datasets/i}));
    expect(screen.getByRole('button', {name: /open research workspace navigation/i})).toHaveAttribute('aria-expanded', 'false');
  });
});
