#!/usr/bin/env bash
# Run Stage 3 (analyst + devil's advocate) across all 21 gold repos, sequential.
# Skips already-analyzed repos. Logs each repo.
cd "$(dirname "$0")/.."
IDS="archon mem0 jq ripgrep express click fd pytest prettier zx yq bat tokei \
mattpocock-skills awesome-graph-eng nolicense suspicious hexyl ratty navi claimgap"
for id in $IDS; do
  if [ -f "data/stage3-analysis/${id}.json" ]; then
    echo "[skip] ${id}"
    continue
  fi
  echo "[run] ${id}"
  python3 scripts/run_stage3.py "$id" 2>&1 | \
    grep -E "\[analyst\]|\[advocate\]|SURVIVED|wrote|ERROR" | tail -5
  echo "[done] ${id}"
done
echo "SWEEP COMPLETE"