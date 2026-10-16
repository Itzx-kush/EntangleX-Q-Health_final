import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Filter,
  Info,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  XCircle,
} from 'lucide-react';
import { qh } from '../../lib/api';
import type {
  CapabilitySupport,
  QuantumBackendDescriptor,
  QuantumProviderDescriptor,
} from '../../types/qhealth';

export interface QuantumSimulatorCatalogProps {
  activeBackendId?: string;
  activeProviderId?: string;
  onSelectBackend?: (providerId: string, backendId: string) => void;
  className?: string;
}

type FilterCategory = 'all' | 'qiskit' | 'pennylane' | 'statevector' | 'shots' | 'noise';

function isCapabilitySupported(val?: CapabilitySupport): boolean {
  return val === 'SUPPORTED';
}

function getCapabilityBadge(val?: CapabilitySupport, detail?: string) {
  if (val === 'SUPPORTED') {
    return (
      <span className="ql-cap-tag is-supported">
        <CheckCircle2 size={11} aria-hidden="true" />
        <span>Supported{detail ? ` (${detail})` : ''}</span>
      </span>
    );
  }
  if (val === 'UNSUPPORTED') {
    return (
      <span className="ql-cap-tag is-unsupported">
        <XCircle size={11} aria-hidden="true" />
        <span>Unsupported</span>
      </span>
    );
  }
  return (
    <span className="ql-cap-tag is-unknown">
      <Info size={11} aria-hidden="true" />
      <span>Unknown</span>
    </span>
  );
}

function getBackendGuidance(backendId: string): string {
  switch (backendId) {
    case 'statevector':
      return 'Exact statevector simulation computing analytic expectation values without stochastic shot noise. Recommended for deterministic VQC, QSVC, and QNN experiments.';
    case 'aer':
      return 'Qiskit Aer simulation supporting shot-based measurement sampling (up to 16,384 shots) and realistic depolarizing noise models.';
    case 'default.qubit':
      return 'PennyLane native statevector simulator with full PyTorch autograd gradient integration for hybrid neural network backpropagation.';
    default:
      return 'Local simulation runtime for quantum machine learning experimentation.';
  }
}

export function QuantumSimulatorCatalog({
  activeBackendId,
  activeProviderId,
  onSelectBackend,
  className = '',
}: QuantumSimulatorCatalogProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('all');

  const providersQuery = useQuery({
    queryKey: ['quantum-providers'],
    queryFn: qh.quantumProviders,
    staleTime: 30000,
  });

  const healthQuery = useQuery({
    queryKey: ['quantum-providers-health'],
    queryFn: qh.quantumProviderHealth,
    staleTime: 30000,
  });

  const isLoading = providersQuery.isLoading || healthQuery.isLoading;
  const isError = providersQuery.isError || healthQuery.isError;
  const errorMessage =
    (providersQuery.error as Error)?.message ||
    (healthQuery.error as Error)?.message ||
    'Unable to load quantum providers and simulator backends.';

  const handleRefresh = () => {
    providersQuery.refetch();
    healthQuery.refetch();
  };

  // Map provider health items by provider_id
  const healthMap = useMemo(() => {
    const map = new Map<string, {
      availability: string;
      packages_present: Record<string, boolean>;
      runtime_verified: boolean;
      execution: string;
    }>();
    if (healthQuery.data?.providers) {
      for (const item of healthQuery.data.providers) {
        map.set(item.provider_id, item);
      }
    }
    return map;
  }, [healthQuery.data]);

  const rawProviders = providersQuery.data || [];

  // Filter providers and their backends based on search and selected filter category
  const filteredProviders = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    return rawProviders
      .map((provider) => {
        // Check provider-level match
        const providerNameMatch =
          provider.display_name.toLowerCase().includes(q) ||
          provider.provider_id.toLowerCase().includes(q);

        const matchingBackends = provider.backends.filter((backend) => {
          // Category filter
          if (activeFilter === 'qiskit' && provider.provider_id !== 'qiskit_local') return false;
          if (activeFilter === 'pennylane' && provider.provider_id !== 'pennylane_local') return false;
          if (activeFilter === 'statevector' && !isCapabilitySupported(backend.capabilities?.supports_statevector)) {
            return false;
          }
          if (activeFilter === 'shots' && !isCapabilitySupported(backend.capabilities?.supports_shots)) {
            return false;
          }
          if (activeFilter === 'noise' && !isCapabilitySupported(backend.capabilities?.supports_noise_model)) {
            return false;
          }

          // Search query filter
          if (!q) return true;
          if (providerNameMatch) return true;

          const backendIdMatch = backend.backend_id.toLowerCase().includes(q);
          const backendNameMatch = backend.display_name.toLowerCase().includes(q);
          const capabilitiesMatch =
            (isCapabilitySupported(backend.capabilities?.supports_statevector) && 'statevector'.includes(q)) ||
            (isCapabilitySupported(backend.capabilities?.supports_shots) && 'shots sampling'.includes(q)) ||
            (isCapabilitySupported(backend.capabilities?.supports_noise_model) && 'noise depolarizing'.includes(q));

          return backendIdMatch || backendNameMatch || capabilitiesMatch;
        });

        return {
          ...provider,
          backends: matchingBackends,
        };
      })
      .filter((provider) => provider.backends.length > 0 || (activeFilter === 'all' && !searchQuery));
  }, [rawProviders, searchQuery, activeFilter]);

  const totalRegisteredBackends = useMemo(
    () => rawProviders.reduce((acc, p) => acc + p.backends.length, 0),
    [rawProviders]
  );

  const totalVisibleBackends = useMemo(
    () => filteredProviders.reduce((acc, p) => acc + p.backends.length, 0),
    [filteredProviders]
  );

  const resetFilters = () => {
    setSearchQuery('');
    setActiveFilter('all');
  };

  return (
    <section
      className={`ql-catalog-container ${className}`}
      aria-label="Quantum Simulator and Provider Discovery Catalog"
      id="quantum-simulator-catalog"
    >
      {/* Header section */}
      <div className="ql-catalog-header">
        <div className="ql-catalog-title-group">
          <div className="ql-catalog-icon" aria-hidden="true">
            <Cpu size={20} />
          </div>
          <div>
            <span className="ql-eyebrow">DISCOVERY &amp; EXECUTION CATALOG</span>
            <h2 className="ql-catalog-heading">Quantum Simulators &amp; Execution Providers</h2>
            <p className="ql-catalog-description">
              Discover verified local quantum execution backends, inspect simulator capability matrices, and evaluate package readiness.
            </p>
          </div>
        </div>

        <div className="ql-catalog-header-actions">
          <button
            type="button"
            className="btn btn-outline ql-refresh-btn"
            onClick={handleRefresh}
            disabled={isLoading}
            aria-label="Refresh quantum providers and backends"
            title="Refresh providers"
          >
            <RefreshCw size={14} className={isLoading ? 'ql-spin' : ''} aria-hidden="true" />
            <span>{isLoading ? 'Checking…' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* Scientific truthfulness & local simulation boundary callout */}
      <div className="ql-catalog-disclaimer" role="note" aria-label="Local simulation disclaimer">
        <ShieldAlert size={16} className="ql-disclaimer-icon" aria-hidden="true" />
        <div className="ql-disclaimer-content">
          <strong>Classical Local Simulation Boundary</strong>
          <p>
            EntangleX Q-Health executes all quantum routines via deterministic local simulators (Qiskit and PennyLane).
            Physical quantum hardware execution, remote cloud queues, and QPU device reservations are explicitly unsupported in this local environment.
          </p>
        </div>
      </div>

      {/* Search and filter toolbar */}
      <div className="ql-catalog-toolbar" role="search" aria-label="Simulator search and filters">
        <div className="ql-search-box">
          <Search size={14} className="ql-search-icon" aria-hidden="true" />
          <input
            type="text"
            className="ql-search-input"
            placeholder="Search simulators, backends, capabilities (e.g., statevector, aer, noise)…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search simulators and capabilities"
          />
          {searchQuery && (
            <button
              type="button"
              className="ql-search-clear"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search query"
            >
              ×
            </button>
          )}
        </div>

        <div className="ql-filter-chips" role="group" aria-label="Filter simulators by capability or framework">
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'all' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('all')}
            aria-pressed={activeFilter === 'all'}
          >
            All Backends ({totalRegisteredBackends})
          </button>
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'qiskit' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('qiskit')}
            aria-pressed={activeFilter === 'qiskit'}
          >
            Qiskit Local
          </button>
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'pennylane' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('pennylane')}
            aria-pressed={activeFilter === 'pennylane'}
          >
            PennyLane Local
          </button>
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'statevector' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('statevector')}
            aria-pressed={activeFilter === 'statevector'}
          >
            Statevector
          </button>
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'shots' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('shots')}
            aria-pressed={activeFilter === 'shots'}
          >
            Shot Sampling
          </button>
          <button
            type="button"
            className={`ql-filter-chip ${activeFilter === 'noise' ? 'is-active' : ''}`}
            onClick={() => setActiveFilter('noise')}
            aria-pressed={activeFilter === 'noise'}
          >
            Noise Modeling
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading && rawProviders.length === 0 && (
        <div className="ql-catalog-skeleton" role="status" aria-busy="true" aria-label="Discovering quantum providers">
          <div className="ql-skeleton-banner" />
          <div className="ql-skeleton-cards">
            <div className="ql-skeleton-card" />
            <div className="ql-skeleton-card" />
          </div>
          <span className="ql-skeleton-text">Discovering quantum providers and simulator backends…</span>
        </div>
      )}

      {/* Error state */}
      {isError && rawProviders.length === 0 && (
        <div className="ql-catalog-error" role="alert">
          <AlertTriangle size={20} className="ql-error-icon" aria-hidden="true" />
          <div className="ql-error-copy">
            <strong>Unable to Load Quantum Providers</strong>
            <p>{errorMessage}</p>
          </div>
          <button type="button" className="btn btn-outline" onClick={handleRefresh}>
            Retry Discovery
          </button>
        </div>
      )}

      {/* Empty search results state */}
      {!isLoading && !isError && filteredProviders.length === 0 && (
        <div className="ql-catalog-empty" role="status">
          <Filter size={24} className="ql-empty-icon" aria-hidden="true" />
          <h3>No Simulators Match Your Filter Criteria</h3>
          <p>
            No registered quantum backend satisfies the search query <code>"{searchQuery}"</code> with filter <code>"{activeFilter}"</code>.
          </p>
          <button type="button" className="btn btn-outline" onClick={resetFilters}>
            Reset Filters
          </button>
        </div>
      )}

      {/* Provider & Backend Groups */}
      {!isLoading && filteredProviders.length > 0 && (
        <div className="ql-providers-list">
          {filteredProviders.map((provider) => {
            const health = healthMap.get(provider.provider_id);
            const isAvailable = provider.availability === 'AVAILABLE' || health?.availability === 'AVAILABLE';
            const packages = health?.packages_present || {};

            return (
              <article
                key={provider.provider_id}
                className="ql-provider-section"
                aria-label={`Provider: ${provider.display_name}`}
              >
                {/* Provider summary card */}
                <header className="ql-provider-header">
                  <div className="ql-provider-info">
                    <div className="ql-provider-meta-row">
                      <h3 className="ql-provider-name">{provider.display_name}</h3>
                      <span className="ql-provider-id-tag"><code>{provider.provider_id}</code></span>
                      <span className="ql-type-badge">{provider.provider_type}</span>
                      <span className={`ql-status-badge ${isAvailable ? 'is-available' : 'is-unavailable'}`}>
                        {isAvailable ? 'AVAILABLE' : 'UNAVAILABLE'}
                      </span>
                    </div>

                    <p className="ql-provider-execution-note">
                      {health?.execution || 'Local quantum simulation only; no hardware credentials or hardware execution.'}
                    </p>

                    {/* Verified Package Dependencies */}
                    <div className="ql-packages-row" aria-label="Verified Python packages">
                      <span className="ql-packages-label">Package Readiness:</span>
                      {Object.keys(packages).length > 0 ? (
                        Object.entries(packages).map(([pkgName, isPresent]) => (
                          <span
                            key={pkgName}
                            className={`ql-pkg-pill ${isPresent ? 'is-installed' : 'is-missing'}`}
                            title={isPresent ? `${pkgName} is installed and verified` : `${pkgName} is missing from Python environment`}
                          >
                            {isPresent ? <CheckCircle2 size={10} aria-hidden="true" /> : <XCircle size={10} aria-hidden="true" />}
                            <span>{pkgName}</span>
                          </span>
                        ))
                      ) : (
                        <span className="ql-pkg-pill is-installed">
                          <CheckCircle2 size={10} aria-hidden="true" />
                          <span>Dependencies registered</span>
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="ql-provider-stats">
                    <span className="ql-backend-count-badge">
                      {provider.backends.length} {provider.backends.length === 1 ? 'backend' : 'backends'}
                    </span>
                  </div>
                </header>

                {/* Backends Grid for this provider */}
                <div className="ql-backends-grid" role="list" aria-label={`Backends for ${provider.display_name}`}>
                  {provider.backends.map((backend) => {
                    const isActive =
                      (activeBackendId === backend.backend_id && (!activeProviderId || activeProviderId === provider.provider_id)) ||
                      (activeBackendId === backend.backend_id);

                    const caps = backend.capabilities || {};
                    const guidance = getBackendGuidance(backend.backend_id);

                    return (
                      <div
                        key={backend.backend_id}
                        role="listitem"
                        className={`ql-backend-card ${isActive ? 'is-active-backend' : ''}`}
                        aria-label={`Backend ${backend.display_name}`}
                      >
                        {/* Top bar with name, active pill, and ID */}
                        <div className="ql-backend-card-header">
                          <div className="ql-backend-name-box">
                            <h4 className="ql-backend-display-name">{backend.display_name}</h4>
                            <span className="ql-backend-id-pill">
                              <code>{backend.backend_id}</code>
                            </span>
                          </div>

                          <div className="ql-backend-badge-box">
                            {isActive && (
                              <span className="ql-active-badge" aria-label="Currently active backend in Quantum Lab">
                                <Sparkles size={11} aria-hidden="true" />
                                <span>Active in Workspace</span>
                              </span>
                            )}
                            <span className={`ql-backend-avail-badge ${backend.available ? 'is-available' : 'is-unavailable'}`}>
                              {backend.available ? 'Available' : 'Unavailable'}
                            </span>
                          </div>
                        </div>

                        {/* Guidance / Recommended use */}
                        <p className="ql-backend-guidance">{guidance}</p>

                        {/* Capabilities matrix */}
                        <div className="ql-cap-matrix" aria-label="Supported execution capabilities">
                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Statevector</span>
                            {getCapabilityBadge(caps.supports_statevector)}
                          </div>

                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Sampling &amp; Shots</span>
                            {getCapabilityBadge(
                              caps.supports_shots,
                              caps.max_shots ? `Max ${caps.max_shots.toLocaleString()} shots` : undefined
                            )}
                          </div>

                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Noise Modeling</span>
                            {getCapabilityBadge(caps.supports_noise_model)}
                          </div>

                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Parameterized Circuits</span>
                            {getCapabilityBadge(caps.supports_parameterized_circuits)}
                          </div>

                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Gradients</span>
                            {getCapabilityBadge(caps.supports_gradients)}
                          </div>

                          <div className="ql-cap-item">
                            <span className="ql-cap-name">Physical Hardware</span>
                            <span className="ql-cap-tag is-hardware-unsupported" title="Local simulators do not connect to physical quantum hardware">
                              <XCircle size={11} aria-hidden="true" />
                              <span>Unsupported</span>
                            </span>
                          </div>
                        </div>

                        {/* Footer action */}
                        <div className="ql-backend-card-footer">
                          <div className="ql-backend-meta-specs">
                            <span>Type: <strong>{backend.backend_type}</strong></span>
                            {caps.max_shots ? (
                              <span>Max Shots: <strong>{caps.max_shots.toLocaleString()}</strong></span>
                            ) : null}
                          </div>

                          {onSelectBackend && (
                            <button
                              type="button"
                              className={`btn ${isActive ? 'btn-outline ql-btn-selected' : 'btn-primary'}`}
                              onClick={() => onSelectBackend(provider.provider_id, backend.backend_id)}
                              aria-pressed={isActive}
                              disabled={!backend.available}
                            >
                              {isActive ? (
                                <>
                                  <CheckCircle2 size={13} aria-hidden="true" />
                                  <span>Active Backend</span>
                                </>
                              ) : (
                                <span>Use in Quantum Lab</span>
                              )}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
export default QuantumSimulatorCatalog;
