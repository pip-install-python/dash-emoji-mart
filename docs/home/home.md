---
name: "Home"
description: "An emoji picker for Dash 4 — emoji-mart wrapped as a single component, with custom categories and Iconify icon sets."
endpoint: "/"
package: dash-emoji-mart
category: "Start here"
icon: "tabler:home"
---

.. llms_copy::Home

.. toc::

### Overview

`dash-emoji-mart` wraps [emoji-mart](https://github.com/missive/emoji-mart) — the picker
behind Missive, and the one most React apps reach for — as a single Dash component.

One import, one component, no clientside setup:

```python
from dash import Dash, callback, html, Input, Output
from dash_emoji_mart import DashEmojiMart

app = Dash(__name__)
app.layout = html.Div([
    DashEmojiMart(id="picker"),
    html.Div(id="out", style={"fontSize": 48}),
])

@callback(Output("out", "children"), Input("picker", "value"))
def show(value):
    return value or "Pick one"

if __name__ == "__main__":
    app.run(debug=True)
```

The full emoji data set is bundled inside the component, so the picker works offline and
makes no requests of its own.

### Install

```bash
pip install dash-emoji-mart
```

Iconify icon-set support is an optional extra — see [Iconify icon sets](/iconify):

```bash
pip install "dash-emoji-mart[iconify]"
```

### Live demo

.. exec::docs.home.example
    :code: false

### What you get

.. admonition::Search, skin tones, frequently used
    :icon: radix-icons:magnifying-glass

    Everything emoji-mart does out of the box: fuzzy search across names, keywords and
    shortcodes, six skin tones, a per-browser "frequently used" row, and 10 UI locales.

.. admonition::Your own emojis
    :icon: radix-icons:star

    Add categories of your own images, GIFs or SVGs with `custom=`, and give each one a
    nav icon with `categoryIcons=`. See [Custom emojis](/custom-emojis).

.. admonition::150+ Iconify sets
    :icon: simple-icons:iconify

    `dash_emoji_mart.iconify` converts any Iconify set — twemoji, openmoji, Fluent Emoji,
    or a non-emoji set like Tabler — into pickable categories. See
    [Iconify icon sets](/iconify).

### Where to go next

* [Configuration](/configuration) — every layout and sizing prop, live.
* [Theming](/theming) — light, dark and following the app's colour scheme.
* [Callbacks & props](/callbacks) — `value` vs `selectedEmoji`, outside clicks, persistence.
* [Picker in a popover](/popover) — the pattern most apps actually want.
* [API reference](/api-reference) — the full prop table.

### Source

.. source::docs/home/example.py
    :defaultExpanded: false
    :withExpandedButton: true
