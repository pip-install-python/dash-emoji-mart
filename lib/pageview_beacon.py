"""SPA page-view beacon — the half of the traffic ledger HTTP alone cannot see.

A Dash app serves ONE HTML document per visit and routes every subsequent page
client-side, so per-request tracking (``lib/analytics_tracker``'s hook, wired in
``run.py``) only ever observes the entry page. Left at that, ``pages`` would
list entry pages only and ``median_session_s`` would be null for every session
— a visitor who read six pages would be indistinguishable from one who bounced.

So the browser beacons each route change to ``/api/pageview`` (same origin,
``keepalive`` so it survives the navigation), and the handler feeds it into the
SAME ``tracker.track_visit`` the request hook uses. One ledger, one schema, and
``lib/traffic_rollup`` reads it without knowing which half a hit came from.

Bots do not run JavaScript, so bot hits stay request-only. That is correct, not
a gap: a crawler genuinely does fetch one URL per request.

This module has no counterpart in dash-documentation-boilerplate — its tracker
skips ``/_dash-update-component`` and it ships no beacon, so SPA navigation goes
uncounted there. This file is the local addition that keeps the behaviour the
hand-rolled ``lib/satellite_analytics.py`` had before the 2plot network trio
replaced it. If the boilerplate ever grows an equivalent, delete this and take
the upstream one.

Wiring (``run.py``, alongside the per-request hook)::

    from lib.pageview_beacon import register_pageview_beacon, register_routes
    register_routes(app, BACKEND)      # mount /api/pageview
    register_pageview_beacon()         # the clientside callback

and ``beacon_component()`` goes in the app shell to give the callback its sink.
"""

from __future__ import annotations

import json

from lib.analytics_tracker import tracker


def _beacon_path(raw: bytes) -> str | None:
    """The path out of a beacon body — ``{"path": "/iconify"}``.

    Anything malformed, non-string, or not rooted at ``/`` is rejected rather
    than tracked: this endpoint takes an unauthenticated body from the browser,
    and a junk path would land in the ledger and be reported to the hub.
    """
    try:
        path = json.loads(raw or b"{}").get("path")
    except Exception:
        return None
    if not isinstance(path, str) or not path.startswith("/") or path.startswith("//"):
        return None
    return path


def _track(path: str, headers, ip: str | None) -> None:
    """Feed one beaconed view into the shared tracker.

    ``headers`` is passed through because behind Render (or any CDN) the socket
    peer is the proxy — without them every visitor geolocates to one datacentre.
    """
    try:
        lowered = {k.lower(): v for k, v in dict(headers).items()}
        tracker.track_visit(
            path, lowered.get("user-agent", ""), ip, headers=lowered
        )
    except Exception:
        # Analytics must never turn into a 500 on a page the user is reading.
        pass


def register_routes(app, backend: str) -> None:
    """Mount ``POST /api/pageview`` on whichever backend is active.

    MUST be called before ``add_llms_routes`` — the package mounts a catch-all
    that would otherwise claim this path.
    """
    server = app.server

    if backend == "fastapi":
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        @server.post("/api/pageview", include_in_schema=False)
        async def _pageview(request: Request):  # pragma: no cover — fastapi runtime
            path = _beacon_path(await request.body())
            if path:
                client = request.client
                _track(path, request.headers, client.host if client else None)
            return JSONResponse({"ok": bool(path)}, status_code=200 if path else 400)

    elif backend == "quart":
        from quart import jsonify, request

        @server.post("/api/pageview")
        async def _pageview():  # pragma: no cover — quart runtime
            path = _beacon_path(await request.get_data())
            if path:
                _track(path, request.headers, request.remote_addr)
            return jsonify({"ok": bool(path)}), 200 if path else 400

    else:
        from flask import jsonify, request

        @server.post("/api/pageview")
        def _pageview():
            path = _beacon_path(request.get_data())
            if path:
                _track(path, request.headers, request.remote_addr)
            return jsonify({"ok": bool(path)}), 200 if path else 400

    print(f"[dash-emoji-mart] /api/pageview registered ({backend}) — SPA page views counted.")


def register_pageview_beacon(location_id: str = "url") -> None:
    """Beacon every client-side route change to ``/api/pageview``.

    ``prevent_initial_call=True`` keeps the entry page out of it — that one
    already arrived as a real HTTP request and was counted by the request hook.
    Without it every visit would be double-counted on its first page.
    """
    from dash import Input, Output, clientside_callback

    clientside_callback(
        """
        function(pathname) {
            if (pathname) {
                try {
                    fetch('/api/pageview', {
                        method: 'POST',
                        keepalive: true,
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({path: pathname})
                    }).catch(function(){});
                } catch (e) {}
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output("satellite-pageview-beacon", "data"),
        Input(location_id, "pathname"),
        prevent_initial_call=True,
    )


def beacon_component():
    """Hidden sink for the beacon callback; place it in the app shell."""
    from dash import dcc, html

    return html.Div(
        dcc.Store(id="satellite-pageview-beacon", data=None),
        style={"display": "none"},
    )
