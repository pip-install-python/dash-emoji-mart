"""Sidebar navigation for the dash-emoji-mart documentation site.

The boilerplate's flat `page_order` list is swapped for category-grouped
sections. Each `docs/<slug>/<slug>.md`'s `category` frontmatter feeds the
grouping, and anything with an unrecognised category falls into "Other" rather
than disappearing from the nav.
"""
from __future__ import annotations

from collections import OrderedDict

import dash_mantine_components as dmc
from dash_iconify import DashIconify

from lib.constants import DISCORD_URL, GITHUB_URL

CATEGORY_ORDER = [
    "Start here",
    "Configuration",
    "Custom emojis",
    "Dash integration",
]

EXCLUDED_LINKS: set[str] = {
    "/404",
    "/not-found",
}


def create_nav_link(icon: str, text: str, href: str, external: bool = False):
    return dmc.Anchor(
        dmc.Group(
            [
                DashIconify(icon=icon or "tabler:file-text", width=18),
                dmc.Text(text, size="sm", fw=500),
            ],
            gap="sm",
        ),
        href=href,
        target="_blank" if external else None,
        className="navbar-link",
        underline=False,
    )


def create_nav_section(title: str, links: list):
    return dmc.Stack(
        [
            dmc.Text(
                title,
                size="xs",
                fw=700,
                tt="uppercase",
                c="dimmed",
                mb="xs",
            ),
            dmc.Stack(links, gap="xs"),
        ],
        gap="sm",
    )


def _categorize(data) -> "OrderedDict[str, list]":
    """Bucket page registry entries by their `category` field, preserving the
    intentional CATEGORY_ORDER and folding unknown categories into 'Other'."""
    buckets: OrderedDict[str, list] = OrderedDict((c, []) for c in CATEGORY_ORDER)
    other: list = []
    for entry in data:
        path = entry.get("path")
        if not path or path in EXCLUDED_LINKS:
            continue
        link = create_nav_link(
            entry.get("icon") or "tabler:file-text",
            entry.get("name", path),
            path,
        )
        category = entry.get("category")
        if category in buckets:
            buckets[category].append(link)
        else:
            other.append(link)
    if other:
        buckets["Other"] = other
    return OrderedDict((k, v) for k, v in buckets.items() if v)


def create_content(data):
    buckets = _categorize(data)
    sections = []
    for i, (title, links) in enumerate(buckets.items()):
        if i > 0:
            sections.append(dmc.Divider(mt="md", mb="sm"))
        sections.append(create_nav_section(title, links))

    sections.append(dmc.Divider(mt="md", mb="sm"))
    sections.append(
        create_nav_section(
            "Resources",
            [
                create_nav_link(
                    "tabler:brand-github", "GitHub", GITHUB_URL, external=True
                ),
                create_nav_link(
                    "tabler:mood-smile",
                    "emoji-mart (upstream)",
                    "https://github.com/missive/emoji-mart",
                    external=True,
                ),
                create_nav_link(
                    "simple-icons:iconify",
                    "Iconify sets",
                    "https://icon-sets.iconify.design/",
                    external=True,
                ),
                create_nav_link(
                    "ic:baseline-design-services",
                    "DMC",
                    "https://www.dash-mantine-components.com/",
                    external=True,
                ),
                create_nav_link(
                    "tabler:brand-discord", "Discord", DISCORD_URL, external=True
                ),
                create_nav_link(
                    "fluent-mdl2:forum",
                    "Dash Community",
                    "https://community.plotly.com/",
                    external=True,
                ),
            ],
        )
    )

    return dmc.ScrollArea(
        offsetScrollbars=True,
        type="scroll",
        style={"height": "100%"},
        children=dmc.Stack(sections, gap="xs", p="md"),
    )


def create_navbar(data):
    return dmc.AppShellNavbar(
        children=create_content(data),
        style={"borderRight": "1px solid var(--mantine-color-gray-3)"},
    )


def create_navbar_drawer(data):
    return dmc.Drawer(
        id="components-navbar-drawer",
        overlayProps={"opacity": 0.55, "blur": 3},
        zIndex=1500,
        offset=8,
        radius="md",
        withCloseButton=True,
        size="280px",
        children=create_content(data),
        trapFocus=False,
        position="left",
    )
