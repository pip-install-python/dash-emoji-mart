"""Every layout prop bound to a live control, plus the generated call.

Note the varying `id=` on the wrapper Div. emoji-mart reads `set` and `locale` once when
it builds its internal store, so changing either on a mounted picker does nothing
visible; the picker has to be unmounted and remounted for the data to reload.

The id is what triggers that. Dash's renderer keys each child on its id —
`key: container.props.id ? stringifyId(container.props.id) : stringifyPath(path)` in
DashWrapper — so a different wrapper id is a different React key, and React discards the
old subtree instead of patching it. A `key=` prop does NOT do this: html components
accept it, but the renderer never reads it for reconciliation, so it only reaches the
`<div>` as a stray prop and React warns "`key` is not a prop".
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from dash_emoji_mart import DashEmojiMart

CATEGORY_OPTIONS = [
    {"value": "frequent", "label": "Frequently used"},
    {"value": "people", "label": "People"},
    {"value": "nature", "label": "Nature"},
    {"value": "foods", "label": "Food & drink"},
    {"value": "activity", "label": "Activities"},
    {"value": "places", "label": "Travel & places"},
    {"value": "objects", "label": "Objects"},
    {"value": "symbols", "label": "Symbols"},
    {"value": "flags", "label": "Flags"},
]


def _select(component_id, label, options, value):
    return dmc.Select(
        id=component_id,
        label=label,
        data=[{"value": v, "label": lbl} for v, lbl in options],
        value=value,
        allowDeselect=False,
    )


controls = dmc.Stack(
    [
        dmc.SimpleGrid(
            [
                dmc.NumberInput(
                    id="cfg-per-line", label="perLine", value=9, min=4, max=16
                ),
                dmc.NumberInput(
                    id="cfg-emoji-size", label="emojiSize", value=24, min=14, max=48, step=2
                ),
                dmc.NumberInput(
                    id="cfg-button-size",
                    label="emojiButtonSize",
                    value=36,
                    min=22,
                    max=64,
                    step=2,
                ),
                dmc.NumberInput(
                    id="cfg-max-frequent", label="maxFrequentRows", value=4, min=0, max=8
                ),
            ],
            cols={"base": 2, "md": 4},
            spacing="md",
        ),
        dmc.SimpleGrid(
            [
                _select(
                    "cfg-nav",
                    "navPosition",
                    [("top", "top"), ("bottom", "bottom"), ("none", "none")],
                    "top",
                ),
                _select(
                    "cfg-preview",
                    "previewPosition",
                    [("top", "top"), ("bottom", "bottom"), ("none", "none")],
                    "bottom",
                ),
                _select(
                    "cfg-search",
                    "searchPosition",
                    [("sticky", "sticky"), ("static", "static"), ("none", "none")],
                    "sticky",
                ),
                _select(
                    "cfg-skin-tone",
                    "skinTonePosition",
                    [("preview", "preview"), ("search", "search"), ("none", "none")],
                    "preview",
                ),
            ],
            cols={"base": 2, "md": 4},
            spacing="md",
        ),
        dmc.SimpleGrid(
            [
                _select(
                    "cfg-set",
                    "set",
                    [
                        ("native", "native"),
                        ("apple", "apple"),
                        ("google", "google"),
                        ("twitter", "twitter"),
                        ("facebook", "facebook"),
                    ],
                    "native",
                ),
                _select(
                    "cfg-locale",
                    "locale",
                    [
                        ("en", "English"),
                        ("es", "Español"),
                        ("fr", "Français"),
                        ("de", "Deutsch"),
                        ("ja", "日本語"),
                        ("zh", "中文"),
                    ],
                    "en",
                ),
                dmc.NumberInput(id="cfg-skin", label="skin", value=1, min=1, max=6),
                dmc.TextInput(
                    id="cfg-radius", label="emojiButtonRadius", value="100%"
                ),
            ],
            cols={"base": 2, "md": 4},
            spacing="md",
        ),
        dmc.MultiSelect(
            id="cfg-categories",
            label="categories (empty shows all)",
            data=CATEGORY_OPTIONS,
            value=[],
            clearable=True,
        ),
        dmc.Group(
            [
                dmc.Switch(id="cfg-dynamic-width", label="dynamicWidth", checked=False),
                dmc.Switch(id="cfg-auto-focus", label="autoFocus", checked=False),
                dmc.Switch(id="cfg-no-flags", label="noCountryFlags", checked=False),
            ],
            gap="xl",
        ),
    ],
    gap="md",
)

component = dmc.Stack(
    [
        dmc.Paper(controls, withBorder=True, p="lg", radius="md"),
        dmc.Group(
            [
                html.Div(id="cfg-picker"),
                dmc.Stack(
                    [
                        dmc.Paper(
                            [
                                dmc.Text("Selected", size="sm", c="dimmed"),
                                html.Div(
                                    id="cfg-output",
                                    style={"fontSize": 48, "minHeight": 60},
                                ),
                            ],
                            withBorder=True,
                            p="lg",
                            radius="md",
                            style={"minWidth": 200, "textAlign": "center"},
                        ),
                        dmc.CodeHighlight(
                            id="cfg-code", code="", language="python"
                        ),
                    ],
                    gap="md",
                    style={"flex": 1, "minWidth": 300},
                ),
            ],
            align="flex-start",
            gap="xl",
        ),
    ],
    gap="md",
)


@callback(
    Output("cfg-picker", "children"),
    Output("cfg-code", "code"),
    Input("cfg-per-line", "value"),
    Input("cfg-emoji-size", "value"),
    Input("cfg-button-size", "value"),
    Input("cfg-max-frequent", "value"),
    Input("cfg-nav", "value"),
    Input("cfg-preview", "value"),
    Input("cfg-search", "value"),
    Input("cfg-skin-tone", "value"),
    Input("cfg-set", "value"),
    Input("cfg-locale", "value"),
    Input("cfg-skin", "value"),
    Input("cfg-radius", "value"),
    Input("cfg-categories", "value"),
    Input("cfg-dynamic-width", "checked"),
    Input("cfg-auto-focus", "checked"),
    Input("cfg-no-flags", "checked"),
)
def rebuild(
    per_line,
    emoji_size,
    button_size,
    max_frequent,
    nav,
    preview,
    search,
    skin_tone,
    emoji_set,
    locale,
    skin,
    radius,
    categories,
    dynamic_width,
    auto_focus,
    no_flags,
):
    props = {
        "perLine": per_line if per_line is not None else 9,
        "emojiSize": emoji_size if emoji_size is not None else 24,
        "emojiButtonSize": button_size if button_size is not None else 36,
        "emojiButtonRadius": radius or "100%",
        "maxFrequentRows": max_frequent if max_frequent is not None else 4,
        "navPosition": nav or "top",
        "previewPosition": preview or "bottom",
        "searchPosition": search or "sticky",
        "skinTonePosition": skin_tone or "preview",
        "set": emoji_set or "native",
        "locale": locale or "en",
        "skin": skin if skin is not None else 1,
        "dynamicWidth": bool(dynamic_width),
        "autoFocus": bool(auto_focus),
        "noCountryFlags": bool(no_flags),
    }
    if categories:
        props["categories"] = categories

    rendered = ",\n".join(f"    {k}={v!r}" for k, v in props.items())
    code = f'DashEmojiMart(\n    id="picker",\n{rendered},\n)'

    # `set` and `locale` only take effect on a fresh mount, so they go in the wrapper id
    # — that is what Dash turns into the React key. See the module docstring.
    mount_id = f"cfg-mount-{props['set']}-{props['locale']}"
    return html.Div(DashEmojiMart(id="cfg-emoji-picker", **props), id=mount_id), code


@callback(Output("cfg-output", "children"), Input("cfg-emoji-picker", "value"))
def show(value):
    if not value:
        return dmc.Text("Nothing yet", c="dimmed", size="lg")
    if value.startswith("http"):
        return html.Img(src=value, style={"width": 48, "height": 48})
    return value
