"""HURCULES stdlib logging helper — single point of logging configuration.

One shared format and level for the whole package:
  format:  "%(asctime)s %(levelname)s %(name)s %(message)s"
  level:   HURCULES_LOG_LEVEL env var (DEBUG/INFO/WARNING/ERROR),
           default WARNING.

Idempotent: the root/basic configuration is applied at most ONCE per
process (module-state guard), so importing modules never reconfigures
logging. Each logger handed out is pinned to the resolved level, so the
level semantics hold even when an embedding host (e.g. pytest) has already
attached its own root handlers.
"""
from __future__ import annotations

import logging
import os

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_DEFAULT_LEVEL = logging.WARNING
_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

_configured = False
_level: int | None = None


def _resolve_level() -> int:
    """Resolve the effective level once (env read happens at first use)."""
    global _level
    if _level is None:
        raw = os.environ.get("HURCULES_LOG_LEVEL", "").upper()
        _level = _LEVELS.get(raw, _DEFAULT_LEVEL)
    return _level


def get_logger(name: str) -> logging.Logger:
    """Return a HURCULES logger with the shared format and resolved level.

    The root/basic configuration (format + level) is applied exactly once
    per process; later calls reuse it. Each returned logger is explicitly
    pinned to the resolved level for deterministic behavior.
    """
    global _configured
    if not _configured:
        logging.basicConfig(format=_LOG_FORMAT, level=_resolve_level())
        _configured = True
    logger = logging.getLogger(name)
    logger.setLevel(_resolve_level())
    return logger