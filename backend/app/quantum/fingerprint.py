"""Deterministic provider configuration fingerprints with secret exclusion."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_FRAGMENTS = ("secret", "token", "password", "credential", "api_key", "apikey", "access_key", "private_key", "connection_url")


def safe_configuration(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): safe_configuration(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not any(fragment in str(key).lower() for fragment in _SECRET_FRAGMENTS)
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [safe_configuration(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def configuration_fingerprint(configuration: Mapping[str, Any]) -> str:
    payload = json.dumps(safe_configuration(configuration), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
