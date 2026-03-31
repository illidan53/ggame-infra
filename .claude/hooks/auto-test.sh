#!/bin/bash
# PostToolUse hook: Run GUT tests after .gd file edits

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path','') or d.get('tool_response',{}).get('filePath',''))" 2>/dev/null)

if [[ "$FILE_PATH" != *.gd ]]; then
  exit 0
fi

if [[ "$FILE_PATH" == */tests/* ]]; then
  exit 0
fi

RESULT=$(/opt/homebrew/bin/godot --headless --script addons/gut/gut_cmdln.gd -gdir=res://tests/ -gexit 2>&1)
PASS_COUNT=$(echo "$RESULT" | grep -o "Passing Tests *[0-9]*" | grep -o "[0-9]*")
FAIL_COUNT=$(echo "$RESULT" | grep -o "Failing Tests *[0-9]*" | grep -o "[0-9]*")

if [[ -n "$FAIL_COUNT" && "$FAIL_COUNT" -gt 0 ]]; then
  python3 -c "import json; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PostToolUse','additionalContext':'AUTO-TEST: ${FAIL_COUNT} tests FAILING after editing ${FILE_PATH}. Fix before continuing.'}}))"
else
  python3 -c "import json; print(json.dumps({'hookSpecificOutput':{'hookEventName':'PostToolUse','additionalContext':'AUTO-TEST: All ${PASS_COUNT:-0} tests passing after editing ${FILE_PATH}.'}}))"
fi
