#!/bin/bash
# PreToolUse hook: Block commits if tests are failing

RESULT=$(/opt/homebrew/bin/godot --headless --script addons/gut/gut_cmdln.gd -gdir=res://tests/ -gexit 2>&1)
FAIL_COUNT=$(echo "$RESULT" | grep -o "Failing Tests *[0-9]*" | grep -o "[0-9]*")

if [[ -n "$FAIL_COUNT" && "$FAIL_COUNT" -gt 0 ]]; then
  python3 -c "import json; print(json.dumps({'decision':'block','reason':'${FAIL_COUNT} tests failing. Fix before committing.'}))"
else
  python3 -c "import json; print(json.dumps({'decision':'allow'}))"
fi
