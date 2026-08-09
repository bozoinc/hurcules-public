"""TDD tests for Stage 3 analyst + devil's advocate (fake LLM client)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.analyst import analyze, _extract_json, _validate_candidates, _truncate_tree, ONTOLOGY
from hurcules.devils_advocate import challenge

MAP = {
    "repository": "/fake/repo",
    "file_count": 3,
    "file_tree": ["src/main.py", "src/util.py", "README.md"],
    "languages": {"python": 2, "markdown": 1},
    "entry_points": ["src/main.py"],
    "test_files": [],
    "documentation_files": ["README.md"],
    "dependency_manifests": [],
    "risk_flags": [],
}


def fake_client(reply: str):
    def chat(messages):
        return reply
    return chat


def test_extract_json_tolerates_prose():
    text = "Here is the analysis:\n{\"capabilities\": []}\nHope this helps."
    assert _extract_json(text) == {"capabilities": []}


def test_validate_rejects_bad_ontology():
    errs = _validate_candidates([{
        "id": "c1", "name": "x", "ontology_type": "MAGIC", "evidence": [],
        "confidence": 0.5,
    }])
    assert any("ontology" in e for e in errs)


def test_validate_rejects_bad_confidence():
    errs = _validate_candidates([{
        "id": "c1", "name": "x", "ontology_type": "TOOL",
        "evidence": [{"file": "a.py", "scope": "s"}], "confidence": 7,
    }])
    assert any("confidence" in e for e in errs)


def test_analyze_returns_validated_candidates():
    reply = json.dumps({"capabilities": [{
        "id": "c1", "name": "JSON parser", "ontology_type": "TOOL",
        "evidence": [{"file": "src/main.py", "scope": "parse"}],
        "confidence": 0.9, "requirements": [],
    }]})
    out = analyze(MAP, fake_client(reply))
    assert out["schema"] == "hurcules.capability-analysis"
    assert out["raw_candidate_count"] == 1
    assert out["capabilities"][0]["id"] == "c1"
    assert out["validation_errors"] == []


def test_analyze_strips_fabricated_evidence():
    # evidence cites a file NOT in the tree -> must be stripped
    reply = json.dumps({"capabilities": [{
        "id": "c1", "name": "Ghost", "ontology_type": "TOOL",
        "evidence": [{"file": "not/in/tree.py", "scope": "x"}],
        "confidence": 0.9, "requirements": [],
    }]})
    out = analyze(MAP, fake_client(reply))
    assert out["capabilities"] == [], "fabricated-evidence candidate must be dropped"


def test_analyze_blank_raw_is_inconclusive_not_crash():
    # W1-[1] quality floor: a blank/weak model reply must be INCONCLUSIVE,
    # NOT raise inside _extract_json (the pilot's exact silent-empty bug).
    out = analyze(MAP, fake_client(""))
    assert out["conclusion"] == "inconclusive"
    assert out["capabilities"] == []


def test_analyze_unparseable_raw_is_inconclusive():
    out = analyze(MAP, fake_client("this is not json { at all"))
    assert out["conclusion"] == "inconclusive"
    assert out["capabilities"] == []


def test_analyze_parsed_but_empty_is_inconclusive():
    # valid JSON, zero capabilities -> inconclusive, never a valid empty pkg
    out = analyze(MAP, fake_client('{"capabilities":[]}'))
    assert out["conclusion"] == "inconclusive"
    assert out["capabilities"] == []


def test_advocate_kills_attacked_candidates():
    candidates = [
        {"id": "c1", "name": "real", "ontology_type": "TOOL", "evidence": [],
         "confidence": 0.9, "requirements": []},
        {"id": "c2", "name": "marketing", "ontology_type": "TOOL", "evidence": [],
         "confidence": 0.9, "requirements": []},
    ]
    reply = json.dumps({"verdicts": [
        {"id": "c1", "survives": True, "reason": "genuine"},
        {"id": "c2", "survives": False, "reason": "README only"},
    ]})
    survivors = challenge(candidates, MAP, fake_client(reply))
    ids = [c["id"] for c in survivors]
    assert ids == ["c1"], f"c2 should be killed, got {ids}"


def test_advocate_empty_candidates_returns_empty():
    assert challenge([], MAP, fake_client("{}")) == []


def test_truncate_tree_caps_huge_trees_keeps_anchors():
    big = [f"src/mod{i}.py" for i in range(5000)] + ["src/main.py", "README.md"]
    out = _truncate_tree(big, cap=400)
    assert len(out) <= 400
    assert "src/main.py" in out, "entry point must be kept"
    assert "README.md" in out, "doc must be kept"
    assert len(out) == len(set(out)), "must be deduped"
