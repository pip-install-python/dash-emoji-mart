"""The network's internal-traffic contract — the analytics point of truth.

The rule (https://2plot.ai/docs/satellite-analytics, "Internal traffic"): a
request whose User-Agent contains `2plot-internal` is 2plot machinery talking
to itself — the hub's hourly health sweep, CI smoke batteries, the 4x-daily
heartbeat, cross-app calls — and is counted NOWHERE. Dropped at write time,
before device detection and before bot classification. `/healthz` is never a
visit either.

Both halves are tested here, because a contract kept on only one side is not
kept at all:

*inbound*   token-carrying requests never reach the ledger, and therefore
            never reach `human_hits` / `bot_hits` in the hourly rollup this
            app POSTs to 2plot.ai;
*outbound*  every call this host makes to another network host sends
            `INTERNAL_UA`, so the far side can apply the same rule. That half
            was missing: the ad client fetched a campaign from 2plot.dev on
            every single docs page view, arriving as `python-requests/2.x`,
            and the hub counted this satellite's readers as its own bots.
"""

from __future__ import annotations

import pytest

# Site suite, not package suite: these need the docs-site dependency set
# (requirements.txt). CI's package-only compat matrix installs just the wheel,
# and without this guard that matrix fails on an import error that says nothing
# about the package under test — LESSONS §19.
pytest.importorskip("dash_mantine_components")
pytest.importorskip("dash_improve_my_llms")

import json  # noqa: E402
from datetime import datetime  # noqa: E402

from conftest import BROWSER_UA, CRAWLER_UA  # noqa: E402
from lib.analytics_tracker import analytics_path, tracker
from lib.constants import APP_KEY, INTERNAL_UA, INTERNAL_UA_TOKEN, internal_ua

# A real page ON THIS SITE. `lib/traffic_rollup` drops infrastructure paths
# (`/llms.txt`, `/robots.txt`, `/healthz`, ...) at read time, so a rollup
# assertion made against one of those would pass no matter what the tracker
# did. The donor's "/backends" does not exist here — and because the tracker
# records any well-formed path, a 404 would still have been counted and every
# assertion below would have passed while measuring nothing real.
PAGE = "/popover"


def _ledger_visits():
    """Every hit on disk, flushing the write buffer first."""
    tracker.flush()
    try:
        with open(analytics_path()) as f:
            return json.load(f).get("visits", [])
    except FileNotFoundError:
        return []


def _ledger_reads():
    """Every READ row on disk, flushing the write buffer first.

    The second table (dimll 2.8.0's `on_document_read`). Absent key reads
    as empty, exactly as the tracker's own writer treats it.
    """
    tracker.flush()
    try:
        with open(analytics_path()) as f:
            return json.load(f).get("reads") or []
    except FileNotFoundError:
        return []


def _rollup():
    """Today's rollup as the hub would receive it, or an all-zero stand-in."""
    from lib.traffic_rollup import daily_rollup

    tracker.flush()
    return daily_rollup(APP_KEY, datetime.now().date()) or {
        "human_hits": 0, "bot_hits": 0,
    }


# --------------------------------------------------------------- the token --


def test_token_is_the_network_wide_string():
    """The contract only works if every host agrees on the byte sequence."""
    assert INTERNAL_UA_TOKEN == "2plot-internal"
    assert INTERNAL_UA_TOKEN in INTERNAL_UA
    assert INTERNAL_UA.startswith(INTERNAL_UA_TOKEN)


def test_caller_suffix_never_breaks_the_token():
    ua = internal_ua("traffic-reporter")
    assert INTERNAL_UA_TOKEN in ua
    assert ua.endswith("traffic-reporter")
    assert internal_ua() == INTERNAL_UA
    assert internal_ua("  ") == INTERNAL_UA


# ------------------------------------------------------------------ inbound --


def test_the_tests_can_see_the_ledger_at_all(client, tmp_state_dir):
    """Guard for every delta assertion below.

    If the ledger path were wrong (or the suite were writing into the repo's
    own visitor_analytics.json), every "count did not change" test would pass
    vacuously. Prove a write lands first.
    """
    assert str(analytics_path()).startswith(tmp_state_dir), analytics_path()
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=BROWSER_UA)
    assert len(_ledger_visits()) == before + 1


def test_internal_ua_is_counted_nowhere(client):
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=internal_ua("network-smoke"))
    client.get("/", user_agent=INTERNAL_UA)
    assert len(_ledger_visits()) == before


def test_a_crawler_shaped_probe_carrying_the_token_stays_internal(client):
    """The battery's crawler probe exercises the bot path deliberately.

    It must still not be counted. This is precisely why the drop happens
    before `detect_device_type` — classification would file it under `bot`.
    """
    before = len(_ledger_visits())
    client.get(PAGE, user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")
    assert len(_ledger_visits()) == before


def test_the_token_is_matched_case_insensitively(client):
    before = len(_ledger_visits())
    client.get(PAGE, user_agent="2PLOT-INTERNAL/1.0 Health-Sweep")
    assert len(_ledger_visits()) == before


def test_healthz_is_never_a_visit(client):
    before = len(_ledger_visits())
    client.get("/healthz", user_agent="Render/1.0 health-check")
    client.get("/healthz", user_agent=BROWSER_UA)
    assert len(_ledger_visits()) == before


def test_the_read_table_drops_internal_traffic_too(client, capsys):
    """SYNC-1.6.43 item 1: "counted nowhere" includes the READ table.

    `record_read` arrived with the 2.8.0 floor and did not inherit the
    internal-traffic drop `track_visit` has always had, so every 2plot probe
    that fetched a corpus document — the hub's hourly health sweep, every
    satellite's link audit, this repo's own post-deploy battery and
    /wire-verify — landed in `reads` and was very likely the busiest
    "vendor" on this host's board.

    BOTH DIRECTIONS IN ONE TEST, and the counts PRINTED beside the result:
    a pin that passes by dropping everything is the same green as a pin
    that passes correctly, and "no rows" is the negative this round learned
    not to trust on its own.

    KEYED ON `ua`. EVENT_FIELDS carries `ua`, never `user_agent`; a drop
    keyed on the wrong name is a silent no-op. Asserted here rather than
    assumed, because the field name is the fix's whole failure mode.
    """
    from importlib.metadata import version

    from dash_improve_my_llms._ledger import EVENT_FIELDS

    resolved = version("dash-improve-my-llms")
    assert "ua" in EVENT_FIELDS, EVENT_FIELDS
    assert "user_agent" not in EVENT_FIELDS, EVENT_FIELDS

    # (1) the internal probe — a crawler-shaped UA carrying the token, which
    # is the network convention for a probe and the shape that would
    # otherwise write a vendor row.
    before = len(_ledger_reads())
    client.get("/llms.txt", user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")
    after_internal = len(_ledger_reads())

    # (2) a real crawler, so the pin cannot pass by dropping everything.
    client.get("/llms.txt", user_agent=CRAWLER_UA)
    after_real = len(_ledger_reads())

    print(
        f"\n[read-table drop] dash-improve-my-llms {resolved} · "
        f"reads before={before} after internal probe={after_internal} "
        f"(+{after_internal - before}) after real crawler={after_real} "
        f"(+{after_real - after_internal})"
    )

    assert after_internal == before, (
        f"the internal probe wrote {after_internal - before} read row(s); "
        "the token must be dropped before the row is built"
    )
    assert after_real == after_internal + 1, (
        f"a real crawler wrote {after_real - after_internal} rows, expected 1 "
        "— the drop is swallowing traffic it should keep"
    )


# ----------------------------------------------- the reported numbers -------
#
# The exclusion that actually matters. Everything above is about the ledger;
# this is about what 2plot.ai charts.


def test_internal_traffic_is_absent_from_human_hits_and_bot_hits(client):
    before = _rollup()

    # Four calls that are all machinery, in the two shapes the network sends:
    # a plain internal UA, and a crawler-shaped probe carrying the token.
    for _ in range(2):
        client.get(PAGE, user_agent=internal_ua("network-smoke"))
        client.get(PAGE, user_agent=f"{CRAWLER_UA} {INTERNAL_UA}")

    after = _rollup()
    assert after["human_hits"] == before["human_hits"], (
        "internal traffic reached human_hits — the hub would chart the health "
        "sweep as readers of these docs"
    )
    assert after["bot_hits"] == before["bot_hits"], (
        "internal traffic reached bot_hits — the hub would chart CI as crawler "
        "interest"
    )


def test_real_traffic_is_still_counted(client):
    """The exclusions must not have lobotomised the tracker.

    A rule that drops everything also satisfies every assertion above, so the
    positive case is load-bearing: one browser hit is one human, one Googlebot
    hit is one bot.
    """
    before = _rollup()
    client.get(PAGE, user_agent=BROWSER_UA)
    client.get(PAGE, user_agent=CRAWLER_UA)
    after = _rollup()

    assert after["human_hits"] == before["human_hits"] + 1
    assert after["bot_hits"] == before["bot_hits"] + 1


# ----------------------------------------------------------------- outbound --


class _Captured(Exception):
    """Abort the request once the headers have been seen."""


def _capture_headers(monkeypatch, module, attr="post"):
    """Record the headers of the next outbound call, then abort it."""
    seen = {}

    def fake(*args, **kwargs):
        seen.update(kwargs.get("headers") or {})
        raise _Captured

    monkeypatch.setattr(module, attr, fake)
    return seen


def test_the_traffic_rollup_post_sends_the_token(monkeypatch):
    import requests

    from lib import satellite_reporter

    seen = _capture_headers(monkeypatch, requests, "post")
    ok, _detail = satellite_reporter.post_rollup(
        {"app": "emojimart", "date": "2026-08-01"}, secret="test-secret"
    )
    assert ok is False  # the fake raised; we only wanted the headers
    assert INTERNAL_UA_TOKEN in seen.get("User-Agent", "")


# The donor also pins `lib/hub_client.py`, the agent-key client. This repo has
# no hub client and no key material by design — every page here is public, so
# there is nothing to verify a doc key for (STANDARD: satellites hold NO key
# material). Nothing to test; the absence is the correct state, and
# test_no_local_key_material below is what keeps it that way.


def test_the_ad_fetch_sends_the_token(monkeypatch):
    """One call per docs page view — the loudest outbound call this app makes."""
    from lib import ad_client

    seen = _capture_headers(monkeypatch, ad_client._session, "get")
    monkeypatch.setattr(ad_client, "_last_failure", 0.0)
    assert ad_client.fetch_ad("/popover") is None
    assert INTERNAL_UA_TOKEN in seen.get("User-Agent", "")


def test_no_local_key_material():
    """Satellites verify doc keys on the hub; they never mint or hold them.

    Pinned because the tempting fix for a hub outage is a local fallback, and
    that would put signing material on eight hosts instead of one.

    TWO files are sanctioned, and for the same reason — each names agent keys
    precisely because it holds none:

      * lib/hub_client.py — the network's verify-on-the-hub client (ported in
        the 1.3.x sync). It names the hub's /api/agent-key/* endpoints; it
        cannot mint, and it cannot verify offline.
      * lib/agent_key.py — the GET /api/agent-key route (ported in the gate
        wave). It reads the browser's Clerk __session cookie and hands it to
        hub_client.current_key(); the HUB verifies that token against Clerk's
        JWKS and pins scope=auth. The satellite asserts no identity of its own
        and cannot mint an admin key. 204 whenever the hub declines.

    Any OTHER lib file mentioning agent keys is still the failure this test
    exists to catch.
    """
    from conftest import REPO_ROOT

    offenders = []
    for path in sorted((REPO_ROOT / "lib").glob("*.py")):
        if path.name in ("hub_client.py", "agent_key.py"):
            continue
        text = path.read_text()
        if "agent-key" in text or "AGENT_KEY" in text:
            offenders.append(path.name)
    assert offenders == [], f"agent-key material in {offenders}"


# `audit_links` is a boilerplate script this repo does not carry (STANDARD §0
# lists only network_smoke, smoke_live and make_social_card). `verify_network`
# is this repo's own pre-existing battery and makes outbound calls, so it is
# held to the same rule.
@pytest.mark.parametrize("script", ["smoke_live", "network_smoke"])
def test_every_battery_script_sends_the_token(script):
    """A post-deploy battery sweeps every peer; it must not register anywhere."""
    import importlib.util

    from conftest import REPO_ROOT

    spec = importlib.util.spec_from_file_location(
        f"_ua_{script}", REPO_ROOT / "scripts" / f"{script}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    agents = [
        value
        for name, value in vars(module).items()
        if (name == "UA" or name.endswith("_UA")) and isinstance(value, str)
    ]
    assert agents, f"scripts/{script}.py declares no User-Agent constant"
    missing = [ua for ua in agents if INTERNAL_UA_TOKEN not in ua]
    assert missing == [], f"scripts/{script}.py sends untokened UAs: {missing}"
