#!/usr/bin/env bash
# Run a repository script with a Python that can actually execute it.
#
# Why this exists: every generator under scripts/ imports repository_model.py,
# which does `import tomllib` at module scope. tomllib landed in Python 3.11, so
# on a host whose PATH `python3` is older (macOS ships 3.9, Debian stable ships
# 3.9) a bare `python3 scripts/build_skill_catalog.py` dies with an ImportError
# that never says "your interpreter is too old". The generators also need the
# two packages from requirements-dev.txt.
#
# Usage:
#   bash scripts/python.sh scripts/build_skill_catalog.py --check
#
# Resolution order:
#   1. $AGI_SUPER_TEAM_PYTHON            explicit override, wins outright
#   2. an activated virtualenv           ($VIRTUAL_ENV/bin/python)
#   3. python3.13, python3.12, python3.11 on PATH
#   4. python3 on PATH, when it is already new enough
#   5. `uv run --python 3.11 --with ...` when uv is installed
#   6. a diagnostic naming what is missing and every escape hatch
#
# A candidate is accepted only after importing tomllib, yaml and jsonschema, so
# "we found an interpreter" and "we found an interpreter that can run the
# generators" are the same question rather than two.
#
# Exit status: the wrapped script's own status, or 127 when no interpreter works.

set -u

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROBE='import tomllib, yaml, jsonschema'
UV_ARGS=(--quiet --python 3.11 --with 'PyYAML>=6.0,<7' --with 'jsonschema>=4.23,<5')

if [ "$#" -eq 0 ]; then
  printf 'usage: %s <script.py> [args...]\n' "${0##*/}" >&2
  exit 64
fi

usable() {
  [ -n "$1" ] || return 1
  command -v "$1" >/dev/null 2>&1 || return 1
  "$1" -c "$PROBE" >/dev/null 2>&1
}

# An explicit override is an instruction, not a hint: if it cannot run the
# generators, say so instead of quietly picking a different interpreter.
if [ -n "${AGI_SUPER_TEAM_PYTHON:-}" ]; then
  if ! usable "$AGI_SUPER_TEAM_PYTHON"; then
    printf 'error: AGI_SUPER_TEAM_PYTHON=%s cannot import tomllib, yaml and jsonschema.\n' \
      "$AGI_SUPER_TEAM_PYTHON" >&2
    printf 'Unset it to let this script auto-detect, or point it at a Python 3.11+ with requirements-dev.txt installed.\n' >&2
    exit 127
  fi
  exec "$AGI_SUPER_TEAM_PYTHON" "$@"
fi

# An activated virtualenv comes next, before the versioned names on PATH: a
# contributor who ran `python3 -m venv .venv && . .venv/bin/activate` expects
# the packages they installed there to be the ones the generators see, and the
# venv only ever shadows `python`/`python3`, never `python3.11`. A venv that
# cannot run the generators is skipped rather than fatal - it may belong to
# something else entirely.
if [ -n "${VIRTUAL_ENV:-}" ] && usable "$VIRTUAL_ENV/bin/python"; then
  exec "$VIRTUAL_ENV/bin/python" "$@"
fi

for candidate in python3.13 python3.12 python3.11 python3; do
  if usable "$candidate"; then
    exec "$candidate" "$@"
  fi
done

# uv can build the interpreter and the two dependencies on demand. It is last
# because its first call may need the network.
if command -v uv >/dev/null 2>&1; then
  if uv run "${UV_ARGS[@]}" python -c "$PROBE" >/dev/null 2>&1; then
    exec uv run "${UV_ARGS[@]}" python "$@"
  fi
fi

found=$(python3 --version 2>&1 || printf 'not on PATH')
printf 'error: no Python interpreter here can run this repository'"'"'s generators.\n' >&2
printf '\nThe generators need Python 3.11 or newer (for tomllib) plus PyYAML and\n' >&2
printf 'jsonschema from requirements-dev.txt.\n' >&2
printf '\nAlso tried: uv (absent, or unable to build a 3.11 environment).\n' >&2
printf 'Your python3 is: %s\n' "$found" >&2
printf '\nAny one of these unblocks it:\n' >&2
printf '  AGI_SUPER_TEAM_PYTHON=/path/to/python3.11 bash scripts/python.sh <script.py>\n' >&2
printf '  python3.11 -m pip install --requirement requirements-dev.txt\n' >&2
printf '  python3 -m venv .venv && . .venv/bin/activate && python -m pip install -r requirements-dev.txt\n' >&2
printf '  install uv (https://docs.astral.sh/uv/); this script then uses it automatically\n' >&2
exit 127
