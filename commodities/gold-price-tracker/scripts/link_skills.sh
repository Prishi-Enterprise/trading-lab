#!/usr/bin/env bash
# Expose repo skills (skills/*) to agent tools that auto-discover project skills.
# Symlinks keep one source of truth in skills/ — safe to re-run.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
for tool in .claude .cursor; do
  mkdir -p "$REPO/$tool/skills"
  for s in "$REPO"/skills/*/; do
    name="$(basename "$s")"
    ln -sfn "../../skills/$name" "$REPO/$tool/skills/$name"
    echo "linked $tool/skills/$name -> skills/$name"
  done
done
