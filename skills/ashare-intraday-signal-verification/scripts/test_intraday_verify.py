#!/usr/bin/env python3
"""纯函数冒烟测试：腾讯行情行解析与数字兜底，不联网。"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("intraday_verify.py")
SPEC = importlib.util.spec_from_file_location("intraday_verify", SCRIPT)
intraday = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(intraday)


class IntradayVerifyTests(unittest.TestCase):
    def test_parse_q_picks_the_requested_line(self):
        raw = (
            'v_sz000001="51~示例股A~000001~10.00~9.90~9.95~1000~500~500";\n'
            'v_sz000002="51~示例股F~000002~8.00~7.90~7.95~800~400~400";'
        )
        fields = intraday.parse_q("sz000002", raw)
        self.assertIsNotNone(fields)
        self.assertEqual(fields[1], "示例股F")
        self.assertEqual(fields[2], "000002")

    def test_parse_q_returns_none_for_unknown_code(self):
        self.assertIsNone(intraday.parse_q("sz999999", 'v_sz000001="51~x";'))

    def test_fnum_falls_back_on_bad_values(self):
        self.assertEqual(intraday.fnum(["1.5"], 0), 1.5)
        self.assertEqual(intraday.fnum([], 0), 0.0)
        self.assertEqual(intraday.fnum(["n/a"], 0, default=-1.0), -1.0)


if __name__ == "__main__":
    unittest.main()
