"""idempotency.py 的标准库测试：首次/重复/TTL 过期/并发追加与并发领取。"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("idempotency.py")
SPEC = importlib.util.spec_from_file_location("reliable_automation_idempotency", SCRIPT)
idempotency = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(idempotency)


KEY = "daily-review:inbox:2026-09-16"
DRIVER = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("idem", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.exit(0 if module.claim(sys.argv[2], sys.argv[3]) else 1)
"""


def read_lines(path):
    return [line for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


class IdempotencyTestCase(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.ledger = Path(self._temporary.name) / "ledger.jsonl"


class ClaimTests(IdempotencyTestCase):
    def test_first_claim_succeeds_and_is_written_to_disk(self):
        self.assertTrue(idempotency.claim(KEY, self.ledger))
        lines = read_lines(self.ledger)
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["key"], KEY)
        self.assertEqual(record["pid"], os.getpid())
        self.assertEqual(record["schemaVersion"], idempotency.SCHEMA_VERSION)
        self.assertTrue(record["iso"].endswith("Z"))
        self.assertAlmostEqual(record["ts"], time.time(), delta=5)

    def test_second_claim_returns_false_and_does_not_append(self):
        self.assertTrue(idempotency.claim(KEY, self.ledger))
        self.assertFalse(idempotency.claim(KEY, self.ledger))
        self.assertEqual(len(read_lines(self.ledger)), 1)

    def test_distinct_keys_are_independent(self):
        self.assertTrue(idempotency.claim("push:daily-report:2026-09-16", self.ledger))
        self.assertTrue(idempotency.claim("publish:weekly-report:2026-W38", self.ledger))
        self.assertFalse(idempotency.claim("push:daily-report:2026-09-16", self.ledger))
        self.assertEqual(len(read_lines(self.ledger)), 2)

    def test_ledger_directory_is_created_on_demand(self):
        nested = Path(self._temporary.name) / "state" / "nested" / "ledger.jsonl"
        self.assertTrue(idempotency.claim(KEY, nested))
        self.assertTrue(nested.is_file())

    def test_claim_expands_tilde_paths(self):
        with mock.patch.dict(os.environ, {"HOME": self._temporary.name}):
            self.assertTrue(idempotency.claim(KEY, "~/ledger.jsonl"))
            self.assertTrue((Path(self._temporary.name) / "ledger.jsonl").is_file())

    def test_keys_are_validated_before_touching_disk(self):
        for bad in ("", "   ", None, "has space", "x" * 600, 12):
            with self.assertRaises(ValueError):
                idempotency.claim(bad, self.ledger)
        self.assertFalse(self.ledger.exists())

    def test_key_shape_warning_flags_unstructured_keys(self):
        self.assertIsNone(idempotency.key_shape_warning(KEY))
        self.assertIn("约定", idempotency.key_shape_warning("just-a-key"))
        self.assertIn("约定", idempotency.key_shape_warning("a::b"))

    def test_records_for_returns_every_claim_of_one_key(self):
        idempotency.claim(KEY, self.ledger)
        idempotency.claim("other:entity:bucket", self.ledger)
        records = idempotency.records_for(KEY, self.ledger)
        self.assertEqual([record["key"] for record in records], [KEY])
        self.assertEqual(idempotency.records_for("absent:key:bucket", self.ledger), [])


class TtlTests(IdempotencyTestCase):
    def test_claim_inside_the_ttl_window_is_blocked(self):
        self.assertTrue(idempotency.claim(KEY, self.ledger, ttl_seconds=300))
        self.assertFalse(idempotency.claim(KEY, self.ledger, ttl_seconds=300))

    def test_claim_after_the_ttl_expires_is_allowed_again(self):
        start = time.time()
        self.assertTrue(idempotency.claim(KEY, self.ledger, ttl_seconds=60, now=start))
        self.assertFalse(idempotency.claim(KEY, self.ledger, ttl_seconds=60, now=start + 59))
        self.assertTrue(idempotency.claim(KEY, self.ledger, ttl_seconds=60, now=start + 61))
        self.assertEqual(len(read_lines(self.ledger)), 2)
        self.assertFalse(idempotency.claim(KEY, self.ledger, ttl_seconds=60, now=start + 62))

    def test_recorded_ttl_is_persisted_for_later_cleanup(self):
        idempotency.claim(KEY, self.ledger, ttl_seconds=30, now=1000)
        record = json.loads(read_lines(self.ledger)[0])
        self.assertEqual(record["ttl_seconds"], 30)
        self.assertEqual(record["ts"], 1000.0)

    def test_ttl_without_an_expiry_is_rejected(self):
        with self.assertRaises(ValueError):
            idempotency.claim(KEY, self.ledger, ttl_seconds=0)
        with self.assertRaises(ValueError):
            idempotency.claim(KEY, self.ledger, ttl_seconds="300")

    def test_permanent_keys_never_expire(self):
        self.assertTrue(idempotency.claim(KEY, self.ledger, now=1000))
        self.assertFalse(idempotency.claim(KEY, self.ledger, now=1000 + 10**9))


class ConcurrencyTests(IdempotencyTestCase):
    def test_concurrent_claims_of_one_key_produce_exactly_one_winner(self):
        workers = 12
        barrier = threading.Barrier(workers)
        results = []
        guard = threading.Lock()

        def worker():
            barrier.wait()
            outcome = idempotency.claim(KEY, self.ledger)
            with guard:
                results.append(outcome)

        threads = [threading.Thread(target=worker) for _ in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), workers - 1)
        self.assertEqual(len(read_lines(self.ledger)), 1)

    def test_concurrent_appends_keep_every_line_intact(self):
        workers = 16
        barrier = threading.Barrier(workers)
        errors = []

        def worker(index):
            barrier.wait()
            try:
                self.assertTrue(idempotency.claim(f"triage:report-{index}:2026-09-16", self.ledger))
            except Exception as error:  # pragma: no cover - 只在并发缺陷时触发
                errors.append(error)

        threads = [threading.Thread(target=worker, args=(index,)) for index in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        lines = read_lines(self.ledger)
        self.assertEqual(len(lines), workers)
        keys = {json.loads(line)["key"] for line in lines}
        self.assertEqual(keys, {f"triage:report-{index}:2026-09-16" for index in range(workers)})

    def test_separate_processes_agree_on_a_single_winner(self):
        driver = Path(self._temporary.name) / "driver.py"
        driver.write_text(DRIVER, encoding="utf-8")
        processes = [
            subprocess.Popen(
                [sys.executable, str(driver), str(SCRIPT), KEY, str(self.ledger)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for _ in range(6)
        ]
        codes = []
        for process in processes:
            process.communicate(timeout=60)
            codes.append(process.returncode)
        self.assertEqual(codes.count(0), 1)
        self.assertEqual(codes.count(1), 5)
        self.assertEqual(len(read_lines(self.ledger)), 1)


class GcTests(IdempotencyTestCase):
    def test_gc_removes_expired_ttl_records_and_keeps_permanent_ones(self):
        idempotency.claim("publish:daily-report:2026-09-15", self.ledger, ttl_seconds=60, now=1000)
        idempotency.claim("daily-review:inbox:2026-09-16", self.ledger, now=1000)
        idempotency.claim("publish:daily-report:2026-09-16", self.ledger, ttl_seconds=10_000, now=1000)

        report = idempotency.gc(self.ledger, now=2000)

        self.assertEqual(report["removed"], 1)
        self.assertEqual(report["kept"], 2)
        keys = {json.loads(line)["key"] for line in read_lines(self.ledger)}
        self.assertEqual(keys, {"daily-review:inbox:2026-09-16", "publish:daily-report:2026-09-16"})

    def test_gc_drops_unparsable_lines_and_reports_them(self):
        idempotency.claim(KEY, self.ledger)
        with self.ledger.open("a", encoding="utf-8") as stream:
            stream.write("this is not json\n")
        report = idempotency.gc(self.ledger)
        self.assertEqual(report["invalid"], 1)
        self.assertEqual(report["kept"], 1)

    def test_gc_on_a_missing_ledger_is_a_noop(self):
        self.assertEqual(idempotency.gc(self.ledger), {"kept": 0, "removed": 0, "invalid": 0})

    def test_gc_keeps_the_ledger_usable(self):
        idempotency.claim(KEY, self.ledger, ttl_seconds=10, now=1000)
        idempotency.gc(self.ledger, now=5000)
        self.assertTrue(idempotency.claim(KEY, self.ledger, now=5000))
        self.assertFalse(idempotency.claim(KEY, self.ledger, now=5000))

    def test_gc_leaves_no_scratch_file_behind(self):
        idempotency.claim(KEY, self.ledger)
        idempotency.gc(self.ledger)
        leftovers = [item.name for item in self.ledger.parent.iterdir() if item.name.endswith(".gc")]
        self.assertEqual(leftovers, [])


class LedgerResolutionTests(IdempotencyTestCase):
    def test_explicit_path_wins_over_the_environment(self):
        with mock.patch.dict(os.environ, {idempotency.LEDGER_ENV: str(self.ledger)}):
            explicit = self.ledger.parent / "explicit.jsonl"
            self.assertEqual(idempotency.resolve_ledger(explicit), explicit)

    def test_environment_variable_is_used_as_a_fallback(self):
        with mock.patch.dict(os.environ, {idempotency.LEDGER_ENV: str(self.ledger)}):
            self.assertEqual(idempotency.resolve_ledger(None), self.ledger)

    def test_missing_ledger_configuration_is_an_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                idempotency.resolve_ledger(None)


class IdempotencyCliTests(IdempotencyTestCase):
    def run_main(self, arguments):
        stream = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(errors):
            code = idempotency.main(arguments)
        self.stderr = errors.getvalue()
        return code, stream.getvalue()

    def test_claim_exit_codes_chain_with_and_or(self):
        code, output = self.run_main(["--ledger", str(self.ledger), "claim", KEY])
        self.assertEqual(code, idempotency.EXIT_CLAIMED)
        self.assertIn("claimed", output)
        code, output = self.run_main(["--ledger", str(self.ledger), "claim", KEY])
        self.assertEqual(code, idempotency.EXIT_ALREADY_CLAIMED)
        self.assertIn("already-claimed", output)

    def test_claim_json_output(self):
        _, output = self.run_main(["--ledger", str(self.ledger), "claim", KEY, "--json"])
        payload = json.loads(output)
        self.assertTrue(payload["first"])
        self.assertEqual(payload["key"], KEY)

    def test_unstructured_keys_warn_on_stderr_but_still_claim(self):
        code, _ = self.run_main(["--ledger", str(self.ledger), "claim", "shortkey"])
        self.assertEqual(code, idempotency.EXIT_CLAIMED)
        self.assertIn("约定", self.stderr)

    def test_claim_respects_the_ttl_flag(self):
        with mock.patch.object(idempotency.time, "time", return_value=1000.0):
            self.assertEqual(self.run_main(["--ledger", str(self.ledger), "claim", KEY, "--ttl", "60"])[0], 0)
            self.assertEqual(self.run_main(["--ledger", str(self.ledger), "claim", KEY, "--ttl", "60"])[0], 1)
        with mock.patch.object(idempotency.time, "time", return_value=1100.0):
            self.assertEqual(self.run_main(["--ledger", str(self.ledger), "claim", KEY, "--ttl", "60"])[0], 0)

    def test_show_and_gc_commands(self):
        idempotency.claim(KEY, self.ledger, ttl_seconds=10, now=1000)
        code, output = self.run_main(["--ledger", str(self.ledger), "show"])
        self.assertEqual(code, idempotency.EXIT_CLAIMED)
        self.assertIn(KEY, output)
        with mock.patch.object(idempotency.time, "time", return_value=99_999.0):
            code, output = self.run_main(["--ledger", str(self.ledger), "gc"])
        self.assertEqual(code, idempotency.EXIT_CLAIMED)
        self.assertIn("清理 1 条", output)

    def test_missing_ledger_configuration_exits_with_usage_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            code, _ = self.run_main(["claim", KEY])
        self.assertEqual(code, idempotency.EXIT_USAGE)
        self.assertIn("ledger", self.stderr)

    def test_invalid_key_exits_with_usage_error(self):
        code, _ = self.run_main(["--ledger", str(self.ledger), "claim", "bad key"])
        self.assertEqual(code, idempotency.EXIT_USAGE)
        self.assertIn("空白", self.stderr)


if __name__ == "__main__":
    unittest.main()
