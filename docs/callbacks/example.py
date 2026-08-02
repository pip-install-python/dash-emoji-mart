"""`value`, `selectedEmoji` and `clickedOutside` shown side by side, live.

Both selection props are Inputs to one callback on purpose: the component writes them in a
single `setProps`, so this fires once per pick rather than twice.
"""

import json

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from dash_emoji_mart import DashEmojiMart

component = dmc.Group(
    [
        DashEmojiMart(
            id="cb-picker",
            perLine=8,
            emojiSize=22,
            maxFrequentRows=1,
            # Persist the pick across reloads. Reload the page after choosing
            # one — the readout comes back with it.
            persistence=True,
            persisted_props=["value", "selectedEmoji"],
            persistence_type="local",
        ),
        dmc.Stack(
            [
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Text("value", size="sm", fw=600),
                                dmc.Badge("str", variant="light", size="sm"),
                            ],
                            gap="xs",
                        ),
                        dmc.Code(id="cb-value", children="None"),
                    ],
                    withBorder=True,
                    p="md",
                    radius="md",
                ),
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Text("selectedEmoji", size="sm", fw=600),
                                dmc.Badge("dict", variant="light", size="sm"),
                            ],
                            gap="xs",
                        ),
                        dmc.CodeHighlight(
                            id="cb-object", code="None", language="json"
                        ),
                    ],
                    withBorder=True,
                    p="md",
                    radius="md",
                ),
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Text("clickedOutside", size="sm", fw=600),
                                dmc.Badge("int", variant="light", size="sm"),
                            ],
                            gap="xs",
                        ),
                        dmc.Text(
                            id="cb-outside",
                            children="0 — click anywhere off the picker",
                            size="sm",
                            c="dimmed",
                        ),
                    ],
                    withBorder=True,
                    p="md",
                    radius="md",
                ),
            ],
            gap="md",
            style={"flex": 1, "minWidth": 320},
        ),
    ],
    align="flex-start",
    gap="xl",
)


@callback(
    Output("cb-value", "children"),
    Output("cb-object", "code"),
    Input("cb-picker", "value"),
    Input("cb-picker", "selectedEmoji"),
)
def show(value, emoji_obj):
    if not value:
        return "None", "None"
    return repr(value), json.dumps(emoji_obj, indent=2, ensure_ascii=False)


@callback(
    Output("cb-outside", "children"),
    Input("cb-picker", "clickedOutside"),
    prevent_initial_call=True,
)
def outside(n):
    return f"{n} — the counter increments, the number itself is not meaningful"
