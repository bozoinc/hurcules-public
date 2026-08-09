"""TDD tests for the gold-set ceiling scorer (pure, deterministic, no network)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.ceiling import (ceiling_score, ceiling_score_semantic,
                              has_valid_evidence, normalize_name)


def cap(cid, name, evidence=None):
    if evidence is None:
        evidence = [{"file": "f"}]
    return {"id": cid, "name": name, "evidence": evidence}


GOLD = [cap("g1", "JSON parser"), cap("g2", "Bytecode VM")]
EXTRACTED = [cap("e1", "JSON parser"), cap("e2", "Bytecode VM")]


def test_perfect_match():
    r = ceiling_score(EXTRACTED, GOLD)
    assert r["precision"] == 1.0
    assert r["recall"] == 1.0
    assert r["unsupported_rate"] == 0.0
    assert r["matching_ids"] == ["e1", "e2"]
    assert r["missing_gold"] == []
    assert r["extra"] == []


def test_extra_lowers_precision_not_recall():
    extracted = EXTRACTED + [cap("e3", "Ghost cap")]
    r = ceiling_score(extracted, GOLD)
    assert r["precision"] == pytest.approx(2 / 3, abs=1e-4)  # rounded to 4dp
    assert r["recall"] == 1.0
    assert r["extra"] == ["e3"]


def test_missing_gold_lowers_recall_not_precision():
    gold = GOLD + [cap("g3", "CLI entrypoint")]
    r = ceiling_score(EXTRACTED, gold)
    assert r["precision"] == 1.0
    assert r["recall"] == pytest.approx(2 / 3, abs=1e-4)  # rounded to 4dp
    assert r["missing_gold"] == ["g3"]


def test_empty_extracted():
    r = ceiling_score([], GOLD)
    assert r["precision"] == 0.0
    assert r["recall"] == 0.0
    assert r["unsupported_rate"] == 0.0
    assert r["matching_ids"] == []


def test_empty_gold():
    r = ceiling_score(EXTRACTED, [])
    assert r["precision"] == 0.0
    assert r["recall"] == 0.0
    assert r["extra"] == ["e1", "e2"]


def test_normalization_is_lowercase_strip():
    assert normalize_name("  JSON Parser  ") == "json parser"
    r = ceiling_score([cap("e1", "  JSON Parser ")],
                      [cap("g1", "json parser")])
    assert r["precision"] == 1.0
    assert r["recall"] == 1.0


def test_unsupported_rate_counts_empty_evidence():
    extracted = [cap("e1", "JSON parser"),
                 cap("e2", "Ghost", evidence=[])]
    r = ceiling_score(extracted, GOLD)
    assert r["unsupported_rate"] == 0.5
    assert r["unsupported_ids"] == ["e2"]
    assert r["precision"] == 0.5  # Ghost still counts in denominator


def test_duplicate_names_matched_once():
    extracted = [cap("e1", "Bytecode VM"), cap("e2", "Bytecode VM")]
    r = ceiling_score(extracted, GOLD)
    assert r["matching_count"] == 1  # one gold, one claim wins
    assert r["precision"] == 0.5
    assert r["recall"] == 0.5


def test_falls_back_to_name_when_no_id():
    r = ceiling_score([{"name": "Bytecode VM"}],
                      [{"name": "Bytecode VM"}])
    assert r["matching_count"] == 1
    assert r["precision"] == 1.0


def test_deterministic():
    a = json.dumps(ceiling_score(EXTRACTED, GOLD), sort_keys=True)
    b = json.dumps(ceiling_score(EXTRACTED, GOLD), sort_keys=True)
    assert a == b


def test_has_valid_evidence():
    assert has_valid_evidence({"evidence": [{"file": "f"}]}) is True
    assert has_valid_evidence({"evidence": []}) is False
    assert has_valid_evidence({}) is False
    assert has_valid_evidence({"evidence": "not-a-list"}) is False


def test_semantic_matches_human_vs_model_wording():
    # gold names are human-authored; extracted names model-authored — same
    # meaning, different words. Exact matcher misses; Jaccard catches at 0.35.
    gold = [{"id": "g1", "name": "YAML workflow engine (DAG)"}]
    ext = [{"id": "e1", "name": "workflow executor engine", "evidence": [{"file": "a"}]}]
    exact = ceiling_score(ext, gold)
    assert exact["matching_count"] == 0
    semi = ceiling_score_semantic(ext, gold, threshold=0.35)
    assert semi["matching_count"] == 1
    assert semi["matcher"] == "token-jaccard>=0.35"


def test_semantic_respects_threshold():
    gold = [{"id": "g1", "name": "memory pool allocator"}]
    ext = [{"id": "e1", "name": "memory pool allocator", "evidence": [{"file": "a"}]}]
    assert ceiling_score_semantic(ext, gold, threshold=0.99)["matching_count"] == 1
    assert ceiling_score_semantic(ext, gold, threshold=0.0)["matching_count"] == 1


def test_semantic_one_to_one_no_dup_inflation():
    gold = [{"id": "g1", "name": "parse config"},
            {"id": "g2", "name": "render output"}]
    ext = [{"id": "e1", "name": "parse config", "evidence": [{"file": "a"}]},
           {"id": "e2", "name": "parse config", "evidence": [{"file": "b"}]}]
    r = ceiling_score_semantic(ext, gold, threshold=0.9)
    assert r["matching_count"] == 1  # one gold claims one dup-parse
    assert r["extra"] == ["e2"]