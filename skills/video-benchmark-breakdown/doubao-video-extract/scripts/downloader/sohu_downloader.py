#!/usr/bin/env python3
"""Anonymous Sohu Video downloader."""

from anonymous_ytdlp_downloader import PlatformConfig, run_cli  # noqa: E402


CONFIG = PlatformConfig(
    platform="sohu",
    display_name="Sohu Video",
    hosts=("tv.sohu.com", "my.tv.sohu.com"),
    extractor_keys=("Sohu", "SohuV"),
)


if __name__ == "__main__":
    raise SystemExit(run_cli(CONFIG))
