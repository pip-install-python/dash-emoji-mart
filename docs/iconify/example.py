"""A picker whose categories come from Iconify rather than emoji-mart's own data.

Categories are built at import time, not in the callback: on a cold cache
`iconify_to_emoji_mart` makes a handful of API calls, and that cost belongs at startup
rather than on the critical path of a click. Switching sets in the demo only swaps between
sets already materialised in `SETS` below.

If api.iconify.design is unreachable the loader returns an empty list and the picker falls
back to plain emojis, which is why there is no error branch here.
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from dash_emoji_mart import DashEmojiMart
from dash_emoji_mart.iconify import iconify_to_emoji_mart

# Three sets with quite different characters: Twitter's emoji, the open-source
# OpenMoji project, and Tabler — a non-emoji UI icon set, to show that the
# conversion is not emoji-specific.
SET_PREFIXES = ["twemoji", "openmoji", "tabler"]

SETS = {
    prefix: iconify_to_emoji_mart(prefix, max_icons_per_category=48)
    for prefix in SET_PREFIXES
}

component = dmc.Stack(
    [
        dmc.SegmentedControl(
            id="iconify-set",
            data=[
                {"value": "twemoji", "label": "Twemoji"},
                {"value": "openmoji", "label": "OpenMoji"},
                {"value": "tabler", "label": "Tabler"},
            ],
            value="twemoji",
        ),
        dmc.Text(id="iconify-count", size="sm", c="dimmed"),
        dmc.Group(
            [
                html.Div(id="iconify-picker"),
                dmc.Paper(
                    [
                        dmc.Text("Selected", size="sm", c="dimmed"),
                        html.Div(id="iconify-out", style={"minHeight": 64}),
                        dmc.Text(id="iconify-name", size="sm", fw=500),
                    ],
                    withBorder=True,
                    p="lg",
                    radius="md",
                    style={"minWidth": 200, "textAlign": "center"},
                ),
            ],
            align="flex-start",
            gap="xl",
        ),
    ],
    gap="md",
)


@callback(
    Output("iconify-picker", "children"),
    Output("iconify-count", "children"),
    Input("iconify-set", "value"),
)
def swap_set(prefix):
    categories = SETS.get(prefix, [])
    if not categories:
        return (
            dmc.Alert(
                "Iconify is unreachable, so this set could not be loaded.",
                color="orange",
            ),
            "",
        )

    total = sum(len(c["emojis"]) for c in categories)
    summary = (
        f"{len(categories)} Iconify categories · {total} icons "
        "(capped at 48 per category) — they appear after emoji-mart's own "
        "categories in the nav bar."
    )

    picker = DashEmojiMart(
        id="iconify-emoji-picker",
        custom=categories,
        # `categories` is deliberately NOT passed alongside `custom`.
        #
        # emoji-mart filters that prop against its `originalCategories` array,
        # which it captures BY REFERENCE on the first init in the page's
        # lifetime. Custom categories pushed during that first init land in it
        # through the aliasing, so the pair appears to work. Every later init
        # rebuilds `categories` as a NEW array, breaking the alias — so from the
        # second picker onwards, `categories` filters against a stale list that
        # cannot contain the custom ids, and every custom category is dropped.
        #
        # Symptom when you get this wrong: the first set renders, and every set
        # you switch to afterwards renders an empty picker.
        #
        # Omitting it skips that filter entirely, so the Iconify categories
        # simply join emoji-mart's built-in ones. Scroll the nav bar along to
        # reach them.
        perLine=9,
        emojiSize=24,
        searchPosition="static",
        previewPosition="none",
    )
    # New custom data needs a fresh mount, the same as `set` and `locale`. Dash keys each
    # child on its id, so varying the wrapper's id is what makes React remount rather than
    # patch — a `key=` prop is not read for reconciliation. See docs/configuration.
    return html.Div(picker, id=f"iconify-mount-{prefix}"), summary


@callback(
    Output("iconify-out", "children"),
    Output("iconify-name", "children"),
    Input("iconify-emoji-picker", "value"),
    Input("iconify-emoji-picker", "selectedEmoji"),
)
def show(value, emoji_obj):
    if not value:
        return dmc.Text("Nothing yet", c="dimmed", size="lg"), ""
    return (
        html.Img(src=value, style={"height": 56, "width": 56}),
        (emoji_obj or {}).get("name", ""),
    )
