---
name: "Configuration"
description: "Every layout, sizing and locale prop, wired to live controls so you can see what each one does."
endpoint: "/configuration"
package: dash-emoji-mart
category: "Configuration"
icon: "tabler:adjustments"
---

.. llms_copy::Configuration

.. toc::

### Overview

The picker's shape is entirely prop-driven. The demo below wires every layout prop to a
control so you can dial in the configuration you want and copy the resulting call.

### Live demo

.. exec::docs.configuration.example
    :code: false

### Sizing

| Prop | Default | What it does |
|------|---------|--------------|
| `perLine` | `9` | Emojis per row. Also sets the picker's width unless `dynamicWidth` is on. |
| `emojiSize` | `24` | Size of the glyph, in px. |
| `emojiButtonSize` | `36` | Size of the button around the glyph, in px. |
| `emojiButtonRadius` | `"100%"` | Any CSS radius — `"6px"` gives square-ish buttons. |
| `dynamicWidth` | `False` | Let the picker fill its container instead of sizing from `perLine`. |

.. admonition::perLine and dynamicWidth are mutually exclusive
    :icon: radix-icons:info-circled
    :color: yellow

    With `dynamicWidth=True` the picker measures its parent, so `perLine` stops having a
    visible effect. Put it in a fixed-width parent, or leave `dynamicWidth` off.

### Layout

| Prop | Default | Options |
|------|---------|---------|
| `navPosition` | `"top"` | `"top"`, `"bottom"`, `"none"` |
| `previewPosition` | `"bottom"` | `"top"`, `"bottom"`, `"none"` |
| `searchPosition` | `"sticky"` | `"sticky"`, `"static"`, `"none"` |
| `skinTonePosition` | `"preview"` | `"preview"`, `"search"`, `"none"` |
| `maxFrequentRows` | `4` | `0` hides the "frequently used" category entirely. |

### Content

`categories` picks which built-in categories appear, and in what order. Leaving it empty
(the default) shows all of them:

```python
DashEmojiMart(
    id="picker",
    categories=["frequent", "people", "nature", "foods"],
    exceptEmojis=["rage", "cry"],
    noCountryFlags=True,
)
```

The built-in category ids are `frequent`, `people`, `nature`, `foods`, `activity`,
`places`, `objects`, `symbols` and `flags`.

.. admonition::`categories` is for built-in categories only
    :icon: radix-icons:exclamation-triangle
    :color: red

    Do not list custom category ids here, and do not pass this prop at all when you pass
    `custom`. emoji-mart filters it against a category list it snapshots on the first
    picker initialised in the page's lifetime, so custom ids resolve on that first picker
    and are silently dropped on every one after it. See
    [Custom emojis](/custom-emojis#ordering-custom-categories) for the full mechanism.

### Emoji set and locale

`set` chooses which artwork the picker renders: `"native"` (the default — the OS's own
emoji font, no images fetched), or `"apple"`, `"google"`, `"twitter"`, `"facebook"`, which
load spritesheets from jsDelivr.

`locale` translates the UI and search index. `"en"`, `"ar"`, `"be"`, `"cs"`, `"de"`,
`"es"`, `"fa"`, `"fi"`, `"fr"`, `"hi"`, `"it"`, `"ja"`, `"ko"`, `"nl"`, `"pl"`, `"pt"`,
`"ru"`, `"sa"`, `"tr"`, `"uk"`, `"vi"` and `"zh"` ship with emoji-mart.

.. admonition::Changing `set` or `locale` needs a remount
    :icon: radix-icons:exclamation-triangle
    :color: orange

    emoji-mart reads both once, when it initialises its internal store. Updating either
    prop on a live picker leaves the old data in place. Wrap the picker in a
    `html.Div(..., id=...)` whose **id** varies with the value, as the demo above does —
    Dash keys every child on its id, so a new id means React discards the old picker
    instead of patching it.

    Not `key=`. Dash's html components accept a `key` prop, but the renderer never reads
    it when reconciling: it builds the React key from the component's id
    (`key: container.props.id ? stringifyId(container.props.id) : stringifyPath(path)`).
    A `key=` therefore forces no remount and reaches the `<div>` as a stray prop, which
    is the source of the `` `key` is not a prop `` warning in the console.

### Source

.. source::docs/configuration/example.py
    :defaultExpanded: false
    :withExpandedButton: true
