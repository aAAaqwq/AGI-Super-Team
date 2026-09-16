#!/usr/bin/env python3
"""Refresh or verify every curated per-harness package under ``plugins/``.

Four packages are generated from the harness adapters:
``agi-super-team-claudecode``, ``-hermes``, ``-dsh``, and ``-openclaw``. Each
has its own builder so a failure names the harness; this script is the single
entry point that runs all four, so `npm run check:harness-packages` is one
command rather than four.

```bash
python3 scripts/build_harness_packages.py            # refresh all four
python3 scripts/build_harness_packages.py --check     # verify, write nothing
```

``--check`` is the assertion that matters: it fails when a checked-in artifact
no longer matches what its adapter renders, which is what stops the packages
from silently drifting away from ``bin/adapters/<harness>.mjs``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from build_harness_packages import REPO_ROOT, registered_packages  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the generated packages are current without writing",
    )
    arguments = parser.parse_args()

    packages = registered_packages(arguments.root)
    if not packages:
        print("no per-harness package builders found")
        return 1

    failures = []
    for entry in packages:
        package = entry.package
        command = [
            sys.executable,
            str(entry.builder),
            "--root",
            str(arguments.root),
        ]
        if arguments.check:
            command.append("--check")
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        if completed.returncode != 0:
            failures.append(package.harness)
        else:
            action = "verified" if arguments.check else "rebuilt"
            print(f"{package.package}: {action}")

    if failures:
        print(f"FAILED: {', '.join(failures)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
