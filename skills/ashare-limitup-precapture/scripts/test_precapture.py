#!/usr/bin/env python3
"""冒烟测试：四个扫描/回测脚本可导入，统计函数不崩，不联网。"""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent
MODULES = ("flow_streak_backtest", "golden_triple", "golden_triple_scan", "limitup_scan")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class PrecaptureTests(unittest.TestCase):
    def test_all_scripts_import(self):
        for name in MODULES:
            self.assertIsNotNone(_load(name))

    def test_stat_summarises_forward_returns(self):
        flow = _load("flow_streak_backtest")
        records = [
            {"f1": 1.0, "f3": 2.0, "f5": 3.0},
            {"f1": -1.0, "f3": 0.0, "f5": 1.0},
        ] * 5
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            flow.stat("demo", records)
        output = buffer.getvalue()
        self.assertIn("demo", output)
        self.assertIn("10", output)

    def test_stat_handles_small_sample(self):
        flow = _load("flow_streak_backtest")
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            flow.stat("tiny", [{"f1": 1.0, "f3": 1.0, "f5": 1.0}])
        self.assertIn("太少", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
