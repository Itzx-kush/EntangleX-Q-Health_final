import type {ModelKind} from '../types/qhealth';
export const families = ['Classical', 'Quantum', 'Hybrid'] as const;
export type Family = typeof families[number];
export const familyColor: Record<Family,string> = {
  Classical: 'var(--qx-classical)', Quantum: 'var(--qx-quantum)', Hybrid: 'var(--qx-hybrid)',
};
export function modelFamily(kind: ModelKind): Family {
  if (kind === 'hybrid_pennylane_torch') return 'Hybrid';
  if (kind === 'vqc' || kind === 'qnn' || kind === 'qsvc') return 'Quantum';
  return 'Classical';
}
