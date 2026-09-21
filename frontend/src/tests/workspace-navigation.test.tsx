import {render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {describe, expect, it} from 'vitest';
import {MobileWorkspaceNav, WorkspaceNavigationBar} from '../components/WorkspaceNavigationBar';

describe('workspace navigation layer', () => {
  it('renders quick destinations using the real route registry', () => {
    render(<MemoryRouter initialEntries={['/training']}><WorkspaceNavigationBar pathname="/training" onOpenSearch={() => undefined}/></MemoryRouter>);
    expect(screen.getByRole('link', {name: 'Research overview'})).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', {name: /Models/})).toHaveAttribute('href', '/training');
    expect(screen.getByRole('button', {name: /Search/})).toBeInTheDocument();
  });

  it('renders five primary mobile destinations and marks the current one', () => {
    render(<MemoryRouter initialEntries={['/quantum']}><MobileWorkspaceNav pathname="/quantum"/></MemoryRouter>);
    expect(screen.getAllByRole('link')).toHaveLength(5);
    expect(screen.getByRole('link', {name: 'Quantum'})).toHaveAttribute('aria-current', 'page');
  });
});
