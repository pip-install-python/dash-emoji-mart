---
name: "Iconify Icon Sets"
description: "Turn any of Iconify's 150+ icon sets — twemoji, OpenMoji, Fluent Emoji, Tabler — into pickable categories."
endpoint: "/iconify"
package: dash-emoji-mart
category: "Custom emojis"
icon: "simple-icons:iconify"
---

.. llms_copy::Iconify Icon Sets

.. toc::

### Overview

[Iconify](https://icon-sets.iconify.design/) hosts over 150 icon sets, several of them
emoji sets far larger than the one emoji-mart bundles — twemoji has ~4,000 glyphs,
OpenMoji ~4,200. `dash_emoji_mart.iconify` fetches a set's index and reshapes it into the
category structure `custom=` expects:

```python
from dash_emoji_mart import DashEmojiMart
from dash_emoji_mart.iconify import iconify_to_emoji_mart

DashEmojiMart(
    id="picker",
    custom=iconify_to_emoji_mart("twemoji", max_icons_per_category=60),
)
```

Because Iconify icons are images, `value` comes back as the icon's SVG URL — the same as
any other [custom emoji](/custom-emojis).

### Install

This is the only part of the package that reaches the network, so `requests` is an opt-in
extra and the module imports lazily. `import dash_emoji_mart` never needs it:

```bash
pip install "dash-emoji-mart[iconify]"
```

### Live demo

.. exec::docs.iconify.example
    :code: false

### API

.. admonition::iconify_to_emoji_mart(prefixes, max_icons_per_category=100, include_categories=None, exclude_categories=None, flatten=False)
    :icon: tabler:code

    Convert one or more sets into `custom=` categories.

    * **prefixes** — a prefix or list of them, e.g. `"twemoji"` or `["twemoji", "noto"]`.
    * **max_icons_per_category** — cap per category; `-1` for no cap. The default of 100
      exists because a whole set can be thousands of icons and every one becomes an
      `<img>` in the picker.
    * **include_categories** / **exclude_categories** — case-insensitive filters.
    * **flatten** — merge each set's categories into a single category per prefix.

Also available:

| Function | Returns |
|----------|---------|
| `get_emoji_icon_sets()` | Curated emoji-style sets, keyed by prefix. |
| `get_icon_sets()` | Curated general-purpose (non-emoji) sets. |
| `get_all_collections()` | Every set Iconify hosts. |
| `get_collection_info(prefix)` | One set's categories and icon names. |
| `search_icons(query, prefix=None, limit=50)` | Matching icons as emoji dicts. |
| `get_svg_url(prefix, icon)` | The CDN URL for one icon. |
| `clear_cache()` | Drop the disk and in-process caches. |

### Caching

Responses are memoised in-process and cached on disk for 24 hours, so a page that builds
its categories at import time pays the API cost once per day per container rather than
once per page view.

The cache lives outside the installed package — a pip-installed package is usually not
writable. Set `DASH_EMOJI_MART_CACHE_DIR` to relocate it:

```bash
export DASH_EMOJI_MART_CACHE_DIR=/var/cache/dash-emoji-mart
```

.. admonition::Build categories at import time, not in a callback
    :icon: radix-icons:exclamation-triangle
    :color: orange

    `iconify_to_emoji_mart` can make several API calls on a cold cache. Call it once at
    module level so the cost lands at startup; calling it inside a callback puts a network
    round-trip on the critical path of every interaction.

### Failure behaviour

Every request is wrapped: a network failure logs a warning and returns `{}`, so
`iconify_to_emoji_mart` yields an empty list and the picker renders without the optional
set. A page that loses its icon categories beats a page that 500s because
`api.iconify.design` had a bad minute.

.. admonition::emoji-mart's own categories stay in the picker
    :icon: radix-icons:info-circled

    Selecting a set filters what this demo *loads*, not what emoji-mart *shows*: its nine
    built-in categories are still there, ahead of the Iconify ones. `categories` looks
    like the fix and is not — measured both ways on this page, it filters correctly for
    the first set chosen and renders an **empty picker** for every set switched to
    afterwards, because emoji-mart resolves that prop against a category list it captured
    on the first init of the page's lifetime. Registering all three sets up front does not
    help either. See [Custom emojis](/custom-emojis) for the underlying aliasing.

    So the demo jumps to the Iconify section instead of hiding the built-ins: choosing a
    set clicks the picker's own custom-category nav button. If you genuinely need a picker
    with no built-in emoji at all, pass a trimmed emoji data set rather than a filter.

### Source

.. source::docs/iconify/example.py
    :defaultExpanded: false
    :withExpandedButton: true
