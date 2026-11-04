#!/usr/bin/env bash
set -euo pipefail

# npm packs the on-disk mode. A restrictive umask otherwise ships 0600/0700
# files, which global installs cannot read as another user.
cd "$(dirname "$0")/.."

for root in bin agents config catalog skills plugins .agents .claude-plugin .cursor-plugin .kimi-plugin .codex; do
  [[ -e "$root" ]] && chmod -R u+rwX,go+rX,go-w "$root"
done
chmod 0755 bin/agi-super-team.mjs
chmod 0644 LICENSE README.md README_CN.md README.es-ES.md package.json gemini-extension.json
