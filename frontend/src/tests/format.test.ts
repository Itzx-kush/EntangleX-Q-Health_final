import {describe, expect, it} from 'vitest';
import {metric, seconds, isActive} from '../utils/format';
describe('scientific formatting', () => {
  it('never substitutes fake measurements for absent data', () => {
    expect(metric(undefined)).toBe('Not measured');
    expect(metric(null)).toBe('Not measured');
    expect(metric(NaN)).toBe('Not measured');
    expect(seconds(undefined)).toBe('Not measured');
  });
  it('does not discard measured zero values', () => {expect(metric(0)).toBe('0.0%');});
  it('distinguishes active job states', () => {expect(isActive('running')).toBe(true); expect(isActive('failed')).toBe(false);});
});
