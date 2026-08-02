"""Three custom categories — memes, tech and company — with their own nav icons.

The readout branches on `value.startswith("http")` because a custom emoji has no native
glyph: `value` is the image URL. The name underneath comes from `selectedEmoji`, which
identifies the pick without that guesswork.
"""

import dash_mantine_components as dmc
from dash import Input, Output, callback, html

from dash_emoji_mart import DashEmojiMart

DEVICON = "https://cdn.jsdelivr.net/gh/devicons/devicon/icons"


def emoji(emoji_id, name, src, keywords):
    return {
        "id": emoji_id,
        "name": name,
        "short_names": [emoji_id],
        "keywords": keywords,
        "skins": [{"src": src}],
        "native": "",
        "unified": "custom",
    }


CUSTOM_EMOJIS = [
    {
        "id": "memes",
        "name": "Memes",
        "emojis": [
            emoji(
                "party_parrot",
                "Party Parrot",
                "https://missiveapp.com/open/emoji-mart/parrot.6a845cb2.gif",
                ["dance", "dancing", "party", "parrot"],
            ),
            emoji(
                "shiba",
                "Shiba",
                "https://cdn.jsdelivr.net/gh/iamcal/emoji-data@15.1.2/img-apple-160/1f436.png",
                ["dog", "meme", "shiba"],
            ),
        ],
    },
    {
        "id": "tech",
        "name": "Tech",
        "emojis": [
            emoji(
                "python",
                "Python",
                f"{DEVICON}/python/python-original.svg",
                ["python", "programming", "code"],
            ),
            emoji(
                "react",
                "React",
                f"{DEVICON}/react/react-original.svg",
                ["react", "javascript", "frontend"],
            ),
            emoji(
                "docker",
                "Docker",
                f"{DEVICON}/docker/docker-original.svg",
                ["docker", "container", "devops"],
            ),
        ],
    },
    {
        "id": "company",
        "name": "Company",
        "emojis": [
            emoji(
                "github",
                "GitHub",
                f"{DEVICON}/github/github-original.svg",
                ["github", "git", "repo"],
            ),
            emoji(
                "slack",
                "Slack",
                f"{DEVICON}/slack/slack-original.svg",
                ["slack", "chat", "communication"],
            ),
        ],
    },
]

# Inline SVG for each custom category's nav icon. `1em` sizing and
# `fill="currentColor"` are what let emoji-mart scale and colour them.
_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" '
    'viewBox="0 0 24 24"><path fill="currentColor" d="{path}"/></svg>'
)

CATEGORY_ICONS = {
    "memes": {
        "svg": _SVG.format(
            path="M12 2C6.47 2 2 6.5 2 12a10 10 0 0 0 10 10a10 10 0 0 0 10-10A10 10 0 0 0 "
            "12 2m3.5 6c.83 0 1.5.67 1.5 1.5S16.33 11 15.5 11S14 10.33 14 9.5S14.67 8 "
            "15.5 8m-7 0c.83 0 1.5.67 1.5 1.5S9.33 11 8.5 11S7 10.33 7 9.5S7.67 8 8.5 "
            "8m3.5 9.5c-2.33 0-4.31-1.46-5.11-3.5h10.22c-.8 2.04-2.78 3.5-5.11 3.5"
        )
    },
    "tech": {
        "svg": _SVG.format(
            path="M20 18c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 "
            "2H0v2h24v-2zM4 6h16v10H4z"
        )
    },
    "company": {
        "svg": _SVG.format(
            path="M18 15h-2v2h2m0-6h-2v2h2m2 6h-8v-2h2v-2h-2v-2h2v-2h-2V9h8M10 7H8V5h2m0 "
            "6H8V9h2m0 6H8v-2h2m0 6H8v-2h2M6 7H4V5h2m0 6H4V9h2m0 6H4v-2h2m0 6H4v-2h2m6-10V3"
            "H2v18h20V7z"
        )
    },
}

component = dmc.Group(
    [
        DashEmojiMart(
            id="custom-picker",
            custom=CUSTOM_EMOJIS,
            categoryIcons=CATEGORY_ICONS,
            # No `categories` here, on purpose — see the note on this page.
            # Passing it alongside `custom` only works for the FIRST picker
            # mounted in a page's lifetime; after that emoji-mart filters the
            # custom ids against a stale internal list and drops them all. On a
            # multi-page docs site that makes rendering depend on which page you
            # visited first, which is about the worst kind of bug to chase.
            perLine=9,
            emojiSize=24,
            maxFrequentRows=1,
        ),
        dmc.Paper(
            [
                dmc.Text("Selected", size="sm", c="dimmed"),
                html.Div(
                    id="custom-out",
                    style={"fontSize": 48, "minHeight": 64},
                ),
                dmc.Text(id="custom-name", size="sm", fw=500),
                dmc.Text(id="custom-kind", size="xs", c="dimmed"),
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
    Output("custom-out", "children"),
    Output("custom-name", "children"),
    Output("custom-kind", "children"),
    Input("custom-picker", "value"),
    Input("custom-picker", "selectedEmoji"),
)
def show(value, emoji_obj):
    if not value:
        return dmc.Text("Nothing yet", c="dimmed", size="lg"), "", ""

    name = (emoji_obj or {}).get("name", "")
    if value.startswith("http"):
        glyph = html.Img(src=value, style={"height": 48, "width": 48})
        kind = "custom — value is an image URL"
    else:
        glyph = value
        kind = "built-in — value is the native glyph"
    return glyph, name, kind
