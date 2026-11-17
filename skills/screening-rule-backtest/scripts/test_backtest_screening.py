#!/usr/bin/env python3
"""纯函数冒烟测试：板块涨跌停幅度与统计口径，不联网。"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("backtest_screening.py")
SPEC = importlib.util.spec_from_file_location("backtest_screening", SCRIPT)
backtest = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(backtest)


class BacktestScreeningTests(unittest.TestCase):
    def test_is_gem_covers_star_and_chinext(self):
        self.assertTrue(backtest.is_gem("300001"))
        self.assertTrue(backtest.is_gem("301001"))
        self.assertTrue(backtest.is_gem("688001"))
        self.assertFalse(backtest.is_gem("600000"))

    def test_limit_pct_matches_board(self):
        self.assertEqual(backtest.limit_pct("300001"), 19.5)
        self.assertEqual(backtest.limit_pct("600000"), 9.5)

    def test_stat_returns_win_rate_mean_and_sample(self):
        rows = [{"x": 1.0}, {"x": -1.0}, {"x": 3.0}, {"x": None}]
        win_rate, mean, sample = backtest.stat(rows, "x")
        self.assertAlmostEqual(win_rate, 200 / 3)
        self.assertAlmostEqual(mean, 1.0)
        self.assertEqual(sample, 3)

    def test_stat_on_empty_sample(self):
        self.assertEqual(backtest.stat([], "x"), (0.0, 0.0, 0))


if __name__ == "__main__":
    unittest.main()
