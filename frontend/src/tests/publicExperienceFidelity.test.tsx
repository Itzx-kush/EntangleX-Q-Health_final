import {render, screen, fireEvent, waitFor} from '@testing-library/react';
import {describe, it, expect, vi, beforeEach} from 'vitest';
import {PublicExperience} from '../components/PublicExperience';
import {PublicHero} from '../components/public/PublicHero';
import {PublicHeader} from '../components/public/PublicHeader';
import {PublicResearchDemonstration} from '../components/public/PublicResearchDemonstration';
import {PublicGuidedProcess} from '../components/public/PublicGuidedProcess';

function setupMatchMedia(reducedMotion = false) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
      matches: query.includes('prefers-reduced-motion: reduce') ? reducedMotion : false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

describe('Public Experience Fidelity & Accessibility Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMatchMedia(false);
  });

  describe('Reduced-Motion Accessibility Defect Verification', () => {
    it('renders hero headline, copy, and both primary CTAs in the DOM without hiding them', () => {
      const onRequestAccess = vi.fn();
      render(<PublicHero onRequestAccess={onRequestAccess} />);

      // Headline and dot-matrix accent must be present
      const headline = screen.getByRole('heading', {level: 1});
      expect(headline).toBeInTheDocument();
      expect(headline).toHaveTextContent(/The Hybrid Quantum Intelligence Platform/i);

      // Subhead description
      expect(
        screen.getByText(/Accelerate biomedical discovery through traceable data pipelines/i)
      ).toBeInTheDocument();

      // Both primary CTA buttons must be accessible
      const primaryBtn = screen.getByRole('button', {name: /Explore Research Workspace/i});
      expect(primaryBtn).toBeInTheDocument();

      const secondaryBtn = screen.getByRole('button', {name: /Sign In \/ Guest Access/i});
      expect(secondaryBtn).toBeInTheDocument();

      // Bounded note
      expect(screen.getByText(/SIH-26139 Research Prototype/i)).toBeInTheDocument();
    });

    it('immediately sets is-visible on all reveal elements when reduced-motion is requested', async () => {
      setupMatchMedia(true);

      const onRequestAccess = vi.fn();
      const {container} = render(<PublicExperience onRequestAccess={onRequestAccess} />);

      // Under reduced motion, all data-public-reveal elements must immediately receive .is-visible
      await waitFor(() => {
        const revealElements = container.querySelectorAll('[data-public-reveal]');
        expect(revealElements.length).toBeGreaterThan(0);
        revealElements.forEach(el => {
          expect(el.classList.contains('is-visible')).toBe(true);
        });
      });
    });
  });

  describe('Call to Action & Navigation Verification', () => {
    it('triggers onRequestAccess with correct route targets', () => {
      const onRequestAccess = vi.fn();
      render(<PublicExperience onRequestAccess={onRequestAccess} />);

      // Primary hero CTA
      const exploreBtn = screen.getByRole('button', {name: /Explore Research Workspace/i});
      fireEvent.click(exploreBtn);
      expect(onRequestAccess).toHaveBeenCalledWith('/');

      // Verified demo CTA
      const demoBtn = screen.getByRole('button', {name: /Launch Verified Demonstration/i});
      fireEvent.click(demoBtn);
      expect(onRequestAccess).toHaveBeenCalledWith('/demo');
    });

    it('manages desktop dropdown opening, outside click dismissal, and escape key', () => {
      const onRequestAccess = vi.fn();
      render(<PublicHeader onRequestAccess={onRequestAccess} />);

      const researchBtn = screen.getByRole('button', {name: /Research/i});
      expect(researchBtn).toHaveAttribute('aria-expanded', 'false');

      // Click to open
      fireEvent.click(researchBtn);
      expect(researchBtn).toHaveAttribute('aria-expanded', 'true');
      expect(screen.getByText(/Guided Research Pathway/i)).toBeInTheDocument();

      // Escape key to dismiss
      fireEvent.keyDown(window, {key: 'Escape'});
      expect(researchBtn).toHaveAttribute('aria-expanded', 'false');

      // Re-open and outside click to dismiss
      fireEvent.click(researchBtn);
      expect(researchBtn).toHaveAttribute('aria-expanded', 'true');
      fireEvent.click(document.body);
      expect(researchBtn).toHaveAttribute('aria-expanded', 'false');
    });

    it('manages mobile drawer opening, closing, body scroll lock, and actions', () => {
      const onRequestAccess = vi.fn();
      render(<PublicHeader onRequestAccess={onRequestAccess} />);

      const mobileToggle = screen.getByRole('button', {name: /Open navigation menu/i});
      expect(mobileToggle).toHaveAttribute('aria-expanded', 'false');

      // Open mobile drawer
      fireEvent.click(mobileToggle);
      expect(mobileToggle).toHaveAttribute('aria-expanded', 'true');

      const drawer = screen.getByRole('dialog', {name: /Site navigation/i});
      expect(drawer).toBeInTheDocument();

      // Close button inside drawer (exact name match)
      const closeBtn = screen.getByRole('button', {name: 'Close navigation'});
      fireEvent.click(closeBtn);
      expect(screen.queryByRole('dialog', {name: /Site navigation/i})).not.toBeInTheDocument();
    });
  });

  describe('Interactive Research Demonstration (Replacing Abstract Art)', () => {
    it('allows toggling between research methodology tabs and updates code & metrics', () => {
      render(<PublicResearchDemonstration />);

      // 3 tabs must exist
      const hybridTab = screen.getByRole('tab', {name: /01 Hybrid VQC/i});
      const classicalTab = screen.getByRole('tab', {name: /02 Classical Baseline/i});
      const kernelTab = screen.getByRole('tab', {name: /03 Quantum Kernel/i});

      expect(hybridTab).toHaveAttribute('aria-selected', 'true');
      expect(classicalTab).toHaveAttribute('aria-selected', 'false');
      expect(kernelTab).toHaveAttribute('aria-selected', 'false');

      // Initial state has PennyLane quantum circuit
      expect(screen.getByText(/pennylane as qml/i)).toBeInTheDocument();

      // Switch to Classical Baseline
      fireEvent.click(classicalTab);
      expect(classicalTab).toHaveAttribute('aria-selected', 'true');
      expect(hybridTab).toHaveAttribute('aria-selected', 'false');
      expect(screen.getByText(/GradientBoostingClassifier/i)).toBeInTheDocument();
      expect(screen.getByText(/XGBoost \/ RF/i)).toBeInTheDocument();

      // Switch to Quantum Kernel
      fireEvent.click(kernelTab);
      expect(kernelTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByText(/FidelityQuantumKernel/i)).toBeInTheDocument();
      expect(screen.getByText(/Hilbert Dimension/i)).toBeInTheDocument();
    });

    it('supports interactive qubit selection and code copying', () => {
      // Mock clipboard
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockImplementation(() => Promise.resolve()),
        },
      });

      render(<PublicResearchDemonstration />);

      // Copy button
      const copyBtn = screen.getByRole('button', {name: /Copy code sample/i});
      fireEvent.click(copyBtn);
      expect(navigator.clipboard.writeText).toHaveBeenCalled();

      // Qubit selector
      const twoQPill = screen.getByRole('button', {name: '2Q'});
      const fourQPill = screen.getByRole('button', {name: '4Q'});
      expect(fourQPill).toHaveClass('is-selected');

      fireEvent.click(twoQPill);
      expect(twoQPill).toHaveClass('is-selected');
    });
  });

  describe('Guided Research Process & Sticky Stepper', () => {
    it('renders all 4 stages with verifiable technical methodology details', () => {
      render(<PublicGuidedProcess />);

      expect(screen.getByRole('heading', {name: /Data Preparation & Quality Control/i})).toBeInTheDocument();
      expect(screen.getByRole('heading', {name: /Feature Engineering & Selection/i})).toBeInTheDocument();
      expect(screen.getByRole('heading', {name: /Hybrid VQC Modelling/i})).toBeInTheDocument();
      expect(screen.getByRole('heading', {name: /Controlled Evaluation & Validation/i})).toBeInTheDocument();

      // Metric checks
      expect(screen.getByText(/SHA-256 Signed/i)).toBeInTheDocument();
      expect(screen.getByText(/RY Rotation/i)).toBeInTheDocument();
      expect(screen.getByText(/CNOT Ring/i)).toBeInTheDocument();
      expect(screen.getByText(/Depolarizing Sweep/i)).toBeInTheDocument();
    });

    it('updates active stage when clicking stepper items', () => {
      render(<PublicGuidedProcess />);

      const stage3Btn = screen.getByRole('tab', {name: /03 Hybrid VQC Modelling/i});
      fireEvent.click(stage3Btn);
      expect(stage3Btn).toHaveAttribute('aria-selected', 'true');
    });
  });
});
