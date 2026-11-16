#!/usr/bin/env bash
# Runs the headless test suite. Imports the project first when .godot/ is
# missing (fresh clones and agent worktrees).
#
#   tools/run-tests.sh                 # all tests
#   tools/run-tests.sh block_registry  # only test files whose path contains this
#
# GODOT defaults to the console build on Windows; override with GODOT=/path/to/godot.
set -euo pipefail

cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Tools/Godot/godot_console.exe}"

if [ ! -d .godot ]; then
  echo "Importing project (first run)..."
  "$GODOT" --headless --path . --import >/dev/null 2>&1 || true
fi

if [ $# -gt 0 ]; then
  exec "$GODOT" --headless --path . -s res://tests/run_tests.gd -- "$@"
else
  exec "$GODOT" --headless --path . -s res://tests/run_tests.gd
fi
