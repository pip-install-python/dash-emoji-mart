"""Teaser demos for the authentication gate cards.

Each auth-gated docs page can register ONE live example that renders inside
the sign-in card (lib.gate_layouts.sign_in_layout) — an interactive taste of
what's behind the gate, with no code and no surrounding docs.

The modules referenced here are the same ``.. exec::`` example modules the
docs pages use (they expose a module-level ``component``), so they're already
imported — and their callbacks already registered — when pages/markdown.py
parses the docs at startup. Only one layout (gate card OR full docs) renders
per request, so sharing the component instances never duplicates IDs.

The table ships EMPTY in the template: entries are site-specific dotted
paths, so each satellite fills in its own hero example (one entry is plenty —
this is a funnel, not a gallery).

Entries:
    endpoint -> {
        "module":     dotted path of the example module,
        "caption":    short label shown next to the "Live demo" badge,
        "max_height": px cap for the demo viewport inside the card,
        "height":     optional explicit px height — needed by components that
                      size to their container,
    }
"""
from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

DEMOS: dict[str, dict] = {
    # This site's hero example, swapped in for the template's chart. Gate
    # /popover (control board toggle, or `tier: auth` in its frontmatter) and
    # the sign-in card renders the real picker-in-a-popover above the
    # "Authentication required" copy — a reader can open it and pick an emoji
    # before deciding whether to sign in.
    #
    # /popover rather than /iconify deliberately: the popover demo is
    # self-contained and needs no network, while the Iconify page builds its
    # categories from api.iconify.design at import time. A gate card is the
    # worst place to discover a third-party CDN is slow.
    "/popover": {
        "module": "docs.popover.example",
        "caption": "Live picker in a popover",
        "max_height": 420,
    },
}


def build_demo(path: str):
    """Return the teaser demo block for ``path``, or None.

    Import/attribute failures degrade to the plain (demo-less) card — a broken
    example must never take down the sign-in funnel.
    """
    spec = DEMOS.get(path)
    if spec is None:
        return None
    try:
        module = importlib.import_module(spec["module"])
        component = getattr(module, "component")
    except Exception as e:
        logger.warning("Auth-gate demo %s failed to load (%s) — card renders "
                       "without it", spec.get("module"), e)
        return None

    import dash_mantine_components as dmc
    from dash_iconify import DashIconify

    return dmc.Box(
        [
            dmc.Group(
                [
                    dmc.Badge(
                        "Live demo — try it",
                        variant="light",
                        color="teal",
                        leftSection=DashIconify(icon="tabler:hand-click", width=13),
                    ),
                    dmc.Text(spec.get("caption", ""), size="sm", c="dimmed"),
                ],
                justify="space-between",
                px="md",
                pt="md",
            ),
            dmc.Box(
                component,
                p="md",
                className="auth-gate-demo",
                style={
                    "maxHeight": f"{spec.get('max_height', 420)}px",
                    "overflowY": "auto",
                    "overflowX": "hidden",
                    **({"height": f"{spec['height']}px"} if "height" in spec else {}),
                },
            ),
        ]
    )
