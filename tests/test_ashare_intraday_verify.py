import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/ashare-intraday-signal-verification/scripts/test_intraday_verify.py"
)
SPEC = importlib.util.spec_from_file_location("test_ashare_intraday_verify", SCRIPT_TEST)
_skill_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(_skill_tests)

IntradayVerifyTests = _skill_tests.IntradayVerifyTests
