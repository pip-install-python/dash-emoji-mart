"""Header for the dash-emoji-mart documentation site.

Branding: a grinning-face emoji + yellow "dash-emoji-mart" title. Preserves the
`color-scheme-toggle` ActionIcon id from the boilerplate so the appshell's
clientside callbacks (theme storage + Mantine forceColorScheme) keep working,
AND the docs pages' `theme` sync — several examples drive `DashEmojiMart.theme`
off the same id.

The Clerk avatar sits beside the theme toggle and returns None whenever Clerk
is unconfigured — which is how this site ships today (PAGE_DEFAULT_TIER=public,
no CLERK_* keys), so the header renders exactly as it did before. The widget
exists so the phase-4 flip is an environment change and not a code change.
"""
import dash_mantine_components as dmc
from dash import Input, Output, State, clientside_callback
from dash_iconify import DashIconify

from lib.backend import get_backend_info
from components.backend_badge import create_backend_badge
from components.navbar import search_data
from lib.constants import (
    API_PACKAGES,
    BASE_URL,
    EMOJI_MART_VERSION,
    GITHUB_URL,
    HEADER_HEIGHT,
    SITE_SHORT_NAME,
)


def create_clerk_avatar():
    """Clerk avatar / sign-in control, sat beside the colour-scheme toggle.

    Returns None when Clerk is not configured, so local development and every
    deploy without the keys renders the header exactly as before rather than
    erroring on a missing package. `lib/auth.py` registers Clerk with
    `headless=True`, meaning dash-clerk-auth injects NO UI of its own — without
    this widget there is no way to sign in even once Clerk initialises.
    """
    from lib.auth import clerk_enabled

    if not clerk_enabled():
        return None
    from dash_clerk_auth import create_clerk_menu

    return create_clerk_menu(show_dropdown=True, dropdown_align="right")


def create_link(icon, href, label):
    """An external-link icon button.

    ``label`` is REQUIRED, and positionally so — an icon-only control has no
    accessible name, so a screen reader announces it as "link" and an agent
    driving the page cannot tell what it does. Making the parameter mandatory
    is what stops the next link being added without one. It lands on both the
    anchor and the button.

    `aria-label` and never `title=`: DMC 2.8's ActionIcon/Anchor accept
    `aria-*` wildcards but REJECT `title`, raising TypeError during app
    construction — a tooltip typo takes the whole site down rather than
    rendering wrong. Hover text, where it is wanted, is `dmc.Tooltip`.
    """
    return dmc.Anchor(
        dmc.ActionIcon(
            DashIconify(icon=icon, width=22),
            variant="subtle",
            size="lg",
            color="gray",
            **{"aria-label": label},
        ),
        href=href,
        target="_blank",
        **{"aria-label": label},
    )


def create_other_apps_menu():
    """*Other Apps* — the network, from ONE registry.

    A hover menu in the top bar (the 2plot.dev shape the owner named as the
    reference), populated from lib.network_directory's PRIMARY set: the
    primary applications only, never the fleet's docs subdomains, which
    2plot.dev's catalogue already lists. This host is removed from its own
    menu. The sidebar carries no network section any more — this is the
    only place the network is listed, so it cannot be listed twice.
    """
    from lib.network_directory import other_apps_for

    return dmc.Menu(
        [
            dmc.MenuTarget(
                dmc.Button(
                    "Other Apps",
                    variant="subtle",
                    color="gray",
                    size="sm",
                    leftSection=DashIconify(icon="svg-spinners:blocks-scale", width=18),
                    visibleFrom="md",
                    id="other-apps-menu-target",
                )
            ),
            dmc.MenuDropdown(
                [
                    dmc.MenuItem(
                        entry["label"],
                        leftSection=DashIconify(icon=entry["icon"], width=16),
                        href=entry["url"],
                        target="_blank",
                    )
                    for entry in other_apps_for(BASE_URL)
                ],
                id="other-apps-menu",
                # Solid, themed panel: Mantine's default dropdown is
                # near-transparent in dark mode and the items wash out.
                styles={"dropdown": {
                    "backgroundColor": "var(--mantine-color-body)",
                    "border": "1px solid var(--mantine-color-default-border)",
                    "boxShadow": "var(--mantine-shadow-md)",
                }},
            ),
        ],
        trigger="hover",
        openDelay=100,
        closeDelay=200,
    )


def _package_version():
    """The documented component package's version, or None."""
    if not API_PACKAGES:
        return None
    try:
        import importlib

        return getattr(importlib.import_module(API_PACKAGES[0]), "__version__", None)
    except Exception:
        return None


def create_version_badge():
    """`v<version>` of the documented package, when the fork declares one."""
    v = _package_version()
    if not v:
        return None
    return dmc.Badge(
        f"v{v}",
        variant="light",
        color="gray",
        radius="sm",
        styles={"root": {"textTransform": "none", "fontWeight": 600}},
        **{"aria-label": f"{API_PACKAGES[0]} version {v}"},
    )


def create_search(data):
    """Searchable dropdown for page navigation — the sidebar's pages and
    nothing else (never /admin/*, never a hidden-tier page). components/
    navbar decides, so the two lists cannot disagree: this used to be an
    inline comprehension here and a second one in the drawer."""
    return dmc.Select(
        id="select-component",
        placeholder="Search pages...",
        searchable=True,
        clearable=True,
        w=240,
        size="sm",
        nothingFoundMessage="No pages found",
        leftSection=DashIconify(icon="mingcute:search-3-line", width=18),
        data=search_data(data),
        visibleFrom="sm",
        comboboxProps={"zIndex": 2000},
        **{"aria-label": "Search pages"},
        styles={"input": {"borderColor": "var(--mantine-color-gray-4)"}},
    )


def _openapi_link():
    """Swagger UI link, FastAPI backend only."""
    info = get_backend_info()
    if info.name != "fastapi":
        return None
    return dmc.Tooltip(
        label="OpenAPI docs (Swagger UI) — FastAPI backend",
        position="bottom",
        withArrow=True,
        children=dmc.Anchor(
            dmc.Badge(
                "OpenAPI",
                leftSection=DashIconify(icon="logos:swagger", width=14),
                variant="light",
                color="cyan",
                radius="sm",
                styles={"root": {"textTransform": "none", "fontWeight": 600}},
            ),
            href="/docs",
            target="_blank",
            underline=False,
        ),
    )


def create_header(data):
    return dmc.AppShellHeader(
        dmc.Group(
            [
                dmc.Group(
                    [
                        dmc.ActionIcon(
                            DashIconify(icon="radix-icons:hamburger-menu", width=22),
                            id="drawer-hamburger-button",
                            variant="subtle",
                            size="lg",
                            color="gray",
                            hiddenFrom="md",
                            **{"aria-label": "Open navigation menu"},
                        ),
                        dmc.Burger(
                            id="desktop-navbar-toggle",
                            opened=True,
                            size="sm",
                            visibleFrom="md",
                            color="var(--mantine-color-yellow-6)",
                            **{"aria-label": "Toggle navigation sidebar"},
                        ),
                        dmc.Anchor(
                            dmc.Group(
                                [
                                    # The site's mark. Same glyph and same
                                    # family as the favicon and the share card,
                                    # which are rendered from Noto's U+1F920
                                    # PNG in assets/brand/ — so the tab icon,
                                    # this header and an unfurl are one drawing
                                    # rather than three vendors' idea of it.
                                    #
                                    # It was `noto:grinning-face-with-smiling-eyes`
                                    # — the generic yellow smiley, which is
                                    # every emoji library's placeholder and
                                    # named nothing about this one.
                                    DashIconify(
                                        icon="noto:cowboy-hat-face",
                                        width=28,
                                    ),
                                    dmc.Stack(
                                        [
                                            # Hidden on xs displays. The mark
                                            # (the cowboy-hat glyph beside it)
                                            # carries the brand on a phone,
                                            # where this wordmark competes with
                                            # the burger, search, GitHub link,
                                            # theme toggle and avatar for a
                                            # header row that has no room for
                                            # all of them.
                                            #
                                            # visibleFrom is CSS-only — Mantine
                                            # emits a media query and the node
                                            # stays in the DOM, so the
                                            # colour-scheme callback further
                                            # down that writes to this id keeps
                                            # firing on every viewport.
                                            dmc.Text(
                                                "dash-emoji-mart",
                                                size="lg",
                                                fw=700,
                                                c="yellow",
                                                id="dash-docs-title",
                                                visibleFrom="sm",
                                            ),
                                            dmc.Text(
                                                f"emoji-mart {EMOJI_MART_VERSION}",
                                                size="xs",
                                                c="dimmed",
                                                visibleFrom="md",
                                                style={"marginTop": -4},
                                            ),
                                        ],
                                        gap=0,
                                    ),
                                ],
                                gap="sm",
                                wrap="nowrap",
                            ),
                            href="/",
                            underline=False,
                            # The home link's accessible name comes from HERE,
                            # not the wordmark text: below `sm` the wordmark is
                            # display:none (visibleFrom), which removes it from
                            # the accessibility tree — without this label the
                            # home link would have no name at all on a phone.
                            **{"aria-label": f"{SITE_SHORT_NAME} — home"},
                        ),
                    ],
                    gap="md",
                ),
                dmc.Group(
                    [
                        dmc.Box(create_backend_badge(), visibleFrom="sm"),
                        dmc.Box(_openapi_link(), visibleFrom="md"),
                        dmc.Box(create_version_badge(), visibleFrom="sm"),
                        create_search(data),
                        create_other_apps_menu(),
                        create_link("radix-icons:github-logo", GITHUB_URL,
                                    "dash-emoji-mart on GitHub"),
                        dmc.ActionIcon(
                            [
                                DashIconify(
                                    icon="radix-icons:sun",
                                    width=22,
                                    id="light-theme-icon",
                                ),
                                DashIconify(
                                    icon="radix-icons:moon",
                                    width=22,
                                    id="dark-theme-icon",
                                ),
                            ],
                            variant="subtle",
                            color="yellow",
                            id="color-scheme-toggle",
                            size="lg",
                            **{"aria-label": "Toggle light and dark theme"},
                        ),
                        create_clerk_avatar(),
                    ],
                    gap="sm",
                ),
            ],
            justify="space-between",
            h=HEADER_HEIGHT,
            px="xl",
        ),
    )


# Search select → URL navigation
clientside_callback(
    """
    function(value) {
        if (value) { return value }
    }
    """,
    Output("url", "href"),
    Input("select-component", "value"),
)

# Mobile drawer search → navigate. The header Select is hidden below `sm`, so
# on a phone the drawer's own copy is the only search there is.
clientside_callback(
    """
    function(value) {
        if (value) { return value }
        return window.dash_clientside.no_update
    }
    """,
    Output("url", "href", allow_duplicate=True),
    Input("mobile-select-component", "value"),
    prevent_initial_call=True,
)

# Drawer TOGGLE, not open. The network-standard drawer leaves the header
# uncovered so the hamburger stays reachable while it is open — which makes a
# second tap on it the obvious way to close, and a no-op the obvious bug.
# Reading `opened` as State is the whole fix.
clientside_callback(
    """function(n_clicks, opened) { return !opened }""",
    Output("components-navbar-drawer", "opened"),
    Input("drawer-hamburger-button", "n_clicks"),
    State("components-navbar-drawer", "opened"),
    prevent_initial_call=True,
)

# Mirror the stored colour scheme onto <html data-mantine-color-scheme>.
# MantineProvider.forceColorScheme alone does NOT set that attribute, and it is
# what Mantine derives its CSS variables from — and what the docs pages read to
# drive `DashEmojiMart(theme=...)` when a page follows the site theme.
clientside_callback(
    """
    function(scheme) {
        const v = scheme || 'light';
        document.documentElement.setAttribute('data-mantine-color-scheme', v);
        return window.dash_clientside.no_update;
    }
    """,
    Output("dash-docs-title", "id"),
    Input("color-scheme-storage", "data"),
)
