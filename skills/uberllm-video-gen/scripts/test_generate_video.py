import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("generate_video.py")
SPEC = importlib.util.spec_from_file_location("uberllm_video_gen", SCRIPT)
uberllm_video_gen = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(uberllm_video_gen)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload
        return json.dumps(self.payload).encode("utf-8")


def _args(**overrides):
    values = dict(
        prompt="A lighthouse at sunrise",
        model="fal-ai/veo3.1/lite",
        ratio="16:9",
        duration=4,
        resolution="720p",
        max_cost=None,
    )
    values.update(overrides)
    return argparse.Namespace(**values)


class UberLLMVideoGenTests(unittest.TestCase):
    def test_payload_uses_uberllm_video_fields(self):
        self.assertEqual(
            uberllm_video_gen.build_payload(_args(max_cost=0.2)),
            {
                "model": "fal-ai/veo3.1/lite",
                "prompt": "A lighthouse at sunrise",
                "aspect_ratio": "16:9",
                "duration_seconds": 4,
                "resolution": "720p",
                "max_cost": 0.2,
            },
        )

    @mock.patch.object(uberllm_video_gen.urllib.request, "urlopen")
    def test_submission_posts_once_with_idempotency_key(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"id": "job-123", "object": "media.job", "status": "queued"}
        )

        job_id = uberllm_video_gen.submit_job(
            "secret", {"model": uberllm_video_gen.DEFAULT_MODEL, "prompt": "test"}
        )

        self.assertEqual(job_id, "job-123")
        self.assertEqual(urlopen.call_count, 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://api.uberllm.dev/v1/video/generations")
        self.assertTrue(request.get_header("Idempotency-key"))
        self.assertNotIn("secret", request.data.decode("utf-8"))

    @mock.patch.object(uberllm_video_gen.urllib.request, "urlopen")
    def test_quote_sends_validate_flag(self, urlopen):
        urlopen.return_value = FakeResponse({"object": "quote", "valid": True, "cost_usd": 0.1})

        quote = uberllm_video_gen.quote_job("secret", {"model": "m", "prompt": "p"})

        self.assertEqual(quote["cost_usd"], 0.1)
        body = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertIs(body["validate"], True)

    @mock.patch.object(uberllm_video_gen, "_request_json")
    def test_polling_waits_until_succeeded(self, request_json):
        request_json.side_effect = [
            {"id": "job-123", "status": "queued"},
            {"id": "job-123", "status": "running"},
            {
                "id": "job-123",
                "status": "succeeded",
                "results": [{"url": "https://api.uberllm.dev/v1/media/artifacts/job-123/0"}],
            },
        ]
        ticks = iter([0.0, 0.0, 1.0, 2.0])

        job = uberllm_video_gen.poll_job(
            "secret",
            "job-123",
            poll_interval=1,
            timeout=10,
            sleep=lambda _seconds: None,
            clock=lambda: next(ticks),
        )

        self.assertEqual(job["status"], "succeeded")
        self.assertEqual(request_json.call_count, 3)
        self.assertTrue(all(call.kwargs["attempts"] == 3 for call in request_json.call_args_list))

    @mock.patch.object(uberllm_video_gen, "_request_json")
    def test_failed_job_reports_reason(self, request_json):
        request_json.return_value = {
            "id": "job-123",
            "status": "failed",
            "error": {"message": "prompt refused", "retryable": False},
        }
        with self.assertRaisesRegex(uberllm_video_gen.UberLLMVideoError, "prompt refused"):
            uberllm_video_gen.poll_job("secret", "job-123", poll_interval=1, timeout=10)

    @mock.patch.object(uberllm_video_gen.urllib.request, "urlopen")
    def test_download_sends_key_only_to_uberllm(self, urlopen):
        urlopen.return_value = FakeResponse(b"\x00\x00\x00\x18ftypmp42")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "out.mp4"
            uberllm_video_gen.download_video(
                "https://api.uberllm.dev/v1/media/artifacts/job-123/0", target, "secret"
            )
            self.assertEqual(
                urlopen.call_args.args[0].get_header("Authorization"), "Bearer secret"
            )
            uberllm_video_gen.download_video("https://cdn.example.com/v.mp4", target, "secret")
            self.assertIsNone(urlopen.call_args.args[0].get_header("Authorization"))

    def test_preview_does_not_read_credentials_or_use_network(self):
        with mock.patch.dict(uberllm_video_gen.os.environ, {}, clear=True), mock.patch.object(
            uberllm_video_gen.urllib.request, "urlopen"
        ) as urlopen:
            exit_code = uberllm_video_gen.main(
                ["A lighthouse at sunrise", "--output", "preview.mp4"]
            )

        self.assertEqual(exit_code, 2)
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
