"""The social card and the installable-app surfaces.

TEMPLATE FILE: satellites copy this and change only the constants it imports.

Both things tested here fail silently and fail OUTSIDE the app, which is why
they need tests rather than a look at the page — nobody sees their own unfurls,
and no browser explains why it declined to offer an install.

The two failures this repo actually shipped, both found during the 2plot
network rollout:

1. **A duplicate og:image, one of them an SVG.** `templates/index.html`
   declared og:image and twitter:image statically, while Dash ALSO emits both
   per page (`dash/_pages.py`). With no `image_url=` passed, Dash inferred one
   from the assets folder, found `assets/logo.svg`, and emitted it alongside
   the static tag. Social scrapers reject SVG, and the inferred tag came last,
   so the carefully-described card lost to an image nothing can render.

2. **An inert manifest.** The icon set shipped in `assets/favicon/`, but the
   manifest and apple-touch-icon links were commented out with a note saying
   the files were missing — a note that outlived the files' arrival — and the
   commented-out hrefs pointed one directory too high anyway. The manifest
   itself still carried another site's name, copied in from dash-email, which
   is what an install prompt would have shown had one ever been offered.

Note where each tag comes from, because it decides which file to open when one
of these fails: `og:image`, `twitter:image` and the `twitter:*` set are DASH's
(per page, from `register_page`); `og:site_name`, the `og:image:*` auxiliaries
and the icon links are `templates/index.html`'s. dash-improve-my-llms adds a
third set, but only on the prerender path, which social scrapers do not take —
its bot list has `facebookbot` (Meta's AI training crawler), not
`facebookexternalhit` (the link-preview fetcher). That is why deleting
index.html would silently kill every unfurl.
"""

from __future__ import annotations

import json
import re
import sys

import pytest

# Site suite, not package suite — LESSONS §19.
pytest.importorskip("dash_mantine_components")
pytest.importorskip("dash_improve_my_llms")

from conftest import REPO_ROOT  # noqa: E402
from lib.constants import (  # noqa: E402
    OG_IMAGE_ALT,
    OG_IMAGE_HEIGHT,
    OG_IMAGE_TYPE,
    OG_IMAGE_URL,
    OG_IMAGE_WIDTH,
    SITE_BRAND,
    SITE_SHORT_NAME,
)

MANIFEST = REPO_ROOT / "assets" / "favicon" / "site.webmanifest"


def _visible(html: str) -> str:
    """The document with HTML comments removed.

    This file's own template documents itself with commented-out example tags,
    and a regex cannot tell those from live ones — an earlier version of this
    check reported a manifest link that was, in fact, commented out.
    """
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def _meta(html: str, value: str) -> list[str]:
    """Every `content` for a property/name — a list, so duplicates show up.

    Tags carrying `data-dimll-prerender` are excluded. dash-improve-my-llms
    injects its own description and OpenGraph block on the prerender path, and
    marks each one precisely so it can be told apart. Counting those here would
    make this test fail on a package behaviour nothing in this repo controls,
    and it would hide what the test is actually for: duplication between
    `templates/index.html` and the tags Dash generates from `register_page`.
    """
    pattern = (
        rf'<meta[^>]*(?:property|name)="{re.escape(value)}"[^>]*content="([^"]*)"'
        rf'|<meta[^>]*content="([^"]*)"[^>]*(?:property|name)="{re.escape(value)}"'
    )
    body = re.sub(r'<meta[^>]*data-dimll-prerender[^>]*>', "", _visible(html))
    return ["".join(m) for m in re.findall(pattern, body)]


# ------------------------------------------------------------- the og image --


def test_the_og_image_is_never_empty(client, page_paths):
    for path in [p for p in page_paths if not p.startswith("/admin")][:8]:
        images = _meta(client.get(path).text, "og:image")
        assert images, f"{path} declares no og:image at all"
        assert all(src.strip() for src in images), (
            f"{path} serves an EMPTY og:image {images} — the card renders blank"
        )


def test_the_image_is_declared_exactly_once(client, page_paths):
    """The duplicate-tag regression, and the reason index.html stops at alt."""
    for path in [p for p in page_paths if not p.startswith("/admin")][:8]:
        html = client.get(path).text
        assert len(_meta(html, "og:image")) == 1, (
            f"{path} has {_meta(html, 'og:image')} — a scraper picks one, and "
            "it will not be the one you meant"
        )
        assert len(_meta(html, "twitter:image")) == 1


def test_the_image_is_not_an_svg(client):
    """SVG is rejected by Facebook, Twitter/X, LinkedIn and Slack alike.

    Dash's asset inference reaches `logo.<ext>` and this repo ships
    `assets/logo.svg`, so this is one missing `image_url=` away from returning.
    """
    for prop in ("og:image", "twitter:image"):
        for src in _meta(client.get("/").text, prop):
            assert not src.lower().endswith(".svg"), f"{prop} is an SVG: {src}"


def test_the_image_is_absolute_and_matches_the_constant(client):
    for prop in ("og:image", "twitter:image"):
        values = _meta(client.get("/").text, prop)
        assert values, f"no {prop} on the home page"
        for src in values:
            assert src.startswith("http"), f"{prop}={src!r} is not absolute"
            assert src == OG_IMAGE_URL


def test_the_image_is_hosted_off_the_app(client):
    """The card must be on the CDN, not served by this app.

    Not a style rule. A card the app serves is fetched by the scraper at
    unfurl time; on a cold free-tier container that request lands mid-wake and
    times out, the preview renders blank ONCE, and the platform caches the
    miss — so the first person to share the link poisons it for everyone.

    That the URL RESOLVES is deliberately not checked here. It is off-host
    now, and reaching a third party would make this suite depend on
    Cloudflare being up (the same reason conftest disables the geo lookup).
    `scripts/smoke_live.py` fetches the real file after every deploy and
    checks its actual pixels against the constants below — which also catches
    the CDN object being replaced with something a different shape, something
    no offline test can see.
    """
    assert OG_IMAGE_URL.startswith("https://cdn.2plot.ai/github_assets/"), (
        f"{OG_IMAGE_URL} is not on the network CDN"
    )
    assert "/assets/" not in OG_IMAGE_URL, "the app is serving its own card again"


def test_the_auxiliary_image_tags_match_the_constants(client):
    """index.html hard-codes the dimensions; lib/constants.py is the source.

    A declared width/height that disagrees with the file is worse than
    declaring none — the platform reserves the wrong box and crops.
    """
    html = client.get("/").text
    assert _meta(html, "og:image:width") == [str(OG_IMAGE_WIDTH)]
    assert _meta(html, "og:image:height") == [str(OG_IMAGE_HEIGHT)]
    assert _meta(html, "og:image:alt") == [OG_IMAGE_ALT]
    assert _meta(html, "og:image:type") == [OG_IMAGE_TYPE]
    assert _meta(html, "og:image:secure_url") == [OG_IMAGE_URL], (
        "secure_url must be the same file as og:image, not a stale copy"
    )


def test_the_declared_ratio_suits_a_large_image_card():
    """`summary_large_image` wants roughly 1.91:1.

    784x741 (the app-served logo this replaced) is 1.06:1 — letterboxed into a
    wide slot with bars either side. Anything past 2:1 gets cropped instead.
    """
    ratio = OG_IMAGE_WIDTH / OG_IMAGE_HEIGHT
    assert 1.7 <= ratio <= 2.05, f"{OG_IMAGE_WIDTH}x{OG_IMAGE_HEIGHT} is {ratio:.2f}:1"


def test_the_twitter_card_is_a_large_image(client):
    assert set(_meta(client.get("/").text, "twitter:card")) == {"summary_large_image"}


def test_the_twitter_card_is_declared_in_the_form_the_spec_names(client):
    """The one tag index.html declares even though Dash emits it too.

    Dash writes its whole per-page meta set with `property=` (dash/_pages.py).
    That is correct for OpenGraph, which defines itself on RDFa, and wrong for
    the Twitter card, which the spec defines on `name=`. So a Dash site that
    leans on Dash alone declares `property="twitter:card"` in the browser
    document, while dash-improve-my-llms declares `name="twitter:card"` in the
    crawler document — the same site telling two consumers two different
    things about itself.

    In practice X, Slack and LinkedIn all fetch the crawler lane on this host
    (verified by user-agent on 2026-08-26), so the browser lane's form was
    costing no unfurl. The reason to fix it anyway is that identity parity
    between the two documents is the invariant, not any single scraper's
    leniency; `scripts/smoke_live.py`'s parity block asserts it after every
    deploy, and this is the offline half.

    Pinning BOTH forms is the point. Dropping the static one loses the spec
    form; dropping Dash's is not this repo's to do; and either one changing
    value while the other does not is the drift worth catching.
    """
    html = client.get("/").text
    for attr in ("name", "property"):
        found = re.findall(
            rf'<meta[^>]*{attr}="twitter:card"[^>]*content="([^"]*)"', html
        )
        assert found == ["summary_large_image"], (
            f'{attr}="twitter:card" is {found}, expected exactly one '
            '"summary_large_image" — the static tag lives in '
            "templates/index.html, Dash's comes from register_page"
        )


def test_no_meta_tag_dash_emits_is_also_declared_statically(client):
    """The rule the OG and Twitter blocks in index.html are built on.

    Dash emits all of these per page. A static copy in the template makes two
    of each, and the static one describes the SITE where Dash's describes the
    PAGE — so the duplicate is both redundant and the less accurate of the
    two. Every one of these shipped doubled before the rollout.

    `twitter:card` is deliberately NOT in this list, and its absence is the
    interesting part. The rule above rests on the static copy being the less
    accurate one, which is true of every per-page value here and false of the
    card type: it is `summary_large_image` on every page of this site. With no
    accuracy to lose, the duplicate buys the `name=` form the spec defines and
    Dash never emits — see the test above, which pins that pair exactly, so
    the tag is not merely exempted here but checked harder elsewhere.
    """
    html = client.get("/").text
    for tag in ("description", "og:type", "og:title", "og:description",
                "og:image", "twitter:url", "twitter:title",
                "twitter:description", "twitter:image"):
        found = _meta(html, tag)
        assert len(found) <= 1, f"{tag} is declared {len(found)} times: {found}"


def test_the_tags_dash_omits_are_declared_here(client):
    """The other half of the rule — do not delete these thinking Dash covers them.

    `og:url` is in the donor's list and NOT in this one, on purpose. STANDARD
    §3 scopes it: the template declares og:url only "on hosts where dimll
    doesn't emit it". Measured on this host, `prerender.build_head_tags` emits
    a per-page og:url pointed at the canonical URL — so declaring it statically
    here would add a second, always-"/" copy of a tag that is already correct.
    test_the_prerender_supplies_og_url below is the guard on that assumption.
    """
    html = client.get("/").text
    for tag in ("og:site_name", "og:image:alt", "twitter:image:alt",
                "og:image:secure_url", "og:image:type",
                "og:image:width", "og:image:height"):
        assert _meta(html, tag), f"{tag} is missing and Dash does not emit it"


def test_the_prerender_supplies_og_url(client):
    """Why templates/index.html is allowed to omit og:url.

    `_meta` strips prerender-marked tags, so this looks at the raw document.
    If a dimll upgrade ever stops emitting og:url, this fails and the tag has
    to move into the template — which is exactly the decision the test above
    depends on.
    """
    html = client.get("/popover").text
    assert 'data-dimll-prerender="1" property="og:url"' in html, (
        "the prerender no longer emits og:url — declare it in templates/index.html"
    )


# ------------------------------------------------------------- the manifest --
#
# Ported from the donor now that there is a surface to assert against. This
# repo had no `assets/favicon/` at all until the brand pass; everything below is
# generated by `scripts/make_brand_assets.py` from one source glyph, which is
# what keeps the manifest, the icons and lib/constants.py from drifting apart.
#
# Nothing here errors when it breaks. A wrong manifest does not raise — the
# browser simply declines to offer an install, silently, forever.


def test_the_manifest_is_linked_and_served(client):
    html = _visible(client.get("/").text)
    assert 'rel="manifest"' in html, "no manifest link — no install prompt"
    match = re.search(r'<link[^>]+rel="manifest"[^>]+href="([^"]+)"', html)
    assert match
    assert client.get(match.group(1)).ok, "the manifest link 404s"


def test_the_manifest_describes_THIS_site(client):
    """An installed app takes its home-screen label from `short_name`.

    That is the one place a wrong string becomes a permanent icon on someone's
    phone, so it is pinned to the constants rather than to a literal.
    """
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["name"] == SITE_BRAND
    assert manifest["short_name"] == SITE_SHORT_NAME
    # The donor's fork-source guard, kept: a manifest copied between repos is
    # exactly how "Dash Email" ended up naming another site's app.
    for foreign in ("Dash Email", "Boilerplate", "dash-leaflet2"):
        assert foreign not in manifest["name"]
        assert foreign not in manifest["short_name"]


def test_the_manifest_is_installable():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["name"].strip(), "empty name — no browser will offer install"
    assert manifest["short_name"].strip(), "empty short_name"
    assert manifest["start_url"] == "/"
    assert manifest["display"] == "standalone"


def test_every_manifest_icon_resolves(client):
    manifest = json.loads(MANIFEST.read_text())
    icons = manifest.get("icons") or []
    assert icons, "the manifest declares no icons"
    for icon in icons:
        assert client.get(icon["src"]).ok, f"manifest icon {icon['src']} 404s"
    # Chrome will not offer an install prompt without both of these.
    assert any(i.get("sizes") == "192x192" for i in icons)
    assert any(i.get("sizes") == "512x512" for i in icons)


def test_the_apple_touch_icon_is_declared_and_resolves(client):
    """iOS ignores the manifest and uses this for Add to Home Screen."""
    html = _visible(client.get("/").text)
    match = re.search(r'<link[^>]*rel="apple-touch-icon"[^>]*href="([^"]+)"', html)
    assert match, "no apple-touch-icon link"
    assert client.get(match.group(1)).ok, f"{match.group(1)} does not resolve"


def test_the_apple_touch_icon_has_no_alpha_channel():
    """iOS composites a transparent icon onto WHITE.

    A dark-themed site that ships an alpha apple-touch-icon gets a glaring
    white tile on the home screen — which nobody sees unless they own an
    iPhone and add the site to it.

    Read from the PNG header rather than with Pillow, on purpose. Pillow is a
    BUILD-time dependency and is deliberately absent from requirements.txt, so
    a test that imports it passes on the machine that generated the icons and
    fails in CI, in the container, and on a fresh checkout. It did.

    The IHDR is fixed-layout: 8-byte signature, 4-byte length, "IHDR", width,
    height, bit depth, then colour type at byte 25. 2 is truecolour with no
    alpha channel at all; 4 and 6 carry one. `scripts/make_brand_assets.py`
    emits RGB for this file specifically so the question is structural instead
    of needing a per-pixel scan.
    """
    raw = (REPO_ROOT / "assets" / "favicon" / "apple-touch-icon.png").read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    colour_type = raw[25]
    assert colour_type in (0, 2), (
        f"apple-touch-icon.png declares PNG colour type {colour_type}, which "
        "carries an alpha channel; iOS will back transparent pixels with white"
    )


def test_the_theme_colour_agrees_with_the_manifest(client):
    """A mismatch is one colour in the browser chrome, another on the splash."""
    manifest = json.loads(MANIFEST.read_text())
    declared = _meta(client.get("/").text, "theme-color")
    assert declared, "no theme-color"
    assert declared[0].lower() == manifest["theme_color"].lower()


def test_the_generated_assets_are_current():
    """The manifest is generated; a hand-edit or a stale run must show up here.

    `--check` re-derives the manifest from lib/constants.py and compares. It is
    the same guard `scripts/make_brand_assets.py` offers CI, run in-process so
    the suite catches it without a separate job.
    """
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/make_brand_assets.py", "--check"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_every_asset_the_template_references_resolves(client):
    """The half-landed-commit guard.

    1.2.1 shipped a template pointing at `/assets/favicon/…` while the icon
    set and this very file sat UNTRACKED in git. The deploy builds from git,
    so production 404'd the manifest, the apple-touch-icon and every PNG icon
    — the whole installable-app surface — for a day, while every local boot
    looked perfect because the files were on disk. `git status` was the only
    place it showed.

    A checkout is what CI tests, so this fails there the moment a referenced
    asset is not committed. It is deliberately broader than the manifest and
    apple-touch-icon checks above: the failure was never specific to icons,
    it was "the template references a file the repository does not have".
    """
    html = _visible(client.get("/").text)
    referenced = sorted(set(re.findall(r'(?:href|content|src)="(/assets/[^"]+)"', html)))
    assert referenced, "no /assets/ references found — did the template change?"

    missing = [ref for ref in referenced if not client.get(ref).ok]
    assert missing == [], (
        f"templates/index.html references assets that do not resolve: {missing}. "
        "If they exist on disk, they are untracked — the deploy builds from git."
    )


def test_the_index_template_is_still_wired_in(app_module):
    """`templates/index.html` looks removable and is not.

    dash-improve-my-llms appears to cover OG, but its injection runs only on
    the prerender path, which social scrapers do not take. Deleting the
    template kills every unfurl, the icons and the manifest at once.
    """
    index = (REPO_ROOT / "templates" / "index.html").read_text()
    for placeholder in ("{%metas%}", "{%favicon%}", "{%css%}", "{%app_entry%}",
                        "{%config%}", "{%scripts%}", "{%renderer%}"):
        assert placeholder in index, f"{placeholder} missing from the template"
    assert app_module.app.index_string.startswith("<!DOCTYPE html>")
