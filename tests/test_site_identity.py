"""Site identity: one brand, every surface, verbatim.

Ported from dash-documentation-boilerplate 1.2.4 and re-pointed at this repo's
surfaces. The network standard says a site states what it is in the same words
everywhere an agent or a reader can reach. The failure this pins is silent,
which is why it needs tests rather than a code review: nothing errors when a
surface falls back to a default.

dash-improve-my-llms 2.3.4's `resolve_site_title` is what makes the fix
possible: it takes the home page's registered `name` first, `app.title` second,
and *skips* generic candidates ("Home", "Index", "Dash") rather than publishing
them. These tests assert both ends of that — the inputs this repo controls, and
the H1 it produces.

WHERE THIS REPO DIFFERS FROM THE TEMPLATE
-----------------------------------------
1. **The brand leads with the package name.** The boilerplate asserts the
   opposite (`dash-documentation-boilerplate` must NOT be in its brand) because
   nobody installs a template. This is a component library: the package is what
   a reader came to find, so `dash-emoji-mart` belongs in the brand and the
   test below is inverted from the donor's on purpose.
2. **There is no `pages/home.md` with a literal `# ` H1.** Pages here are
   `docs/<slug>/<slug>.md` and the on-page heading is rendered by
   `pages/markdown.py` from frontmatter, so the assertion is against the
   rendered heading rather than a markdown line.
"""

from __future__ import annotations

import re

import pytest

# Site suite, not package suite: these need the docs-site dependency set
# (requirements.txt), and CI's package-only compat matrix installs just the
# wheel. Without this guard that matrix fails on an import error that says
# nothing about the package under test — LESSONS §19.
pytest.importorskip("dash_mantine_components")
pytest.importorskip("dash_improve_my_llms")

from conftest import REPO_ROOT  # noqa: E402
from lib.constants import (  # noqa: E402
    PAGE_TITLE_PREFIX,
    SITE_BRAND,
    SITE_DESCRIPTION,
    SITE_SHORT_NAME,
    SITE_TITLE,
)

# Spelled out rather than imported, so that renaming the constant cannot
# silently rename the site. Changing the brand should require changing this
# line, deliberately.
EXPECTED_BRAND = "dash-emoji-mart — emoji picker for Dash"

# A page that certainly exists, for the surfaces that need a concrete URL.
A_REAL_PAGE = "/popover"


def test_brand_constant_is_the_agreed_identity():
    assert SITE_BRAND == EXPECTED_BRAND


def test_site_title_is_not_a_second_source_of_truth():
    """`SITE_TITLE` predates `SITE_BRAND` here and run.py still passes it."""
    assert SITE_TITLE == SITE_BRAND


def test_app_title_is_the_brand(app):
    """`Dash(title=...)` — the <title> and `resolve_site_title`'s fallback."""
    assert app.title == EXPECTED_BRAND


def test_template_fallback_title_is_the_brand():
    """What the served HTML carries if the prerender is ever rolled back."""
    html = (REPO_ROOT / "templates" / "index.html").read_text()
    assert f"<title>{EXPECTED_BRAND}</title>" in html


def test_home_page_heading_is_the_brand(client):
    """The root's own H1.

    Every other page heads itself with its frontmatter `name`, which is also
    its sidebar label. The home page's label is "Home", which names nothing —
    so `pages/markdown.py` substitutes the brand for the root page only. This
    asserts the substitution survived, because losing it leaves the most-linked
    URL on the site as the only page that never says what the site is.
    """
    body = client.get("/").text
    assert EXPECTED_BRAND in body


def test_llms_index_h1_is_the_brand(client):
    """The single most-read line of this site, and the one nobody looks at."""
    response = client.get("/llms.txt")
    assert response.ok
    assert response.text.splitlines()[0] == f"# {EXPECTED_BRAND}"


def test_llms_index_tagline_is_the_description(client):
    body = client.get("/llms.txt").text
    assert f"> {SITE_DESCRIPTION}" in body


def test_the_viewer_brand_chip_is_not_a_framework_default(client):
    """The chip that reads a bare "Dash" on a pre-2.3.4 artifact.

    Rendered from the same `resolve_site_title` call as the H1, so asserting
    the brand is present catches both a stale package and a regressed constant.
    """
    import html as html_module

    from conftest import BROWSER_ACCEPT

    page = client.get(f"{A_REAL_PAGE}/llms.txt", accept=BROWSER_ACCEPT).text
    # The banner is templated markup, so the brand may arrive escaped.
    assert (EXPECTED_BRAND in page) or (html_module.escape(EXPECTED_BRAND) in page), (
        "the viewer banner does not name this site"
    )


def test_the_package_name_leads_the_brand_and_the_byline_does_not():
    """Naming rules from the standard — inverted from the boilerplate's.

    STANDARD §1's library rule: the package name comes FIRST in the brand,
    because for a component library the package is what a reader came to find.
    "Pip Install Python" is the byline and belongs in the description only; a
    brand of "Pip Install Python" would make every satellite share one name.
    """
    assert SITE_BRAND.startswith("dash-emoji-mart")
    assert "dash-emoji-mart" in SITE_DESCRIPTION
    assert "Pip Install Python" in SITE_DESCRIPTION
    assert "Pip Install Python" not in SITE_BRAND


def test_no_surface_falls_back_to_a_generic_title():
    """The values `resolve_site_title` is designed to skip."""
    from dash_improve_my_llms.handlers import _GENERIC_SITE_TITLES

    assert SITE_BRAND.strip().lower() not in _GENERIC_SITE_TITLES


def test_readme_states_the_brand():
    """A README that names the site differently is the next drift."""
    readme = (REPO_ROOT / "README.md").read_text()
    assert EXPECTED_BRAND in readme, "README.md does not state the site brand"


def test_llms_package_floor_is_the_network_standard():
    """Identity resolution lives in the package; the floor is what delivers it."""
    import dash_improve_my_llms as pkg

    parts = tuple(int(p) for p in pkg.__version__.split(".")[:3] if p.isdigit())
    assert parts >= (2, 5, 1), (
        f"dash-improve-my-llms {pkg.__version__} is below the network's "
        "402-instrumentation floor; the tier wiring in run.py would be dead "
        "code and the prerender's title handling reverts to the pre-2.5 "
        "override this suite used to pin"
    )


def test_the_requirements_floor_matches():
    """The installed version proves nothing about what CI or Render installs."""
    reqs = (REPO_ROOT / "requirements.txt").read_text()
    assert "dash-improve-my-llms[flask]>=2.5.1" in reqs


# ---------------------------------------------------------------------------
# The per-page title — a share-card surface, not just a browser tab
#
# Dash passes each page's `title` straight into `og:title` and `twitter:title`
# (dash/_pages.py `_page_meta_tags`), so PAGE_TITLE_PREFIX sets the headline of
# every unfurl this site produces. Nobody sees their own share cards.
# ---------------------------------------------------------------------------


def test_the_page_title_prefix_is_derived_from_the_short_name():
    assert PAGE_TITLE_PREFIX == f"{SITE_SHORT_NAME} | "


def test_the_short_name_cannot_drift_from_the_brand():
    """Two constants, one identity. Derived, so this should be automatic."""
    assert SITE_BRAND.startswith(SITE_SHORT_NAME)


def test_no_share_card_tag_is_empty(client):
    """The failure LESSONS §1 is about: a declared-but-blank tag.

    Scrapers take the LAST tag of a kind, so one page missing `image_url=` or
    `description=` publishes `content=""` and unfurls as a blank card even
    though a correct tag sits earlier in the head.
    """
    html = client.get(A_REAL_PAGE).text
    for tag in ("og:title", "og:description", "og:image",
                "twitter:title", "twitter:description", "twitter:image"):
        for value in re.findall(
            rf'<meta[^>]*(?:property|name)="{tag}"[^>]*content="([^"]*)"', html
        ):
            assert value.strip(), f"{tag} is declared empty on {A_REAL_PAGE}"


def test_dash_emits_the_prefixed_title(client):
    """The scraper-winning og:title carries PAGE_TITLE_PREFIX.

    RE-MEASURED 2026-08-16 on dash-improve-my-llms 2.5.1 (the 1.3.x sync's
    floor): the prerender no longer appends its own bare-name og:title, so the
    document now carries exactly one, and it is Dash's prefixed tag —
    "dash-emoji-mart | Picker in a Popover". The 2.3.4-era pin that documented
    the old override (`test_measured_upstream_the_prerender_overrides_dash_title`)
    failed on the upgrade exactly as its docstring predicted and was deleted
    per its own instructions; this test is the tightened survivor. Scrapers
    take the LAST tag of a kind, so the last one is the one that must carry
    the prefix.
    """
    html = client.get(A_REAL_PAGE).text
    titles = re.findall(
        r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html
    )
    assert titles, f"no og:title on {A_REAL_PAGE}"
    assert titles[-1].startswith(PAGE_TITLE_PREFIX), (
        f"the scraper-winning og:title lost {PAGE_TITLE_PREFIX!r}; got {titles!r}"
    )


def test_exactly_one_og_image_in_the_raw_document(client):
    """The rule `scripts/smoke_live.py` enforces after every deploy.

    It counts og:image in the RAW document — prerender-marked tags included —
    and requires exactly one. tests/test_social_card.py's `_meta` helper
    strips the prerender's tags, so this is the only place the raw count is
    checked, and without it a change that adds a second tag passes the whole
    local suite and fails the deploy gate.

    That is not hypothetical: passing `og_image=` to `register_page_metadata`
    does exactly that. It works — the prerender emits the tag — and it takes
    the count to two. See the long note in pages/markdown.py.
    """
    from lib.constants import OG_IMAGE_URL

    for path in ("/", A_REAL_PAGE):
        images = re.findall(
            r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"',
            client.get(path).text,
        )
        assert images == [OG_IMAGE_URL], (
            f"{path} declares og:image {images!r}; smoke_live requires exactly "
            f"one, equal to {OG_IMAGE_URL!r}"
        )


def test_identity_publishing_files_agree_on_the_brand():
    """A sweep, scoped to the files that PUBLISH identity.

    Deliberately NOT a whole-repo grep — LESSONS §7. This repo's prose
    legitimately describes the picker in other words all over docs/, and a
    broad sweep would flag every one of them.
    """
    offenders = []
    for path in ("lib/constants.py", "templates/index.html"):
        text = (REPO_ROOT / path).read_text()
        if EXPECTED_BRAND not in text:
            offenders.append(path)
    assert offenders == [], f"the brand is missing from {offenders}"


def test_the_superseded_site_title_is_gone():
    """The pre-pass string, which disagreed with the brand by two words.

    "dash-emoji-mart — an emoji picker for Dash 4" was the old SITE_TITLE and
    the old <title>. Close enough to look right in a diff, different enough
    that /llms.txt and the share cards would have advertised two names.
    """
    old = "an emoji picker for Dash 4"
    for path in ("lib/constants.py", "templates/index.html"):
        text = (REPO_ROOT / path).read_text()
        stripped = re.sub(r"#.*", "", text) if path.endswith(".py") else text
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.S)
        assert old not in stripped, f"{path} still carries the superseded title"
