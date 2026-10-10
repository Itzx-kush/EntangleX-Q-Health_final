"""Optional adapter for the custom Java Redis-compatible TCP/RESP server.

The bridge deliberately exposes only a small, explicit command allowlist. It is
not a general-purpose network proxy and never persists application records.
"""
from __future__ import annotations

import socket
import time
from typing import BinaryIO, Any

from .config import Settings


class RedisBridgeError(RuntimeError):
    """Safe-to-display error from the optional Redis integration."""


def _encode_command(parts: list[str]) -> bytes:
    encoded = [part.encode("utf-8") for part in parts]
    chunks = [f"*{len(encoded)}\r\n".encode("ascii")]
    for item in encoded:
        chunks.extend((f"${len(item)}\r\n".encode("ascii"), item, b"\r\n"))
    return b"".join(chunks)


def _read_line(stream: BinaryIO) -> bytes:
    line = stream.readline()
    if not line or not line.endswith(b"\r\n"):
        raise RedisBridgeError("The Redis server returned an incomplete RESP response.")
    return line[:-2]


def _read_resp(stream: BinaryIO) -> Any:
    """Read the RESP2 response types used by the Java server."""
    line = _read_line(stream)
    if not line:
        raise RedisBridgeError("The Redis server returned an empty RESP response.")

    prefix, payload = line[:1], line[1:]
    if prefix == b"+":
        return payload.decode("utf-8", errors="replace")
    if prefix == b"-":
        raise RedisBridgeError(payload.decode("utf-8", errors="replace")[:240])
    if prefix == b":":
        try:
            return int(payload)
        except ValueError as exc:
            raise RedisBridgeError("The Redis server returned an invalid integer.") from exc
    if prefix == b"$":
        try:
            length = int(payload)
        except ValueError as exc:
            raise RedisBridgeError("The Redis server returned an invalid bulk-string length.") from exc
        if length == -1:
            return None
        if length < 0 or length > 1_048_576:
            raise RedisBridgeError("The Redis server returned an unsupported bulk-string length.")
        value = stream.read(length)
        trailer = stream.read(2)
        if len(value) != length or trailer != b"\r\n":
            raise RedisBridgeError("The Redis server returned an incomplete bulk string.")
        return value.decode("utf-8", errors="replace")
    if prefix == b"*":
        try:
            count = int(payload)
        except ValueError as exc:
            raise RedisBridgeError("The Redis server returned an invalid array length.") from exc
        if count == -1:
            return None
        if count < 0 or count > 1_000:
            raise RedisBridgeError("The Redis server returned an unsupported array length.")
        return [_read_resp(stream) for _ in range(count)]
    raise RedisBridgeError("The Redis server returned an unsupported RESP response type.")


def validate_command(command: list[str]) -> list[str]:
    if not command or any(not isinstance(part, str) for part in command):
        raise RedisBridgeError("Enter a Redis command.")
    if any("\x00" in part for part in command):
        raise RedisBridgeError("Commands cannot contain null bytes.")
    name = command[0].strip().upper()
    args = command[1:]
    arity = {"PING": (0, 0), "ECHO": (1, 1), "SET": (2, 2), "GET": (1, 1)}
    if name not in arity:
        raise RedisBridgeError("For safety, Redis Lab currently supports PING, ECHO, SET, and GET only.")
    minimum, maximum = arity[name]
    if not minimum <= len(args) <= maximum:
        expected = "no arguments" if maximum == 0 else ("one argument" if minimum == 1 else "a key and a value")
        raise RedisBridgeError(f"{name} expects {expected}.")
    if any(len(part.encode("utf-8")) > 65_536 for part in command):
        raise RedisBridgeError("Each command argument must be 64 KiB or smaller.")
    return [name, *args]


def execute_command(settings: Settings, command: list[str]) -> Any:
    if not settings.redis_enabled:
        raise RedisBridgeError("Redis Lab is disabled. Enable QHEALTH_REDIS_ENABLED and start the Java Redis service.")
    normalized = validate_command(command)
    try:
        with socket.create_connection(
            (settings.redis_host, settings.redis_port),
            timeout=settings.redis_timeout_seconds,
        ) as client:
            client.settimeout(settings.redis_timeout_seconds)
            client.sendall(_encode_command(normalized))
            with client.makefile("rb") as stream:
                return _read_resp(stream)
    except RedisBridgeError:
        raise
    except (OSError, TimeoutError) as exc:
        raise RedisBridgeError("The Java Redis server is unreachable or did not respond in time.") from exc


def get_status(settings: Settings) -> dict[str, Any]:
    if not settings.redis_enabled:
        return {
            "enabled": False,
            "status": "disabled",
            "target": None,
            "latency_ms": None,
            "message": "Redis is optional and currently disabled. The existing Q-Health workflow is unchanged.",
        }
    started = time.perf_counter()
    try:
        response = execute_command(settings, ["PING"])
        elapsed = round((time.perf_counter() - started) * 1_000, 2)
        if response != "PONG":
            raise RedisBridgeError("The Redis server responded, but its PING response was unexpected.")
        return {
            "enabled": True,
            "status": "online",
            "target": f"{settings.redis_host}:{settings.redis_port}",
            "latency_ms": elapsed,
            "message": "The custom Java Redis server responded to PING.",
        }
    except RedisBridgeError:
        return {
            "enabled": True,
            "status": "offline",
            "target": f"{settings.redis_host}:{settings.redis_port}",
            "latency_ms": None,
            "message": "Redis is configured but unavailable. Q-Health continues without the optional Redis feature.",
        }
