---
name: "Configuration"
description: "Every layout, sizing and locale prop, wired to live controls so you can see what each one does."
endpoint: "/configuration"
package: dash-emoji-mart
category: "Configuration"
order: 10
icon: "tabler:adjustments"
lastmod: 2026-08-01
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

.. admonition::Removing a category is one-way until you reload
    :icon: radix-icons:exclamation-triangle
    :color: orange

    Two controls above can take a category away and not give it back:

    * set `maxFrequentRows` to `0` and the Frequently-used section disappears —
      setting it back to `4` does not bring it back;
    * pick a few `categories`, then clear the field. "All of them" does not return.

    Both are the same emoji-mart behaviour, and it is global rather than per-picker.
    `init()` builds `Data.categories` once and then mutates that array in place: a
    category that ends up empty is `splice`d straight out of it. The only code path
    that rebuilds the list from `Data.originalCategories` is the one that runs when
    you pass `categories` — which is why choosing categories restores Frequently-used
    while clearing them does not.

    So the state lives in a module global that outlives the component, the page and
    every remount. Reloading the page is the only reset. If a category needs to come
    and go at runtime, pass `categories` explicitly every time rather than relying on
    the empty default.

.. admonition::`noCountryFlags` and `exceptEmojis` filter the grid, not the search
    :icon: radix-icons:exclamation-triangle
    :color: orange

    Turn `noCountryFlags` on above, then type "united" into the picker's search box. The
    flags category has shrunk to a short safe list — and the search still returns the
    flags of the UK, the US, the UAE and the UN.

    Measured against emoji-mart 5.6.0, and it is the same code path for both props: the
    filter runs while each category is built and splices the emoji out of
    `category.emojis`, while `SearchIndex.search` matches over
    `Object.values(Data.emojis)` — the unfiltered map — and applies no category filter of
    its own.

    Not worked around in this component, deliberately. emoji-mart loads its data into a
    module-global exactly once per page, so pre-filtering the data for one picker would
    silently change every other picker on the page, and every page after it in a Dash
    SPA — the same aliasing trap described on [Custom emojis](/custom-emojis). A visible
    search result beats an invisible, mount-order-dependent one.

    Use them for tidying, never as access control. To keep an emoji away from a user
    entirely, pass a trimmed data set rather than a filter.

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
