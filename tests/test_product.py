"""TDD tests for Stage 10 productisation foundation (moat + product)."""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from hurcules.registry import Registry
from hurcules.moat import inventory
from hurcules.product import marketplace, new_org, readiness_report, ProductCapability, Org

PKG = {
    "provenance": {"repository": "owner/repo", "commit_sha": "deadbeef"},
    "capabilities": [
        {"id": "c1", "name": "Market research", "ontology_type": "TOOL", "confidence": 0.9},
        {"id": "c2", "name": "Workflow executor", "ontology_type": "WORKFLOW", "confidence": 0.85},
    ],
}


def _approved(tmpdir):
    r = Registry(os.path.join(tmpdir, "reg.json"))
    e = r.register(PKG)
    r.approve(e["entry_id"], "owner")
    return r


# ---------------------------------------------------------------------------
# Moat inventory
# ---------------------------------------------------------------------------


def test_moat_inventory_reads_real_data():
    root = Path(os.path.join(os.path.dirname(__file__), ".."))
    moat = inventory(root)
    assets = moat["assets"]
    # registry entry present, capacities counted (no vanity = counts only, no claim)
    assert moat["schema"] == "hurcules.moat-inventory-v1"
    assert "total_capabilities" in assets
    assert assets["total_capabilities"] > 0
    assert "gold_corpus" in assets


def test_moat_empty_tree():
    with tempfile.TemporaryDirectory() as td:
        inv = inventory(Path(td))
        assert inv["assets"]["total_capabilities"] == 0
        assert inv["assets"]["approved_capabilities"] == 0


def test_moat_high_value_assets_flag():
    with tempfile.TemporaryDirectory() as td:
        inv = inventory(Path(td), high_value=["provenance-graph", "evaluation-library"])
        assert inv["assets"]["high_value_assets"] == ["provenance-graph", "evaluation-library"]


# ---------------------------------------------------------------------------
# Marketplace (10.5/10.6)
# ---------------------------------------------------------------------------


def test_marketplace_lists_only_approved():
    with tempfile.TemporaryDirectory() as td:
        r = Registry(os.path.join(td, "reg.json"))
        r.register(PKG)  # candidate only
        assert marketplace(r) == []
        e = r.register(PKG)  # register again then approve
        r.approve(e["entry_id"], "owner")
        caps = marketplace(r)
        assert len(caps) == 2


def test_marketplace_carries_provenance_and_license():
    with tempfile.TemporaryDirectory() as td:
        r = _approved(td)
        caps = marketplace(r, package_licenses={"owner/repo": "permissive"})
        assert len(caps) == 2
        for c in caps:
            assert c["commit_sha"] == "deadbeef"
            assert c["package"] == "owner/repo"
            assert c["license_posture"] == "permissive"
            assert c["registry_entry"]


def test_product_capability_to_dict():
    pc = ProductCapability("c1", "Research", "TOOL", 0.9, "e1", "p", "sha",
                           "permissive")
    d = pc.to_dict()
    assert d["capability_id"] == "c1" and d["commit_sha"] == "sha"


# ---------------------------------------------------------------------------
# Org shell (10.1)
# ---------------------------------------------------------------------------


def test_org_shell_grant_license():
    org = new_org("acme", "Acme Corp")
    assert isinstance(org, Org)
    org.grant("license-A")
    assert "license-A" in org.licenses


# ---------------------------------------------------------------------------
# Readiness gate (honest blockers, no vanity metric)
# ---------------------------------------------------------------------------


def test_readiness_blocks_when_few_caps():
    from hurcules.product import readiness_report
    moat = {"assets": {"approved_capabilities": 3}}
    rpt = readiness_report(moat, minimum_caps=50)
    assert rpt["capability_threshold_met"] is False
    assert rpt["verdict"].startswith("Owner decides")
    assert rpt["vanity_metric_warning"]


def test_readiness_and_threshold_reflects_caps():
    moat = {"assets": {"approved_capabilities": 30}}
    rpt = readiness_report(moat, minimum_caps=10)
    assert rpt["capability_threshold_met"] is True


def test_readiness_never_auto_greenlights():
    rpt = readiness_report({"assets": {"approved_capabilities": 999}}, minimum_caps=10)
    # even with plentiful caps, verdict is the owner's call, and hard blockers remain
    assert rpt["verdict"].startswith("Owner decides")
    assert rpt["at_capability_gate"] is True
    assert any("auth" in b for b in rpt["blockers"])


def test_readiness_lists_honest_blockers():
    rpt = readiness_report({"assets": {"approved_capabilities": 15}}, minimum_caps=10)
    joined = " ".join(rpt["blockers"])
    assert "auth" in joined
    assert "private-repo" in joined
    assert "billing" in joined