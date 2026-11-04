#!/usr/bin/env python3
"""Read the latest radar pointer and fail closed when it is stale.

This is the explicit STALE gate for the single ``latest`` directory pointer.
It reads the compatibility ``latest.json`` link, compares the recorded
artifact time against the current time, and exits non-zero with a message that
includes the pointer path, the recorded timestamp, the current time and the
elapsed age.

The escape hatch (``--allow-stale`` or ``BINANCE_ALLOW_STALE=1``) prints a loud
warning but still returns the stale payload; it never downgrades silently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from datetime import timedelta


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from scanner.contracts import ContractViolation  # noqa: E402
from scanner.freshness import (  # noqa: E402
    DEFAULT_MAX_POINTER_AGE,
    observe_pointer_freshness,
    read_verified_latest_pointer,
)


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pointer",
        type=Path,
        default=PROJECT_DIR / "data" / "v4" / "runs" / "latest.json",
        help="compatibility latest pointer (latest.json)",
    )
    parser.add_argument(
        "--max-age-minutes",
        type=float,
        default=DEFAULT_MAX_POINTER_AGE.total_seconds() / 60.0,
        help=(
            "maximum accepted pointer age in minutes (default 260 = one "
            "four-hour slot plus retry/lateness slack)"
        ),
    )
    parser.add_argument(
        "--allow-stale",
        action="store_true",
        default=None,
        help=(
            "explicitly accept a stale pointer; prints a loud warning and "
            "exits 0.  Overrides BINANCE_ALLOW_STALE.  A pointer from the "
            "future is always rejected."
        ),
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="verify freshness without printing the pointer payload",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    maximum_age = timedelta(minutes=args.max_age_minutes)
    try:
        payload, observation = read_verified_latest_pointer(
            args.pointer,
            maximum_age=maximum_age,
            allow_stale=args.allow_stale,
        )
    except ContractViolation as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    result: dict[str, object] = {
        "status": "ok",
        "pointer": observation.pointer_path,
        "captured_at_utc": observation.captured_at_utc,
        "consumed_at_utc": observation.consumed_at_utc,
        "age_seconds": round(observation.age_seconds, 1),
        "maximum_age_seconds": observation.maximum_age_seconds,
        "stale": observation.is_stale,
        "future": observation.is_future,
    }
    if not args.check_only:
        result["payload"] = payload
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
