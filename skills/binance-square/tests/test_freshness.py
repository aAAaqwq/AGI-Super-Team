"""Tests for the explicit STALE gate on the latest pointer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scanner.contracts import ContractViolation, format_utc
from scanner.freshness import (
    ALLOW_STALE_ENV,
    DEFAULT_MAX_POINTER_AGE,
    allow_stale_requested,
    assert_pointer_fresh,
    observe_pointer_freshness,
    read_verified_latest_pointer,
)


NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=timezone.utc)


def _payload(minutes_old: float) -> dict[str, object]:
    captured = NOW - timedelta(minutes=minutes_old)
    return {"scanned_at": format_utc(captured), "posts": []}


class StalePointerGateTests(unittest.TestCase):
    def test_fresh_pointer_passes(self) -> None:
        observation = assert_pointer_fresh(
            "data/v4/runs/latest.json",
            _payload(2),
            consumed_at=NOW,
        )
        self.assertFalse(observation.is_stale)
        self.assertFalse(observation.is_future)

    def test_boundary_within_window_passes(self) -> None:
        within = DEFAULT_MAX_POINTER_AGE.total_seconds() / 60.0
        observation = assert_pointer_fresh(
            "latest.json",
            _payload(within),
            consumed_at=NOW,
        )
        self.assertFalse(observation.is_stale)

    def test_boundary_just_over_window_fails_closed(self) -> None:
        over = DEFAULT_MAX_POINTER_AGE.total_seconds() / 60.0 + 1.0
        with self.assertRaises(ContractViolation):
            assert_pointer_fresh(
                "latest.json",
                _payload(over),
                consumed_at=NOW,
            )

    def test_default_window_covers_one_full_four_hour_slot(self) -> None:
        # The radar runs on a four-hour UTC slot; the default must comfortably
        # span one slot so a current pointer is never flagged between runs.
        self.assertGreaterEqual(
            DEFAULT_MAX_POINTER_AGE,
            timedelta(hours=4),
        )
        observation = assert_pointer_fresh(
            "latest.json",
            _payload(60 * 4),
            consumed_at=NOW,
        )
        self.assertFalse(observation.is_stale)

    def test_stale_pointer_fails_closed_with_full_context(self) -> None:
        with self.assertRaises(ContractViolation) as caught:
            assert_pointer_fresh(
                "data/v4/runs/latest.json",
                _payload(60 * 24 * 49),
                consumed_at=NOW,
            )
        message = str(caught.exception)
        self.assertIn("STALE_LATEST_POINTER", message)
        self.assertIn("pointer=data/v4/runs/latest.json", message)
        self.assertIn("captured_at=", message)
        self.assertIn("consumed_at=", message)
        self.assertIn("age_seconds=", message)

    def test_future_pointer_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            assert_pointer_fresh(
                "latest.json",
                _payload(-5),
                consumed_at=NOW,
            )

    def test_future_pointer_ignores_allow_stale_and_still_raises(self) -> None:
        # A future timestamp is a clock/logic fault, never merely old data: the
        # escape hatch must not mask it.  It raises even with allow_stale=True.
        with self.assertRaises(ContractViolation) as caught:
            assert_pointer_fresh(
                "latest.json",
                _payload(-5),
                consumed_at=NOW,
                allow_stale=True,
            )
        self.assertIn("captured after consumption", str(caught.exception))

    def test_allow_stale_returns_without_raising(self) -> None:
        observation = assert_pointer_fresh(
            "latest.json",
            _payload(60 * 24 * 49),
            consumed_at=NOW,
            allow_stale=True,
        )
        self.assertTrue(observation.is_stale)

    def test_allow_stale_env_is_honoured(self) -> None:
        with mock.patch.dict("os.environ", {ALLOW_STALE_ENV: "1"}):
            self.assertTrue(allow_stale_requested())
            observation = assert_pointer_fresh(
                "latest.json",
                _payload(60 * 24 * 49),
                consumed_at=NOW,
            )
        self.assertTrue(observation.is_stale)

    def test_allow_stale_explicit_false_overrides_env(self) -> None:
        with mock.patch.dict("os.environ", {ALLOW_STALE_ENV: "1"}):
            self.assertFalse(allow_stale_requested(explicit=False))

    def test_missing_timestamp_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            assert_pointer_fresh("latest.json", {"posts": []}, consumed_at=NOW)

    def test_observe_reports_age(self) -> None:
        observation = observe_pointer_freshness(
            "latest.json",
            _payload(3),
            consumed_at=NOW,
        )
        self.assertAlmostEqual(observation.age_seconds, 180.0, places=0)
        self.assertEqual(
            observation.maximum_age_seconds,
            DEFAULT_MAX_POINTER_AGE.total_seconds(),
        )


class ReadVerifiedPointerTests(unittest.TestCase):
    def _write_pointer(self, directory: Path, payload: dict[str, object]) -> Path:
        pointer = directory / "latest.json"
        pointer.write_text(json.dumps(payload), encoding="utf-8")
        return pointer

    def test_fresh_pointer_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pointer = self._write_pointer(Path(temporary), _payload(1))
            payload, observation = read_verified_latest_pointer(
                pointer, consumed_at=NOW
            )
            self.assertEqual(payload["posts"], [])
            self.assertFalse(observation.is_stale)

    def test_stale_pointer_read_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pointer = self._write_pointer(Path(temporary), _payload(60 * 24 * 49))
            with self.assertRaises(ContractViolation) as caught:
                read_verified_latest_pointer(pointer, consumed_at=NOW)
            self.assertIn("STALE_LATEST_POINTER", str(caught.exception))

    def test_stale_pointer_read_allows_escape_hatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pointer = self._write_pointer(Path(temporary), _payload(60 * 24 * 49))
            _, observation = read_verified_latest_pointer(
                pointer, consumed_at=NOW, allow_stale=True
            )
            self.assertTrue(observation.is_stale)

    def test_missing_pointer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing = Path(temporary) / "latest.json"
            with self.assertRaises(ContractViolation):
                read_verified_latest_pointer(missing, consumed_at=NOW)

    def test_unreadable_pointer_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pointer = Path(temporary) / "latest.json"
            pointer.write_text("not json", encoding="utf-8")
            with self.assertRaises(ContractViolation):
                read_verified_latest_pointer(pointer, consumed_at=NOW)


if __name__ == "__main__":
    unittest.main()
