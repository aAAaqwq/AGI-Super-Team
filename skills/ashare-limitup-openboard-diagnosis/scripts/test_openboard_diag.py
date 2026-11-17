#!/usr/bin/env python3
"""纯函数冒烟测试：涨停分时时间格式化，不联网。"""

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("openboard_diag.py")
SPEC = importlib.util.spec_from_file_location("openboard_diag", SCRIPT)
diag = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(diag)


class OpenboardDiagTests(unittest.TestCase):
    def test_fmt_t_formats_hhmmss_digits(self):
        self.assertEqual(diag.fmt_t("92500"), "09:25:00")
        self.assertEqual(diag.fmt_t(93000), "09:30:00")
        self.assertEqual(diag.fmt_t("145959"), "14:59:59")

    def test_fmt_t_rejects_non_numeric(self):
        self.assertEqual(diag.fmt_t("abc"), "-")
        self.assertEqual(diag.fmt_t(""), "-")


if __name__ == "__main__":
    unittest.main()
