"""Three theme modes side by side, plus a picker bound to this site's own toggle.

The right-hand picker has no `theme` control of its own: a clientside callback maps the
site's stored colour scheme onto its `theme` prop, so the sun/moon button in the header
drives it. That is the pattern to copy for an app with its own theme switch — `theme` is
re-read on every render, so no remount is needed.
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, clientside_callback, html

from dash_emoji_mart import DashEmojiMart

component = dmc.Stack(
    [
        dmc.SegmentedControl(
            id="theme-mode",
            data=[
                {"value": "light", "label": "light"},
                {"value": "dark", "label": "dark"},
                {"value": "auto", "label": "auto"},
            ],
            value="light",
        ),
        dmc.SimpleGrid(
            [
                dmc.Stack(
                    [
                        dmc.Text("Explicit theme", fw=600, size="sm"),
                        DashEmojiMart(
                            id="theme-explicit-picker",
                            theme="light",
                            perLine=8,
                            emojiSize=22,
                            maxFrequentRows=1,
                            previewPosition="none",
                        ),
                        dmc.Text(id="theme-explicit-out", size="xl"),
                    ],
                    gap="xs",
                ),
                dmc.Stack(
                    [
                        dmc.Text("Follows this site's toggle", fw=600, size="sm"),
                        DashEmojiMart(
                            id="theme-synced-picker",
                            perLine=8,
                            emojiSize=22,
                            maxFrequentRows=1,
                            previewPosition="none",
                        ),
                        dmc.Text(
                            "Flip the sun/moon in the header.",
                            size="xs",
                            c="dimmed",
                        ),
                    ],
                    gap="xs",
                ),
            ],
            cols={"base": 1, "md": 2},
            spacing="xl",
        ),
    ],
    gap="md",
)


@callback(Output("theme-explicit-picker", "theme"), Input("theme-mode", "value"))
def set_theme(value):
    return value or "auto"


@callback(Output("theme-explicit-out", "children"), Input("theme-explicit-picker", "value"))
def show(value):
    return value or ""


# The site header stores the active colour scheme in `color-scheme-storage`.
# Clientside so the picker repaints in the same frame as the rest of the page.
clientside_callback(
    "(scheme) => scheme || 'light'",
    Output("theme-synced-picker", "theme"),
    Input("color-scheme-storage", "data"),
)
