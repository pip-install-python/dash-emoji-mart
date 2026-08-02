---
name: "Theming"
description: "Light, dark and auto — and how to make the picker follow your app's colour scheme instead of the OS."
endpoint: "/theming"
package: dash-emoji-mart
category: "Configuration"
icon: "tabler:sun-moon"
---

.. llms_copy::Theming

.. toc::

### Overview

`theme` takes three values:

| Value | Behaviour |
|-------|-----------|
| `"auto"` (default) | Follows the OS/browser `prefers-color-scheme` setting. |
| `"light"` | Always light, whatever the OS says. |
| `"dark"` | Always dark, whatever the OS says. |

`"auto"` is the right default for a standalone picker, and the wrong one for any app with
its own theme toggle: the OS preference and the app's toggle disagree the moment a user
flips the toggle. Drive `theme` from your own state instead.

### Live demo

.. exec::docs.theming.example
    :code: false

### Following a Mantine colour scheme

The cheapest way to keep the picker in step with a `dmc.MantineProvider` is a clientside
callback that maps the scheme onto `theme` — no server round-trip, so the picker flips in
the same frame as the rest of the page:

```python
from dash import Input, Output, clientside_callback

clientside_callback(
    "(scheme) => scheme || 'light'",
    Output("picker", "theme"),
    Input("color-scheme-storage", "data"),
)
```

This documentation site does exactly that — the sun/moon toggle in the header drives every
picker on every page.

.. admonition::Theme changes do not need a remount
    :icon: radix-icons:check-circled
    :color: green

    Unlike `set` and `locale`, `theme` is read on every render. Updating it on a mounted
    picker works, and keeps the user's search text and scroll position intact.

### Styling the picker itself

emoji-mart exposes its own CSS custom properties, which you can set on any ancestor —
including through `style` on the component:

```python
DashEmojiMart(
    id="picker",
    style={
        "--em-rgb-accent": "250, 176, 5",
        "--em-rgb-background": "255, 255, 255",
        "--em-rgb-input": "245, 245, 245",
        "--em-rgb-color": "34, 36, 39",
    },
)
```

`emojiButtonColors` cycles hover backgrounds through a list instead:

```python
DashEmojiMart(
    id="picker",
    emojiButtonColors=[
        "rgba(155,223,88,.7)",
        "rgba(149,211,254,.7)",
        "rgba(247,233,34,.7)",
    ],
)
```

### Source

.. source::docs/theming/example.py
    :defaultExpanded: false
    :withExpandedButton: true
