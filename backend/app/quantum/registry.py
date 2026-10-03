"""Provider registry with explicit duplicate and lookup behavior."""
from __future__ import annotations

from collections.abc import Iterable
from .contracts import ErrorCategory
from .errors import QuantumProviderError
from .providers import PennyLaneLocalProvider, QuantumProvider, QiskitLocalProvider


class ProviderRegistry:
    def __init__(self, providers: Iterable[QuantumProvider] = ()):
        self._providers: dict[str, QuantumProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: QuantumProvider) -> None:
        if provider.provider_id in self._providers:
            raise QuantumProviderError(ErrorCategory.CONFIGURATION_ERROR, "A quantum provider with this identifier is already registered.")
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> QuantumProvider:
        provider = self._providers.get(provider_id)
        if provider is None:
            raise QuantumProviderError(ErrorCategory.CONFIGURATION_ERROR, "The requested quantum provider is not registered.")
        return provider

    def list(self) -> list[QuantumProvider]:
        return list(self._providers.values())


registry = ProviderRegistry([QiskitLocalProvider(), PennyLaneLocalProvider()])
