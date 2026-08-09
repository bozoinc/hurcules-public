#!/usr/bin/env python3
"""HURCULES CLI — the real-user front door to the ingestion pipeline.

KISS, stdlib only (argparse + importlib). The heavy logic lives in the
pipeline modules under src/hurcules/ and the run-harness scripts under
scripts/; this CLI is a thin honest wrapper. The discovery-to-pipeline
harness is reused AS-IS by importlib (no fork, no edit).

Usage:
  hurcules --version
  hurcules ingest --repo owner/name [--clones DIR]
  hurcules ceiling [case_id,...]    # surface only, not yet wired
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# Repo root = src/hurcules/cli.py -> src/hurcules -> src -> repo root
ROOT = Path(__file__).resolve().parent.parent.parent

CLI_VERSION = "0.7.0"


def _load_script(name):
    """Load a scripts/<name>.py module by path (no import side effects)."""
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot create module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cmd_ingest(args) -> int:
    """Clone then run the full ingestion chain for ONE repo (same as gold)."""
    try:
        pipeline = _load_script("discovery_to_pipeline")
    except Exception as e:  # hostile-by-default: fail loudly, honestly
        print(f"could not load scripts/discovery_to_pipeline.py: {e}")
        return 1
    out_dir = ROOT / "data" / "stage4-packages"
    clone_root = Path(args.clones) if args.clones else Path("/tmp/hurcules-discovery")
    clone_root.mkdir(parents=True, exist_ok=True)
    result = pipeline.ingest(args.repo, out_dir, clone_root)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def _cmd_ceiling(args) -> int:
    # Honest CLI surface: the harness exists but is not wired to this CLI yet.
    print("ceiling: not yet wired — run scripts/run_gold_ceiling.py directly "
          "(e.g. python3 scripts/run_gold_ceiling.py [case_id,...])")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="hurcules", description="HURCULES pipeline CLI")
    ap.add_argument("--version", action="store_true", help="print version and exit")
    sub = ap.add_subparsers(dest="subcommand")

    p_ingest = sub.add_parser("ingest", help="run the full ingestion pipeline "
                                             "for one repo")
    p_ingest.add_argument("--repo", required=True,
                          help="owner/name of the public GitHub repo")
    p_ingest.add_argument("--clones", default=None,
                          help="clone root dir (default /tmp/hurcules-discovery)")
    p_ingest.set_defaults(func=_cmd_ingest)

    p_ceil = sub.add_parser("ceiling", help="gold-set extraction ceiling "
                                            "(CLI surface only)")
    p_ceil.add_argument("case_args", nargs="*", metavar="case_id,...",
                        help="optional gold case ids")
    p_ceil.set_defaults(func=_cmd_ceiling)

    return ap


def main(argv=None) -> int:
    """CLI entry point. Accepts an optional argv list for testability."""
    ap = _build_parser()
    args = ap.parse_args(argv)
    if args.version:
        print(CLI_VERSION)
        return 0
    if getattr(args, "func", None):
        return args.func(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())