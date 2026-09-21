import hashlib
import os
import re
from pathlib import Path
from uuid import UUID, uuid4
from ..config import get_settings
from ..utils.errors import AppError

def sanitize_filename(name: str) -> str:
    name = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:160] or "dataset.csv"

def safe_path(area: str, identity: str, suffix: str) -> Path:
    if area not in {"data/datasets", "models", "experiments"} or suffix not in {".csv", ".dill", ".json", ".html"}:
        raise AppError("invalid_path", "Unsupported storage location.")
    try:
        identity = str(UUID(str(identity)))
    except ValueError as exc:
        raise AppError("invalid_id", "Resource IDs must be UUIDs.") from exc
    base = (get_settings().root / area).resolve()
    path = (base / f"{identity}{suffix}").resolve()
    if path.parent != base:
        raise AppError("invalid_path", "Unsafe storage path.")
    return path

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def atomic_bytes(path: Path, value: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{uuid4().hex}.tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            temp.chmod(0o600)
        except OSError:
            pass  # Windows may not implement POSIX mode semantics.
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return hashlib.sha256(value).hexdigest()

def verify(path: Path, expected: str) -> None:
    if not path.is_file() or digest(path) != expected:
        raise AppError("integrity_error", "Stored artifact is missing or its integrity hash has changed.", 409)

def save_model(identity: str, bundle: dict) -> str:
    import dill
    return atomic_bytes(safe_path("models", identity, ".dill"), dill.dumps(bundle, protocol=5))

def load_model(identity: str, expected: str) -> dict:
    # Only application-created, hash-checked local artifacts. NEVER accept uploaded models.
    import dill
    path = safe_path("models", identity, ".dill")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AppError("integrity_error", "Stored artifact is missing or its integrity hash has changed.", 409) from exc
    if hashlib.sha256(payload).hexdigest() != expected:
        raise AppError("integrity_error", "Stored artifact is missing or its integrity hash has changed.", 409)
    try:
        return dill.loads(payload)
    except Exception as exc:
        raise AppError("artifact_invalid", "Stored model artifact could not be loaded safely.", 409) from exc
