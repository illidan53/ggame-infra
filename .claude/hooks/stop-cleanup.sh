#!/bin/bash
# Stop hook: Warn about uncommitted changes
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

DIRTY=$(git status --porcelain 2>/dev/null)
if [[ -n "$DIRTY" ]]; then
  COUNT=$(echo "$DIRTY" | wc -l | tr -d ' ')
  python3 -c "import json; print(json.dumps({'systemMessage':'Session ending with ${COUNT} uncommitted file(s). Consider committing.'}))"
fi
