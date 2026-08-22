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
from __future__ import annotations

import os

import dash


def health_payload(backend: str) -> dict:
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
    return payload


def register_health_route(app, backend: str) -> None:
    """Mount ``/healthz`` on Flask/Quart. No-op on FastAPI (already typed)."""
    if backend == "fastapi":
        return

    server = app.server
    payload = health_payload(backend)

    if backend == "quart":
        from quart import jsonify

        @server.get("/healthz")
        async def _healthz():  # pragma: no cover — quart runtime
            return jsonify(payload)
    else:
        from flask import jsonify

        @server.get("/healthz")
        def _healthz():
            return jsonify(payload)

    print(f"[dash-emoji-mart] /healthz registered ({backend}) — "
          "the 2plot.ai hourly health sweep probes this path.")
