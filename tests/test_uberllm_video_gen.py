import importlib.util
from pathlib import Path


SCRIPT_TEST = (
    Path(__file__).resolve().parents[1]
    / "skills/uberllm-video-gen/scripts/test_generate_video.py"
)
SPEC = importlib.util.spec_from_file_location("uberllm_video_gen_tests", SCRIPT_TEST)
uberllm_video_gen_tests = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(uberllm_video_gen_tests)

UberLLMVideoGenTests = uberllm_video_gen_tests.UberLLMVideoGenTests
