"""TDD tests for W1-[1] — LLM route policy, failover, quality floor."""

import pytest
from hurcules.routes import (
    Route, Router, RoutingClient, ExtractionFloor,
    NoHealthyRoute, classify_http_error,
)


def _route(base="http://a/v1", model="m1", key="k"):
    return Route(base_url=base, model=model, api_key=key)


def _ok_client(body):
    def chat(messages):
        return body
    return chat


def test_route_holds_fields():
    r = _route()
    assert r.base_url == "http://a/v1"
    assert r.model == "m1"
    assert r.api_key == "k"
    assert r.healthy is True


def test_router_probe_marks_down_route():
    def probe(base, key):
        return base != "http://bad/v1"
    router = Router(
        [_route("http://good/v1", "m1"), _route("http://bad/v1", "m2")],
        probe_fn=probe,
    )
    health = router.probe()
    assert health["http://good/v1"] is True
    assert health["http://bad/v1"] is False
    assert router.routes[1].healthy is False


def test_router_selects_first_healthy():
    router = Router([_route("http://a/v1", "m1"), _route("http://b/v1", "m2")])
    router.routes[1].healthy = False
    assert router.client_for("analyst").route is router.routes[0]


def test_router_failover_picks_next_healthy():
    router = Router([_route("http://a/v1", "m1"), _route("http://b/v1", "m2")])
    router.routes[0].healthy = False
    c = router.client_for("analyst")
    assert c.route is router.routes[1]


def test_router_no_healthy_raises():
    router = Router([_route("http://a/v1", "m1")])
    router.routes[0].healthy = False
    with pytest.raises(NoHealthyRoute) as e:
        router.client_for("analyst")
    assert "no healthy" in str(e.value)


def test_stage_selection_uses_stage_policy():
    # per-stage model selection: analyst may allow multiple models,
    # compiler is deterministic (no LLM) -> error if requested
    router = Router([_route("http://a/v1", "m1")])
    with pytest.raises(ValueError) as e:
        router.client_for("compiler")
    assert "compiler" in str(e.value)  # deterministic stage must not request LLM


def test_empty_extraction_marked_inconclusive():
    floor = ExtractionFloor(empty_marker="INCONCLUSIVE")
    raw = ""
    rec = floor.judge(raw=raw, candidates=[])
    assert rec.conclusion == "inconclusive"
    assert rec.empty is True


def test_nonempty_extraction_ok():
    floor = ExtractionFloor(empty_marker="INCONCLUSIVE")
    rec = floor.judge(raw='{"capabilities":[{"id":"c1"}]}', candidates=[{"id": "c1"}])
    assert rec.conclusion == "ok"
    assert rec.empty is False


def test_extraction_floor_never_silent_empty():
    # the pilot bug: empty capabilities were treated as a valid non-result.
    # judge must report inconclusive for empty + not-even-parseable raw.
    floor = ExtractionFloor(empty_marker="INCONCLUSIVE")
    rec = floor.judge(raw="not json", candidates=[])
    assert rec.conclusion == "inconclusive"
    assert rec.unparseable is True


def test_client_for_returns_callable():
    router = Router([_route("http://a/v1", "m1")])
    c = router.client_for("analyst")
    assert callable(c.chat)


def test_route_from_config():
    r = Route.from_config({
        "base_url": "http://x/v1", "model": "free-model", "api_key": "key"})
    assert r.model == "free-model"


def test_probe_accepts_data_list_omni(monkeypatch):
    # OmniRoute /models returns {"object":"list","data":[...]} — the probe must
    # treat that as healthy (not require {"models":[...]} which is OpenAI shape).
    import urllib.request as ur
    calls = []

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"object":"list","data":[{"id":"m1"}]}'

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return FakeResp()

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    from hurcules.routes import _probe_route
    assert _probe_route("http://x/v1", "k") is True
    assert calls and "/models" in calls[0]


def test_probe_accepts_models_openai(monkeypatch):
    import urllib.request as ur

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"models":["m1"]}'

    monkeypatch.setattr(ur, "urlopen", lambda req, timeout=None: FakeResp())
    from hurcules.routes import _probe_route
    assert _probe_route("http://x/v1", "k") is True


# ---------------------------------------------------------------------------
# Phase A hardening — transient retry/backoff + error taxonomy
# ---------------------------------------------------------------------------


def _resp(body: bytes):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return body

    return FakeResp()


OK_BODY = b'{"choices":[{"message":{"content":"ok response"}}]}'


def test_transient_retry_succeeds_on_2nd_attempt(monkeypatch):
    # fake transport: first call raises HTTP 503 (transient), retry succeeds.
    # The route must stay healthy and the successful retry's content returned.
    import urllib.error
    import urllib.request as ur
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise urllib.error.HTTPError(req.full_url, 503, "Unavailable", {}, None)
        return _resp(OK_BODY)

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    c = RoutingClient([_route("http://a/v1", "m1")], backoff=lambda attempt: 0.0)
    out = c.chat([{"role": "user", "content": "hi"}])
    assert out == "ok response"
    assert c.route is c.routes[0]
    assert c.routes[0].healthy is True
    assert len(calls) == 2


def test_transient_retry_exhausted_fails_over(monkeypatch):
    # first route always 503 -> 1 initial + 2 retries, then route down and
    # failover to the second healthy route.
    import urllib.error
    import urllib.request as ur
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        if "first" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 503, "Unavailable", {}, None)
        return _resp(b'{"choices":[{"message":{"content":"second served"}}]}')

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    c = RoutingClient(
        [_route("http://first/v1", "m1"), _route("http://second/v1", "m2")],
        backoff=lambda attempt: 0.0,
    )
    out = c.chat([{"role": "user", "content": "hi"}])
    assert out == "second served"
    assert c.route is c.routes[1]
    assert c.routes[0].healthy is False
    assert len([u for u in calls if "first" in u]) == 3  # initial + max_retries(2)


def test_non_transient_no_retry_fails_over(monkeypatch):
    # HTTP 400 is non-transient: exactly ONE call to the bad route, then
    # immediate failover to the next route.
    import urllib.error
    import urllib.request as ur
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        if "bad" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, None)
        return _resp(b'{"choices":[{"message":{"content":"good served"}}]}')

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    c = RoutingClient(
        [_route("http://bad/v1", "m1"), _route("http://good/v1", "m2")],
        backoff=lambda attempt: 0.0,
    )
    out = c.chat([{"role": "user", "content": "hi"}])
    assert out == "good served"
    assert c.route is c.routes[1]
    assert c.routes[0].healthy is False
    assert len([u for u in calls if "bad" in u]) == 1


def test_classify_http_error():
    import urllib.error
    assert classify_http_error(urllib.error.HTTPError("u", 429, "", {}, None)) == "transient"
    assert classify_http_error(urllib.error.HTTPError("u", 503, "", {}, None)) == "transient"
    assert classify_http_error(urllib.error.HTTPError("u", 400, "", {}, None)) == "non_transient"
    assert classify_http_error(TimeoutError("timed out")) == "transient"
    assert classify_http_error(urllib.error.URLError("dns failed")) == "transient"
    assert classify_http_error(ValueError("boom")) == "unknown"


def test_all_routes_down_raises_no_healthy_route(monkeypatch):
    import urllib.error
    import urllib.request as ur

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 503, "Unavailable", {}, None)

    monkeypatch.setattr(ur, "urlopen", fake_urlopen)
    c = RoutingClient([_route("http://a/v1", "m1")], backoff=lambda attempt: 0.0)
    with pytest.raises(NoHealthyRoute):
        c.chat([{"role": "user", "content": "hi"}])
    assert c.routes[0].healthy is False