import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/ashare-limitup-openboard-diagnosis/scripts/test_openboard_diag.py"
)
SPEC = importlib.util.spec_from_file_location("test_ashare_openboard_diag", SCRIPT_TEST)
_skill_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(_skill_tests)

OpenboardDiagTests = _skill_tests.OpenboardDiagTests
