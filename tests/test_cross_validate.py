"""TDD tests for W1-[2] — cross-model validation (>=2 models must agree).

Uses canned JSON replies through injectable client callables — no network.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.cross_validate import (
    cross_validate,
    validate_before_registry,
    normalize_name,
    clients_from_router,
)
from hurcules.routes import Route, Router

MAP = {
    "repository": "/fake/repo",
    "file_count": 2,
    "file_tree": ["src/main.py", "README.md"],
    "languages": {"python": 2},
    "entry_points": ["src/main.py"],
    "test_files": [],
    "documentation_files": ["README.md"],
    "dependency_manifests": [],
    "risk_flags": [],
}


def cap(cid, name):
    return {
        "id": cid, "name": name, "ontology_type": "TOOL",
        "evidence": [{"file": "src/main.py", "scope": "core"}],
        "confidence": 0.9, "requirements": [],
    }


def fake_client(*caps):
    """Client callable returning canned capabilities JSON."""
    reply = json.dumps({"capabilities": list(caps)})

    def chat(messages):
        return reply
    return chat


# ── normalization ──────────────────────────────────────────────────────────

def test_normalize_name_lowercases_strips_punctuation():
    assert normalize_name("JSON Parser!") == "json parser"
    assert normalize_name("JSON-Parser") == "json parser"
    assert normalize_name("  A. B  ") == "a b"
    assert normalize_name("") == ""
    assert normalize_name(None) == ""


# ── cross_validate ─────────────────────────────────────────────────────────

def test_two_models_agree():
    out = cross_validate(MAP, [fake_client(cap("c1", "PDF handling")),
                               fake_client(cap("c1", "PDF handling"))],
                         ["m1", "m2"])
    assert out["schema"] == "hurcules.cross-validation"
    assert out["agreement"] == ["pdf handling"]
    assert out["disagreement"] == []
    assert out["verdict"] == "validated"
    assert out["verdicts"] == {"m1": "agrees", "m2": "agrees"}
    assert out["support"] == {"pdf handling": 2}


def test_two_models_disagree():
    out = cross_validate(MAP, [fake_client(cap("c1", "PDF handling")),
                               fake_client(cap("c2", "Video encoding"))],
                         ["m1", "m2"])
    assert out["agreement"] == []
    assert out["disagreement"] == ["pdf handling", "video encoding"]
    assert out["verdict"] == "disputed"
    assert out["verdicts"] == {"m1": "disagrees", "m2": "disagrees"}


def test_partial_agreement_flags_run_with_extra_candidate():
    out = cross_validate(MAP, [fake_client(cap("c1", "PDF handling"),
                                           cap("c2", "Video encoding")),
                               fake_client(cap("c1", "PDF handling"))],
                         ["m1", "m2"])
    assert out["agreement"] == ["pdf handling"]
    assert out["disagreement"] == ["video encoding"]
    assert out["verdict"] == "validated"
    assert out["verdicts"] == {"m1": "disagrees", "m2": "agrees"}


def test_agreement_matches_on_normalized_name_not_id():
    # different ids, differently-spelled names -> same normalized name
    out = cross_validate(MAP, [fake_client(cap("c1", "JSON Parser!")),
                               fake_client(cap("x9", "json-parser"))],
                         ["m1", "m2"])
    assert out["agreement"] == ["json parser"]
    assert out["verdict"] == "validated"
    assert out["runs"][0]["capability_ids"] == ["c1"]
    assert out["runs"][1]["capability_ids"] == ["x9"]


def test_cross_validate_requires_two_models():
    try:
        cross_validate(MAP, [fake_client(cap("c1", "x"))], ["m1"])
        assert False, "must reject <2 models"
    except ValueError:
        pass


def test_cross_validate_rejects_mismatched_clients_models():
    try:
        cross_validate(MAP, [fake_client(cap("c1", "x"))], ["m1", "m2"])
        assert False, "must reject len(clients) != len(models)"
    except ValueError:
        pass


def test_inconclusive_run_voids_agreement():
    # a model that returns zero candidates must NOT validate anything
    out = cross_validate(MAP, [fake_client(cap("c1", "PDF handling")),
                               fake_client()],  # empty capabilities
                         ["m1", "m2"])
    assert out["agreement"] == []
    assert out["verdict"] == "disputed"
    assert out["verdicts"] == {"m1": "disagrees", "m2": "inconclusive"}


# ── validate_before_registry ───────────────────────────────────────────────

def test_validate_allows_agreed_candidates():
    res = validate_before_registry([cap("c1", "PDF handling")],
                                   agreement=["pdf handling"])
    assert res["ok"] is True
    assert [c["id"] for c in res["allowed"]] == ["c1"]
    assert res["blocked"] == []


def test_validate_blocks_candidate_without_agreement():
    res = validate_before_registry([cap("c1", "PDF handling"),
                                    cap("c2", "Video encoding")],
                                   agreement=["pdf handling"])
    assert res["ok"] is False
    assert [c["id"] for c in res["allowed"]] == ["c1"]
    assert len(res["blocked"]) == 1
    assert res["blocked"][0]["candidate"]["id"] == "c2"
    assert "agreement" in res["blocked"][0]["reason"]


def test_validate_normalizes_agreement_members():
    res = validate_before_registry([cap("c1", "json parser")],
                                   agreement=["JSON Parser!"])
    assert res["ok"] is True


def test_validate_blocks_missing_name():
    res = validate_before_registry([{"id": "c1"}], agreement=["x"])
    assert res["ok"] is False
    assert "name" in res["blocked"][0]["reason"]


def test_validate_enforces_min_models_via_support():
    cand = cap("c1", "PDF handling")
    res = validate_before_registry([cand], agreement=["pdf handling"],
                                   support={"pdf handling": 1},
                                   total_models=3, min_models=2)
    assert res["ok"] is False
    assert "min_models" in res["blocked"][0]["reason"]


def test_validate_enforces_min_agreement_ratio():
    cand = cap("c1", "PDF handling")
    res = validate_before_registry([cand], agreement=["pdf handling"],
                                   support={"pdf handling": 1},
                                   total_models=3, min_models=1,
                                   min_agreement_ratio=0.5)
    assert res["ok"] is False
    assert "ratio" in res["blocked"][0]["reason"]


def test_validate_passes_with_sufficient_support():
    cand = cap("c1", "PDF handling")
    res = validate_before_registry([cand], agreement=["pdf handling"],
                                   support={"pdf handling": 2},
                                   total_models=3, min_models=2,
                                   min_agreement_ratio=0.5)
    assert res["ok"] is True
    assert [c["id"] for c in res["allowed"]] == ["c1"]


# ── router integration seam (no network) ───────────────────────────────────

def test_clients_from_router_one_per_healthy_route():
    router = Router([Route(base_url="http://a/v1", model="m1"),
                     Route(base_url="http://b/v1", model="m2")])
    clients, models = clients_from_router(router)
    assert models == ["m1", "m2"]
    assert len(clients) == 2
    assert all(callable(c) for c in clients)


def test_clients_from_router_requires_two_healthy():
    router = Router([Route(base_url="http://a/v1", model="m1"),
                     Route(base_url="http://b/v1", model="m2")])
    router.routes[1].healthy = False
    try:
        clients_from_router(router)
        assert False, "must reject <2 healthy routes"
    except RuntimeError as e:
        assert "2 healthy" in str(e)


def test_clients_from_router_refuses_deterministic_stage():
    router = Router([Route(base_url="http://a/v1", model="m1"),
                     Route(base_url="http://b/v1", model="m2")])
    try:
        clients_from_router(router, stage="compiler")
        assert False, "deterministic stage must not request LLM clients"
    except ValueError:
        pass
