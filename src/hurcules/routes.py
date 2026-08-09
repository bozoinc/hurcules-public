"""HURCULES W1-[1] — LLM route policy, failover, and quality floor.

The pilot's failure mode: when the free route was down it fell back to a weak
local 1.5B model and produced `capabilities: []` — a SILENT, indistinguishable
"valid empty package". This module fixes that at three layers:

1. Route policy  — an ordered list of OpenAI-compatible routes (base_url +
   model) with an active health probe. Deterministic stages are refused.
2. Failover      — a routing client tries healthy routes in priority order and
   only surfaces an error (never a silent empty) when ALL routes fail.
3. Quality floor — ExtractionFloor judges every response: empty or unparseable
   output is marked INCONCLUSIVE, never recorded as a valid empty package.

Public seam:
  Router.from_env()  -> Router with OmniRoute free-route defaults
  router.client_for("analyst") -> callable routing client (like make_openai_client)
  ExtractionFloor().judge(raw, candidates) -> record with .conclusion
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Non-deterministic stages may request an LLM client.
LLM_STAGES = {"analyst", "advocate", "judge", "cross_model", "gold_judge"}

OPENAI_COMPAT_KEY = "x-api-key"  # OmniRoute proxy accepts Bearer; keep simple


class RouteDown(RuntimeError):
    """A specific route was attempted and failed (transient retries exhausted
    or a non-transient error). The route is marked unhealthy; callers fail over
    to the next route."""


class NoHealthyRoute(RuntimeError):
    """No healthy LLM route exists to serve the request."""


def classify_http_error(e: Exception) -> str:
    """Pure, deterministic error classification for the retry policy.

    Inspects only the exception type and any ``code``/``status`` attribute —
    no network, no I/O — so it is unit-testable in isolation.

    Returns:
        "transient"      — HTTP 429 / 5xx, timeouts, URLError: retry same route
        "non_transient"  — HTTP 4xx (except 429), invalid response JSON: fail over
        "unknown"        — anything else: do not retry
    """
    status = getattr(e, "code", None)
    if status is None:
        status = getattr(e, "status", None)
    if status is not None:
        status = int(status)
        if status == 429 or 500 <= status < 600:
            return "transient"
        if 400 <= status < 500:
            return "non_transient"
    if isinstance(e, (TimeoutError, urllib.error.URLError)):
        return "transient"
    if isinstance(e, json.JSONDecodeError):
        return "non_transient"
    return "unknown"


def _exponential_backoff(attempt: int) -> float:
    """Default backoff schedule: base 0.5s, factor 2 -> 0.5, 1.0, 2.0, ..."""
    return 0.5 * (2 ** attempt)


def _default_key_file() -> Path:
    """Where to look for the Hermes/OmniRoute key, portably.

    HURCULES_KEY_FILE env overrides; otherwise `~/.hermes/mem0.json` (home-
    relative, not an absolute personal path). Missing file -> empty key, the
    tool degrades gracefully (works for a local proxy needing no auth).
    """
    raw = os.environ.get("HURCULES_KEY_FILE", "")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes" / "mem0.json"


def _default_key() -> str:
    try:
        j = json.load(open(_default_key_file()))
        return j["oss"]["llm"]["config"]["api_key"]
    except Exception:
        return ""


@dataclass
class Route:
    base_url: str
    model: str
    api_key: str = ""
    healthy: bool = True
    last_error: str = ""

    @classmethod
    def from_config(cls, cfg: dict) -> "Route":
        return cls(
            base_url=cfg["base_url"],
            model=cfg["model"],
            api_key=cfg.get("api_key", ""),
        )

    def to_config(self) -> dict:
        return {"base_url": self.base_url, "model": self.model}


def default_routes() -> list[Route]:
    """OmniRoute free-route priority list (no local hardware)."""
    base = os.environ.get("HURCULES_BASE", "http://127.0.0.1:20128/v1")
    key = os.environ.get("HURCULES_API_KEY", "") or _default_key()
    models = os.environ.get(
        "HURCULES_MODELS",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free,"
        "openrouter/nemotron-super/ultra:free,"
        "oc/deepseek-v4-flash-free",
    ).split(",")
    return [Route(base_url=base, model=m.strip(), api_key=key) for m in models if m.strip()]


def _probe_route(base_url: str, api_key: str, timeout: float = 6.0) -> bool:
    """Active health probe: GET /models succeeds => route reachable."""
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/models",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        # OmniRoute /models returns {"object":"list","data":[...]}; OpenAI-
        # compatible proxies may return {"models":[...]}. Accept either.
        if isinstance(data, dict):
            return bool(data.get("data") or data.get("models"))
        return bool(data)
    except Exception:
        return False


class RoutingClient:
    """Callable LLM client with per-call failover across healthy routes.

    Satisfies the same contract as analyst.make_openai_client: call(messages)
    -> str. Adds `route` (the Route that served the last call) and `chat`
    (the raw callable) so the ledger/caller can read provenance.
    """

    def __init__(self, routes: list[Route],
                 probe_fn: Callable[[str, str], bool] = _probe_route,
                 timeout: float = 300.0, max_empty_tries: int = 1,
                 max_retries: int = 2,
                 backoff: Optional[Callable[[int], float]] = None):
        self.routes = routes
        self._probe_fn = probe_fn
        self._timeout = timeout
        self._max_empty_tries = max_empty_tries
        self.max_retries = max_retries
        self.backoff = backoff if backoff is not None else _exponential_backoff
        self.route: Optional[Route] = None

    def __call__(self, messages: list[dict]) -> str:
        return self.chat(messages)

    def _call_once(self, route: Route, messages: list[dict]) -> Optional[str]:
        """Single HTTP attempt against one route.

        Returns the content string, or None for an empty payload (a quality
        floor call, not a health failure). Raises on network/HTTP error; the
        retry decision belongs to the caller (``_attempt_route``).
        """
        body = json.dumps({
            "model": route.model, "messages": messages,
            "stream": False, "temperature": 0.2,
        }).encode()
        req = urllib.request.Request(
            f"{route.base_url.rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {route.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.load(resp)
        raw = data["choices"][0]["message"]["content"]
        if raw is None or not raw.strip():
            return None  # empty payload is not a health failure
        return raw

    def _attempt_route(self, route: Route, messages: list[dict]) -> Optional[str]:
        """Full attempt on one route: first call, then transient retries with
        backoff up to ``max_retries``.

        Returns content, or None for empty payloads (route stays healthy, the
        caller moves on). On failure (retries exhausted or a non-transient
        error) the route is marked unhealthy and ``RouteDown`` is raised.
        """
        try:
            return self._call_once(route, messages)
        except Exception as e:
            route.last_error = str(e)
            if classify_http_error(e) != "transient":
                # non-transient -> failover immediately, no retry
                route.healthy = False
                raise RouteDown(f"{route.model}: {e}") from e
            last_exc = e
            for attempt in range(self.max_retries):
                time.sleep(self.backoff(attempt))
                try:
                    return self._call_once(route, messages)
                except Exception as e2:
                    route.last_error = str(e2)
                    last_exc = e2
                    if classify_http_error(e2) != "transient":
                        break
            route.healthy = False
            raise RouteDown(f"{route.model}: {last_exc}") from last_exc

    def chat(self, messages: list[dict]) -> str:
        candidates = [r for r in self.routes if r.healthy]
        if not candidates:
            raise NoHealthyRoute("no healthy LLM route available")
        last_err = ""
        for _ in range(self._max_empty_tries):
            for r in candidates:
                try:
                    raw = self._attempt_route(r, messages)
                except RouteDown as rd:
                    last_err = str(rd)
                    continue  # failover to next route
                if raw is None:
                    last_err = f"{r.model}: empty response"
                    continue  # next route (route stays healthy)
                self.route = r
                return raw
            # all routes failed this round; probe downed routes once
            for r in self.routes:
                if not r.healthy:
                    try:
                        r.healthy = self._probe_fn(r.base_url, r.api_key)
                    except Exception:
                        r.healthy = False
        raise NoHealthyRoute(f"all LLM routes failed ({last_err})")


@dataclass
class ExtractionFloorRecord:
    conclusion: str          # "ok" | "inconclusive"
    empty: bool
    unparseable: bool = False
    candidates_count: int = 0
    marker: str = "INCONCLUSIVE"


class ExtractionFloor:
    """Quality floor: an empty/unparseable result is INCONCLUSIVE, never OK.

    Mirrors the pilot rule: a weak model returning nothing must not be recorded
    as a valid package with zero capabilities. Downstream must treat a
    conclusion != "ok" as a failed/indeterminate run, not an empty pass.
    """

    def __init__(self, empty_marker: str = "INCONCLUSIVE"):
        self.marker = empty_marker

    def judge(self, raw: str, candidates: list) -> ExtractionFloorRecord:
        empty = raw is None or not raw.strip()
        unparseable = False
        count = len(candidates or [])
        if not empty:
            try:
                start, end = raw.find("{"), raw.rfind("}")
                if start == -1 or end == -1 or end <= start:
                    unparseable = True
                else:
                    json.loads(raw[start:end + 1])
            except Exception:
                unparseable = True
        if empty or unparseable or count == 0:
            return ExtractionFloorRecord(
                conclusion="inconclusive", empty=empty,
                unparseable=unparseable, candidates_count=count,
                marker=self.marker)
        return ExtractionFloorRecord(
            conclusion="ok", empty=False, candidates_count=count)


class Router:
    """Holds routes + per-stage selection policy + health probing."""

    def __init__(self, routes: Optional[list[Route]] = None,
                 probe_fn: Callable[[str, str], bool] = _probe_route):
        self.routes = routes if routes is not None else default_routes()
        self._probe_fn = probe_fn

    @classmethod
    def from_env(cls) -> "Router":
        return cls(default_routes())

    def probe(self) -> dict:
        health = {}
        for r in self.routes:
            ok = self._probe_fn(r.base_url, r.api_key)
            r.healthy = ok
            health[r.base_url] = ok
        return health

    def healthy_routes(self) -> list[Route]:
        return [r for r in self.routes if r.healthy]

    def client_for(self, stage: str) -> RoutingClient:
        if stage not in LLM_STAGES:
            raise ValueError(
                f"stage {stage!r} is deterministic and must not request an LLM "
                "client (analyst/advocate/judge/cross_model only)")
        healthy = self.healthy_routes()
        if not healthy:
            raise NoHealthyRoute(
                "no healthy LLM route available"
                f" (checked {[r.model for r in self.routes]})")
        client = RoutingClient(self.routes, probe_fn=self._probe_fn)
        client.route = healthy[0]  # pin provenance up-front
        return client