"""A picker whose categories come from Iconify rather than emoji-mart's own data.

Categories are built at import time, not in the callback: on a cold cache
`iconify_to_emoji_mart` makes a handful of API calls, and that cost belongs at startup
rather than on the critical path of a click. Switching sets in the demo only swaps between
sets already materialised in `SETS` below.

If api.iconify.design is unreachable the loader returns an empty list and the picker falls
back to plain emojis, which is why there is no error branch here.
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, clientside_callback, html

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
        "(capped at 48 per category). emoji-mart's own categories are still "
        "here, before these — the picker jumps you past them."
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
    """Render the pick — which is NOT always an Iconify icon.

    emoji-mart's own categories are still in this picker (see the note on the
    page about why `categories` cannot filter them out here), so a reader can
    perfectly well click 🆑 from Symbols. `value` is then the native glyph, not
    a URL, and this callback used to hand it to `html.Img(src=...)` regardless
    — producing `<img src="🆑">`, i.e. a broken-image placeholder next to a
    correct name.

    Same branch as the custom-emojis page: only a custom emoji has a URL.
    """
    if not value:
        return dmc.Text("Nothing yet", c="dimmed", size="lg"), ""
    if value.startswith("http"):
        glyph = html.Img(src=value, style={"height": 56, "width": 56})
    else:
        glyph = dmc.Text(value, style={"fontSize": 56, "lineHeight": 1})
    return glyph, (emoji_obj or {}).get("name", "")


# ---------------------------------------------------------------------------
# Scroll to the Iconify categories after a set is chosen.
#
# emoji-mart appends custom categories AFTER its own nine, and `categories`
# cannot be used to hide those (see the long note on the picker above — it
# works for the first set and empties the picker for every set you switch to
# afterwards; both variants were measured). So choosing "OpenMoji" left the
# reader looking at Smileys & People with roughly five thousand built-in emoji
# between them and the thing they just asked for.
#
# Rather than fight emoji-mart's data model, jump to the section. This is the
# picker's own affordance: the last button in its nav bar is the custom-category
# group, and clicking it is exactly what a reader would do if they knew it was
# there.
#
# Clientside because it is pure DOM work that must happen after the remount
# paints, and it reaches into the shadow root because that is where the picker
# lives — nothing about it can be expressed as a Dash prop. Fail-silent by
# design: if emoji-mart ever renames its nav, the demo simply behaves as it did
# before rather than erroring.
clientside_callback(
    """
    function (summary) {
        const jump = (tries) => {
            const host = document.querySelector('#iconify-picker em-emoji-picker');
            const nav = host && host.shadowRoot && host.shadowRoot.querySelector('nav');
            if (!nav) {
                if (tries > 0) { setTimeout(() => jump(tries - 1), 120); }
                return;
            }
            const buttons = nav.querySelectorAll('button');
            if (buttons.length) { buttons[buttons.length - 1].click(); }
        };
        jump(25);
        return window.dash_clientside.no_update;
    }
    """,
    Output("iconify-count", "children", allow_duplicate=True),
    Input("iconify-count", "children"),
    prevent_initial_call=True,
)
