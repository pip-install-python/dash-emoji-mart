"""Every live tool's default User-Agent names the BROWSER lane.

Template 1.6.40 item 17, found by muischeduler on its item-12 port: at
dash-improve-my-llms >= 2.8 a User-Agent with no browser engine token is
classified crawler-lane, so a tool whose default UA is a bare internal
token — or, worse, absent — reads the prerendered CRAWLER document on
every default-UA check. A manifest-link, og:image or prerender-marker
assertion then goes red the moment a floor moves, in CD's verify job,
naming the wrong cause.

The upstream item pins ONE tool (`scripts/network_smoke.py`, in the
template's `tests/test_network_smoke.py`, which this fork does not
carry). This repo has THREE tools that send requests, so all three are
pinned here — the same "grep the number, move every one" rule the floor
traps teach, applied to a lane instead of a version:

    scripts/network_smoke.py    UA / CRAWLER_UA
    scripts/smoke_live.py       BROWSER_UA / CRAWLER_UA  (already correct)
    scripts/verify_network.py   BROWSER_UA               (fork-original)

`verify_network.py` is the one this pin exists for. It sent NO
User-Agent at all, which is the crawler lane too, and its "prerender
marker present" check had therefore been RED on `main` since the floor
moved — invisibly, because that script is hand-run and wired into
neither CI nor CD. Measured in this tree: `data-dimll-prerender="1"` is
on the BROWSER document and the crawler lane never carries it.

In every case the internal token stays IN the string, AFTER the engine
token: `INTERNAL_UA_TOKEN` is matched as a substring, so the receiving
host's internal-traffic exclusion still drops the request and these
probes never land in anybody's ledger as real traffic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dash_improve_my_llms import classify  # noqa: E402

from lib.constants import INTERNAL_UA_TOKEN  # noqa: E402


def _browser_lane(ua: str, where: str) -> None:
    assert classify(ua)["lane"] == "browser", (
        f"{where}: {ua!r} classifies as "
        f"{classify(ua)['lane']!r} — a default-UA check would read the "
        "crawler document"
    )
    assert ua.startswith("Mozilla/5.0") and "AppleWebKit" in ua, where
    assert INTERNAL_UA_TOKEN in ua.lower(), (
        f"{where}: the internal token must survive the fix, or these probes "
        "start counting as real traffic on the far side"
    )


def test_network_smoke_defaults_to_the_browser_lane():
    from scripts import network_smoke as ns

    _browser_lane(ns.UA, "scripts/network_smoke.py UA")
    assert ns.UA.endswith("network-smoke")


def test_smoke_live_defaults_to_the_browser_lane():
    from scripts import smoke_live as sl

    _browser_lane(sl.BROWSER_UA, "scripts/smoke_live.py BROWSER_UA")


def test_verify_network_defaults_to_the_browser_lane():
    """The fork-original third tool — the one that was sending no UA."""
    from scripts import verify_network as vn

    _browser_lane(vn.BROWSER_UA, "scripts/verify_network.py BROWSER_UA")
    assert vn.BROWSER_UA.endswith("verify-network")


@pytest.mark.parametrize("module,attr", [
    ("scripts.network_smoke", "CRAWLER_UA"),
    ("scripts.smoke_live", "CRAWLER_UA"),
])
def test_the_crawler_ua_is_untouched(module, attr):
    """The other lane stays the other lane — the fix must not collapse the
    two into one, or every crawler-document assertion goes vacuous."""
    import importlib

    ua = getattr(importlib.import_module(module), attr)
    assert classify(ua)["lane"] == "crawler", f"{module}.{attr} -> {ua!r}"
    assert INTERNAL_UA_TOKEN in ua.lower(), f"{module}.{attr}"


def test_no_live_tool_sends_a_bare_internal_token():
    """The exact shape item 17 removes: the internal token with no engine
    token in front of it. Greps the sources so a NEW tool cannot
    reintroduce it without this pin noticing."""
    offenders = []
    for name in ("network_smoke.py", "smoke_live.py", "verify_network.py"):
        text = (REPO_ROOT / "scripts" / name).read_text()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or "_INTERNAL_UA" not in stripped:
                continue
            if "=" not in stripped or "import" in stripped:
                continue
            # A UA assembled from the token alone, with no engine token on
            # the same line and none concatenated before it.
            if stripped.startswith(("UA =", "BROWSER_UA =")) and "Mozilla" not in stripped:
                offenders.append(f"{name}: {stripped}")
    assert not offenders, offenders
