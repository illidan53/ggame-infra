#!/bin/bash
# PreCompact hook: Save context before compaction
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
echo "Context compacting — SCRATCHPAD.md and ITERATIONS.md preserved on disk."
