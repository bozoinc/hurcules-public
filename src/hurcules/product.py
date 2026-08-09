"""HURCULES Stage 10 — Productisation foundation (10.1, 10.5, 10.6, gate).

Buildable-now pieces of productisation, laid as a foundation for full SaaS:

  - capability marketplace (10.5/10.6): approved capabilities exposed as
    listable, shareable products with provenance + license posture.
  - org/account shell (10.1): orgs that can adopt capabilities; NO auth backend
    yet (that's a real infra task, flagged below) — just the data model.
  - readiness gate (exit gate): the product owner's go/no-go facts, with no vanity metrics.

Honest scope: this lays the product data model + decision report. Real external
auth, billing, hosted dashboards are deliberately NOT stubbed as fake "done" —
they are listed as blockers for full product readiness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

PRODUCT_VERSION = "1.0.0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Marketplace capability (shareable approved capability, with provenance)
# ---------------------------------------------------------------------------

@dataclass
class ProductCapability:
    capability_id: str
    name: str
    ontology_type: str
    confidence: float
    registry_entry: str
    package: str
    commit_sha: str
    license_posture: str = "unknown"   # permissive/restrictive/unknown

    def to_dict(self) -> dict:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "ontology_type": self.ontology_type,
            "confidence": self.confidence,
            "registry_entry": self.registry_entry,
            "package": self.package,
            "commit_sha": self.commit_sha,
            "license_posture": self.license_posture,
        }


def marketplace(registry, package_licenses: dict[str, str] | None = None) -> list[dict]:
    """Approved capabilities as listable marketplace products (provenanced)."""
    lic = package_licenses or {}
    caps = []
    for entry in registry.list(status="approved"):
        posture = "unknown"
        for name, lic_val in lic.items():
            if name == entry.get("pkg_id"):
                posture = lic_val
        for c in entry.get("capabilities", []):
            caps.append(ProductCapability(
                capability_id=c.get("id"),
                name=c.get("name"),
                ontology_type=c.get("ontology_type"),
                confidence=c.get("confidence"),
                registry_entry=entry.get("entry_id"),
                package=entry.get("pkg_id"),
                commit_sha=entry.get("commit_sha", ""),
                license_posture=posture,
            ).to_dict())
    return caps


# ---------------------------------------------------------------------------
# Org shell (10.1) — data model only (auth backend is a real-infra blocker)
# ---------------------------------------------------------------------------

@dataclass
class Org:
    org_id: str
    name: str
    created_at: str = field(default_factory=_now)
    licenses: set[str] = field(default_factory=set)

    def grant(self, license_key: str) -> None:
        self.licenses.add(license_key)


def new_org(org_id: str, name: str) -> Org:
    return Org(org_id=org_id, name=name)


# ---------------------------------------------------------------------------
# Product readiness gate (the product owner's go/no-go)
# ---------------------------------------------------------------------------

def readiness_report(moat: dict, *, minimum_caps: int = 10) -> dict:
    """Product-readiness decision facts for the product owner. Honest: flags real blockers.

    Uses capability counts as a signal, never as the sole "success" proof.
    Readiness => the owner's explicit decision, not an auto-greenlight.
    """
    assets = moat.get("assets", {})
    approved_caps = assets.get("approved_capabilities", 0)
    caps_ok = approved_caps >= minimum_caps

    blockers = []
    if not caps_ok:
        blockers.append(f"only {approved_caps} approved capabilities "
                        f"(need >= {minimum_caps})")
    # hard infra blockers that we deliberately have NOT built/faked
    blockers += [
        "auth/user backend not implemented (10.1)",
        "private-repo ingestion not implemented (10.2)",
        "billing/marketplace not implemented (10.6)",
    ]

    return {
        "schema": "hurcules.product-readiness-v1",
        "product_version": PRODUCT_VERSION,
        "generated_at": _now(),
        "approved_capabilities": approved_caps,
        "capability_threshold_met": caps_ok,
        "at_capability_gate": caps_ok,
        "blockers": blockers,
        "verdict": "Owner decides — evidence above; blockers listed for honest scoping",
        "vanity_metric_warning": "capability count alone != product success (SUB-GOALS)",
    }