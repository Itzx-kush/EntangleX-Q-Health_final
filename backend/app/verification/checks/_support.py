"""Shared helpers for Scientific CI check runners."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from app.utils.errors import AppError


@contextmanager
def expect_app_error(*codes: str) -> Iterator[dict[str, Any]]:
    """Capture an expected AppError; expose its code and message to the caller."""
    captured: dict[str, Any] = {"raised": False, "code": None, "message": None}
    try:
        yield captured
    except AppError as exc:
        captured.update({"raised": True, "code": exc.code, "message": exc.message})
    if not captured["raised"]:
        raise AssertionError(f"expected an AppError with code in {codes or ('*',)}, but none was raised")
    if codes and captured["code"] not in codes:
        raise AssertionError(f"expected an AppError with code in {codes}, received {captured['code']!r}")


def walk_keys(payload: Any) -> set[str]:
    """Every mapping key in a nested payload."""
    keys: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(str(key))
            keys |= walk_keys(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            keys |= walk_keys(item)
    return keys


SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "secret",
        "api_key",
        "apikey",
        "access_token",
        "refresh_token",
        "private_key",
        "credential",
        "credentials",
        "authorization",
        "bearer",
        "patient_id",
        "patient_identifier",
        "mrn",
        "ssn",
        "raw_rows",
        "raw_patient_rows",
        "csv_content",
    }
)


def sensitive_keys_present(payload: Any) -> list[str]:
    """Keys that must never appear in a serialized research payload."""
    return sorted(key for key in walk_keys(payload) if key.lower() in SENSITIVE_KEYS)


def flatten_strings(payload: Any, limit: int = 4000) -> str:
    """Compact text view of a payload for forbidden-substring assertions."""
    import json

    from app.utils.serialization import clean_json

    text = json.dumps(clean_json(payload), default=str, sort_keys=True)
    return text[:limit]


def deterministic_fingerprint(fn, *args, **kwargs) -> tuple[str, str]:
    """Return two fingerprints computed from identical input."""
    first = fn(*args, **kwargs)
    second = fn(*args, **kwargs)
    return first, second


def require_fingerprint(value: Any, *, label: str) -> str:
    text = str(value)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise AssertionError(f"{label} is not a 64-character lowercase hex fingerprint: {text!r}")
    return text
