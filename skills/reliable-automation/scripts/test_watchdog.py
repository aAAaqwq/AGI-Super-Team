"""watchdog.py 的标准库测试：健康/过期/缺失/配置错误/坏 JSON。"""

import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("watchdog.py")
SPEC = importlib.util.spec_from_file_location("reliable_automation_watchdog", SCRIPT)
watchdog = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(watchdog)


class FakeCompleted:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def evaluate(entry, now, runner=None):
    return watchdog.evaluate_task(entry, 0, now, runner)


class WatchdogTestCase(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary.cleanup)
        self.root = Path(self._temporary.name)
        self.now = 1_800_000_000.0

    def make_file(self, name, text="{}", age_seconds=0.0, touch=True, base=None):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        if touch:
            stamp = (self.now if base is None else base) - age_seconds
            os.utime(path, (stamp, stamp))
        return path

    def artifact(self, path, max_age_seconds=60.0, **overrides):
        entry = {
            "name": "task",
            "kind": "artifact",
            "path": str(path),
            "max_age_seconds": max_age_seconds,
        }
        entry.update(overrides)
        return entry


class WatchdogArtifactTests(WatchdogTestCase):
    def test_fresh_artifact_is_healthy(self):
        path = self.make_file("ofi.json", age_seconds=3)
        result = evaluate(self.artifact(path), self.now)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["age_seconds"], 3.0, places=3)
        self.assertIn("3s", result["detail"])

    def test_artifact_older_than_limit_is_stale(self):
        path = self.make_file("ofi.json", age_seconds=600)
        result = evaluate(self.artifact(path, max_age_seconds=60), self.now)
        self.assertEqual(result["status"], "stale")
        self.assertIn("10.0m", result["detail"])

    def test_missing_artifact_is_config_error_not_stale(self):
        result = evaluate(self.artifact(self.root / "absent.json"), self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertNotIn(result["status"], watchdog.ANOMALY_STATUSES[0:1])
        self.assertIn("配置错误", result["detail"])

    def test_on_missing_can_opt_into_stale(self):
        entry = self.artifact(self.root / "absent.json", on_missing="stale")
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "stale")

    def test_on_missing_rejects_unknown_value(self):
        entry = self.artifact(self.make_file("x.json"), on_missing="ignore")
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertIn("on_missing", result["detail"])

    def test_artifact_below_min_bytes_is_empty(self):
        path = self.make_file("paper.log", text="")
        entry = self.artifact(path, max_age_seconds=600, min_bytes=10)
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "empty")
        self.assertIn("0 字节", result["detail"])

    def test_artifact_rejects_bad_max_age(self):
        entry = self.artifact(self.make_file("x.json"), max_age_seconds="soon")
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertIn("max_age_seconds", result["detail"])

    def test_artifact_requires_path(self):
        entry = {"name": "task", "kind": "artifact", "max_age_seconds": 10}
        self.assertEqual(evaluate(entry, self.now)["status"], "config-error")

    def test_directory_target_is_a_config_error(self):
        entry = self.artifact(self.root)
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertIn("目录", result["detail"])

    def test_min_bytes_must_be_non_negative(self):
        path = self.make_file("x.json", text="ok")
        self.assertEqual(evaluate(self.artifact(path, min_bytes=0), self.now)["status"], "ok")
        self.assertEqual(evaluate(self.artifact(path, min_bytes=-1), self.now)["status"], "config-error")


class WatchdogHeartbeatTests(WatchdogTestCase):
    def heartbeat(self, payload, max_age_seconds=420.0, **overrides):
        path = self.make_file("beat.json", text=json.dumps(payload), touch=False)
        entry = {
            "name": "daily-review",
            "kind": "heartbeat",
            "path": str(path),
            "max_age_seconds": max_age_seconds,
        }
        entry.update(overrides)
        return entry

    def test_fresh_heartbeat_is_healthy(self):
        entry = self.heartbeat({"ts": self.now - 30})
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["age_seconds"], 30.0, places=3)

    def test_stale_heartbeat_is_stale(self):
        entry = self.heartbeat({"ts": self.now - 900})
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "stale")
        self.assertIn("超过上限", result["detail"])

    def test_heartbeat_accepts_epoch_milliseconds_and_iso_text(self):
        milliseconds = evaluate(self.heartbeat({"ts": (self.now - 5) * 1000}), self.now)
        self.assertEqual(milliseconds["status"], "ok")
        self.assertAlmostEqual(milliseconds["age_seconds"], 5.0, places=2)
        iso_text = evaluate(self.heartbeat({"ts": "2027-01-15T08:00:00Z"}), self.now)
        self.assertEqual(iso_text["status"], "ok")

    def test_heartbeat_honours_custom_ts_field(self):
        entry = self.heartbeat({"updated_ms": (self.now - 4) * 1000}, ts_field="updated_ms")
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "ok")
        self.assertAlmostEqual(result["age_seconds"], 4.0, places=2)
        self.assertEqual(result["heartbeat_at"], watchdog._iso(self.now - 4))

    def test_broken_json_heartbeat_is_config_error(self):
        entry = self.heartbeat({"ts": self.now})
        Path(entry["path"]).write_text("not json at all", encoding="utf-8")
        result = evaluate(entry, self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertIn("JSON", result["detail"])

    def test_heartbeat_without_parsable_timestamp_is_config_error(self):
        result = evaluate(self.heartbeat({"ts": "yesterday"}), self.now)
        self.assertEqual(result["status"], "config-error")
        self.assertIn("时间戳", result["detail"])

    def test_heartbeat_missing_file_is_config_error(self):
        entry = {
            "name": "daily-review",
            "kind": "heartbeat",
            "path": str(self.root / "never-written.json"),
            "max_age_seconds": 60,
        }
        self.assertEqual(evaluate(entry, self.now)["status"], "config-error")


class WatchdogCommandTests(WatchdogTestCase):
    def command(self, value, **overrides):
        entry = {"name": "probe", "kind": "command", "command": value}
        entry.update(overrides)
        return entry

    def test_command_success_and_failure_by_exit_code(self):
        ok = evaluate(self.command("true"), self.now, runner=lambda *a, **k: FakeCompleted(0))
        self.assertEqual(ok["status"], "ok")
        failed = evaluate(
            self.command("boom"), self.now, runner=lambda *a, **k: FakeCompleted(3, stderr="kaboom\n")
        )
        self.assertEqual(failed["status"], "failed")
        self.assertIn("退出码 3", failed["detail"])
        self.assertIn("kaboom", failed["detail"])

    def test_command_accepts_argv_list(self):
        seen = {}

        def runner(argv, **kwargs):
            seen["argv"] = argv
            seen["shell"] = kwargs.get("shell")
            return FakeCompleted(0)

        entry = self.command(["/bin/sh", "-c", "exit 0"])
        self.assertEqual(evaluate(entry, self.now, runner=runner)["status"], "ok")
        self.assertEqual(seen["argv"], ["/bin/sh", "-c", "exit 0"])
        self.assertFalse(seen["shell"])
        self.assertEqual(entry["name"], "probe")

    def test_command_timeout_is_failure(self):
        def runner(argv, **kwargs):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs.get("timeout", 1))

        result = evaluate(self.command("sleep 99", timeout_seconds=5), self.now, runner=runner)
        self.assertEqual(result["status"], "failed")
        self.assertIn("没有结束", result["detail"])

    def test_command_rejects_empty_definition(self):
        self.assertEqual(evaluate(self.command("   "), self.now)["status"], "config-error")
        self.assertEqual(evaluate(self.command([]), self.now)["status"], "config-error")

    def test_real_command_runs_through_subprocess(self):
        result = evaluate(self.command("/bin/sh -c 'exit 0'"), self.now)
        self.assertEqual(result["status"], "ok")


class WatchdogRegistryTests(WatchdogTestCase):
    def test_unknown_kind_and_non_object_entries_are_config_errors(self):
        self.assertEqual(evaluate({"name": "x", "kind": "cron"}, self.now)["status"], "config-error")
        self.assertEqual(evaluate("not-an-object", 7, self.now)["status"], "config-error")

    def test_tilde_paths_expand_to_the_user_home(self):
        result = evaluate(self.artifact("~/definitely-missing-artifact.json"), self.now)
        self.assertTrue(result["target"].startswith(str(Path.home())))
        self.assertNotIn("~", result["target"])

    def test_load_registry_reports_read_and_parse_failures(self):
        entries, error = watchdog.load_registry(self.root / "absent.json")
        self.assertEqual(entries, [])
        self.assertIn("不可读", error)
        broken = self.make_file("registry.json", text="{oops")
        entries, error = watchdog.load_registry(broken)
        self.assertEqual(entries, [])
        self.assertIn("不是合法 JSON", error)
        no_tasks = self.make_file("empty.json", text='{"task": []}')
        entries, error = watchdog.load_registry(no_tasks)
        self.assertIn("tasks", error)

    def test_parse_timestamp_handles_seconds_milliseconds_and_garbage(self):
        self.assertEqual(watchdog.parse_timestamp(100), 100.0)
        self.assertEqual(watchdog.parse_timestamp(1_800_000_000_250), 1_800_000_000.25)
        self.assertEqual(watchdog.parse_timestamp("1970-01-01T00:01:40Z"), 100.0)
        self.assertEqual(watchdog.parse_timestamp(True), None)
        self.assertEqual(watchdog.parse_timestamp(float("nan")), None)
        self.assertEqual(watchdog.parse_timestamp("tomorrow"), None)
        self.assertEqual(watchdog.parse_timestamp(None), None)


class WatchdogCliTests(WatchdogTestCase):
    """CLI 走真实时钟，所以这里造文件时以 time.time() 为基准。"""

    def make_aged_file(self, name, age_seconds):
        return self.make_file(name, age_seconds=age_seconds, base=time.time())

    def run_main(self, arguments):
        stream = io.StringIO()
        errors = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(errors):
            code = watchdog.main(arguments)
        self.stderr = errors.getvalue()
        return code, stream.getvalue()

    def registry_file(self, tasks):
        path = self.root / "registry.json"
        path.write_text(json.dumps({"tasks": tasks}, ensure_ascii=False), encoding="utf-8")
        return path

    def test_healthy_registry_exits_zero(self):
        path = self.make_aged_file("ofi.json", age_seconds=1)
        registry = self.registry_file([self.artifact(path, name="inbox-triage")])
        code, output = self.run_main(["--registry", str(registry)])
        self.assertEqual(code, watchdog.EXIT_HEALTHY)
        self.assertIn("inbox-triage", output)
        self.assertIn("异常 0 项", output)

    def test_anomaly_exits_one_and_json_reports_every_status(self):
        fresh = self.make_aged_file("fresh.json", age_seconds=1)
        stale = self.make_aged_file("stale.json", age_seconds=600)
        registry = self.registry_file(
            [
                self.artifact(fresh),
                self.artifact(stale, max_age_seconds=60),
                self.artifact(self.root / "gone.json"),
            ]
        )
        code, output = self.run_main(["--registry", str(registry), "--json"])
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        payload = json.loads(output)
        self.assertEqual(payload["schemaVersion"], watchdog.SCHEMA_VERSION)
        self.assertEqual(payload["summary"]["anomalies"], 2)
        statuses = [result["status"] for result in payload["results"]]
        self.assertEqual(statuses, ["ok", "stale", "config-error"])

    def test_missing_registry_exits_one_without_traceback(self):
        code, _ = self.run_main(["--registry", str(self.root / "absent.json")])
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        self.assertIn("注册表不可读", self.stderr)

    def test_alert_without_placeholder_warns_but_still_delivers_on_stdin(self):
        stale = self.make_aged_file("stale.json", age_seconds=600)
        registry = self.registry_file([self.artifact(stale, max_age_seconds=60)])
        received = self.root / "no-placeholder.txt"
        code, _ = self.run_main(["--registry", str(registry), "--alert-cmd", f"cat >> {received}"])
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        self.assertIn("{msg}", self.stderr)
        self.assertIn("[watchdog] 1 项异常", received.read_text(encoding="utf-8"))

    def test_alert_command_receives_message_with_placeholder_and_stdin(self):
        stale = self.make_aged_file("stale.json", age_seconds=600)
        registry = self.registry_file([self.artifact(stale, max_age_seconds=60)])
        received = self.root / "alert.txt"
        code, output = self.run_main(
            [
                "--registry",
                str(registry),
                "--alert-cmd",
                f"cat >> {received}",
            ]
        )
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        message = received.read_text(encoding="utf-8")
        self.assertIn("[watchdog] 1 项异常", message)
        self.assertIn("stale", message)
        self.assertIn("告警命令已执行", output)

    def test_alert_placeholder_is_substituted_into_argv(self):
        stale = self.make_aged_file("stale.json", age_seconds=600)
        registry = self.registry_file([self.artifact(stale, max_age_seconds=60)])
        received = self.root / "placeholder.txt"
        code, _ = self.run_main(
            ["--registry", str(registry), "--alert-cmd", f"printf '%s' '{{msg}}' > {received}"]
        )
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        self.assertIn("[watchdog] 1 项异常", received.read_text(encoding="utf-8"))

    def test_healthy_registry_never_runs_the_alert_command(self):
        path = self.make_aged_file("ofi.json", age_seconds=1)
        registry = self.registry_file([self.artifact(path)])
        received = self.root / "should-not-exist.txt"
        code, _ = self.run_main(["--registry", str(registry), "--alert-cmd", f"touch {received}"])
        self.assertEqual(code, watchdog.EXIT_HEALTHY)
        self.assertFalse(received.exists())

    def test_failing_alert_command_keeps_the_run_anomalous(self):
        stale = self.make_aged_file("stale.json", age_seconds=600)
        registry = self.registry_file([self.artifact(stale, max_age_seconds=60)])
        code, output = self.run_main(
            ["--registry", str(registry), "--alert-cmd", "/bin/sh -c 'exit 7'"]
        )
        self.assertEqual(code, watchdog.EXIT_ANOMALY)
        self.assertIn("告警失败", output)

    def test_summary_counts_every_status_bucket(self):
        results = [
            {"status": "ok"},
            {"status": "ok"},
            {"status": "stale"},
            {"status": "config-error"},
        ]
        summary = watchdog.summarize(results)
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["anomalies"], 2)
        self.assertEqual(summary["counts"]["healthy"], 2)
        self.assertEqual(summary["counts"]["config-error"], 1)

    def test_table_width_handles_cjk_text(self):
        self.assertEqual(watchdog._display_width("abc"), 3)
        self.assertEqual(watchdog._display_width("心跳"), 4)
        self.assertTrue(watchdog._truncate("心跳" * 40, 10).endswith("…"))
        self.assertEqual(watchdog._truncate("short", 10), "short")


if __name__ == "__main__":
    unittest.main()
