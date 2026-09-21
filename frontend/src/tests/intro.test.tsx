import {fireEvent, render, screen, waitFor} from '@testing-library/react';
import {afterEach, beforeEach, describe, expect, it} from 'vitest';
import {IntroGate, INTRO_STORAGE_KEY, replayIntro} from '../components/Intro';

describe('Q-Health intro persistence', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => localStorage.clear());

  it('shows once and persists completion locally', async () => {
    render(<IntroGate><p>Workspace content</p></IntroGate>);
    expect(screen.getByRole('region', {name: /introduction/i})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: /enter workspace/i}));
    expect(screen.getByText('Workspace content')).toBeInTheDocument();
    expect(localStorage.getItem(INTRO_STORAGE_KEY)).toBe('true');
  });

  it('skips the intro for returning visits and exposes a replay hook', async () => {
    localStorage.setItem(INTRO_STORAGE_KEY, 'true');
    render(<IntroGate><p>Workspace content</p></IntroGate>);
    expect(screen.queryByRole('region', {name: /introduction/i})).not.toBeInTheDocument();
    expect(screen.getByText('Workspace content')).toBeInTheDocument();
    replayIntro();
    expect(localStorage.getItem(INTRO_STORAGE_KEY)).toBeNull();
    await waitFor(() => expect(screen.getByText('Workspace content')).toBeInTheDocument());
  });
});
