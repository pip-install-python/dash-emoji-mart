"""The smallest useful DashEmojiMart: a picker and a readout of what was picked.

`value` is a plain string — the native glyph for a standard emoji. `selectedEmoji`
carries the whole emoji-mart object alongside it, which is where the name and shortcode
below come from.
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from dash_emoji_mart import DashEmojiMart

component = dmc.Group(
    [
        DashEmojiMart(
            id="home-picker",
            perLine=9,
            emojiSize=24,
            maxFrequentRows=2,
            previewPosition="none",
        ),
        dmc.Paper(
            [
                dmc.Text("Selected", size="sm", c="dimmed"),
                html.Div(
                    id="home-picker-glyph",
                    style={"fontSize": 56, "minHeight": 70, "lineHeight": 1.2},
                ),
                dmc.Text(id="home-picker-name", size="sm", fw=500),
                dmc.Text(id="home-picker-shortcode", size="xs", c="dimmed"),
            ],
            withBorder=True,
            p="lg",
            radius="md",
            style={"minWidth": 200, "textAlign": "center"},
        ),
    ],
    align="flex-start",
    gap="xl",
)


@callback(
    Output("home-picker-glyph", "children"),
    Output("home-picker-name", "children"),
    Output("home-picker-shortcode", "children"),
    Input("home-picker", "selectedEmoji"),
)
def show(emoji):
    if not emoji:
        return dmc.Text("Nothing yet", c="dimmed", size="lg"), "", ""
    shortcodes = emoji.get("shortcodes") or ""
    return emoji.get("native", ""), emoji.get("name", ""), shortcodes
