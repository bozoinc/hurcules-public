"""TDD tests for Stage 5 evaluator (evidence & evaluation gates)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.evaluator import evaluate_capabilities

TREE = ["src/main.py", "src/util.py", "README.md"]

GOOD = [
    {"id": "c1", "name": "Parser", "ontology_type": "TOOL",
     "evidence": [{"file": "src/main.py", "scope": "parse"}], "confidence": 0.9, "requirements": []},
]
BAD_EVIDENCE = [
    {"id": "c1", "name": "Ghost", "ontology_type": "TOOL",
     "evidence": [{"file": "not/here.py", "scope": "x"}], "confidence": 0.9, "requirements": []},
]
NO_EVIDENCE = [
    {"id": "c1", "name": "Empty", "ontology_type": "TOOL",
     "evidence": [], "confidence": 0.9, "requirements": []},
]


def test_good_capability_passes():
    r = evaluate_capabilities(GOOD, TREE)
    assert r["unsupported_capability_rate"] == 0.0
    assert r["verdicts"][0]["status"] == "PASS"
    assert r["verdicts"][0]["checks"]["citation_accuracy"]["status"] == "PASS"


def test_fabricated_evidence_fails():
    r = evaluate_capabilities(BAD_EVIDENCE, TREE)
    assert r["unsupported_capability_rate"] == 1.0
    v = r["verdicts"][0]
    assert v["status"] == "CONDITIONAL"
    assert v["checks"]["citation_accuracy"]["status"] == "FAIL"


def test_missing_evidence_conditional():
    r = evaluate_capabilities(NO_EVIDENCE, TREE)
    assert r["verdicts"][0]["checks"]["citation_accuracy"]["status"] == "FAIL"


def test_unsupported_rate_metric():
    mix = GOOD + BAD_EVIDENCE
    r = evaluate_capabilities(mix, TREE)
    assert r["unsupported_capability_rate"] == 0.5


def test_schema_checks():
    bad = [{"id": "x", "name": "bad", "ontology_type": "MAGIC",
            "evidence": [{"file": "src/main.py", "scope": "s"}], "confidence": 2.0}]
    r = evaluate_capabilities(bad, TREE)
    v = r["verdicts"][0]
    assert v["checks"]["schema"]["status"] == "FAIL"
    assert v["supported"] is False


def test_empty_capabilities():
    r = evaluate_capabilities([], TREE)
    assert r["capability_count"] == 0
    assert r["unsupported_capability_rate"] == 0.0
    assert r["verdicts"] == []


def test_evaluator_deterministic():
    a = json.dumps(evaluate_capabilities(GOOD, TREE), sort_keys=True)
    b = json.dumps(evaluate_capabilities(GOOD, TREE), sort_keys=True)
    assert a == b