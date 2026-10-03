"""Quantum provider and diagnostics verification (Prompts 9 and 21).

Verifies that the provider registry loads, that local providers describe their
capabilities honestly, that preflight is deterministic and blocks unsupported
capabilities, and that quantum diagnostics remain structured.  No cloud quantum
hardware and no long quantum jobs are required.
"""

from __future__ import annotations

from ..fixtures import canonical_circuit_configuration, persist_chain
from ..isolation import initialize_database, session
from ..models import CheckCategory, CheckResult, FailureCategory, Severity
from ..registry import FULL_PROFILE, FAST_PROFILE, check
from ._support import require_fingerprint

FAKE_HARDWARE_TERMS = ("ibm", "ionq", "rigetti", "braket", "d-wave", "dwave", "quantum_hardware")


@check(
    check_id="quantum_provider_contract",
    name="Quantum provider contract",
    category=CheckCategory.QUANTUM_INTEGRITY,
    description="Provider registry, honest capability metadata, deterministic preflight and unsupported-capability blocking.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def quantum_provider_contract() -> CheckResult:
    from app.quantum.backends import availability
    from app.quantum.service import service

    initialize_database()
    problems: list[str] = []

    providers = {provider["provider_id"]: provider for provider in service.list_providers()}
    for required in ("qiskit_local", "pennylane_local"):
        if required not in providers:
            problems.append(f"the quantum provider registry no longer contains {required}")
    for provider_id, provider in providers.items():
        if provider["provider_type"] != "LOCAL_SIMULATOR":
            problems.append(f"provider {provider_id} claims provider type {provider['provider_type']!r}")
        for backend in provider.get("backends") or []:
            capabilities = backend.get("capabilities") or {}
            if capabilities.get("supports_hardware_execution") != "UNSUPPORTED":
                problems.append(f"backend {backend['backend_id']} does not declare hardware execution as unsupported")
            if backend.get("backend_type") != "LOCAL_SIMULATOR":
                problems.append(f"backend {backend['backend_id']} claims backend type {backend.get('backend_type')!r}")

    health = availability()
    if health.get("provider_id") != "qiskit_local":
        problems.append("the compatibility availability facade no longer reports the local provider")
    if not health.get("packages_present"):
        problems.append("the local quantum packages are not detectable")
    if "no hardware" not in str(health.get("execution", "")).lower():
        problems.append("the availability description no longer states that no hardware execution occurs")

    configuration = {"qubits": 4, "reps": 2, "feature_map": "zz", "ansatz": "real_amplitudes"}
    first = service.preflight("qiskit_local", "statevector", configuration)
    second = service.preflight("qiskit_local", "statevector", configuration)
    if first.get("status") not in {"READY", "BLOCKED"}:
        problems.append(f"preflight reported an unknown status {first.get('status')!r}")
    if first.get("execution_mode") != "local_simulator":
        problems.append(f"preflight reported execution mode {first.get('execution_mode')!r}")
    require_fingerprint(first.get("configuration_fingerprint"), label="provider configuration fingerprint")
    if first != second:
        problems.append("provider preflight is not deterministic for identical configuration")

    blocked = service.preflight("qiskit_local", "statevector", configuration, ["supports_hardware_execution"])
    if blocked.get("status") != "BLOCKED" or not any(
        blocker.startswith("unsupported_capability") for blocker in blocked.get("blockers") or []
    ):
        problems.append("requesting an unsupported capability did not block preflight")

    text = " ".join(
        [
            str(provider.get("provider_id")) + " " + str(provider.get("display_name"))
            for provider in providers.values()
        ]
    ).lower()
    for term in FAKE_HARDWARE_TERMS:
        if term in text:
            problems.append(f"a provider descriptor mentions unsupported hardware term {term!r}")

    if problems:
        return CheckResult(
            check_id="quantum_provider_contract",
            category=CheckCategory.QUANTUM_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="honest local-simulator provider metadata with deterministic, capability-aware preflight",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="quantum_provider_contract",
        category=CheckCategory.QUANTUM_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Quantum providers load, describe local-simulator capabilities honestly and preflight deterministically.",
        evidence={
            "provider_ids": sorted(providers),
            "preflight_status": first.get("status"),
            "configuration_fingerprint": first.get("configuration_fingerprint"),
            "hardware_execution": "UNSUPPORTED",
            "availability": health,
        },
    )


@check(
    check_id="quantum_diagnostics_contract",
    name="Quantum diagnostics contract",
    category=CheckCategory.QUANTUM_INTEGRITY,
    description="Diagnostics preflight is structured for quantum models and refuses classical models without fabricating reports.",
    severity=Severity.REQUIRED,
    profiles=(FAST_PROFILE, FULL_PROFILE),
    timeout_seconds=180.0,
)
def quantum_diagnostics_contract() -> CheckResult:
    from app.quantum.diagnostics import compute_circuit_fingerprint, preflight_quantum_diagnostics

    initialize_database()
    problems: list[str] = []
    quantum = persist_chain(model_type="vqc")
    classical = persist_chain(model_type="logistic_regression")

    with session() as scope:
        supported = preflight_quantum_diagnostics(scope, quantum.experiment_id, quantum.model_id)
        unsupported = preflight_quantum_diagnostics(scope, classical.experiment_id, classical.model_id)
        missing = preflight_quantum_diagnostics(scope, quantum.experiment_id, classical.model_id)

    if not supported.feasible:
        problems.append("diagnostics preflight rejected a supported quantum model")
    if not supported.limitations:
        problems.append("diagnostics preflight no longer declares local-simulator limitations")
    if unsupported.feasible:
        problems.append("diagnostics preflight accepted a classical model")
    if not unsupported.limitations:
        problems.append("diagnostics preflight did not explain why a classical model is unsupported")
    if missing.feasible:
        problems.append("diagnostics preflight accepted a model that does not belong to the experiment")

    configuration = canonical_circuit_configuration()
    first = require_fingerprint(
        compute_circuit_fingerprint(configuration["model_type"], configuration), label="circuit fingerprint"
    )
    second = compute_circuit_fingerprint(configuration["model_type"], configuration)
    if first != second:
        problems.append("circuit fingerprint is not deterministic")

    limitations = " ".join(list(supported.limitations)).lower()
    if "hardware" in limitations and "no " not in limitations and "unavailable" not in limitations:
        problems.append("diagnostics limitations appear to claim hardware execution")

    if problems:
        return CheckResult(
            check_id="quantum_diagnostics_contract",
            category=CheckCategory.QUANTUM_INTEGRITY.value,
            status="FAIL",
            severity=Severity.REQUIRED,
            message="; ".join(problems),
            evidence={"problems": problems},
            failure_category=FailureCategory.SCIENTIFIC_REGRESSION,
            expected="structured, honest quantum diagnostics preflight for quantum models only",
            observed="; ".join(problems),
        )
    return CheckResult(
        check_id="quantum_diagnostics_contract",
        category=CheckCategory.QUANTUM_INTEGRITY.value,
        status="PASS",
        severity=Severity.REQUIRED,
        message="Quantum diagnostics preflight is structured, deterministic and refuses unsupported model families.",
        evidence={
            "circuit_fingerprint": first,
            "supported_limitations": list(supported.limitations),
            "unsupported_limitations": list(unsupported.limitations),
        },
    )
