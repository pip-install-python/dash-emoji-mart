"""``/healthz`` — the probe contract, pinned per backend.

The 2plot.ai hub sweeps this path hourly and render.yaml names it as the
service's ``healthCheckPath``, so it is the one endpoint whose behaviour two
different systems depend on without either of them being in this repo.

Three defects this file exists to keep fixed, all of the same shape — a health
endpoint LYING BY OMISSION, which is worse than one that is down:

1. The payload was a snapshot closed over at registration. Harmless while every
   field was static, and silently wrong the moment one is not.
2. The FastAPI lane never existed here at all, so ``DASH_BACKEND=fastapi``
   served no ``/healthz`` whatsoever. (The template's narrower version of this:
   its FastAPI route built its own payload and lacked ``build``, so cd.yml's
   build-match wait verified whichever release happened to be serving.)
3. ``geo.resolved`` read Flask's request context, so every non-Flask lane
   answered "no request context" forever.
"""

from __future__ import annotations

import pytest


def test_healthz(client):
    """The 2plot.ai hub probes this hourly, on whichever backend is running."""
    response = client.get("/healthz")
    assert response.ok
    assert "ok" in response.text.lower()


def test_healthz_is_live_not_a_snapshot(monkeypatch):
    """The payload must be built per request, not closed over at registration.

    A snapshot was harmless while every field was static — ok/backend/
    dash_version/build never change for a running process — and silently wrong
    the moment one is not. ``geo`` is exactly that field: this route is
    registered well before any geo configuration runs, so a snapshot reports
    the guardrail as unconfigured on a host where it is configured, which is
    the diagnostic lying in precisely the situation it exists for.
    """
    from types import SimpleNamespace

    from flask import Flask

    from lib.health import register_health_route

    monkeypatch.setenv("SATELLITE_APP_KEY", "before")
    stub = SimpleNamespace(server=Flask("healthz_snapshot_pin"))
    register_health_route(stub, "flask")
    probe = stub.server.test_client()
    assert probe.get("/healthz").get_json()["app"] == "before"

    monkeypatch.setenv("SATELLITE_APP_KEY", "after")
    assert probe.get("/healthz").get_json()["app"] == "after"

    # Flask lane: the route hands its OWN request headers to geo's `resolved`,
    # the same contract the FastAPI test below pins for Starlette.
    body = probe.get("/healthz", headers={"CF-IPCountry": "FR"}).get_json()
    if body.get("geo"):
        assert "FR" in body["geo"]["resolved"], body["geo"]


def test_healthz_identity_fields(monkeypatch):
    """``build`` says which commit answered; ``app`` says which satellite.

    Different questions on a fleet where every host is forked from one template
    and a hostname can be repointed between services. ``app`` falls back to
    "unknown" rather than this repo's own key, so a missing SATELLITE_APP_KEY
    reads as missing instead of quietly asserting an identity.
    """
    from lib.health import health_payload

    monkeypatch.setenv("RENDER_GIT_COMMIT", "cafebabe")
    monkeypatch.setenv("SATELLITE_APP_KEY", "emojimart")
    payload = health_payload("flask")
    assert payload["build"] == "cafebabe"
    assert payload["app"] == "emojimart"

    monkeypatch.delenv("SATELLITE_APP_KEY")
    assert health_payload("flask")["app"] == "unknown"


def test_fastapi_healthz_renders_from_the_shared_payload(monkeypatch):
    """Every backend renders from the ONE payload builder.

    This repo carries no ``lib/asgi_routes``, so before the ≥2.7.1 floor round
    a ``DASH_BACKEND=fastapi`` deployment served no ``/healthz`` at all — the
    path render.yaml declares as its health check and the hub probes hourly.
    Production runs Flask, which is the only reason that never surfaced.
    """
    fastapi = pytest.importorskip("fastapi")
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from lib.health import register_health_route

    monkeypatch.setenv("RENDER_GIT_COMMIT", "cafebabe")
    monkeypatch.setenv("SATELLITE_APP_KEY", "emojimart")
    stub = SimpleNamespace(server=fastapi.FastAPI())
    register_health_route(stub, "fastapi")

    body = TestClient(stub.server).get(
        "/healthz", headers={"CF-IPCountry": "DE"}
    ).json()
    assert body["build"] == "cafebabe"
    assert body["app"] == "emojimart"
    assert body["backend"] == "fastapi"
    # THIS request's headers must reach geo's `resolved`: the route passes them
    # explicitly, because the Flask-context fallback can never see a Starlette
    # request. A sibling host's production healthz answered "no request
    # context" forever for exactly this reason.
    if body.get("geo"):
        assert "DE" in body["geo"]["resolved"], body["geo"]


def test_resolved_country_reads_explicit_headers_without_a_request():
    """The context-free pin — the only one of these that can actually fail.

    The in-request pins above still pass if a Flask route drops its
    ``headers=`` argument: inside a request the context fallback reads the same
    headers, and the lanes that genuinely break (Starlette, Quart) are
    unreachable from a Flask-pinned suite. Calling ``_resolved_country`` with a
    plain dict OUTSIDE any request context has no fallback to hide behind.
    """
    from lib.health import _resolved_country

    result = _resolved_country({"CF-IPCountry": "DE"})
    if result.startswith("unavailable (pre-2.7.0"):
        pytest.skip("geo shipped in dash-improve-my-llms 2.7.0")
    assert "DE" in result, result


def test_healthz_geo_block_is_counts_not_codes():
    """Counts and flags only — a health endpoint is not where anyone should
    learn policy — and OMITTED on pre-2.7.0 packages rather than error-flagged.
    A host on an older floor is not broken; it predates the diagnostic."""
    from lib.health import health_payload

    payload = health_payload("flask")
    try:
        from dash_improve_my_llms import geo  # noqa: F401
    except ImportError:
        assert "geo" not in payload
    else:
        block = payload["geo"]
        assert isinstance(block["configured"], bool)
        assert isinstance(block["denied"], int), "counts, never country codes"
        assert "deny_countries" not in block
        assert not any(
            isinstance(v, (list, tuple)) for v in block.values()
        ), "the geo block must never carry the denylist itself"
