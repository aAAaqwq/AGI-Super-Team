import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("generate_video.py")
SPEC = importlib.util.spec_from_file_location("muapi_video_gen", SCRIPT)
muapi_video_gen = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(muapi_video_gen)


class FakeResponse:
    def __init__(self, payload=None, content=b"", url="https://cdn.example/video.mp4"):
        self.payload = payload
        self.content = content or json.dumps(payload).encode("utf-8")
        self.url = url

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit=-1):
        return self.content

    def geturl(self):
        return self.url


def make_args(**overrides):
    values = {
        "prompt": "A lighthouse at sunrise",
        "ratio": "16:9",
        "duration": 8,
        "resolution": "720p",
        "generate_audio": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class MuapiVideoGenTests(unittest.TestCase):
    def test_payload_matches_muapi_schema(self):
        self.assertEqual(
            muapi_video_gen.build_payload(make_args()),
            {
                "prompt": "A lighthouse at sunrise",
                "aspect_ratio": "16:9",
                "resolution": "720p",
                "duration": 8,
                "generate_audio": True,
            },
        )

    def test_payload_rejects_values_outside_schema(self):
        with self.assertRaisesRegex(muapi_video_gen.MuapiVideoError, "duration"):
            muapi_video_gen.build_payload(make_args(duration=21))
        with self.assertRaisesRegex(muapi_video_gen.MuapiVideoError, "aspect ratio"):
            muapi_video_gen.build_payload(make_args(ratio="5:4"))
        with self.assertRaisesRegex(muapi_video_gen.MuapiVideoError, "empty"):
            muapi_video_gen.build_payload(make_args(prompt="  "))

    @mock.patch.object(muapi_video_gen.urllib.request, "urlopen")
    def test_submission_posts_once_and_uses_x_api_key(self, urlopen):
        urlopen.return_value = FakeResponse(payload={"request_id": "request-123"})

        prediction_id = muapi_video_gen.submit_prediction(
            "secret", {"prompt": "test", "duration": 5}
        )

        self.assertEqual(prediction_id, "request-123")
        self.assertEqual(urlopen.call_count, 1)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, "https://api.muapi.ai/api/v1/flux-3-text-to-video")
        self.assertNotIn("secret", request.data.decode("utf-8"))
        self.assertIn("secret", dict(request.header_items()).get("X-api-key", ""))

    @mock.patch.object(muapi_video_gen, "_request_json")
    def test_polling_accepts_wrapped_and_flat_completed_response(self, request_json):
        request_json.side_effect = [
            {"data": {"status": "processing"}},
            {"status": "completed", "outputs": ["https://cdn.example/video.mp4"]},
        ]
        ticks = iter([0.0, 0.0, 1.0])

        outputs = muapi_video_gen.poll_prediction(
            "secret",
            "request-123",
            poll_interval=1,
            timeout=10,
            sleep=lambda _seconds: None,
            clock=lambda: next(ticks),
        )

        self.assertEqual(outputs, ["https://cdn.example/video.mp4"])
        self.assertEqual(request_json.call_count, 2)
        self.assertTrue(
            all(call.kwargs["attempts"] == 3 for call in request_json.call_args_list)
        )

    @mock.patch.object(muapi_video_gen, "_request_json")
    def test_polling_reports_terminal_failure(self, request_json):
        request_json.return_value = {"status": "failed", "message": "bad prompt"}

        with self.assertRaisesRegex(muapi_video_gen.MuapiVideoError, "bad prompt"):
            muapi_video_gen.poll_prediction(
                "secret",
                "request-123",
                poll_interval=1,
                timeout=10,
                sleep=lambda _seconds: None,
                clock=lambda: 0.0,
            )

    @mock.patch.object(muapi_video_gen.urllib.request, "urlopen")
    def test_preview_does_not_read_credentials_or_use_network(self, urlopen):
        with mock.patch.dict(muapi_video_gen.os.environ, {}, clear=True):
            exit_code = muapi_video_gen.main(
                ["A lighthouse at sunrise", "--output", "preview.mp4"]
            )

        self.assertEqual(exit_code, 2)
        urlopen.assert_not_called()

    def test_download_rejects_non_https_output(self):
        with self.assertRaisesRegex(muapi_video_gen.MuapiVideoError, "HTTPS"):
            muapi_video_gen.download_video(
                "http://cdn.example/video.mp4", Path("video.mp4")
            )

    @mock.patch.object(muapi_video_gen.urllib.request, "urlopen")
    def test_download_writes_video_after_validating_redirect(self, urlopen):
        urlopen.return_value = FakeResponse(content=b"mp4-bytes")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "video.mp4"
            muapi_video_gen.download_video("https://cdn.example/video.mp4", output)
            self.assertEqual(output.read_bytes(), b"mp4-bytes")

    def test_error_redacts_api_key(self):
        error = muapi_video_gen.urllib.error.HTTPError(
            "https://api.muapi.ai/api/v1/flux-3-text-to-video",
            401,
            "unauthorized",
            {},
            None,
        )
        error.fp = FakeResponse(content=b"secret token")
        with mock.patch.object(muapi_video_gen.urllib.request, "urlopen", side_effect=error):
            with self.assertRaises(muapi_video_gen.MuapiVideoError) as raised:
                muapi_video_gen.submit_prediction("secret", {"prompt": "test"})
        self.assertNotIn("secret", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
