import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/ashare-stock-research/scripts/test_indicators.py"
)
SPEC = importlib.util.spec_from_file_location("test_ashare_stock_research", SCRIPT_TEST)
_skill_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(_skill_tests)

IndicatorsTests = _skill_tests.IndicatorsTests
