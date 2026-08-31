#!/usr/bin/env python
"""The 2plot migration verification battery, run in-process.

Mirrors the curl battery in dash-hook-my-ai/handoff/existing_subdomains.md
("Verification"), but drives the app through its backend's test client instead
of a socket. Same WSGI stack, same responses — what it cannot cover is DNS, TLS
and the CDN, so run the curl version against the deployed host as well.

    python scripts/verify_network.py

Exit code 0 when every check passed, 1 otherwise.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Flask is what production runs (gunicorn is WSGI) and the only backend whose
# in-process client needs no extra dependency.
os.environ.setdefault("DASH_BACKEND", "flask")
# Never let a verification run write the real ledger or beacon the live hub.
os.environ.setdefault("TRAFFIC_ANALYTICS_FILE", "/tmp/verify_visitor_analytics.json")
os.environ.pop("CROSS_APP_WEBHOOK_SECRET", None)
os.environ.setdefault("AD_SERVER_URL", "http://127.0.0.1:1")

failures: list[str] = []


try:
    from lib.constants import INTERNAL_UA as _INTERNAL_UA
except Exception:  # pragma: no cover — running outside a repo checkout
    _INTERNAL_UA = "2plot-internal/1.0 (+https://2plot.ai/docs/satellite-analytics)"

# The third encoding of the browser lane in this repo (scripts/network_smoke.py
# and scripts/smoke_live.py are the other two); all three move together.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 "
    + _INTERNAL_UA + " verify-network"
)


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<44} {detail}")
    if not ok:
        failures.append(name)


def main() -> int:
    import run  # noqa: F401  — side effects are the point

    import dash

    client = run.app.server.test_client()

    def get(path: str, **kwargs):
        # DEFAULT TO THE BROWSER LANE (template 1.6.40 item 17, ported into
        # this fork-original tool). At dash-improve-my-llms >= 2.8 a request
        # with NO User-Agent is crawler-lane — so every bare `get()` here was
        # reading the prerendered crawler document, and the prerender-marker
        # check below has been RED on main since the floor moved without
        # anyone seeing it: this script is hand-run, not wired into CI.
        # Measured in this tree: `data-dimll-prerender="1"` is on the BROWSER
        # document; the crawler lane never carries it. The internal token
        # stays in the string, AFTER the engine token, so the far side's
        # internal-traffic exclusion still holds (substring match).
        # A check that means the crawler lane passes its own UA explicitly.
        headers = dict(kwargs.pop("headers", None) or {})
        headers.setdefault("User-Agent", BROWSER_UA)
        # `headers=` passed EXPLICITLY at the call, not folded into **kwargs:
        # the fleet's per-call-site pin reads the call text, and a UA that
        # arrives through a dict splat is invisible to it. Legible to the
        # reader for the same reason it is legible to the grep.
        return client.get(path, headers=headers)

    print("=" * 78)
    print(" 2plot network verification · dash-emoji-mart")
    print("=" * 78)

    # -- health ------------------------------------------------------------
    print("\n[health]")
    resp = get("/healthz")
    check("/healthz returns 200", resp.status_code == 200, f"HTTP {resp.status_code}")
    # The payload GROWS by design — `python` and `geo` arrived with later
    # template items and this frozen three-key equality had been red on main
    # ever since, silently, because nothing runs this script but a person.
    # Assert the contract: the keys this host promises, with the values that
    # can actually be wrong. `build` is Render-only and absent locally.
    body = resp.get_json(silent=True) or {}
    missing = [k for k in ("ok", "app", "backend", "dash_version", "python", "geo")
               if k not in body]
    check("/healthz carries the fleet shape", not missing, f"missing {missing}")
    check("/healthz reports ok",
          body.get("ok") is True
          and body.get("backend") == "flask"
          and body.get("dash_version") == dash.__version__,
          str(body))

    # -- canonical ---------------------------------------------------------
    # The shim-collision check. 2.3.3's prerender writes the canonical tag;
    # a leftover static one in templates/index.html would make this 2.
    print("\n[canonical]")
    for path in ("/", "/iconify", "/api-reference"):
        html = get(path).get_data(as_text=True)
        n = html.count('rel="canonical"')
        check(f"exactly one canonical on {path}", n == 1, f"found {n}")

    home = get("/").get_data(as_text=True)
    hrefs = re.findall(r'rel="canonical" href="([^"]+)"', home)
    check("canonical points at this host", hrefs == ["https://emojimart.2plot.dev/"],
          str(hrefs))

    page = get("/iconify").get_data(as_text=True)
    hrefs = re.findall(r'rel="canonical" href="([^"]+)"', page)
    check("canonical is per-page, not frozen at /",
          hrefs == ["https://emojimart.2plot.dev/iconify"], str(hrefs))

    check("prerender marker present", 'data-dimll-prerender="1"' in home,
          "data-dimll-prerender")
    check("no pushState canonical shim survives",
          "history[method]" not in home and "var ORIGIN" not in home)

    # og:url is emitted by the prerender now; a static copy would double it.
    n = home.count('property="og:url"')
    check("exactly one og:url", n == 1, f"found {n}")

    # -- crawler view ------------------------------------------------------
    # The runbook writes this as `grep -c "requires JavaScript"` expecting 0,
    # but that phrase also appears in this site's own <noscript> fallback, which
    # is legitimate content. Match the package's actual stub sentence instead —
    # otherwise the check reads as failing on a perfectly healthy page.
    print("\n[crawlers]")
    STUB = "This page contains interactive content that requires JavaScript"
    for agent in ("Googlebot/2.1", "ClaudeBot/1.0", "OAI-SearchBot/1.0"):
        body = get("/", headers={"User-Agent": agent}).get_data(as_text=True)
        check(f"{agent.split('/')[0]} gets real content", STUB not in body,
              f"{len(body):,} bytes")

    # The home page is the one the fleet survey found stubbed on 2.0, where the
    # root register_page_metadata call above overwrote the markdown loader's
    # prose. Assert the prose is actually in the crawler's copy.
    body = get("/", headers={"User-Agent": "Googlebot/2.1"}).get_data(as_text=True)
    check("home prose reaches crawlers", "emoji-mart" in body and "pip install" in body,
          f"{len(body):,} bytes")

    # -- robots ------------------------------------------------------------
    # The >=2.3.3 fingerprint for the ALLOWED fetchers, plus the posture check
    # for the training crawlers — this host retired the training wall
    # (run.py `block_ai_training=False`), so their stanza is absent, not
    # Disallow.
    print("\n[robots]")
    robots = get("/robots.txt").get_data(as_text=True)
    check("/robots.txt served", bool(robots.strip()), f"{len(robots)} bytes")

    def agent_block(name: str) -> str:
        m = re.search(rf"^User-agent: {re.escape(name)}\s*$(.*?)(?=^User-agent:|\Z)",
                      robots, re.M | re.S)
        return m.group(1).strip() if m else ""

    oai = agent_block("OAI-SearchBot")
    check("OAI-SearchBot -> Allow", oai.startswith("Allow:"), oai.splitlines()[:1])
    check("no leftover OAI-SearchBot Disallow workaround",
          "Disallow" not in oai, oai.splitlines()[:2])

    # POSTURE, not artifact (template 1.6.37, Round 3.4): the training wall is
    # retired here, so the package emits no training stanza at all — absent and
    # Allow are both the allow shape, and only Disallow is a failure. This is
    # the THIRD encoding of the fingerprint in this repo (network_smoke.py and
    # smoke_live.py are the other two); all three move together.
    for training in ("ClaudeBot", "GPTBot"):
        block = agent_block(training)
        check(f"{training} not Disallowed (posture flip)",
              not block.startswith("Disallow:"),
              block.splitlines()[:1] or "absent")
    for allowed in ("Claude-User", "ChatGPT-User"):
        block = agent_block(allowed)
        check(f"{allowed} -> Allow", block.startswith("Allow:"),
              block.splitlines()[:1] or "absent")
    check("sitemap advertised", "Sitemap:" in robots,
          re.search(r"Sitemap: .*", robots).group(0) if "Sitemap:" in robots else "")

    # -- llms.txt ----------------------------------------------------------
    print("\n[llms.txt]")
    llms = get("/llms.txt").get_data(as_text=True)
    check("/llms.txt served", bool(llms.strip()), f"{len(llms):,} bytes")

    # The whole-index shape. Each of these has a real failure behind it:
    #   * the stub is what a sub-2.2 package produces, because the root
    #     register_page_metadata call overwrites the markdown loader's prose;
    #   * two taglines is what a preamble on the ROOT doc produces, since the
    #     index emits its own and only strips a leading H1, not a blockquote;
    #   * `## Pages` missing means page registration never reached the handler.
    check("home prose is not the stub",
          "No `LLMS_DOC` registered" not in llms,
          "stub present — check the dash-improve-my-llms version" if
          "No `LLMS_DOC` registered" in llms else "real prose")
    check("## Pages section present", "## Pages" in llms)

    prose_only = re.sub(r"```.*?```", "", llms, flags=re.S)
    h1s = [ln for ln in prose_only.splitlines() if ln.startswith("# ")]
    check("exactly one H1 on the index", len(h1s) == 1, str(h1s))
    taglines = [ln for ln in prose_only.splitlines()[:10] if ln.startswith("> ")]
    check("tagline is not duplicated", len(taglines) == 1,
          f"{len(taglines)} taglines in the first 10 lines")

    # Per-page docs are returned verbatim by the package, so they must carry
    # their OWN title — the inverse of the index rule above.
    page = get("/iconify/llms.txt").get_data(as_text=True)
    check("per-page doc keeps its title",
          page.lstrip().startswith("# Iconify Icon Sets"),
          page.splitlines()[0] if page.strip() else "empty")
    check("zero dv-banner in markdown", llms.count("dv-banner") == 0,
          f"{llms.count('dv-banner')} found")
    check("## Network section present", "## Network" in llms)

    # Scope the directory assertions to the ## Network section. The rest of
    # llms.txt is this site's own page index, which is FULL of
    # emojimart.2plot.dev/<page>/llms.txt links — matching those would make a
    # healthy index look like a self-referencing peer list.
    network = llms.split("## Network", 1)[1] if "## Network" in llms else ""
    check("hub listed in ## Network", "https://2plot.dev" in network)
    check("does not list itself as a peer",
          "https://emojimart.2plot.dev" not in network,
          "self stripped from peers")

    # Directive leakage. Two shapes, and the second is the one that actually
    # got through: the runbook's `^\.\. \w+::` catches an unexpanded directive
    # LINE, but not the indented `:option: value` lines orphaned when a
    # directive is expanded in place and its options are left behind. Both are
    # noise in an agent's copy of the page, so check for both.
    print("\n[directive leakage]")
    directive = re.compile(r"^\s*\.\. \w+::", re.M)
    orphan_option = re.compile(r"^[ \t]+:[a-zA-Z_][a-zA-Z0-9_]*:", re.M)
    for path in ("/", "/iconify", "/popover", "/configuration", "/api-reference",
                 "/custom-emojis", "/theming", "/callbacks"):
        url = "/llms.txt" if path == "/" else f"{path}/llms.txt"
        body = get(url).get_data(as_text=True)
        # Fenced code blocks legitimately contain anything — strip them first so
        # a Python dict literal in an example cannot look like a leaked option.
        prose = re.sub(r"```.*?```", "", body, flags=re.S)
        leaked = directive.findall(prose) + orphan_option.findall(prose)
        check(f"no directive leak in {url}", not leaked,
              ", ".join(sorted({s.strip() for s in leaked})) or "clean")

    # The per-page prose must actually be the page, not a stub.
    body = get("/iconify/llms.txt").get_data(as_text=True)
    check("/iconify/llms.txt carries real prose",
          "iconify_to_emoji_mart" in body, f"{len(body):,} bytes")

    # -- sitemap -----------------------------------------------------------
    print("\n[sitemap]")
    sitemap = get("/sitemap.xml").get_data(as_text=True)
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    # Counted from the registry, never a literal: this said `== 8` and the
    # nav round's /changelog and /api made it 10 — a check that has to be
    # edited every time a page is added is a check that gets edited wrong.
    expected = len([p for p in dash.page_registry.values()
                    if not (p["path"] or "").startswith("/admin/")
                    and p["path"] != "/404"])
    check(f"sitemap lists every public page ({expected})",
          len(urls) == expected, f"{len(urls)} urls, registry says {expected}")
    check("every sitemap url is on this host",
          all(u.startswith("https://emojimart.2plot.dev") for u in urls),
          sorted(urls)[:2])

    # -- SPA beacon --------------------------------------------------------
    # The half of the ledger the boilerplate's trio does not cover.
    print("\n[spa beacon]")
    resp = client.post("/api/pageview", json={"path": "/theming"},
                       headers={"User-Agent": BROWSER_UA})
    check("/api/pageview accepts a valid path", resp.status_code == 200,
          f"HTTP {resp.status_code}")
    resp = client.post("/api/pageview", json={"path": "not-a-path"},
                       headers={"User-Agent": BROWSER_UA})
    check("/api/pageview rejects a junk path", resp.status_code == 400,
          f"HTTP {resp.status_code}")

    # -- peers resolve -----------------------------------------------------
    # The check the runbook says is worth putting in CI: a directory of dead
    # links degrades quietly and nothing else reports it.
    print("\n[peer directory]")
    # Peers only — see the scoping note above.
    peers = sorted(set(re.findall(r"https://[^\s)\]]+", network)))
    peers = [p for p in peers if "emojimart.2plot.dev" not in p]
    check("peers advertised", len(peers) >= 5, f"{len(peers)} peer hosts")
    if os.environ.get("VERIFY_PEERS") == "1":
        import time

        import requests

        # Retries and a long timeout are not optional here: most peers are on
        # Render's free tier, which sleeps after ~15 min idle and cold-starts on
        # the next request. A single 10s probe reports healthy sites as dead —
        # flows.2plot.dev and muischeduler.2plot.dev both did exactly that
        # before failing over to 200 on the second attempt.
        for url in peers:
            code: object = None
            for attempt in range(3):
                try:
                    code = requests.get(url, timeout=45).status_code
                    if code == 200:
                        break
                except Exception as exc:  # noqa: BLE001
                    code = type(exc).__name__
                time.sleep(2)
            check(f"peer resolves: {url}", code == 200, str(code))
    else:
        print("  ....  peer reachability                        "
              "SKIPPED — set VERIFY_PEERS=1 (needs network)")

    print()
    print("-" * 78)
    if failures:
        print(f" {len(failures)} FAILED: {', '.join(failures)}")
        print("-" * 78)
        return 1
    print(" all checks passed")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
