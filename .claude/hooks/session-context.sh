#!/bin/bash
# SessionStart hook: Load project context
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

# Gather phase status, active errors, recent iterations, uncommitted changes
PHASE_STATUS=$(grep -A1 "^| P" docs/PLAN.md 2>/dev/null | head -20)
ERRORS=$(cat docs/SCRATCHPAD.md 2>/dev/null | grep -A10 "^## Active Error" | head -20)
ITERATIONS=$(head -30 docs/ITERATIONS.md 2>/dev/null | grep -A5 "^## \[I-" | head -20)
UNCOMMITTED=$(git diff --stat 2>/dev/null; git diff --cached --stat 2>/dev/null)

python3 -c "
import json
ctx = '''PHASE STATUS:
${PHASE_STATUS}

ACTIVE ERRORS:
${ERRORS}

RECENT ITERATIONS:
${ITERATIONS}

UNCOMMITTED CHANGES:
${UNCOMMITTED}'''
print(json.dumps({'hookSpecificOutput':{'hookEventName':'SessionStart','additionalContext': ctx}}))"
