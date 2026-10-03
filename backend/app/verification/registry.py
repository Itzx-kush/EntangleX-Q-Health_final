"""Controlled registry of Scientific CI checks.

The registry is the single source of truth for what Scientific CI guarantees.
It powers three consumers:

* the CLI (``python -m app.verification``)
* the machine-readable check manifest (``scientific-ci-manifest.json``)
* the read-only ``/api/system/scientific-ci`` endpoint

Duplicate identifiers are rejected so a check can never silently shadow
another check's protection.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .models import SCIENTIFIC_CI_SCHEMA_VERSION, CheckCategory, CheckResult, Severity

# Profiles are declared here so the CLI, the manifest and the workflows agree.
FAST_PROFILE = "fast"
FULL_PROFILE = "full"
SUPPORTED_PROFILES: tuple[str, ...] = (FAST_PROFILE, FULL_PROFILE)

DEFAULT_TIMEOUT_SECONDS = 120.0


class DuplicateCheckError(ValueError):
    """Raised when two checks claim the same identifier."""


class UnknownCheckError(KeyError):
    """Raised when a caller requests a check identifier that is not registered."""


@dataclass(frozen=True)
class CheckDefinition:
    """Declarative description of one verification check."""

    check_id: str
    name: str
    category: str
    description: str
    severity: Severity
    runner: Callable[[], CheckResult]
    profiles: frozenset[str] = field(default_factory=lambda: frozenset({FAST_PROFILE, FULL_PROFILE}))
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    deprecated: bool = False
    replacement: str | None = None

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("check_id is required")
        unknown = set(self.profiles) - set(SUPPORTED_PROFILES)
        if unknown:
            raise ValueError(f"unknown profiles for {self.check_id}: {sorted(unknown)}")
        if not self.profiles:
            raise ValueError(f"{self.check_id} must belong to at least one profile")
        if self.deprecated and not self.replacement:
            raise ValueError(f"deprecated check {self.check_id} must name its replacement")

    def manifest_entry(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "id": self.check_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "severity": self.severity.value,
            "profiles": sorted(self.profiles),
            "timeout_seconds": self.timeout_seconds,
        }
        if self.deprecated:
            entry["deprecated"] = True
            entry["replacement"] = self.replacement
        return entry


class CheckRegistry:
    """Ordered registry with explicit duplicate and lookup behaviour."""

    def __init__(self) -> None:
        self._definitions: dict[str, CheckDefinition] = {}

    def register(self, definition: CheckDefinition) -> CheckDefinition:
        if definition.check_id in self._definitions:
            raise DuplicateCheckError(
                f"Scientific CI check identifier {definition.check_id!r} is already registered."
            )
        self._definitions[definition.check_id] = definition
        return definition

    def get(self, check_id: str) -> CheckDefinition:
        try:
            return self._definitions[check_id]
        except KeyError as exc:
            raise UnknownCheckError(f"Unknown Scientific CI check identifier: {check_id!r}") from exc

    def __contains__(self, check_id: object) -> bool:
        return check_id in self._definitions

    def __len__(self) -> int:
        return len(self._definitions)

    def definitions(self, *, include_deprecated: bool = False) -> list[CheckDefinition]:
        items = [
            definition
            for definition in sorted(self._definitions.values(), key=lambda item: item.check_id)
            if include_deprecated or not definition.deprecated
        ]
        return items

    def for_profile(self, profile: str, *, include_deprecated: bool = False) -> list[CheckDefinition]:
        if profile not in SUPPORTED_PROFILES:
            raise ValueError(f"Unknown Scientific CI profile: {profile!r}")
        return [
            definition
            for definition in self.definitions(include_deprecated=include_deprecated)
            if profile in definition.profiles
        ]

    def select(self, check_ids: Iterable[str]) -> list[CheckDefinition]:
        requested = list(check_ids)
        unknown = [check_id for check_id in requested if check_id not in self._definitions]
        if unknown:
            raise UnknownCheckError(f"Unknown Scientific CI check identifiers: {sorted(unknown)}")
        return [self._definitions[check_id] for check_id in requested]

    def categories(self) -> list[str]:
        return sorted({definition.category for definition in self._definitions.values()})

    def manifest(self, *, include_deprecated: bool = True) -> dict[str, Any]:
        return {
            "schema_version": SCIENTIFIC_CI_SCHEMA_VERSION,
            "profiles": list(SUPPORTED_PROFILES),
            "categories": self.categories(),
            "checks": [
                definition.manifest_entry()
                for definition in self.definitions(include_deprecated=include_deprecated)
            ],
        }


registry = CheckRegistry()


def check(
    *,
    check_id: str,
    name: str,
    category: str | CheckCategory,
    description: str,
    severity: Severity,
    profiles: Iterable[str] = SUPPORTED_PROFILES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    deprecated: bool = False,
    replacement: str | None = None,
) -> Callable[[Callable[[], CheckResult]], Callable[[], CheckResult]]:
    """Decorator registering a zero-argument runner as a Scientific CI check."""

    resolved_category = category.value if isinstance(category, CheckCategory) else category

    def decorator(runner: Callable[[], CheckResult]) -> Callable[[], CheckResult]:
        registry.register(
            CheckDefinition(
                check_id=check_id,
                name=name,
                category=resolved_category,
                description=description,
                severity=severity,
                runner=runner,
                profiles=frozenset(profiles),
                timeout_seconds=timeout_seconds,
                deprecated=deprecated,
                replacement=replacement,
            )
        )
        return runner

    return decorator


# Import order is fixed and deterministic: every module registers its checks as
# an import side effect.  Adding a module here is the only way to add checks.
CHECK_MODULES: tuple[str, ...] = (
    ".checks.imports",
    ".checks.deployment",
    ".checks.database",
    ".checks.reproducibility",
    ".checks.fingerprints",
    ".checks.immutability",
    ".checks.pipelines",
    ".checks.protocols",
    ".checks.experiments",
    ".checks.evidence",
    ".checks.lineage",
    ".checks.audit",
    ".checks.subgroups",
    ".checks.dataset_quality",
    ".checks.model_cards",
    ".checks.controlled_comparison",
    ".checks.quantum",
    ".checks.artifacts",
    ".checks.privacy",
    ".checks.schema_contracts",
    ".checks.selfcheck",
)

_loaded = False


def load_checks() -> CheckRegistry:
    """Import every check module exactly once, then return the populated registry."""
    global _loaded
    if not _loaded:
        for module in CHECK_MODULES:
            importlib.import_module(module, package=__package__)
        _loaded = True
    return registry
