"""Command-line entry point: ``python -m app.verification``.

Exit codes:
    0  every required check passed
    1  at least one required check failed
    2  the verification infrastructure itself failed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .isolation import cleanup_environment, prepare_environment
from .models import SCIENTIFIC_CI_SCHEMA_VERSION
from .registry import SUPPORTED_PROFILES, load_checks
from .service import (
    EXIT_INFRASTRUCTURE_ERROR,
    baseline_document,
    render_report,
    run_verification,
    verification_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.verification",
        description=(
            "Scientific CI verification: implementation-level scientific, reproducibility and deployment invariants. "
            "A passing run is not independent scientific validation."
        ),
    )
    parser.add_argument("--profile", choices=SUPPORTED_PROFILES, default="fast", help="verification profile to run")
    parser.add_argument("--check", action="append", default=None, help="run only this check identifier (repeatable)")
    parser.add_argument("--list", action="store_true", help="list the registered checks and exit")
    parser.add_argument("--manifest-out", type=Path, default=None, help="write the machine-readable check manifest")
    parser.add_argument("--baseline-out", type=Path, default=None, help="write the scientific baseline document")
    parser.add_argument("--json-out", type=Path, default=None, help="write the full report as JSON")
    parser.add_argument("--print-baseline", action="store_true", help="print the baseline document and exit")
    parser.add_argument("--include-deprecated", action="store_true", help="include deprecated checks")
    parser.add_argument("--quiet", action="store_true", help="suppress per-check progress lines")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        prepare_environment()
        active = load_checks()

        if args.list:
            for definition in active.definitions(include_deprecated=args.include_deprecated):
                print(f"{definition.severity.value:<8} {definition.category:<24} {definition.check_id}")
            print(f"\n{len(active)} checks registered (schema {SCIENTIFIC_CI_SCHEMA_VERSION}).")
            return 0

        if args.manifest_out is not None:
            args.manifest_out.write_text(json.dumps(verification_manifest(), indent=2, sort_keys=True) + "\n")
        if args.baseline_out is not None:
            args.baseline_out.write_text(json.dumps(baseline_document(), indent=2, sort_keys=True) + "\n")
        if args.print_baseline:
            print(json.dumps(baseline_document(), indent=2, sort_keys=True))
            return 0

        def progress(result) -> None:
            if not args.quiet:
                print(f"{result.status.value:<12} {result.check_id}", flush=True)

        report = run_verification(
            args.profile,
            check_ids=args.check,
            include_deprecated=args.include_deprecated,
            check_registry=active,
            progress=progress,
        )
        if not args.quiet:
            print()
        print(render_report(report, show_checks=args.quiet))
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n")
        return report.exit_code
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        print(f"Scientific CI infrastructure error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INFRASTRUCTURE_ERROR
    finally:
        cleanup_environment()


if __name__ == "__main__":
    raise SystemExit(main())
