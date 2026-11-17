import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/screening-rule-backtest/scripts/test_backtest_screening.py"
)
SPEC = importlib.util.spec_from_file_location("test_screening_rule_backtest", SCRIPT_TEST)
_skill_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(_skill_tests)

BacktestScreeningTests = _skill_tests.BacktestScreeningTests
