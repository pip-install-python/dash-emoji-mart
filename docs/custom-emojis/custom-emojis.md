---
name: "Custom Emojis"
description: "Add your own categories of images, GIFs and SVGs — with their own nav icons — alongside the built-in emojis."
endpoint: "/custom-emojis"
package: dash-emoji-mart
category: "Custom emojis"
order: 10
icon: "tabler:photo-plus"
lastmod: 2026-08-01
---

.. llms_copy::Custom Emojis

.. toc::

### Overview

`custom` takes a list of categories. Each category has an `id`, a display `name`, and a
list of `emojis`, and each emoji points at an image URL:

```python
CUSTOM = [
    {
        "id": "team",
        "name": "Team",
        "emojis": [
            {
                "id": "party_parrot",
                "name": "Party Parrot",
                "short_names": ["party_parrot"],
                "keywords": ["dance", "party", "parrot"],
                "skins": [{"src": "https://example.com/parrot.gif"}],
                "native": "",
                "unified": "custom",
            },
        ],
    },
]

DashEmojiMart(id="picker", custom=CUSTOM)
```

Anything the browser can render in an `<img>` works: PNG, SVG, animated GIF, WebP.

.. admonition::SVGs with no width/height used to render blank — fixed in 0.2.1
    :icon: radix-icons:info-circled

    emoji-mart sizes a custom emoji's image with `max-width`/`max-height` alone. A raster
    source has intrinsic dimensions and scales down to fit, but an SVG carrying only a
    `viewBox` has no intrinsic size, so it collapsed to 0x0 — present and clickable, but
    invisible. Raw SVGs off a repo (devicons and most icon projects) hit this; Iconify's
    API SVGs ship `width="1em"` and never did.

    The component now sizes custom-emoji images in the picker's shadow root, so any SVG
    works regardless of what its root element declares. Nothing is required of your data.

### Live demo

.. exec::docs.custom-emojis.example
    :code: false

### The emoji object

| Key | Required | Notes |
|-----|----------|-------|
| `id` | yes | Unique across every category. This is what `selectedEmoji["id"]` returns. |
| `name` | yes | Shown in the preview pane. |
| `skins` | yes | A list of `{"src": url}`. Custom emojis have no skin tones — give it one entry. |
| `keywords` | no | Extra search terms. `name` and `id` are already indexed. |
| `short_names` | no | Shortcode aliases, searchable with a leading `:`. |
| `native` | no | Leave as `""`. Custom emojis have no glyph. |
| `unified` | no | Leave as `"custom"`. |

### What a callback receives

Custom emojis have no native glyph, so `value` is the **image URL** rather than a
character. That is the one behavioural difference from a built-in emoji, and the reason
most readouts branch on it:

```python
@callback(Output("out", "children"), Input("picker", "value"))
def show(value):
    if not value:
        return "Nothing picked"
    if value.startswith("http"):
        return html.Img(src=value, style={"height": 48})
    return value
```

`selectedEmoji` avoids the guesswork — a custom emoji's object carries `src`, a built-in
one carries `native`. See [Callbacks & props](/callbacks).

### Category icons

`categoryIcons` maps a category `id` to the icon shown in the nav bar. The value is an
object with an `svg` key holding inline SVG markup:

```python
DashEmojiMart(
    id="picker",
    custom=CUSTOM,
    categoryIcons={
        "team": {
            "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
                   'width="1em" height="1em"><path fill="currentColor" d="..."/></svg>'
        },
    },
)
```

.. admonition::Size the SVG in `em`, and fill with `currentColor`
    :icon: radix-icons:info-circled

    `width="1em" height="1em"` lets the icon scale with the nav bar, and
    `fill="currentColor"` lets it pick up the active/inactive colours emoji-mart applies.
    A hard-coded `width="24"` and a literal colour will look wrong in one of the themes.

### Ordering custom categories

Custom categories are appended after the built-in ones, in the order you list them in
`custom`. That order you control; their position relative to the built-ins you do not.

.. admonition::Do not pass `categories` together with `custom`
    :icon: radix-icons:exclamation-triangle
    :color: red

    It appears to work and then fails, which is worse than failing outright.

    emoji-mart filters `categories` against an internal `originalCategories` array that
    it captures **by reference** on the first picker initialised in the page's lifetime.
    Custom categories pushed during that first init land in it through the aliasing, so
    the combination looks fine. Every later init rebuilds the category list as a *new*
    array, breaking the alias — so from the second picker onwards the filter runs against
    a stale list that cannot contain your custom ids, and **every custom category is
    silently dropped**.

    In a multi-page app that makes rendering depend on which page the user opened first.
    The picker on this page renders custom emojis on a cold load and an empty grid after
    you have visited [Iconify icon sets](/iconify) — for as long as the tab lives.

    There is no `categories` value that avoids this. Omit the prop when you use `custom`;
    the filter is then skipped entirely and your categories survive.

If you need *only* your own categories with no built-ins at all, the reliable route is
to pass a trimmed emoji data set rather than to filter with `categories`.

### Source

.. source::docs/custom-emojis/example.py
    :defaultExpanded: false
    :withExpandedButton: true
