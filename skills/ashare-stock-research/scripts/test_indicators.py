#!/usr/bin/env python3
"""纯函数冒烟测试：MA / RSI / MACD，不联网。"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("indicators.py")
SPEC = importlib.util.spec_from_file_location("indicators", SCRIPT)
indicators = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(indicators)


class IndicatorsTests(unittest.TestCase):
    def test_ma_uses_running_window(self):
        self.assertEqual(indicators.ma([1, 2, 3, 4], 2), [1.0, 1.5, 2.5, 3.5])

    def test_ma_handles_short_series(self):
        self.assertEqual(indicators.ma([5], 5), [5.0])

    def test_rsi_is_high_when_every_step_is_a_gain(self):
        values = [float(i) for i in range(1, 31)]
        rsi = indicators.rsi(values)
        self.assertIsNone(rsi[0])
        self.assertGreater(rsi[-1], 99.0)

    def test_rsi_returns_all_none_before_window(self):
        self.assertEqual(indicators.rsi([1, 2, 3], 14), [None, None, None])

    def test_macd_series_align_with_input(self):
        closes = [float(i) for i in range(1, 61)]
        dif, dea, hist = indicators.macd(closes)
        self.assertEqual(len(dif), len(closes))
        self.assertEqual(len(dea), len(closes))
        self.assertEqual(len(hist), len(closes))
        self.assertAlmostEqual(hist[-1], (dif[-1] - dea[-1]) * 2)


if __name__ == "__main__":
    unittest.main()
