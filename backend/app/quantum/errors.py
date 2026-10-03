"""Stable, sanitized errors crossing the provider boundary."""
from __future__ import annotations

from typing import Any
from .contracts import ErrorCategory


class QuantumProviderError(RuntimeError):
    def __init__(self, category: ErrorCategory, message: str, *, provider_context: dict[str, Any] | None = None):
        super().__init__(message)
        self.category = category
        self.safe_message = message
        self.provider_context = provider_context or {}

    def as_dict(self) -> dict[str, Any]:
        return {"category": self.category.value, "message": self.safe_message}
