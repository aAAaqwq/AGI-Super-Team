"""Explicit STALE gate for the single ``latest`` directory pointer.

The radar publishes one atomically-switched directory pointer
(``data/v4/runs/latest``) plus compatibility links (``latest.json`` /
``latest.md``).  When no successful run has replaced the pointer for a long
time, downstream consumers used to read the old artifacts and present them as
current data: a *silent* failure, which is worse than an explicit error.

This module adds one explicit freshness assertion at the pointer read point.
It fails closed by default.  A visible escape hatch
(``BINANCE_ALLOW_STALE=1`` or ``allow_stale=True``) is available but always
prints a loud warning, and never silently downgrades to stale data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import sys
from typing import Any, Mapping

from .contracts import ContractViolation, format_utc, parse_utc


# Contract default.  The pointer is published by ``_publish_latest`` once per
# successful radar run.  The radar runs on the fixed four-hour UTC slot
# (``MAX_PRODUCTION_SLOT_LATENESS``), so a 10-minute window would flag a
# perfectly current pointer as STALE within minutes of every run.  The window
# must therefore span one full slot plus scheduling/retry slack: the two
# independent Feed captures (initial + the single +10 minute retry) plus the
# maximum tolerated slot lateness.
#
# 4h slot + 10min retry + 10min lateness slack = 260 minutes.
DEFAULT_MAX_POINTER_AGE = timedelta(minutes=260)

ALLOW_STALE_ENV = "BINANCE_ALLOW_STALE"

STALE_POINTER_PREFIX = "STALE_LATEST_POINTER"


@dataclass(frozen=True)
class LatestPointerFreshness:
    """Observation of one pointer's recorded artifact time against ``now``."""

    pointer_path: str
    captured_at_utc: str
    consumed_at_utc: str
    age_seconds: float
    maximum_age_seconds: float
    is_stale: bool
    is_future: bool


def allow_stale_requested(explicit: bool | None = None) -> bool:
    """Return whether the caller explicitly opted into stale consumption.

    ``explicit`` wins when supplied; otherwise the ``BINANCE_ALLOW_STALE``
    environment variable is consulted.  Only an unambiguous truthy value
    enables the escape hatch.
    """

    if explicit is not None:
        return bool(explicit)
    value = os.environ.get(ALLOW_STALE_ENV)
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _pointer_captured_at(payload: Mapping[str, Any]) -> Any:
    """Return the pointer's recorded artifact timestamp.

    The compatibility ``latest.json`` link resolves to ``latest/report.json``;
    the report records ``scanned_at`` (as a ``{"utc": ...}`` mapping) and
    ``report_generated_at`` (a scalar).  Feed snapshots use
    ``scanned_at``/``captured_at`` scalars.  The first usable value wins so one
    contract covers both shapes.
    """

    for key in ("scanned_at", "report_generated_at", "captured_at"):
        value = payload.get(key)
        if not value:
            continue
        if isinstance(value, Mapping):
            for nested in ("utc", "iso", "iso8601"):
                candidate = value.get(nested)
                if candidate:
                    return candidate
            continue
        return value
    return None


def observe_pointer_freshness(
    pointer_path: Path | str,
    payload: Mapping[str, Any],
    *,
    consumed_at: datetime | str,
    maximum_age: timedelta = DEFAULT_MAX_POINTER_AGE,
) -> LatestPointerFreshness:
    """Observe freshness without raising; the caller decides policy."""

    if maximum_age <= timedelta(0):
        raise ContractViolation("STALE pointer maximum_age must be positive")
    captured_value = _pointer_captured_at(payload)
    if captured_value is None:
        raise ContractViolation(
            "latest pointer is missing a recorded artifact timestamp"
        )
    captured = parse_utc(captured_value)
    consumed = parse_utc(consumed_at)
    age = consumed - captured
    is_future = age < timedelta(0)
    is_stale = (not is_future) and age > maximum_age
    return LatestPointerFreshness(
        pointer_path=str(pointer_path),
        captured_at_utc=format_utc(captured),
        consumed_at_utc=format_utc(consumed),
        age_seconds=age.total_seconds(),
        maximum_age_seconds=maximum_age.total_seconds(),
        is_stale=is_stale,
        is_future=is_future,
    )


def assert_pointer_fresh(
    pointer_path: Path | str,
    payload: Mapping[str, Any],
    *,
    consumed_at: datetime | str | None = None,
    maximum_age: timedelta = DEFAULT_MAX_POINTER_AGE,
    allow_stale: bool | None = None,
) -> LatestPointerFreshness:
    """Fail closed when the ``latest`` pointer is stale or from the future.

    Raises :class:`ContractViolation` with a message carrying the pointer path,
    the recorded timestamp, the current time and the elapsed age.  The stale
    escape hatch prints a loud warning to stderr and returns the observation
    instead.

    A *future* timestamp (the pointer claims to have been captured after
    consumption) is a clock/logic fault rather than merely old data, so it is
    **always** rejected -- the escape hatch does not disable it.  When the hatch
    is requested for a future pointer it still prints the loud warning, then
    raises, so an operator cannot mistake the masked fault for a served run.
    """

    consumed = consumed_at if consumed_at is not None else datetime.now(timezone.utc)
    observation = observe_pointer_freshness(
        pointer_path,
        payload,
        consumed_at=consumed,
        maximum_age=maximum_age,
    )
    if observation.is_future:
        # A future pointer is a clock/logic fault, not merely old data.  It is
        # never downgraded silently: the escape hatch still fails closed for it
        # (unlike the stale branch) so a corrupt timestamp can never be masked.
        if allow_stale_requested(allow_stale):
            print(
                "[WARN] "
                f"{STALE_POINTER_PREFIX}: pointer is from the future and "
                f"remains rejected even though "
                f"{ALLOW_STALE_ENV} / allow_stale was set | "
                f"pointer={observation.pointer_path} "
                f"captured_at={observation.captured_at_utc} "
                f"consumed_at={observation.consumed_at_utc} "
                f"age_seconds={observation.age_seconds:.0f}",
                file=sys.stderr,
                flush=True,
            )
        raise ContractViolation(
            f"{STALE_POINTER_PREFIX}: latest pointer was captured after "
            f"consumption | pointer={observation.pointer_path} "
            f"captured_at={observation.captured_at_utc} "
            f"consumed_at={observation.consumed_at_utc} "
            f"age_seconds={observation.age_seconds:.0f}"
        )
    if observation.is_stale:
        if allow_stale_requested(allow_stale):
            print(
                "[WARN] "
                f"{STALE_POINTER_PREFIX}: serving STALE data because "
                f"{ALLOW_STALE_ENV} / allow_stale was set | "
                f"pointer={observation.pointer_path} "
                f"captured_at={observation.captured_at_utc} "
                f"age_seconds={observation.age_seconds:.0f} "
                f"maximum_age_seconds={observation.maximum_age_seconds:.0f}",
                file=sys.stderr,
                flush=True,
            )
            return observation
        raise ContractViolation(
            f"{STALE_POINTER_PREFIX}: latest pointer is stale and must not be "
            f"silently consumed | pointer={observation.pointer_path} "
            f"captured_at={observation.captured_at_utc} "
            f"consumed_at={observation.consumed_at_utc} "
            f"age_seconds={observation.age_seconds:.0f} "
            f"maximum_age_seconds={observation.maximum_age_seconds:.0f}"
        )
    return observation


def read_verified_latest_pointer(
    pointer_path: Path | str,
    *,
    resolved_artifacts: Mapping[str, Any] | None = None,
    consumed_at: datetime | str | None = None,
    maximum_age: timedelta = DEFAULT_MAX_POINTER_AGE,
    allow_stale: bool | None = None,
) -> tuple[dict[str, Any], LatestPointerFreshness]:
    """Read and freshness-check the compatibility ``latest.json`` pointer.

    ``pointer_path`` is the ``latest.json`` link.  Its target artifacts are
    read from the link itself (the symlink resolves to ``latest/report.json``).
    Raises :class:`ContractViolation` when the pointer is missing, unreadable,
    not a JSON object, stale, or from the future.
    """

    import json

    path = Path(pointer_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContractViolation(
            f"{STALE_POINTER_PREFIX}: latest pointer does not exist | "
            f"pointer={path}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractViolation(
            f"{STALE_POINTER_PREFIX}: latest pointer is not readable JSON | "
            f"pointer={path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ContractViolation(
            f"{STALE_POINTER_PREFIX}: latest pointer must be a JSON object | "
            f"pointer={path}"
        )
    observation = assert_pointer_fresh(
        path,
        payload,
        consumed_at=consumed_at,
        maximum_age=maximum_age,
        allow_stale=allow_stale,
    )
    return payload, observation


__all__ = [
    "ALLOW_STALE_ENV",
    "DEFAULT_MAX_POINTER_AGE",
    "STALE_POINTER_PREFIX",
    "LatestPointerFreshness",
    "allow_stale_requested",
    "assert_pointer_fresh",
    "observe_pointer_freshness",
    "read_verified_latest_pointer",
]
