#!/usr/bin/env python3
"""Preview the generated atlas with UTF-8 MIME types.

Python's SimpleHTTPRequestHandler does not append a charset to text/plain or
application/json. Browsers then fall back to windows-1252 and show mojibake for
llms.txt. GitHub Pages already sends charset=utf-8; this server keeps local
previews faithful to production.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "docs"


class Utf8Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/plain; charset=utf-8",
        ".svg": "image/svg+xml; charset=utf-8",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview the generated Skills Atlas")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "skills-atlas" / "index.html").is_file():
        raise SystemExit(
            f"{root}/skills-atlas/index.html not found; run "
            "python3 skills-atlas/scripts/build.py first"
        )
    handler = partial(Utf8Handler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Serving {root} at http://127.0.0.1:{args.port}/skills-atlas/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
