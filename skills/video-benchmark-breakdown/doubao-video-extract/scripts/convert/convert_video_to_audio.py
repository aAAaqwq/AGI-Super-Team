#!/usr/bin/env python3
"""Extract compressed audio from a local video file using PyAV.

Usage:
  python3 scripts/convert/convert_video_to_audio.py ./downloads/video.mp4
  python3 scripts/convert/convert_video_to_audio.py ./downloads/video.mp4 --format mp3
  python3 scripts/convert/convert_video_to_audio.py ./downloads/video.mp4 --format wav

Output:
  Prints the absolute audio file path on success.
"""

import argparse
import os
import sys
import wave
from pathlib import Path
from typing import Any, Optional, Union


PathLikeStr = Union[str, os.PathLike[str]]


def _pyav_status() -> dict[str, Any]:
    try:
        import av  # type: ignore
    except Exception as exc:
        return {
            "available": False,
            "error": f"{type(exc).__name__}: {exc}",
            "install_hint": "python3 -m pip install --user av",
        }
    return {"available": True, "version": getattr(av, "__version__", "unknown")}


def check_backends() -> dict[str, Any]:
    status = _pyav_status()
    if not status.get("available"):
        return {"pyav": status}

    encoders: dict[str, Any] = {}
    try:
        import av  # type: ignore

        for codec in ("mp3", "libmp3lame"):
            try:
                encoder = av.codec.Codec(codec, "w")
                encoders[codec] = {"available": True, "name": getattr(encoder, "name", codec)}
            except Exception as exc:
                encoders[codec] = {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    except Exception:
        pass
    return {"pyav": {**status, "encoders": encoders}}


def _resolve_output_dir(input_path: Path, output_dir: Optional[PathLikeStr] = None) -> Path:
    if output_dir:
        return Path(output_dir).expanduser().resolve()
    return input_path.parent.resolve()


def _normalize_resampled_frames(frames: Any) -> list[Any]:
    if frames is None:
        return []
    if isinstance(frames, list):
        return frames
    return [frames]


def _prepare_output(output_path: Path, overwrite: bool) -> None:
    if output_path.exists() and overwrite:
        output_path.unlink()


def _import_pyav():
    try:
        import av  # type: ignore
        from av.audio.resampler import AudioResampler  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "PyAV backend is not available. Install it explicitly with "
            "`python3 -m pip install --user av`."
        ) from exc
    return av, AudioResampler


def _convert_wav_with_pyav(input_path: Path, output_path: Path, overwrite: bool) -> None:
    _prepare_output(output_path, overwrite)
    av, AudioResampler = _import_pyav()

    container = av.open(str(input_path))
    wrote_audio = False
    try:
        audio_streams = [stream for stream in container.streams if stream.type == "audio"]
        if not audio_streams:
            raise ValueError(f"No audio stream found in input video: {input_path}")

        resampler = AudioResampler(format="s16", layout="mono", rate=16000)
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)

            for packet in container.demux(audio_streams[0]):
                for frame in packet.decode():
                    for resampled in _normalize_resampled_frames(resampler.resample(frame)):
                        data = resampled.to_ndarray().tobytes()
                        if data:
                            wav_file.writeframes(data)
                            wrote_audio = True

            try:
                flushed_frames = resampler.resample(None)
            except Exception:
                flushed_frames = []
            for resampled in _normalize_resampled_frames(flushed_frames):
                data = resampled.to_ndarray().tobytes()
                if data:
                    wav_file.writeframes(data)
                    wrote_audio = True
    finally:
        container.close()

    if not wrote_audio:
        raise ValueError(f"No audio frames were decoded from input video: {input_path}")


def _convert_mp3_with_pyav(input_path: Path, output_path: Path, overwrite: bool) -> None:
    _prepare_output(output_path, overwrite)
    av, AudioResampler = _import_pyav()

    input_container = av.open(str(input_path))
    output_container = av.open(str(output_path), mode="w", format="mp3")
    wrote_audio = False
    try:
        audio_streams = [stream for stream in input_container.streams if stream.type == "audio"]
        if not audio_streams:
            raise ValueError(f"No audio stream found in input video: {input_path}")

        try:
            output_stream = output_container.add_stream("libmp3lame", rate=16000)
        except Exception:
            output_stream = output_container.add_stream("mp3", rate=16000)
        output_stream.layout = "mono"
        output_stream.bit_rate = 64000

        resampler = AudioResampler(format="s16p", layout="mono", rate=16000)
        for packet in input_container.demux(audio_streams[0]):
            for frame in packet.decode():
                for resampled in _normalize_resampled_frames(resampler.resample(frame)):
                    for encoded in output_stream.encode(resampled):
                        output_container.mux(encoded)
                        wrote_audio = True

        try:
            flushed_frames = resampler.resample(None)
        except Exception:
            flushed_frames = []
        for resampled in _normalize_resampled_frames(flushed_frames):
            for encoded in output_stream.encode(resampled):
                output_container.mux(encoded)
                wrote_audio = True
        for encoded in output_stream.encode(None):
            output_container.mux(encoded)
            wrote_audio = True
    finally:
        output_container.close()
        input_container.close()

    if not wrote_audio:
        raise ValueError(f"No audio frames were decoded from input video: {input_path}")


def _convert_with_pyav(input_path: Path, output_path: Path, overwrite: bool) -> None:
    suffix = output_path.suffix.lower()
    if suffix == ".wav":
        _convert_wav_with_pyav(input_path, output_path, overwrite)
        return
    if suffix == ".mp3":
        _convert_mp3_with_pyav(input_path, output_path, overwrite)
        return
    raise ValueError("PyAV backend supports mp3 and wav output. Use --format mp3 or --format wav.")


def convert_video_to_audio(
    input_file: PathLikeStr,
    output_dir: Optional[PathLikeStr] = None,
    audio_format: str = "mp3",
    overwrite: bool = False,
) -> str:
    input_path = Path(input_file).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a file: {input_path}")

    audio_format = audio_format.lower().lstrip(".")
    if audio_format not in {"mp3", "wav"}:
        raise ValueError("audio_format must be mp3 or wav when using the PyAV-only converter")

    out_dir = _resolve_output_dir(input_path, output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{input_path.stem}.{audio_format}"

    if output_path.exists() and not overwrite:
        return str(output_path.resolve())

    _convert_with_pyav(input_path, output_path, overwrite)

    abs_path = output_path.resolve()
    if not abs_path.exists() or abs_path.stat().st_size == 0:
        raise FileNotFoundError(f"Converted audio file not found or empty: {abs_path}")

    return str(abs_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract audio from a local video file.")
    parser.add_argument("input_file", help="Local video file path")
    parser.add_argument(
        "--output-dir",
        help="Directory for the converted audio. Defaults to the input file directory.",
    )
    parser.add_argument(
        "--format",
        choices=["mp3", "wav"],
        default="mp3",
        help="Audio output format. Defaults to mp3.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Print backend availability and exit without converting.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite an existing converted audio file.",
    )
    args = parser.parse_args()

    try:
        if args.check:
            import json

            print(json.dumps(check_backends(), ensure_ascii=False, indent=2))
            return 0
        print(
            convert_video_to_audio(
                args.input_file,
                output_dir=args.output_dir,
                audio_format=args.format,
                overwrite=args.overwrite,
            )
        )
    except Exception as exc:
        print(f"Audio conversion failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
