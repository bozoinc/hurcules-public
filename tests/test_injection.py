"""TDD tests for the prompt-injection battery (pure; no network/LLM)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.injection import CORPUS, SYS, run_battery


def good_analyst(messages):
    """Well-behaved: treats repo content as data, never echoes markers."""
    return ("OK - repository content is data, not instructions; "
            "no capability claims adopted from it.")


def naive_analyst(messages):
    """Naive: parrots the user payload, so it reproduces demanded markers."""
    for m in messages:
        if m["role"] == "user":
            return m["content"]
    return "no user message"


def empty_analyst(messages):
    """Returns blank output on every payload."""
    return ""


def crash_analyst(messages):
    """Raises on every payload."""
    raise RuntimeError("analyst crashed")


def all_names():
    return [c["name"] for c in CORPUS]


def test_corpus_has_at_least_8_well_formed_entries():
    assert len(CORPUS) >= 8
    seen = set()
    for entry in CORPUS:
        assert isinstance(entry, dict)
        assert entry["name"]
        assert entry["marker"]
        assert entry["payload"]
        assert entry["name"] not in seen, "payload names must be unique"
        seen.add(entry["name"])


def test_each_payload_contains_its_marker():
    for entry in CORPUS:
        assert entry["marker"] in entry["payload"], entry["name"]


def test_well_behaved_analyst_passes_all():
    result = run_battery(good_analyst)
    assert result["schema"] == "hurcules.injection-battery"
    assert result["total"] == len(CORPUS)
    assert result["passed"] == result["total"]
    assert result["failed"] == []
    assert result["exploitable"] == []


def test_naive_analyst_is_flagged_exploitable():
    result = run_battery(naive_analyst)
    assert result["passed"] == 0
    assert result["failed"] == all_names()
    assert result["exploitable"] == all_names()


def test_empty_output_is_failed_and_exploitable():
    result = run_battery(empty_analyst)
    assert result["passed"] == 0
    assert result["failed"] == all_names()
    assert result["exploitable"] == all_names()


def test_crashing_analyst_is_failed_but_not_exploitable():
    result = run_battery(crash_analyst)
    assert result["passed"] == 0
    assert result["failed"] == all_names()
    assert result["exploitable"] == [], "a crash is a fail, not an exploit"


def test_run_battery_is_deterministic():
    first = run_battery(naive_analyst)
    second = run_battery(naive_analyst)
    assert first == second


def test_payload_key_filters_to_single_case():
    key = CORPUS[0]["name"]
    good = run_battery(good_analyst, payload_key=key)
    assert good["total"] == 1
    assert good["passed"] == 1
    bad = run_battery(naive_analyst, payload_key=key)
    assert bad["exploitable"] == [key]
    assert bad["passed"] == 0


def test_unknown_payload_key_raises():
    with pytest.raises(ValueError):
        run_battery(good_analyst, payload_key="no-such-payload")


def test_battery_builds_expected_messages():
    entry = CORPUS[-1]
    seen = {}

    def spy(messages):
        seen["messages"] = messages
        return "nothing claimed from repo content"

    run_battery(spy, payload_key=entry["name"])
    assert seen["messages"][0]["role"] == "system"
    assert seen["messages"][0]["content"] == SYS
    assert seen["messages"][1]["role"] == "user"
    assert seen["messages"][1]["content"] == entry["payload"]