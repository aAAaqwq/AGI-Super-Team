from pathlib import Path
import importlib.util
import unittest


SCRIPT = Path(__file__).resolve().parent / "check_x_length.py"
SPEC = importlib.util.spec_from_file_location("check_x_length", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class XLengthTests(unittest.TestCase):
    def test_ascii_and_chinese_weighting(self):
        self.assertEqual(MODULE.weighted_length("ab中"), 4)

    def test_url_uses_conservative_fixed_weight(self):
        self.assertEqual(MODULE.weighted_length("看 https://example.com/a"), 26)

    def test_multiple_urls_keep_surrounding_text(self):
        text = "a https://a.example b https://b.example 中"
        self.assertEqual(MODULE.weighted_length(text), 54)


if __name__ == "__main__":
    unittest.main()
