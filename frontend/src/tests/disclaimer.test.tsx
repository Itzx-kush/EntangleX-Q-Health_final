import {render, screen} from '@testing-library/react';
import {describe, expect, it} from 'vitest';
import {Disclaimer, disclaimer} from '../components/Common';
describe('health boundary', () => {
  it('shows the research-prototype disclaimer', () => {
    render(<Disclaimer/>);
    expect(screen.getByRole('note')).toHaveTextContent(disclaimer);
    expect(screen.getByRole('note')).toHaveTextContent('not a substitute for professional medical diagnosis');
  });
});
