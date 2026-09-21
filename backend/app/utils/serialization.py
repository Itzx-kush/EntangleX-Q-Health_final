import hashlib
import json
import math
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from typing import Any
import numpy as np

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.generic):
        return clean_json(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value

def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(clean_json(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def software_versions() -> dict[str, str | None]:
    import platform
    names = ["fastapi", "pydantic", "SQLAlchemy", "numpy", "pandas", "scipy", "scikit-learn", "shap", "qiskit", "qiskit-machine-learning", "qiskit-aer", "dill"]
    result: dict[str, str | None] = {"python": platform.python_version(), "platform": platform.platform()}
    for name in names:
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result
