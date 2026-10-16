import {useEffect, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import {ArrowRight, ArrowUpRight, ChevronDown, Menu, X, ShieldCheck, Atom, BrainCircuit, Database, FileText} from 'lucide-react';

interface PublicHeaderProps {
  onRequestAccess: (destination?: string) => void;
}

export function PublicHeader({onRequestAccess}: PublicHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  const headerRef = useRef<HTMLElement | null>(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (headerRef.current && !headerRef.current.contains(event.target as Node)) {
        setActiveDropdown(null);
      }
    };
    document.addEventListener('click', handleOutsideClick);
    return () => document.removeEventListener('click', handleOutsideClick);
  }, []);

  // Keyboard navigation & escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setActiveDropdown(null);
        if (mobileMenuOpen) {
          setMobileMenuOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  // Body scroll lock during mobile menu open
  useEffect(() => {
    if (mobileMenuOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [mobileMenuOpen]);

  const handleNavClick = (href: string) => {
    setActiveDropdown(null);
    setMobileMenuOpen(false);
    if (href.startsWith('#')) {
      const el = document.querySelector(href);
      if (el) {
        el.scrollIntoView({behavior: 'smooth'});
      }
    }
  };

  const handleAccess = (destination = '/') => {
    setActiveDropdown(null);
    setMobileMenuOpen(false);
    onRequestAccess(destination);
  };

  const toggleDropdown = (name: string) => {
    setActiveDropdown(current => (current === name ? null : name));
  };

  return (
    <header className="public-header" ref={headerRef}>
      <div className="public-header-inner">
        <a
          className="public-brand"
          href="#top"
          aria-label="EntangleX Q-Health home"
          onClick={() => handleNavClick('#top')}
        >
          <img src="/entanglex-logo-dark.svg" alt="EntangleX Logo" />
          <span className="public-brand-name">Q-HEALTH</span>
        </a>

        {/* Desktop Navigation */}
        <nav className="public-desktop-nav" aria-label="Main public navigation">
          {/* Research Dropdown */}
          <div className="public-nav-item">
            <button
              type="button"
              className={`public-nav-trigger ${activeDropdown === 'research' ? 'is-active' : ''}`}
              aria-expanded={activeDropdown === 'research'}
              aria-haspopup="true"
              onClick={() => toggleDropdown('research')}
            >
              <span>Research</span>
              <ChevronDown size={13} className="public-dropdown-icon" />
            </button>
            {activeDropdown === 'research' && (
              <div className="public-dropdown-panel" role="menu">
                <a
                  href="#guided-process"
                  className="public-dropdown-link"
                  role="menuitem"
                  onClick={() => handleNavClick('#guided-process')}
                >
                  <BrainCircuit size={16} />
                  <div>
                    <strong>Guided Research Pathway</strong>
                    <small>4-stage reproducible biomedical methodology</small>
                  </div>
                </a>
                <a
                  href="#technical-stack"
                  className="public-dropdown-link"
                  role="menuitem"
                  onClick={() => handleNavClick('#technical-stack')}
                >
                  <Database size={16} />
                  <div>
                    <strong>Data Provenance & QC</strong>
                    <small>Dataset verification and clinical bounds</small>
                  </div>
                </a>
                <a
                  href="#demonstration"
                  className="public-dropdown-link"
                  role="menuitem"
                  onClick={() => handleNavClick('#demonstration')}
                >
                  <ShieldCheck size={16} />
                  <div>
                    <strong>SIH-26139 Evidence Base</strong>
                    <small>Diabetes risk prediction benchmark</small>
                  </div>
                </a>
              </div>
            )}
          </div>

          {/* Platform Dropdown */}
          <div className="public-nav-item">
            <button
              type="button"
              className={`public-nav-trigger ${activeDropdown === 'platform' ? 'is-active' : ''}`}
              aria-expanded={activeDropdown === 'platform'}
              aria-haspopup="true"
              onClick={() => toggleDropdown('platform')}
            >
              <span>Platform</span>
              <ChevronDown size={13} className="public-dropdown-icon" />
            </button>
            {activeDropdown === 'platform' && (
              <div className="public-dropdown-panel" role="menu">
                <a
                  href="#interactive-demo"
                  className="public-dropdown-link"
                  role="menuitem"
                  onClick={() => handleNavClick('#interactive-demo')}
                >
                  <Atom size={16} />
                  <div>
                    <strong>Hybrid VQC Architecture</strong>
                    <small>Variational circuits & classical baselines</small>
                  </div>
                </a>
                <button
                  type="button"
                  className="public-dropdown-link is-action"
                  role="menuitem"
                  onClick={() => handleAccess('/quantum')}
                >
                  <FileText size={16} />
                  <div>
                    <strong>Quantum Simulator Catalog</strong>
                    <small>Statevector, Aer, and noise simulation</small>
                  </div>
                </button>
              </div>
            )}
          </div>

          <a
            href="#demonstration"
            className="public-nav-link"
            onClick={() => handleNavClick('#demonstration')}
          >
            Demonstration
          </a>

          <a
            href="#about"
            className="public-nav-link"
            onClick={() => handleNavClick('#about')}
          >
            About
          </a>
        </nav>

        {/* Desktop CTA */}
        <div className="public-header-actions">
          <button
            className="public-header-cta"
            type="button"
            onClick={() => handleAccess('/')}
          >
            <span>Sign in</span>
            <ArrowUpRight size={14} />
          </button>
        </div>

        {/* Mobile Menu Button */}
        <button
          className="public-mobile-toggle"
          type="button"
          aria-expanded={mobileMenuOpen}
          aria-controls="public-mobile-drawer"
          aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          onClick={() => setMobileMenuOpen(open => !open)}
        >
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Mobile Drawer (Site Navigation Benchmark) rendered via Portal */}
      {mobileMenuOpen && typeof document !== 'undefined' &&
        createPortal(
          <div className="public-mobile-drawer-overlay" onClick={() => setMobileMenuOpen(false)}>
            <div
              id="public-mobile-drawer"
              className="public-mobile-drawer"
              role="dialog"
              aria-modal="true"
              aria-label="Site navigation"
              onClick={e => e.stopPropagation()}
            >
              <div className="public-mobile-drawer-header">
                <div className="public-brand">
                  <img src="/entanglex-logo-dark.svg" alt="EntangleX" />
                  <span className="public-brand-name">Q-HEALTH</span>
                </div>
                <button
                  className="public-mobile-close"
                  type="button"
                  aria-label="Close navigation"
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <X size={20} />
                </button>
              </div>

              <div className="public-mobile-drawer-content">
                <div className="public-mobile-section-title">PLATFORM NAVIGATION</div>
                <nav className="public-mobile-links" aria-label="Mobile navigation links">
                  <a
                    href="#guided-process"
                    className="public-mobile-link"
                    onClick={() => handleNavClick('#guided-process')}
                  >
                    <BrainCircuit size={18} />
                    <span>Research Pathway</span>
                  </a>
                  <a
                    href="#interactive-demo"
                    className="public-mobile-link"
                    onClick={() => handleNavClick('#interactive-demo')}
                  >
                    <Atom size={18} />
                    <span>Hybrid Demonstration</span>
                  </a>
                  <a
                    href="#technical-stack"
                    className="public-mobile-link"
                    onClick={() => handleNavClick('#technical-stack')}
                  >
                    <Database size={18} />
                    <span>Technical Platform</span>
                  </a>
                  <a
                    href="#demonstration"
                    className="public-mobile-link"
                    onClick={() => handleNavClick('#demonstration')}
                  >
                    <ShieldCheck size={18} />
                    <span>Verified Flagship (SIH-26139)</span>
                  </a>
                  <a
                    href="#about"
                    className="public-mobile-link"
                    onClick={() => handleNavClick('#about')}
                  >
                    <FileText size={18} />
                    <span>About EntangleX</span>
                  </a>
                </nav>

                <div className="public-mobile-drawer-divider" />

                <div className="public-mobile-actions">
                  <button
                    type="button"
                    className="public-button is-primary is-full-width"
                    onClick={() => handleAccess('/')}
                  >
                    <span>Explore Research Workspace</span>
                    <ArrowRight size={15} />
                  </button>
                  <button
                    type="button"
                    className="public-button is-secondary is-full-width"
                    onClick={() => handleAccess('/')}
                  >
                    <span>Sign In / Guest Access</span>
                  </button>
                </div>

                <div className="public-mobile-footer-note">
                  <small>SIH 2026 · Problem Statement 26139 · Biomedical ML Prototype</small>
                </div>
              </div>
            </div>
          </div>,
          document.body
        )}
    </header>
  );
}
