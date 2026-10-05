"""CLI entrypoint for the flagship live hybrid runtime verification."""
from __future__ import annotations

import json

from app.hybrid_runtime import verify_hybrid_runtime


if __name__ == "__main__":
    print(json.dumps(verify_hybrid_runtime(force=True), indent=2))
