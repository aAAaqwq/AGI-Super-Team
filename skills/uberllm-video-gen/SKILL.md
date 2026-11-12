---
name: uberllm-video-gen
description: Generate one text-to-video clip through UberLLM. Use when a video needs a choice of models on one key, a free price check, paid-request confirmation, and a local MP4.
---

# UberLLM Video Generation

Generate one text-to-video clip through UberLLM's `/v1/video/generations` job API.
The default model is `fal-ai/veo3.1/lite`; `--model` picks any other text-to-video
model on the same key (Kling, Vidu, Wan, LTX, Hailuo and others). This is an opt-in
workflow and does not replace any other video provider.

## Prerequisites

- Python 3.10 or newer; the helper uses only the standard library.
- An UberLLM API key in `UBERLLM_API_KEY` (https://uberllm.dev/signup; prepaid credit).
- Outbound HTTPS access to `api.uberllm.dev`.

Set the key in the environment. Never put it in a prompt, command argument,
source file, or log.

```bash
export UBERLLM_API_KEY="..."
```

## Safety Boundary

Running a generation request may incur charges. The helper prints the exact
request plan and exits without network access unless `--quote` or `--yes` is present.

`--quote` sends the same request with `"validate": true`: UberLLM checks the model and
options as if the request were real and answers with the listed price (`cost_usd`) and
the most the job can be billed (`max_cost_usd`). Nothing is made and nothing is charged.

The generation `POST` is sent exactly once, with an `Idempotency-Key`, and is never
retried. Only job-status and download `GET` requests use bounded retries for transient
failures. `--max-cost` caps what the job may be billed. If the submission result is
unclear, stop and check Dashboard > Activity on uberllm.dev instead of running the
command again. Failed, canceled and expired jobs are not billed.

The key is sent only to `api.uberllm.dev`; a result link on any other host is downloaded
without it.

## Usage

Preview the request first:

```bash
python skills/uberllm-video-gen/scripts/generate_video.py \
  "A slow aerial orbit around a lighthouse at sunrise" \
  --output lighthouse.mp4
```

Check the price (nothing is charged):

```bash
python skills/uberllm-video-gen/scripts/generate_video.py \
  "A slow aerial orbit around a lighthouse at sunrise" \
  --output lighthouse.mp4 --duration 4 --quote
```

After reviewing the plan and price, confirm one paid submission:

```bash
python skills/uberllm-video-gen/scripts/generate_video.py \
  "A slow aerial orbit around a lighthouse at sunrise" \
  --output lighthouse.mp4 \
  --duration 4 \
  --ratio 16:9 \
  --resolution 720p \
  --max-cost 0.30 \
  --yes
```

Use `--json` for a machine-readable result (job id, model, `cost_usd`, output path).
The default timeout is 10 minutes, and `--poll-interval` controls job polling frequency.

## Supported Inputs

| Option | Values | Default |
|---|---|---|
| `--model` | any UberLLM text-to-video model id | `fal-ai/veo3.1/lite` |
| `--duration` | seconds the model makes (Veo 3.1 Lite: `4`, `6`, `8`) | `4` |
| `--ratio` | shapes the model makes (Veo 3.1 Lite: `16:9`, `9:16`) | `16:9` |
| `--resolution` | resolutions the model makes (Veo 3.1 Lite: `720p`, `1080p`) | `720p` |
| `--max-cost` | most the job may be billed, in USD | none |

Each model makes only certain lengths, resolutions and shapes; list them with
`GET https://api.uberllm.dev/v1/models/<model id>`. A request for one the model does not
make is refused with the allowed values before anything is charged, so run `--quote`
when you change model or options.

## Workflow

1. Turn the request into a concise English video prompt with subject motion,
   camera movement, setting, lighting, and audio cues when relevant.
2. Preview the helper command without `--yes`, then run it with `--quote`.
3. Obtain explicit human approval for the displayed model, parameters and price.
4. Run once with `--yes`.
5. Wait for the job to end and report the saved MP4 path and `cost_usd`.
6. On an ambiguous submission or failure, do not resubmit automatically.

## Limitations

- This helper supports text-to-video only. Use a separate image-to-video skill
  when a start or end frame is required.
- Model availability, options and prices change. Check the live list with
  `GET https://api.uberllm.dev/v1/models?type=video` and prices at
  https://uberllm.dev/models.
- A job that reaches `--timeout` keeps running on UberLLM and is billed when it ends.
- Generated media remains subject to the model's content policies.

## Test Evidence

Run the focused standard-library tests with:

```bash
python -m unittest -v skills/uberllm-video-gen/scripts/test_generate_video.py
```

The tests cover the UberLLM payload fields, the single-POST boundary with an
idempotency key, the free `validate` quote, job polling to success and failure, sending
the key only to `api.uberllm.dev`, and preview mode.

## API References

- Video models: `https://api.uberllm.dev/v1/models?type=video`
- Submit: `POST https://api.uberllm.dev/v1/video/generations`
- Poll: `GET https://api.uberllm.dev/v1/video/generations/{id}`
- Docs: `https://uberllm.dev/docs/media`
