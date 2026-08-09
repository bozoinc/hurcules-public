"""TDD tests for Stage 3 capability consolidation (precision tuning)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.consolidate import consolidate, jaccard, norm_tokens


def test_jaccard_norm():
    a = norm_tokens("JSON parsing and value model")
    b = norm_tokens("JSON parsing and generation")
    assert jaccard(a, b) >= 0.4  # shared json+parsing
    assert jaccard(norm_tokens("parser"), norm_tokens("hex viewer")) == 0.0


def test_merges_overgranular_json_candidates():
    # the exact case that caused low precision on jq
    candidates = [
        {"id": "c1", "name": "JSON parsing", "ontology_type": "TOOL",
         "evidence": [{"file": "src/jv.c", "scope": "parse"}], "confidence": 0.9, "requirements": []},
        {"id": "c2", "name": "JSON generation library", "ontology_type": "TOOL",
         "evidence": [{"file": "src/jv_aux.c", "scope": "gen"}], "confidence": 0.95, "requirements": []},
        {"id": "c3", "name": "JSON query language interpreter", "ontology_type": "WORKFLOW",
         "evidence": [{"file": "src/execute.c", "scope": "exec"}], "confidence": 0.9, "requirements": []},
        {"id": "c4", "name": "Hex viewer", "ontology_type": "TOOL",
         "evidence": [{"file": "src/view.c", "scope": "view"}], "confidence": 0.8, "requirements": []},
    ]
    out = consolidate(candidates)
    # c1+c2 merge (same TOOL + shared json token); c3 stays (different ontology);
    # c4 stays (different topic)
    assert len(out) == 3, f"expected 3 clusters, got {len(out)}: {[c['name'] for c in out]}"
    tool_json = [c for c in out if c["ontology_type"] == "TOOL" and "JSON" in c["name"]]
    assert len(tool_json) == 1, "TOOL JSON candidates should merge into one"
    merged = tool_json[0]
    assert len(merged["evidence"]) == 2, "merged evidence unioned"
    assert "c1" in merged["members"] and "c2" in merged["members"]


def test_consolidate_preserves_distinct_capabilities():
    candidates = [
        {"id": "a1", "name": "CLI tool", "ontology_type": "TOOL",
         "evidence": [{"file": "a.c", "scope": "x"}], "confidence": 0.9, "requirements": []},
        {"id": "a2", "name": "Database engine", "ontology_type": "TOOL",
         "evidence": [{"file": "b.c", "scope": "y"}], "confidence": 0.9, "requirements": []},
    ]
    out = consolidate(candidates)
    assert len(out) == 2, "unrelated capabilities must not merge"


def test_consolidate_deterministic():
    candidates = [
        {"id": "c1", "name": "XML parsing", "ontology_type": "TOOL",
         "evidence": [{"file": "p.c", "scope": "x"}], "confidence": 0.9, "requirements": []},
        {"id": "c2", "name": "XML writer", "ontology_type": "TOOL",
         "evidence": [{"file": "q.c", "scope": "y"}], "confidence": 0.95, "requirements": []},
    ]
    a = json.dumps(consolidate(candidates), sort_keys=True)
    b = json.dumps(consolidate(candidates), sort_keys=True)
    assert a == b


def test_consolidate_reduces_granularity():
    many = [{"id": f"m{i}", "name": f"CLI command {i} builder", "ontology_type": "TOOL",
             "evidence": [{"file": f"cmd{i}.c", "scope": "x"}], "confidence": 0.9, "requirements": []}
            for i in range(20)]
    out = consolidate(many)
    assert len(out) < len(many), "over-granular candidates must be reduced"