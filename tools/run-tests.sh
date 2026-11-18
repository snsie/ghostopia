#!/usr/bin/env bash
# Runs the headless test suite. Imports the project first when .godot/ is
# missing (fresh clones and agent worktrees).
#
#   tools/run-tests.sh                 # all tests
#   tools/run-tests.sh block_registry  # only test files whose path contains this
#
# GODOT defaults to the console build on Windows; override with GODOT=/path/to/godot.
# A GDScript runtime error (SCRIPT ERROR) anywhere in the run fails the suite, even when
# the test that hit it reported PASS (task4 issue).
set -uo pipefail

cd "$(dirname "$0")/.."
GODOT="${GODOT:-/c/Tools/Godot/godot_console.exe}"

if [ ! -d .godot ] || ! grep -q "GhostAppearance" .godot/global_script_class_cache.cfg 2>/dev/null; then
  echo "Importing project..."
  "$GODOT" --headless --path . --import >/dev/null 2>&1 || true
fi

LOG="$(mktemp)"
if [ $# -gt 0 ]; then
  "$GODOT" --headless --path . -s res://tests/run_tests.gd -- "$@" 2>&1 | tee "$LOG"
else
  "$GODOT" --headless --path . -s res://tests/run_tests.gd 2>&1 | tee "$LOG"
fi
STATUS=${PIPESTATUS[0]}

if grep -q "SCRIPT ERROR" "$LOG"; then
  echo ""
  echo "FAILED: GDScript runtime errors during the run:"
  grep -A2 "SCRIPT ERROR" "$LOG" | head -40
  STATUS=1
fi
rm -f "$LOG"
exit "$STATUS"
