#!/usr/bin/env bash
# Forced Stage 3 re-sweep with tuned prompts: analyst + advocate, all 21 repos.
# Overwrites data/stage3-analysis/*.json (regenerable artifacts). Keeps .judged.json.
cd "$(dirname "$0")/.."
IDS="archon mem0 jq ripgrep express click fd pytest prettier zx yq bat tokei \
mattpocock-skills awesome-graph-eng nolicense suspicious hexyl ratty navi claimgap"
for id in $IDS; do
  echo "[run] ${id}"
  python3 scripts/run_stage3.py "$id" 2>&1 | \
    grep -E "\[analyst\]|\[advocate\]|wrote|ERROR|Bad Request" | tail -4
  echo "[done] ${id}"
done
echo "TUNED SWEEP COMPLETE"