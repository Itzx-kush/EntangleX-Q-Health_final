"""Run a REAL, bounded benchmark against an already-running local backend.
No application result exists until the user executes this script.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import get_settings

def request(base: str, method: str, path: str, payload=None):
    headers = {"Accept": "application/json"}
    token = get_settings().api_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    encoded = None
    if payload is not None:
        encoded = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base.rstrip("/") + "/api" + path, data=encoded, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read()).get("error", {}).get("message", f"HTTP {exc.code}")
        except (ValueError, AttributeError):
            message = f"HTTP {exc.code}"
        raise RuntimeError(message) from None
    except urllib.error.URLError:
        raise RuntimeError("Backend is not reachable. Start it before executing this script.") from None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--quantum", action="store_true", help="Include VQC and QSVC; may be computationally expensive.")
    parser.add_argument("--max-samples", type=int, default=160)
    parser.add_argument("--timeout", type=int, default=7200, help="Maximum seconds to poll before exiting, without pretending the job completed.")
    args = parser.parse_args()
    dataset = request(args.base, "POST", "/datasets/demo")
    models = ["logistic_regression", "svm", "random_forest"]
    if args.quantum:
        models += ["vqc", "qsvc"]
    created = request(args.base, "POST", "/training/jobs", {"dataset_id": dataset["id"], "models": models, "max_samples": args.max_samples})
    job_id, experiment_id = created["job"]["id"], created["experiment"]["id"]
    print(f"Created experiment: {experiment_id}\nTraining job: {job_id}")
    start, previous = time.monotonic(), None
    while time.monotonic() - start < args.timeout:
        job = request(args.base, "GET", f"/training/jobs/{job_id}")
        current = (job["status"], job["state"])
        if current != previous:
            print(f"{job['status']}: {job['state']}", flush=True)
            previous = current
        if job["status"] not in ("queued", "running", "cancel_requested"):
            break
        time.sleep(2)
    else:
        print("Polling timed out. The server may still be processing. Inspect Training in the UI; no completion is claimed.")
        return 2
    result = request(args.base, "GET", f"/experiments/{experiment_id}/comparison")
    print(json.dumps(result, indent=2))
    print("Research benchmark only. No result establishes clinical validation or general quantum advantage.")
    return 0 if job["status"] == "succeeded" else 1

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, KeyboardInterrupt) as exc:
        print(str(exc) or "Polling interrupted; inspect server job status.", file=sys.stderr)
        raise SystemExit(1)
