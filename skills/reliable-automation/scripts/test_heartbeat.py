"""heartbeat.py 的标准库测试：写入、读取、新鲜度、原子性、目录解析。"""

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("heartbeat.py")
SPEC = importlib.util.spec_from_file_location("reliable_automation_heartbeat", SCRIPT)
heartbeat = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(heartbeat)


class HeartbeatTestCase(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.directory = Path(self._temporary.name)


class HeartbeatWriteReadTests(HeartbeatTestCase):
    def test_write_then_read_round_trip(self):
        target = heartbeat.write_heartbeat("daily-review", self.directory, note="循环第 12 轮")
        self.assertTrue(target.is_file())
        payload = heartbeat.read_heartbeat("daily-review", self.directory)
        self.assertEqual(payload["name"], "daily-review")
        self.assertEqual(payload["note"], "循环第 12 轮")
        self.assertEqual(payload["pid"], os.getpid())
        self.assertAlmostEqual(payload["ts"], time.time(), delta=5)
        self.assertTrue(payload["iso"].endswith("Z"))

    def test_write_is_atomic_and_leaves_no_temporary_files(self):
        for round_number in range(5):
            heartbeat.write_heartbeat("loop", self.directory, extra={"round": round_number})
            leftovers = [item.name for item in self.directory.iterdir() if item.name.startswith(".heartbeat-")]
            self.assertEqual(leftovers, [])
        payload = json.loads((self.directory / "loop.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["round"], 4)

    def test_rewriting_updates_the_timestamp(self):
        heartbeat.write_heartbeat("loop", self.directory, now=time.time() - 900)
        self.assertGreater(heartbeat.heartbeat_age("loop", self.directory), 800)
        heartbeat.write_heartbeat("loop", self.directory)
        self.assertLess(heartbeat.heartbeat_age("loop", self.directory), 5)

    def test_extra_cannot_overwrite_reserved_fields(self):
        target = heartbeat.write_heartbeat("loop", self.directory, extra={"ts": 1, "name": "hacked"})
        payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertNotEqual(payload["name"], "hacked")
        self.assertGreater(payload["ts"], 1_000_000)

    def test_read_failures_return_none_instead_of_raising(self):
        self.assertIsNone(heartbeat.read_heartbeat("never-written", self.directory))
        (self.directory / "broken.json").write_text("{not json", encoding="utf-8")
        self.assertIsNone(heartbeat.read_heartbeat("broken", self.directory))
        (self.directory / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
        self.assertIsNone(heartbeat.read_heartbeat("list", self.directory))

    def test_heartbeat_age_is_none_without_a_numeric_timestamp(self):
        (self.directory / "text.json").write_text(json.dumps({"ts": "yesterday"}), encoding="utf-8")
        self.assertIsNone(heartbeat.heartbeat_age("text", self.directory))

    def test_explicit_paths_are_accepted(self):
        target = self.directory / "custom-name.json"
        target.write_text(json.dumps({"ts": time.time()}), encoding="utf-8")
        self.assertIsNotNone(heartbeat.read_heartbeat(str(target)))


class HeartbeatNamingTests(HeartbeatTestCase):
    def test_names_reject_path_traversal_and_whitespace(self):
        for bad in ("../escape", "a/b", "", "   ", "has space", "x" * 65, None, 7):
            with self.assertRaises(ValueError):
                heartbeat.validate_name(bad)
        self.assertEqual(heartbeat.validate_name(" daily-review "), "daily-review")

    def test_paths_stay_inside_the_state_directory(self):
        path = heartbeat.heartbeat_path("inbox-triage", self.directory)
        self.assertEqual(path.parent, self.directory)
        self.assertEqual(path.name, "inbox-triage.json")

    def test_directory_resolution_prefers_override_then_environment(self):
        with mock.patch.dict(os.environ, {heartbeat.DIRECTORY_ENV: str(self.directory / "env")}):
            self.assertEqual(heartbeat.state_dir(), self.directory / "env")
            self.assertEqual(heartbeat.state_dir(self.directory / "flag"), self.directory / "flag")
        with mock.patch.dict(os.environ, {heartbeat.DIRECTORY_ENV: str(self.directory / "xdg")}):
            self.assertEqual(heartbeat.state_dir(), self.directory / "xdg")

    def test_directory_falls_back_to_the_xdg_state_home(self):
        environment = {"XDG_STATE_HOME": str(self.directory / "state")}
        with mock.patch.dict(os.environ, environment, clear=False):
            os.environ.pop(heartbeat.DIRECTORY_ENV, None)
            self.assertEqual(heartbeat.state_dir(), self.directory / "state" / "heartbeats")

    def test_directory_expands_tilde(self):
        resolved = heartbeat.state_dir("~/reliable-automation-heartbeats")
        self.assertTrue(resolved.is_absolute())
        self.assertTrue(str(resolved).startswith(str(Path.home())))


class HeartbeatInspectTests(HeartbeatTestCase):
    def test_fresh_heartbeat_is_ok(self):
        heartbeat.write_heartbeat("inbox-triage", self.directory)
        report = heartbeat.inspect("inbox-triage", self.directory, 60)
        self.assertEqual(report["status"], heartbeat.STATUS_OK)
        self.assertLess(report["age_seconds"], 5)

    def test_old_heartbeat_is_stale(self):
        heartbeat.write_heartbeat("inbox-triage", self.directory, now=time.time() - 1200)
        report = heartbeat.inspect("inbox-triage", self.directory, 420)
        self.assertEqual(report["status"], heartbeat.STATUS_STALE)
        self.assertGreater(report["age_seconds"], 1100)

    def test_missing_heartbeat_is_missing_not_stale(self):
        report = heartbeat.inspect("never-written", self.directory, 60)
        self.assertEqual(report["status"], heartbeat.STATUS_MISSING)
        self.assertIsNone(report["age_seconds"])

    def test_inspect_without_a_limit_only_reports_presence(self):
        heartbeat.write_heartbeat("inbox-triage", self.directory, now=time.time() - 10_000)
        self.assertEqual(heartbeat.inspect("inbox-triage", self.directory)["status"], heartbeat.STATUS_OK)


class HeartbeatCliTests(HeartbeatTestCase):
    def run_main(self, arguments):
        stream = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(errors):
            code = heartbeat.main(arguments)
        self.stderr = errors.getvalue()
        return code, stream.getvalue()

    def test_beat_writes_and_check_reads_back(self):
        code, output = self.run_main(["--dir", str(self.directory), "beat", "daily-review"])
        self.assertEqual(code, heartbeat.EXIT_OK)
        self.assertIn("心跳已写入", output)
        code, output = self.run_main(
            ["--dir", str(self.directory), "check", "daily-review", "--max-age", "420"]
        )
        self.assertEqual(code, heartbeat.EXIT_OK)
        self.assertIn("ok", output)

    def test_check_returns_one_for_stale_and_missing(self):
        heartbeat.write_heartbeat("stale-one", self.directory, now=time.time() - 3600)
        code, _ = self.run_main(["--dir", str(self.directory), "check", "stale-one", "--max-age", "60"])
        self.assertEqual(code, heartbeat.EXIT_STALE)
        code, _ = self.run_main(["--dir", str(self.directory), "check", "absent", "--max-age", "60"])
        self.assertEqual(code, heartbeat.EXIT_STALE)

    def test_check_json_output_is_machine_readable(self):
        heartbeat.write_heartbeat("inbox-triage", self.directory)
        _, output = self.run_main(
            ["--dir", str(self.directory), "check", "inbox-triage", "--max-age", "60", "--json"]
        )
        payload = json.loads(output)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["max_age_seconds"], 60.0)

    def test_path_and_list_commands(self):
        _, output = self.run_main(["--dir", str(self.directory), "path", "inbox-triage"])
        self.assertEqual(output.strip(), str(self.directory / "inbox-triage.json"))
        heartbeat.write_heartbeat("a-task", self.directory)
        heartbeat.write_heartbeat("b-task", self.directory)
        _, output = self.run_main(["--dir", str(self.directory), "list"])
        self.assertIn("a-task", output)
        self.assertIn("b-task", output)

    def test_list_on_a_missing_directory_is_empty_not_an_error(self):
        code, output = self.run_main(["--dir", str(self.directory / "absent"), "list"])
        self.assertEqual(code, heartbeat.EXIT_OK)
        self.assertIn("0 个心跳", output)

    def test_invalid_names_exit_with_usage_error(self):
        code, _ = self.run_main(["--dir", str(self.directory), "beat", "../escape"])
        self.assertEqual(code, heartbeat.EXIT_USAGE)
        self.assertIn("不合法", self.stderr)

    def test_cli_uses_the_environment_directory(self):
        with mock.patch.dict(os.environ, {heartbeat.DIRECTORY_ENV: str(self.directory)}):
            code, _ = self.run_main(["beat", "env-task"])
        self.assertEqual(code, heartbeat.EXIT_OK)
        self.assertTrue((self.directory / "env-task.json").is_file())


if __name__ == "__main__":
    unittest.main()
