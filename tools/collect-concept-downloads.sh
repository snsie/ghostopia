#!/usr/bin/env bash
# Moves ChatGPT downloads named ghostopia__<folder>__<file>.png from ~/Downloads
# into concept/<folder>/<file>.png, checking each is a real PNG.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
shopt -s nullglob
for f in "$HOME"/Downloads/ghostopia__*.png; do
  rel="$(basename "$f" .png)"; rel="${rel#ghostopia__}"; rel="${rel//__//}.png"
  if [ "$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')" != "89504e47" ]; then
    echo "SKIP (not PNG): $f"; continue
  fi
  mkdir -p "$root/concept/$(dirname "$rel")"
  mv -f "$f" "$root/concept/$rel"
  echo "concept/$rel"
done
