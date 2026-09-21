"""Static-only checks; never import the application or run tests/models.
A successful result says nothing about dependency or runtime compatibility.
"""
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {".venv", "node_modules", ".git", "__pycache__", "dist"}
REQUIRED = ["README.md", ".env.example", "docker-compose.yml", "backend/requirements.txt",
    "backend/Dockerfile", "backend/app/main.py", "frontend/Dockerfile", "frontend/package.json",
    "frontend/src/App.tsx", "frontend/src/styles.css", "docs/architecture.md", "docs/limitations.md"]

def main():
    failures, python_count, json_count = [], 0, 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.relative_to(ROOT).parts):
            continue
        try:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
                python_count += 1
            elif path.suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
                json_count += 1
        except (SyntaxError, ValueError, UnicodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}")
    for filename in REQUIRED:
        if not (ROOT / filename).is_file():
            failures.append(f"Missing required source file: {filename}")
    print(json.dumps({"scope": "static syntax and file presence only", "python_files_parsed": python_count,
        "json_files_parsed": json_count, "failures": failures, "application_executed": False,
        "tests_executed": False, "runtime_verified": False}, indent=2))
    return bool(failures)

if __name__ == "__main__":
    sys.exit(main())
