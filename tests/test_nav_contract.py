"""The navigation contract (1.6.38) — uniform where it must be, free where it may.

Owner's brief of 2026-08-30 (DESIGN-navigation-uniformity): the sidebar's
sections come from frontmatter against CATEGORY_ORDER; the network is ONE
registry rendered as the top bar's Other Apps menu; Resources is one
constant; Admin is owner-only and absent from the tree otherwise; every
icon-only control has a name; no `dcc.*` where DMC has the component. Each
pin here is one line of that brief.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ALLOWED_DCC = {"Location", "Store", "Interval", "Upload", "Graph"}


def _calls(src: str, name: str):
    """Yield the source text of every `name(` call, parens balanced."""
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 0, m.start()
        while i < len(src):
            if src[i] == "(":
                depth += 1
            elif src[i] == ")":
                depth -= 1
                if depth == 0:
                    yield src[m.start():i + 1]
                    break
            i += 1


# ------------------------------------------------------------- a11y --


@pytest.mark.parametrize("control", ["dmc.Burger", "dmc.ActionIcon"])
def test_every_icon_only_control_in_components_has_a_name(control):
    """Requirement 9: the audits named the unlabelled Burger and copy
    button. Every Burger/ActionIcon in components/ carries aria-label."""
    unlabelled = []
    for path in sorted((REPO / "components").glob("*.py")):
        for call in _calls(path.read_text(), control):
            if "aria-label" not in call:
                unlabelled.append(f"{path.name}: {call[:60]}…")
    assert unlabelled == [], unlabelled


def test_code_highlight_copy_button_has_a_name():
    src = (REPO / "lib" / "directives" / "source.py").read_text()
    assert "copyLabel=" in src and "copiedLabel=" in src


def test_no_dcc_where_dmc_has_the_component():
    """Requirement 10, fleet-wide: `dcc.` only for Location, Store,
    Interval, Upload, Graph (no DMC equivalent)."""
    offenders = []
    for folder in ("pages", "components"):
        for path in sorted((REPO / folder).glob("*.py")):
            code = "\n".join(line for line in path.read_text().splitlines()
                             if not line.lstrip().startswith("#"))
            for m in re.finditer(r"\bdcc\.([A-Za-z]+)", code):
                if m.group(1) not in ALLOWED_DCC:
                    offenders.append(f"{folder}/{path.name}: dcc.{m.group(1)}")
    assert offenders == [], offenders


def test_the_traffic_page_uses_a_date_picker_not_a_dropdown():
    src = (REPO / "pages" / "traffic.py").read_text()
    assert "dcc.Dropdown" not in src
    assert "dmc.DatePickerInput" in src and 'valueFormat="YYYY-MM-DD"' in src
    assert "presets=" in src and "minDate=" in src and "maxDate=" in src


# --------------------------------------------------------- registry --


def test_other_apps_menu_is_the_registrys_primary_set(app_module):
    """Requirement 4 + the owner's review (2026-08-30): the PRIMARY
    applications only — never the docs subdomains — from the registry,
    no duplicates, self omitted, short labels (the domain)."""
    from components.header import create_other_apps_menu
    from lib.constants import BASE_URL
    from lib.network_directory import AFFILIATED, PEERS, PRIMARY, other_apps_for

    menu = create_other_apps_menu()
    items = menu.children[1].children
    hrefs = [i.href for i in items]
    expected = [e["url"] for e in other_apps_for(BASE_URL)]
    assert hrefs == expected
    assert set(h.rstrip("/") for h in hrefs) == PRIMARY - {BASE_URL.rstrip("/")}
    assert {"https://2plot.ai", "https://2plot.dev", "https://2plot.media",
            "https://piratesbargain.com", "https://ai-agent.buzz"} == set(PRIMARY)
    assert PRIMARY <= {e["url"].rstrip("/") for e in PEERS + AFFILIATED}, "PRIMARY names a URL the registry lacks"
    assert not any(".2plot.dev" in h for h in hrefs), "a docs subdomain leaked into the menu"
    assert len(set(hrefs)) == len(hrefs), "a host is listed twice"
    for item in items:
        label = item.children
        assert "." in label and " " not in label and "—" not in label, label
        assert item.target == "_blank"


def test_resources_are_third_party_only():
    """Owner's review (2026-08-30): the sidebar's Resources holds dmc and
    the upstream project(s) only; the owner's own links are top bar + footer.

    ADAPTED FROM THE TEMPLATE'S COPY, and the change is the point. Upstream
    banned the substring "github.com" — which works only for a fork whose
    UPSTREAM is None, as the template's is. Every component fork in the
    fleet wraps a project hosted ON GitHub (emoji-mart here, and Leaflet,
    React Flow, FlexLayout, Excalidraw, model-viewer, Pannellum elsewhere),
    so that ban forbids the one link the item exists to add. What the
    requirement actually says is that the OWNER's links do not appear here,
    so that is what this asserts: the owner's repo, profile, Discord and
    YouTube by value, plus the two named removals.
    """
    from lib.constants import (
        DISCORD_URL, GITHUB_PROFILE_URL, GITHUB_URL, YOUTUBE_URL, resources,
    )

    items = resources()
    assert items[0]["label"] == "dmc" and items[0]["url"] == "https://www.dash-mantine-components.com/"
    urls = [r["url"] for r in items]
    for banned in (GITHUB_URL, GITHUB_PROFILE_URL, DISCORD_URL, YOUTUBE_URL,
                   "pip-install-python", "discord", "youtube",
                   "community.plotly.com", "https://2plot.dev"):
        assert not any(banned in u for u in urls), banned
    # And every remaining entry really is third-party.
    assert all("2plot" not in u for u in urls), urls


def test_github_icon_and_same_as_share_one_constant(app_module):
    from components.header import create_header
    from lib.constants import GITHUB_URL, SAME_AS

    assert GITHUB_URL in SAME_AS
    assert GITHUB_URL.startswith("https://github.com/pip-install-python/")
    assert GITHUB_URL.count("/") == 4, "the REPOSITORY, not the profile"
    assert GITHUB_URL in str(create_header([]))


# ---------------------------------------------------------- sidebar --


def test_sections_follow_category_order_and_never_hold_admin(app_module):
    import dash

    from components.navbar import sections_for
    from lib.constants import CATEGORY_ORDER

    data = list(dash.page_registry.values())
    sections = sections_for(data)
    titles = [t for t, _ in sections]
    known = [t for t in titles if t in CATEGORY_ORDER]
    assert known == [c for c in CATEGORY_ORDER if c in titles], titles
    for _, entries in sections:
        assert not any(e["path"].startswith("/admin/") for e in entries)
        assert not any(e["path"] in ("/", "/changelog", "/api") for e in entries)
    # the template's own docs all declare a category
    assert "Documentation" not in titles, "a docs page lost its category: frontmatter"


def test_frontmatter_order_sorts_within_a_section(app_module):
    import dash

    from components.navbar import sections_for

    for title, entries in sections_for(dash.page_registry.values()):
        orders = [int(e.get("order") or 1000) for e in entries]
        assert orders == sorted(orders), (title, orders)


def test_anonymous_tree_has_no_admin_href(app_module, monkeypatch):
    """Requirement 7: hidden, not blocked. The startup tree carries only an
    empty Admin placeholder; the callback returns nothing to a non-admin."""
    import dash

    from components.navbar import create_content, render_admin_section

    tree = str(create_content(dash.page_registry.values()))
    assert "/admin/" not in tree
    assert "navbar-admin-desktop" in tree
    monkeypatch.delenv("ALLOW_UNGATED_ADMIN", raising=False)
    assert render_admin_section("navbar-admin-desktop") == (None, None)


def test_admin_tree_lists_every_admin_page(app_module, monkeypatch):
    from components.navbar import render_admin_section

    monkeypatch.setenv("ALLOW_UNGATED_ADMIN", "1")
    desktop, mobile = render_admin_section("navbar-admin-desktop")
    text = str(desktop)
    assert "/admin/control-board" in text and "/admin/traffic" in text
    assert str(mobile) == text


def test_search_lists_only_sidebar_pages(app_module):
    import dash

    from components.navbar import search_data

    values = [d["value"] for d in search_data(dash.page_registry.values())]
    assert values and not any(v.startswith("/admin/") for v in values)
    assert "/" not in values and "/changelog" not in values


# ---------------------------------------------------------- footer --


def test_footer_is_the_contract(app_module):
    from datetime import datetime

    from components.footer import create_footer
    from lib.constants import DISCORD_URL, GITHUB_PROFILE_URL, GITHUB_URL, YOUTUBE_SUBSCRIBE_URL

    text = str(create_footer())
    assert f"© {datetime.now().year} Pip Install Python LLC" in text
    for href in (GITHUB_PROFILE_URL, DISCORD_URL, YOUTUBE_SUBSCRIBE_URL):
        assert href in text
    assert GITHUB_URL not in text, "the repo link is the top bar's; the footer links the profile"
    assert "/changelog" not in text, "the sidebar's single Changelog link is the one"
    assert "/terms" not in text and "/privacy" not in text


# ------------------------------------------------------- changelog --


def test_changelog_page_is_the_file(app_module, client):
    from pages.changelog import parse_changelog

    versions = parse_changelog()
    newest = re.search(r"^## \[([^\]]+)\]", (REPO / "CHANGELOG.md").read_text(), re.M).group(1)
    assert versions and versions[0]["version"] == newest
    doc = client.get("/changelog/llms.txt", user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert doc.status == 200
    assert doc.text.startswith("# Changelog") and "\n# Changelog" not in doc.text, "the file's H1 was not deduplicated"
    assert f"## [{newest}]" in doc.text
    page = client.get("/changelog", user_agent="Mozilla/5.0 (compatible; Googlebot/2.1)")
    assert page.status == 200 and newest in page.text


# ------------------------------------------------------------- api --


def test_api_reference_reads_a_dash_package_metadata():
    from lib import api_reference

    comps = api_reference.load_package("tests.fixtures.fake_dash_pkg")
    names = [c["name"] for c in comps]
    assert names == ["FakeGauge", "FakeWidget"], "sorted, exported only"
    widget = comps[1]
    props = {p["name"]: p for p in widget["props"]}
    assert "setProps" not in props
    assert props["value"]["required"] and props["value"]["default"] == "0"
    assert props["variant"]["type"].startswith("one of ")
    assert widget["props"][0]["name"] == "id"
    md = api_reference.as_markdown(["tests.fixtures.fake_dash_pkg"])
    assert "| `value` * | number | 0 | Current value. |" in md


def test_api_page_renders_one_table_per_component():
    from pages.api import build_page

    text = str(build_page(["tests.fixtures.fake_dash_pkg"]))
    assert "api-table-FakeWidget" in text and "api-table-FakeGauge" in text
    assert "Current value." in text


def test_the_api_page_is_registered_for_this_fork(app_module):
    """The template's copy asserts the NEGATIVE — `API_PACKAGES == []`, "the
    template documents no component package" — because the template wraps
    nothing. This fork documents dash_emoji_mart, so the same contract line
    ("not registered when the list is empty") is tested from its other side:
    the list is non-empty here, so the page must exist and must carry the
    component's own props."""
    import dash

    from lib.constants import API_PACKAGES

    assert API_PACKAGES == ["dash_emoji_mart"]
    assert "/api" in [p["path"] for p in dash.page_registry.values()]

    from lib.api_reference import load_packages

    pkgs = load_packages(API_PACKAGES)
    assert pkgs and "error" not in pkgs[0], pkgs
    names = [c["name"] for c in pkgs[0]["components"]]
    assert "DashEmojiMart" in names, names
    props = pkgs[0]["components"][0]["props"]
    assert len(props) > 25, f"only {len(props)} props — is the page empty?"


def test_the_api_page_does_not_need_metadata_json(tmp_path, monkeypatch):
    """THE REGRESSION THIS FILE EXISTS FOR — caught by CD run 33335469726,
    not by a local run.

    `dash_emoji_mart/metadata.json` is excluded from git, from the wheel and
    from the package data, in three places that each say "nothing loads it at
    runtime". It therefore exists ONLY in a working tree that has run
    dash-generate-components, and is absent from every clean checkout, both
    CI runners and the Docker image that serves production. Upstream's loader
    returns [] there — so /api would have rendered with no tables, in
    production, while every check stayed green.

    Simulated by pointing the loader at a package directory with no
    metadata.json: the docstring fallback must still produce the component.
    """
    from lib import api_reference

    # Resolve the metadata path into an empty tmp dir, so `is_file()` is False
    # without touching the real package tree.
    monkeypatch.setattr(api_reference, "Path", lambda *_a, **_k: tmp_path / "pkg")
    got = api_reference.load_package("dash_emoji_mart")

    assert [c["name"] for c in got] == ["DashEmojiMart"], got
    names = {p["name"] for p in got[0]["props"]}
    assert len(names) > 25, f"docstring fallback produced {len(names)} props"
    assert {"perLine", "theme", "set"} <= names
    # `style` is the one prop metadata.json carries that the component's own
    # docstring never declares — it appears only inside another prop's prose.
    # Recorded as a measured fact so the gap is not a surprise later.
    assert "style" not in names


def test_missing_package_is_reported_not_raised():
    from lib import api_reference

    out = api_reference.load_packages(["no_such_dash_package_xyz"])
    assert out[0]["components"] == [] and "error" in out[0]


# ------------------------------------------------ 1.6.39 fix-forward --


def test_the_aside_collapses_on_pages_without_a_toc(app_module):
    """Owner's note 1: /changelog full width. Docs pages with `.. toc::`
    keep the column; everything else collapses it."""
    from lib.aside import aside_config, has_aside

    # This fork's own docs endpoints (the template's copy names its).
    assert has_aside("/configuration") and has_aside("/custom-emojis")
    for path in ("/changelog", "/admin/traffic", "/api"):
        assert not has_aside(path), path
        assert aside_config(path)["collapsed"]["desktop"] is True
    assert aside_config("/configuration")["collapsed"]["desktop"] is False
    assert aside_config(None)["collapsed"]["mobile"] is True


def test_the_mobile_drawer_is_always_mounted(app_module):
    """Owner's note 2: the burger must not depend on a mount-on-open
    transition, and #navbar-admin-mobile must exist on every load."""
    from components.navbar import create_navbar_drawer

    drawer = create_navbar_drawer([])
    assert drawer.keepMounted is True
    assert "navbar-admin-mobile" in str(drawer)


def test_code_blocks_cannot_widen_the_page():
    """Owner's note 3: the overflow rule lives in the stylesheet, for every
    container a code block can sit in — never a per-page fix."""
    css = (REPO / "assets" / "main.css").read_text()
    for selector in (".mantine-List-itemWrapper", ".mantine-List-itemLabel",
                     ".mantine-Timeline-itemBody", ".mantine-CodeHighlight-root",
                     ".mantine-CodeHighlightTabs-root", ".mantine-AppShell-main pre",
                     "table.m2d-block-kwargs", "code.m2d-codespan"):
        assert selector in css, selector
    # and the changelog's rows let an unbreakable code token wrap
    src = (REPO / "pages" / "changelog.py").read_text()
    assert '"overflowWrap": "anywhere"' in src and '"minWidth": 0' in src
    wrappers = css[css.index(".mantine-List-itemWrapper"):]
    assert "min-width: 0" in wrappers[:400]
    pre_rule = css[css.index(".mantine-AppShell-main pre"):]
    assert "overflow-x: auto" in pre_rule[:200]
    assert "overflow-wrap: anywhere" in css[css.index("code.m2d-codespan"):][:200]


def test_other_apps_dropdown_is_solid_and_every_primary_app_has_an_icon(app_module):
    """Seat's note 4."""
    from components.header import create_other_apps_menu
    from lib.network_directory import ICONS, PRIMARY

    dropdown = create_other_apps_menu().children[1]
    assert dropdown.styles["dropdown"]["backgroundColor"]
    for url in PRIMARY:
        assert ICONS.get(url) not in (None, "mdi:web"), f"{url} has no icon"


def test_battery_hidden_paths_match_the_registry(app_module):
    """Template 1.6.42 note 74: the battery's literal tuple is pinned
    against the registry, so a page added, renamed or deleted moves it in
    the same change.

    This pin arrived with a red on this fork, not green: HIDDEN_DOC_PATHS
    still carried the TEMPLATE's canary list (`/admin/llms.txt`,
    `/analytics/llms.txt`) — neither a registered page here — so both 404'd
    trivially while the two admin pages that DO exist went unchecked. A
    vacuous pass is worse than no check: it reads as coverage.
    """
    import dash

    from scripts.network_smoke import HIDDEN_DOC_PATHS

    admin = {p["path"] for p in dash.page_registry.values()
             if (p["path"] or "").startswith("/admin/")}
    assert admin, "no admin pages registered — this pin would be vacuous"
    assert set(HIDDEN_DOC_PATHS) == {f"{p}/llms.txt" for p in admin}, (
        "network_smoke.HIDDEN_DOC_PATHS drifted from the registered admin "
        f"pages: {sorted(HIDDEN_DOC_PATHS)} vs {sorted(admin)}"
    )


def test_every_test_client_user_names_headers():
    """Template 1.6.42 notes 70/74: a bare test client sends `Werkzeug/x.y`
    — crawler lane at dimll >= 2.8 — so a mark_hidden page 404s and an
    every-page-200 loop goes red at the floor bump. Any file that drives
    `.test_client()` must pass headers naming a lane.

    THIS FORK HAS FOUR request-sending tools, not the template's two, and
    each one had to be moved separately: network_smoke, smoke_live,
    verify_network and smoke_test. The grep is what stops a fifth arriving
    without a lane.
    """
    offenders = []
    for folder in ("tests", "scripts"):
        for path in sorted((REPO / folder).glob("*.py")):
            src = path.read_text()
            names_ua = "headers=" in src or "HTTP_USER_AGENT" in src
            if ".test_client()" in src and not names_ua:
                offenders.append(f"{folder}/{path.name}")
    assert offenders == [], offenders


# --------------------------------------------------- /api lane parity --
#
# Template 1.6.42 contract highlight (7), amended: a silent `[]` is only the
# THIRD of four ways /api ships empty. The fourth is structural — a renderer
# whose output lives ONLY in the React tree while the machine lane, the
# prerender and the crawler HTML are built from a different source. /api has
# exactly that shape here: the Dash layout comes from `build_page()`, and
# LLMS_DOC comes from `as_markdown()`. Both read lib/api_reference, so they
# cannot disagree about the DATA — but one can be built while the other is
# not, and nothing above this line would notice.
#
# The lesson the amendment draws is about the TEST, not the fix: assert ROWS
# and row CONTENT, never section headings, and mutation-check the pins.
# `## dash_emoji_mart` was present on the wire the whole time /api served
# zero props.
#
# NAMING THE ARTIFACT, because "the browser lane" is three things: the
# app-shell markup, the dimll prerender block inside the SAME received HTML,
# and the JS-rendered DOM. Measured in this tree: the app-shell markup alone
# carries NO prop rows — the table reaches a reader either through the
# prerender block (no JS) or through the React tree (JS). A curl-fetched
# "Chrome HTML" shows the former and can say nothing about the latter, so
# the layout tree is asserted directly rather than pretended at.

_API_PROBE = "perLine"          # a real prop of this fork's component
_API_ROW_RE = r"^\| `[a-zA-Z]"  # a markdown table row, not a heading


def _api_lanes(client, app_module):
    """Every measurable /api artifact, by name."""
    import re as _re

    from conftest import CRAWLER_UA

    from pages.api import build_page
    from lib.constants import API_PACKAGES

    browser = client.get("/api").text
    m = _re.search(r'data-dimll-prerender="1"(.*?)</div>', browser, _re.S)
    prerender = m.group(1) if m else ""
    return {
        "machine /api/llms.txt": client.get("/api/llms.txt").text,
        "crawler document": client.get("/api", user_agent=CRAWLER_UA).text,
        "browser: prerender block": prerender,
        "browser: layout tree (the JS-rendered DOM's source)": str(build_page(API_PACKAGES)),
    }


def test_api_carries_real_rows_in_every_lane(client, app_module):
    """ROWS and row CONTENT, per lane — never the section heading."""
    import re as _re

    lanes = _api_lanes(client, app_module)
    for name, text in lanes.items():
        assert text, f"{name} is empty"
        assert _API_PROBE in text, f"{name} carries no {_API_PROBE} prop"
    # The two markdown lanes must carry real table ROWS, counted.
    doc = lanes["machine /api/llms.txt"]
    rows = _re.findall(_API_ROW_RE, doc, _re.M)
    assert len(rows) > 25, f"/api/llms.txt has {len(rows)} prop rows"
    # Parity: the machine lane and the prerender describe the same component.
    assert "DashEmojiMart" in doc
    assert "DashEmojiMart" in lanes["browser: prerender block"]


def test_the_api_lane_pins_go_red_when_the_source_is_empty(client, app_module, monkeypatch):
    """MUTATION CHECK, which is the half the amendment says was missing:
    disable the source and watch the pins fail. A lane pin that cannot go
    red is the same silence it was written to catch."""
    from lib import api_reference
    from pages import api as api_page

    monkeypatch.setattr(api_reference, "load_packages",
                        lambda pkgs: [{"package": p, "components": []} for p in pkgs])
    monkeypatch.setattr(api_page.api_reference, "load_packages",
                        api_reference.load_packages, raising=False)

    from lib.constants import API_PACKAGES

    starved = api_reference.as_markdown(API_PACKAGES)
    assert _API_PROBE not in starved, "the mutation did not actually starve the source"
    # The heading SURVIVES the mutation — which is exactly why asserting on
    # it proves nothing, and why this file counts rows instead.
    assert "dash_emoji_mart" in starved
    import re as _re
    assert _re.findall(_API_ROW_RE, starved, _re.M) == []


def test_the_skip_link_is_the_first_tab_stop(app_module):
    """a11y (template 1.6.41): the first tab stop jumps past the sidebar's
    stops straight to the content.

    ASSERTED ON THE LAYOUT TREE — the JS-rendered DOM's source — and NOT on
    the received HTML, because a Dash SPA serves the index template and
    mounts the layout with JS. A curl-shaped check here reports a missing
    skip link that is present, which is the three-artifact confusion the
    1.6.42 amendment names from the other direction.
    """
    import dash

    tree = str(app_module.app.layout)
    assert "skip-link" in tree and "Skip to content" in tree
    assert "'#main-content'" in tree or '"#main-content"' in tree

    # The target exists, and the stylesheet keeps the control OFF-SCREEN
    # rather than display:none — a display:none skip link is unreachable by
    # the keyboard, which is the one user it exists for.
    assert "main-content" in tree
    css = (REPO / "assets" / "main.css").read_text()
    assert ".skip-link" in css and ".skip-link:focus" in css
    block = css.split(".skip-link {", 1)[1].split("}", 1)[0]
    assert "position: absolute" in block and "left: -9999px" in block
    assert "display: none" not in block
