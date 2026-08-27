"""dimll 2.6.0's SEO honesty features, pinned from the app's side.

Two contracts land with the 2.6.0 floor:

1. **Icon discovery agrees with the declaration.** This app still declares
   `configure_seo(icons=[...])` explicitly (declared wins), but the fleet's
   satellites will increasingly rely on discovery alone — so the reference
   host proves the two produce the SAME set. Set-equality, not order: the
   release notes are explicit that discovery orders differently
   (.ico first, biggest square descending, apple-touch last) and that
   order-inequality is not a failure.

2. **The sitemap tells the truth or says nothing.** `<lastmod>` is emitted
   verbatim from frontmatter `lastmod:` and omitted when unset. No date in
   the sitemap may exist that no page declared — the invented daily "today"
   is the exact lie 2.6.0 exists to end.
"""

from __future__ import annotations

import re
from pathlib import Path


def _normalize(entries):
    """(rel, href, sizes) triples from the package's mixed icon shapes."""
    out = set()
    for e in entries:
        if isinstance(e, str):
            out.add(("icon", e, None))
        else:
            out.add((e.get("rel", "icon"), e["href"], e.get("sizes")))
    return out


def test_discovery_agrees_with_the_declared_icons(app):
    from dash_improve_my_llms.seo import _config, discover_icons

    declared = _normalize(_config.icons or [])
    discovered = _normalize(discover_icons(app))

    assert declared, "configure_seo(icons=) is no longer declared in run.py?"
    assert discovered, "discovery found nothing in assets/ — pattern drift?"
    assert declared == discovered, (
        "Declared and discovered icon sets diverged.\n"
        f"declared only:   {sorted(declared - discovered)}\n"
        f"discovered only: {sorted(discovered - declared)}\n"
        "If a favicon file was added/renamed, update run.py's icons list — "
        "or if discovery's patterns changed upstream, this is the canary."
    )


def test_the_browser_head_declares_the_same_icons_as_the_crawler_head(app):
    """The third side of the icon triangle, and the one nothing was checking.

    `test_discovery_agrees_with_the_declared_icons` above pins run.py's list
    against what dimll discovers on disk. run.py's list is also what builds
    the CRAWLER document's head. Nothing pinned it against the BROWSER
    document's head — the `<link rel="icon">` tags in templates/index.html —
    even though run.py's own comment promises they are "the SAME four files
    templates/index.html links, so the browser head and the crawler head
    cannot drift apart".

    They had drifted, both ways: the .ico declared `sizes="any"` here and
    nothing there, apple-touch-icon declared `180x180` there and nothing here.
    Neither is visible from inside the app — every offline test read one side
    or the other, never the pair — and it took `scripts/smoke_live.py`'s
    crawler/browser identity parity block, running against production on
    2026-08-26, to see it. This is the same assertion moved offline, so the
    next drift costs a test run instead of a red deploy.

    Compared as (rel, href, sizes) triples, unordered: emission order differs
    between the two heads by design, and Dash injects an extra cache-busting
    favicon link into the browser head that belongs to neither list.
    """
    from dash_improve_my_llms.seo import _config

    declared = _normalize(_config.icons or [])
    assert declared, "configure_seo(icons=) is no longer declared in run.py?"

    html = (Path(__file__).resolve().parent.parent / "templates" / "index.html").read_text()
    linked = set()
    for tag in re.findall(r'<link[^>]+rel="(?:icon|apple-touch-icon)"[^>]*>', html):
        rel = re.search(r'rel="([^"]+)"', tag).group(1)
        href = re.search(r'href="([^"]+)"', tag).group(1)
        sizes = re.search(r'sizes="([^"]+)"', tag)
        linked.add((rel, href, sizes.group(1) if sizes else None))

    assert linked == declared, (
        "The browser head and the crawler head declare different icons.\n"
        f"run.py only:      {sorted(declared - linked)}\n"
        f"index.html only:  {sorted(linked - declared)}\n"
        "Both lists describe the same files; move them together. Identity may "
        "not differ between the two documents — content is what the prerender "
        "is for."
    )


def _declared_lastmods() -> set[str]:
    dates = set()
    for md in Path("docs").glob("**/*.md"):
        head = md.read_text().split("---")[1] if md.read_text().startswith("---") else ""
        m = re.search(r"^lastmod:\s*(\d{4}-\d{2}-\d{2})\s*$", head, re.MULTILINE)
        if m:
            dates.add(m.group(1))
    return dates


def test_sitemap_lastmod_is_verbatim_or_absent(client):
    sitemap = client.get("/sitemap.xml").text
    emitted = re.findall(r"<lastmod>([^<]+)</lastmod>", sitemap)
    declared = _declared_lastmods()

    assert emitted, (
        "No <lastmod> anywhere — the frontmatter stamps were removed? "
        "Truth-or-silence allows silence per page, but the docs set "
        "deliberately declares real dates."
    )
    undeclared = [d for d in emitted if d not in declared]
    assert not undeclared, (
        f"Sitemap emits dates nobody declared: {undeclared} — an invented "
        "date is the lie that gets the whole sitemap discarded."
    )

    # The home page declares no lastmod; its <url> entry must carry none.
    home_block = re.search(
        r"<url>\s*<loc>[^<]*?://[^/<]+/</loc>.*?</url>", sitemap, re.DOTALL
    )
    assert home_block and "<lastmod>" not in home_block.group(0), (
        "The home page's sitemap entry carries a lastmod it never declared."
    )


def test_prerender_rides_the_generic_lane_and_is_visible(client):
    """The universal prerender must be in the initial HTML for a PLAIN client,
    and must not be `hidden`.

    Two failures, one test, because they were discovered together.

    The lane: every other test in this suite that reads a rendered document
    fetches with a crawler user-agent, which exercises dash-improve-my-llms'
    separate BOT-document path. A regression that UA-gated the universal lane
    would therefore have been invisible here — the crawler tests would keep
    passing while browsers got an empty shell. This fetches with the default
    (browser) UA on purpose.

    The visibility: dimll <= 2.6.0 emitted this block with a literal `hidden`
    attribute, so every visibility-respecting reader — html-to-text extractors,
    and arguably crawler content-weighting — saw "Loading..." and nothing else
    while the prose sat in the markup unread. Present and invisible, the worst
    of both. 2.6.1 serves it visible and hides it with a synchronous inline
    script only JS browsers run, so humans see no flash and React's mount wipes
    the pair as before.

    Measured live on this host 2026-08-22: the deploy that was supposed to
    "pick up 2.6.1" was still serving 2.6.0's hidden div, because `>=2.6.0`
    permitted the new version without requiring it and Docker's cached
    dependency layer had no reason to re-resolve. The floor in requirements.txt
    is >=2.7.1 (2.6.1 for this behaviour) for exactly that reason, and this is its pin from the app's side.
    """
    import re

    for path in ("/", "/popover"):
        html = client.get(path).text  # default UA — the point of the test
        div = re.search(r'<div id="dimll-prerender"[^>]*>', html)
        assert div, (
            f"{path}: no prerender block for a generic client — the universal "
            "lane is gated or off"
        )
        assert "hidden" not in div.group(0), (
            f"{path}: the prerender div carries `hidden` again — "
            "visibility-respecting consumers are back to reading 'Loading...'; "
            "the dimll floor is >=2.7.1, and was raised to 2.6.1 for exactly this"
        )
        assert 'data-dimll-prerender="1">document.getElementById' in html, (
            f"{path}: the marked synchronous hide script is missing — JS "
            "browsers would flash the prose before React mounts"
        )
