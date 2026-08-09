"""HURCULES Stage 2 — deterministic repository mapper.

Produces objective repository facts WITHOUT any LLM. Deterministic: same input
commit => same output (no timestamps, no volatile fields, sorted structures).

Public seam: map_repository(repo_dir) -> dict
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from hurcules.logutil import get_logger

MAPPER_VERSION = "1.0.0"

LOG = get_logger(__name__)

LANG_BY_EXT = {
    ".py": "python", ".pyw": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".c": "c", ".h": "c",
    ".cpp": "c++", ".cc": "c++", ".hpp": "c++", ".hxx": "c++",
    ".java": "java", ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "c#",
    ".swift": "swift",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".rst": "restructuredtext",
    ".html": "html", ".css": "css",
    ".sql": "sql",
    ".scala": "scala", ".ex": "elixir", ".exs": "elixir",
    ".dart": "dart", ".lua": "lua", ".lisp": "lisp", ".clj": "clojure",
}

MANIFEST_NAMES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Cargo.toml", "go.mod", "npm-shrinkwrap.json",
}

ENTRY_POINT_NAMES = {
    "main.py", "__main__.py", "app.py", "index.js", "index.ts", "main.ts",
    "main.go", "main.rs", "cli.py",
}

DOC_NAMES = {"readme.md", "readme.rst", "readme.txt", "readme", "readme.markdown"}
DOC_DIRS = {"docs", "doc"}
TEST_DIR_NAMES = {"tests", "test", "__tests__", "spec"}
LIC_NAMES = {"license", "license.md", "license.txt", "copying", "license-mit"}
SECRET_FILENAMES = {".env", ".env.local", "id_rsa", "id_dsa", "id_ed25519",
                    "credentials", "secrets", "secret"}

TEXT_EXTS = {
    ".py", ".js", ".ts", ".go", ".c", ".cpp", ".h", ".rs", ".java", ".rb",
    ".php", ".sh", ".bash", ".json", ".yaml", ".yml", ".toml", ".md", ".html",
    ".css", ".mdx", ".rst",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".tox", ".pytest_cache", "target", "coverage", ".gradle", ".idea",
    "ego-cache", ".svn", ".hg", ".next",
}
SKIP_FILES = {"package-lock.json", "yarn.lock", "bun.lock", "Cargo.lock",
              "poetry.lock", "Pipfile.lock", "composer.lock", "Gemfile.lock"}

# dangerous-content patterns: (regex, reason)
DANGEROUS_PATTERNS = [
    (r"\beval\s*\(", "dynamic-execution"),
    (r"\bexec\s*\(", "dynamic-execution"),
    (r"\bsubprocess\b", "subprocess-usage"),
    (r"os\.system", "shell-exec"),
    (r"shell\s*=\s*True", "shell-exec"),
    (r"(curl|wget)\s+[^\n]*\|\s*(sh|bash)", "pipe-to-shell"),
    (r"BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY", "embedded-private-key"),
    (r"AKIA[0-9A-Z]{16}", "aws-access-key"),
    (r"\bghp_[A-Za-z0-9]{36}\b", "github-token"),
    (r"\bsk-[A-Za-z0-9]{20,}\b", "api-key-pattern"),
]
SECRET_REF_WORDS = ["api_key", "api-key", "private_key", "access_token", "secret"]

def _is_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]

def map_repository(repo_dir: str) -> dict:
    LOG.info("map start repo_dir=%s", repo_dir)
    root = Path(repo_dir)
    if not root.is_dir():
        raise ValueError(f"not a directory: {repo_dir}")

    file_tree: list[str] = []
    languages: dict[str, int] = {}
    manifests: list[str] = []
    entry_points: list[str] = []
    doc_files: list[str] = []
    test_files: list[str] = []
    license_files: list[str] = []
    secret_files: list[str] = []
    found_secret_refs: list[str] = []
    risk_flags: list[dict] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for fn in sorted(filenames):
            rel_path = Path(dirpath).relative_to(root) / fn
            rel = rel_path.as_posix()
            low = rel.lower()
            low_fn = fn.lower()
            ext = Path(fn).suffix.lower()

            if low_fn in SKIP_FILES:
                continue
            file_tree.append(rel)

            lang = LANG_BY_EXT.get(ext)
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            if low_fn in MANIFEST_NAMES:
                manifests.append(rel)
            if low_fn in ENTRY_POINT_NAMES:
                entry_points.append(rel)
            if low_fn in DOC_NAMES or any(p.lower() in DOC_DIRS for p in rel_path.parts):
                doc_files.append(rel)
            if any(p.lower() in TEST_DIR_NAMES for p in rel_path.parts) or \
               (low_fn.startswith(("test_", "test-"))
                and ext in {".py", ".js", ".ts", ".rs", ".go"}):
                test_files.append(rel)
            if low_fn in LIC_NAMES:
                license_files.append(rel)
            if low_fn in SECRET_FILENAMES:
                secret_files.append(rel)

            full = root / rel_path
            try:
                if full.is_file() and full.stat().st_size < 500_000 and ext in TEXT_EXTS:
                    data = full.read_bytes()
                    if _is_binary(data):
                        continue
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    low_text = text.lower()
                    for pat, reason in DANGEROUS_PATTERNS:
                        if re.search(pat, low_text):
                            risk_flags.append({"file": rel, "reason": reason})
                    for word in SECRET_REF_WORDS:
                        if word in low_text:
                            risk_flags.append({"file": rel, "reason": "secret-reference"})
                            break
            except OSError:
                continue

    # dedupe risks preserving a stable order
    seen: set[tuple[str, str]] = set()
    unique_risks = []
    for r in sorted(risk_flags, key=lambda r: (r["file"], r["reason"])):
        key = (r["file"], r["reason"])
        if key not in seen:
            seen.add(key)
            unique_risks.append(r)

    LOG.info("map complete files=%d langs=%s",
             len(file_tree), ",".join(sorted(languages)))
    return {
        "schema": "hurcules.repo-map",
        "schema_version": MAPPER_VERSION,
        "repository": str(root),
        "file_count": len(file_tree),
        "file_tree": sorted(file_tree),
        "languages": dict(sorted(languages.items(), key=lambda kv: (-kv[1], kv[0]))),
        "dependency_manifests": sorted(manifests),
        "entry_points": sorted(entry_points),
        "documentation_files": sorted(doc_files),
        "test_files": sorted(test_files),
        "license_files": sorted(license_files),
        "secret_file_locations": sorted(secret_files),
        "risk_flags": unique_risks,
    }