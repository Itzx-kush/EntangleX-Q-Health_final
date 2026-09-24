import hashlib
import hmac
import io
import os
import pickle
import re
from pathlib import Path
from uuid import UUID, uuid4
import dill
from ..config import get_settings
from ..utils.errors import AppError


def get_artifact_key() -> bytes:
    key_path = (get_settings().root / ".artifact_key").resolve()
    if key_path.is_file():
        try:
            key = key_path.read_bytes()
            if len(key) >= 32:
                return key
        except OSError:
            pass
    key = os.urandom(32)
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        temp = key_path.with_name(f".{uuid4().hex}.tmp")
        temp.write_bytes(key)
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        temp.replace(key_path)
    except OSError:
        pass
    return key


class RestrictedUnpickler(dill.Unpickler):
    ALLOWED_MODULE_PREFIXES = (
        "builtins", "collections", "datetime", "numpy", "pandas",
        "sklearn", "scipy", "qiskit", "qiskit_machine_learning",
        "qiskit_aer", "app", "typing", "dill", "_codecs", "copyreg",
        "uuid", "decimal", "math", "re", "functools", "operator"
    )
    BLOCKED_MODULES = {
        "os", "posix", "nt", "subprocess", "sys", "shutil", "socket",
        "asyncio", "importlib", "ctypes", "code", "pdb", "threading",
        "multiprocessing", "webbrowser", "platform", "types"
    }
    BLOCKED_BUILTINS = {
        "eval", "exec", "compile", "open", "input", "__import__",
        "globals", "locals", "breakpoint", "exit", "quit", "system"
    }
    BLOCKED_CODE_NAMES = {
        "os", "posix", "nt", "subprocess", "sys", "shutil", "socket",
        "asyncio", "importlib", "ctypes", "eval", "exec", "compile",
        "open", "input", "__import__", "globals", "locals", "system",
        "Popen", "call", "check_output", "run", "spawn", "fork"
    }

    def find_class(self, module: str, name: str):
        if module in self.BLOCKED_MODULES:
            raise pickle.UnpicklingError(f"Forbidden module during deserialization: {module}")
        if module == "builtins" and name in self.BLOCKED_BUILTINS:
            raise pickle.UnpicklingError(f"Forbidden builtin function during deserialization: {name}")
        if not any(module == prefix or module.startswith(prefix + ".") for prefix in self.ALLOWED_MODULE_PREFIXES):
            raise pickle.UnpicklingError(f"Forbidden module/class during deserialization: {module}.{name}")

        target = super().find_class(module, name)
        if module == "dill._dill" and name == "_create_code":
            def safe_create_code(*args, **kwargs):
                code_obj = target(*args, **kwargs)
                forbidden = set(code_obj.co_names).intersection(self.BLOCKED_CODE_NAMES)
                if forbidden:
                    raise pickle.UnpicklingError(f"Forbidden reference in compiled code object: {forbidden}")
                return code_obj
            return safe_create_code
        return target

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
    payload = dill.dumps(bundle, protocol=5)
    key = get_artifact_key()
    digest_val = hmac.new(key, payload, hashlib.sha256).hexdigest()
    atomic_bytes(safe_path("models", identity, ".dill"), payload)
    return digest_val

def load_model(identity: str, expected: str) -> dict:
    # Only application-created, HMAC-verified local artifacts. NEVER accept uploaded models.
    path = safe_path("models", identity, ".dill")
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AppError("integrity_error", "Stored artifact is missing or its integrity hash has changed.", 409) from exc
    key = get_artifact_key()
    computed_hmac = hmac.new(key, payload, hashlib.sha256).hexdigest()
    computed_sha256 = hashlib.sha256(payload).hexdigest()
    if not (hmac.compare_digest(computed_hmac, expected) or hmac.compare_digest(computed_sha256, expected)):
        raise AppError("integrity_error", "Stored artifact is missing or its integrity hash has changed.", 409)
    try:
        return RestrictedUnpickler(io.BytesIO(payload)).load()
    except Exception as exc:
        raise AppError("artifact_invalid", "Stored model artifact could not be loaded safely.", 409) from exc
