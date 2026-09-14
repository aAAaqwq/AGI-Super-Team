---
name: muapi-video-gen
description: Generate one MuAPI FLUX 3 text-to-video clip when a local MP4 is needed, with explicit paid-request confirmation and bounded polling.
---

# MuAPI Video Generation

Generate one text-to-video clip through MuAPI's `flux-3-text-to-video`
endpoint. This is an opt-in workflow: it previews the request first and keeps
the billable submission separate from status polling and output download.

## Prerequisites

- Python 3.10 or newer; the helper uses only the standard library.
- A MuAPI API key in `MUAPI_API_KEY`.
- Outbound HTTPS access to `api.muapi.ai` and the returned output URL.

Set the key in the environment. Never put it in a prompt, command argument,
source file, or log.

```bash
export MUAPI_API_KEY="..."
```

## Safety Boundary

Video generation may incur charges. The helper prints the exact request plan
and exits without network access unless `--yes` is present.

The generation `POST` is sent exactly once and is never retried. Only
prediction and output `GET` requests use bounded retries for transient
failures. If the submission result is unclear, stop and inspect the MuAPI
dashboard instead of running the command again.

## Usage

Preview the request first:

```bash
python skills/muapi-video-gen/scripts/generate_video.py \
  "A slow aerial orbit around a lighthouse at sunrise" \
  --output lighthouse.mp4
```

After reviewing the plan, confirm one paid submission:

```bash
python skills/muapi-video-gen/scripts/generate_video.py \
  "A slow aerial orbit around a lighthouse at sunrise" \
  --output lighthouse.mp4 \
  --duration 8 \
  --ratio 16:9 \
  --resolution 720p \
  --generate-audio \
  --yes
```

Use `--json` for a machine-readable result. The default timeout is 10 minutes,
and `--poll-interval` controls prediction polling frequency.

## Supported Inputs

| Option | Values | Default |
|---|---|---|
| `--duration` | integer from `5` through `20` | `5` |
| `--ratio` | `21:9`, `2:1`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16` | `9:16` |
| `--resolution` | `720p`, `1080p` | `720p` |
| `--generate-audio` | flag | disabled |

The helper validates these values before submitting. The endpoint determines
the model; the request payload does not include credentials or an unverified
model selector.

## Workflow

1. Turn the request into a concise scene-driven prompt with subject motion,
   camera movement, setting, lighting, and timing when relevant.
2. Preview the helper command without `--yes`.
3. Obtain explicit human approval for the displayed parameters.
4. Run once with `--yes`.
5. Wait for a terminal prediction status and report the saved MP4 path.
6. On an ambiguous submission or failure, do not resubmit automatically.

## Limitations

- This helper supports text-to-video only. Use a separate workflow when a
  starting image, ending image, or existing video is required.
- Model availability and accepted parameters can change. If MuAPI rejects a
  previously valid request, check the current API reference before changing
  the helper.
- Generated media remains subject to MuAPI and model content policies.

## Test Evidence

Run the focused standard-library tests with:

```bash
python -m unittest -v skills/muapi-video-gen/scripts/test_generate_video.py
```

The tests cover schema-aligned payloads, the single-POST boundary, wrapped and
flat API responses, preview mode, bounded polling, and output URL validation.

## API References

- FLUX 3 guide: `https://muapi.ai/flux-3`
- API reference: `https://muapi.ai/docs/api-reference`
- Access keys: `https://muapi.ai/access-keys`
