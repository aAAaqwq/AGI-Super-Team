import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/muapi-video-gen/scripts/test_generate_video.py"
)
SPEC = importlib.util.spec_from_file_location("muapi_video_gen_tests", SCRIPT_TEST)
muapi_video_gen_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(muapi_video_gen_tests)

MuapiVideoGenTests = muapi_video_gen_tests.MuapiVideoGenTests
