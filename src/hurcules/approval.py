"""HURCULES Wave 3 — D4 Approval Artifacts (deterministic, auditable).

The D4 approval ritual bundles four required parts into ONE signed,
recorded artifact per registry entry (one audit trail per spawn decision):

  1. eval        — the evaluation result dict (verdict matrix)
  2. summary     — human-readable description of what the capability does
  3. provenance  — repo / commit / registry-entry data
  4. live_demo   — evidence the demo actually ran (short log / fingerprint)

Everything here is stdlib and deterministic. The "signature" is an audit
HMAC-style digest (sha256 over content+"|"+approver), NOT real public-key
cryptography — it makes tampering detectable against casual/accidental
changes, not dispute-proof against an attacker holding the registry on disk.

Storage assumption (record_approval): the signed artifact is stored under
`entry["approval_artifact"]` as:

    {
        "artifact": <signed artifact dict>,
        "digest":   <sha256 of the artifact content>,
        "verified": True,
    }

require_approval_before_spawn — the spawn gate — reads exactly this shape.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

FOUR_PART_KEYS = {"eval", "summary", "provenance", "live_demo"}
SCHEMA = "hurcules.approval-artifact-v1"

# Signing fields are excluded from the content digest so the fingerprint is
# stable whether the artifact is signed or not, and any change to one of the
# four parts (or schema/metadata) breaks verification.
_SIGN_FIELDS = ("approver", "signature")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_empty(value) -> bool:
    """True when a required part is missing or empty (None/"", [], {}, ...)."""
    if value is None:
        return True
    if isinstance(value, (str, list, dict, tuple, set)):
        return len(value) == 0
    return False


def build_artifact(eval_result, summary, provenance, live_demo,
                   metadata=None) -> dict:
    """Bundle the four required D4 parts into one artifact dict.

    Raises ValueError if any of the four parts is missing or empty.
    `metadata` (optional) is carried through verbatim — e.g. fleet spec id,
    task id, or review notes — but is not one of the four required parts.
    """
    parts = {
        "eval": eval_result,
        "summary": summary,
        "provenance": provenance,
        "live_demo": live_demo,
    }
    for key in FOUR_PART_KEYS:
        if _is_empty(parts[key]):
            raise ValueError(
                f"approval artifact missing required part {key!r}")
    artifact = dict(parts)
    artifact["schema"] = SCHEMA
    artifact["created_at"] = _now()
    if metadata is not None:
        artifact["metadata"] = metadata
    return artifact


def _content(artifact: dict) -> dict:
    """Artifact without the signing fields — the canonical signed payload."""
    return {k: v for k, v in artifact.items() if k not in _SIGN_FIELDS}


def digest(artifact: dict) -> str:
    """Deterministic sha256 over the canonical JSON of the artifact content.

    sort_keys + compact separators make key order irrelevant; approver and
    signature never affect the digest.
    """
    canonical = json.dumps(_content(artifact), sort_keys=True,
                           separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign_artifact(artifact: dict, approver: str, key: str | None = None) -> dict:
    """Return a copy of the artifact carrying approver + audit signature.

    Audit HMAC-style signature = sha256(digest + "|" + approver), with an
    optional `key` salt for tests. Deterministic and tamper-evident; NOT
    real PKI — for internal audit trail use, documented honestly. Note:
    verify_signature (and therefore the spawn gate) uses key=None, so a
    keyed signature will not verify by default — callers using a key must
    handle it consistently (tests only).
    """
    signed = dict(artifact)
    signed["approver"] = approver
    base = digest(artifact) + "|" + approver
    if key is not None:
        base += "|" + key
    signed["signature"] = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return signed


def verify_signature(artifact: dict) -> bool:
    """Recompute the signature and compare against the stored one."""
    approver = artifact.get("approver")
    signature = artifact.get("signature")
    if not approver or not signature:
        return False
    expected = hashlib.sha256(
        (digest(artifact) + "|" + approver).encode("utf-8")
    ).hexdigest()
    return expected == signature


def _lookup_entry(registry, entry_id: str) -> dict:
    """Resolve an entry from a Registry instance (get()) or a plain dict."""
    entry = registry.get(entry_id)
    if not isinstance(entry, dict):
        raise KeyError(f"no registry entry {entry_id}")
    return entry


def record_approval(registry, entry_id: str, artifact: dict,
                    approver: str) -> dict:
    """Attach a signed approval artifact to a registry entry.

    Mutates the entry in place (via registry._entries / _persist when the
    registry is a Registry instance, else a plain dict of entries) and
    returns the updated entry. Raises KeyError if the entry is missing.
    """
    entry = _lookup_entry(registry, entry_id)
    signed = sign_artifact(artifact, approver)
    entry["approval_artifact"] = {
        "artifact": signed,
        "digest": digest(signed),
        "verified": verify_signature(signed),
    }
    if hasattr(registry, "_persist"):
        registry._persist()
    return entry


def require_approval_before_spawn(registry, entry_id: str) -> bool:
    """The spawn gate. True only for a fully approved, verifiable entry.

    Conditions — ALL required:
      - entry exists
      - status == "approved"
      - an approval_artifact is present
      - its signature verifies (digest matches, nothing tampered)
    """
    entry = registry.get(entry_id)
    if not isinstance(entry, dict):
        return False
    if entry.get("status") != "approved":
        return False
    aa = entry.get("approval_artifact")
    if not isinstance(aa, dict):
        return False
    artifact = aa.get("artifact")
    if not isinstance(artifact, dict):
        return False
    return verify_signature(artifact)