"""
``/healthz`` liveness probe for the Flask and Quart backends.

The 2plot.ai hub sweeps every satellite's ``/healthz`` once an hour and records
up/down + latency — that's the "Satellite health & reach" panel on ``/traffic``
(the traffic rollup this app POSTs supplies the other half). The FastAPI build
already declares a typed ``/healthz`` in ``lib/asgi_routes`` so it shows up in
Swagger; this module gives the other two backends the same endpoint, so the
probe result doesn't depend on which backend a deployment happens to run.

Keep it cheap: the hub measures the round trip, so any work done here is
reported back as this app being slow.
"""
import os

import dash

# NO ``from __future__ import annotations`` in this module, deliberately, and
# the FastAPI lane below is why. PEP 563 turns that route's ``request:
# Request`` annotation into the STRING "Request", which FastAPI then tries to
# resolve from module globals — where the locally imported Request does not
# exist — so the parameter silently degrades into a required QUERY field and
# every call 422s. Measured here: adding the fastapi branch under postponed
# annotations returned
#   {"detail":[{"type":"missing","loc":["query","request"],...}]}
# on a probe that must answer 200. lib/agent_key.py and lib/pageview_beacon.py
# carry the same constraint for the same reason; the annotations in this file
# (``-> dict``, ``-> str``, ``-> None``) need nothing from PEP 563.


def _resolved_country(headers=None) -> str:
    """``geo.explain_resolution`` over THIS request's headers, or a reason.

    Reads the request headers directly rather than anything the package
    threads through, so it answers "did the country header reach this app at
    all?" independently of how the enforcement seam is wired.

    Each route passes its own framework's headers explicitly. Reading Flask's
    request context instead makes the FastAPI and Quart lanes answer "no
    request context" forever — a sibling host's production healthz said
    exactly that until this was fixed. ``normalize_headers`` accepts
    Flask/Starlette/Quart/dict and never raises; the Flask-context fallback
    stays for callers that pass nothing.
    """
    try:
        from dash_improve_my_llms import geo
        from dash_improve_my_llms._headers import normalize_headers
    except Exception:
        return "unavailable (pre-2.7.0 package)"

    try:
        if headers is not None:
            return geo.explain_resolution(normalize_headers(headers))

        from flask import has_request_context, request

        if not has_request_context():
            return "no request context"
        return geo.explain_resolution(normalize_headers(request.headers))
    except Exception:
        return "unavailable"


def health_payload(backend: str, headers=None) -> dict:
    payload = {"ok": True, "backend": backend, "dash_version": dash.__version__}
    # Which commit the RUNNING instance was built from — the field that lets CD
    # verify the artifact IT shipped rather than whichever build happens to be
    # serving. A Render service with a disk restarts with a brief blip instead
    # of overlapping instances, so a bare 200 proves nothing about WHICH build
    # answered: the muicharts finding of 2026-08-21, where the battery had been
    # measuring the PREVIOUS release on every run, invisibly, because the old
    # build always passed the old battery. It only shows when a run adds a new
    # surface.
    #
    # Optional on purpose: omitted wherever the platform variable does not
    # exist, so the fleet's /healthz probe contract is unchanged and the hourly
    # sweep reads exactly what it always did.
    build = os.environ.get("RENDER_GIT_COMMIT")
    if build:
        payload["build"] = build

    # WHICH satellite answered. `build` says which commit; this says which app
    # — and on a fleet where every host shares one template and a hostname can
    # be repointed between services, "is this the site I think it is?" is a
    # different question from "is this the build I shipped?". Falls back to
    # "unknown" rather than this repo's key, so a missing SATELLITE_APP_KEY
    # reads as missing instead of quietly asserting an identity.
    payload["app"] = os.environ.get("SATELLITE_APP_KEY") or "unknown"

    # The geo guardrail's LIVE state (dash-improve-my-llms >= 2.7.0). Added
    # after a sibling host's production verification could not answer "is the
    # denylist actually in force?" from outside: the surfaces that could
    # settle it need credentials a verification pass does not have.
    #
    # Counts and flags ONLY — never the denylist's country codes. A health
    # endpoint is not where anyone should learn policy. `resolved` reveals
    # only the caller's own country back to them, which Cloudflare's
    # /cdn-cgi/trace already does, and it localises the failure that matters:
    # geo can be fully configured and still never match because the country
    # header is not reaching the app. "configured: true, denied: 7, resolved:
    # unknown" says that in one line.
    try:
        from dash_improve_my_llms import geo
    except ImportError:
        # Pre-2.7 package: the key is OMITTED, not error-flagged. A host on an
        # older floor is not broken, it just predates the diagnostic.
        pass
    else:
        try:
            payload["geo"] = {
                "configured": bool(geo.is_configured()),
                "denied": len(geo.effective_policy().get("deny_countries") or []),
                "resolved": _resolved_country(headers),
            }
        except Exception:  # never let a diagnostic break the health probe
            payload["geo"] = {"configured": False, "denied": 0, "error": True}

    return payload


def register_health_route(app, backend: str) -> None:
    """Mount ``/healthz`` on whichever backend is active — all three.

    The payload is built PER REQUEST, not snapshotted at registration. It used
    to be a snapshot closed over by the route, which was harmless while every
    field was static — ok/backend/dash_version/build never change for a running
    process — and silently wrong the moment one is not. `geo` is exactly that:
    this route is registered well before any geo configuration runs, so a
    snapshot would report the guardrail as unconfigured on a host where it is
    configured, the diagnostic lying in precisely the situation it exists for.
    """
    server = app.server

    if backend == "fastapi":
        # This repo ships no lib/asgi_routes, so without this branch a
        # DASH_BACKEND=fastapi deployment serves NO /healthz at all — and
        # /healthz is render.yaml's healthCheckPath as well as the hub's
        # hourly probe. include_in_schema stays default so it still appears
        # in Swagger at /docs.
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        @server.get("/healthz")
        async def _healthz(request: Request):  # pragma: no cover — fastapi runtime
            return JSONResponse(health_payload(backend, headers=request.headers))
    elif backend == "quart":
        from quart import jsonify, request

        @server.get("/healthz")
        async def _healthz():  # pragma: no cover — quart runtime
            return jsonify(health_payload(backend, headers=request.headers))
    else:
        from flask import jsonify, request

        @server.get("/healthz")
        def _healthz():
            return jsonify(health_payload(backend, headers=request.headers))

    print(f"[dash-emoji-mart] /healthz registered ({backend}) — "
          "the 2plot.ai hourly health sweep probes this path.")
