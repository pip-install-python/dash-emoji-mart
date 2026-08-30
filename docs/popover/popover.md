---
name: "Picker in a Popover"
description: "The pattern most apps actually want — a trigger button that opens the picker, and closes it on pick or on an outside click. One callback."
endpoint: "/popover"
package: dash-emoji-mart
category: "Dash integration"
order: 20
icon: "tabler:message-2-share"
lastmod: 2026-08-01
---

.. llms_copy::Picker in a Popover

.. toc::

### Overview

Very few apps want a 400px picker sitting in the page. The usual shape is a small trigger
— a button, an avatar, a reaction affordance — that opens the picker, takes one pick, and
closes.

`dmc.Popover` gets you all of that except the last step. It opens itself when the target
is clicked and closes itself on an outside click or on `Escape`, so the only thing left to
write is *close after a pick* — one callback.

### Live demo

.. exec::docs.popover.example
    :code: false

### The wiring

One callback, one `opened` state:

```python
import dash_mantine_components as dmc
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from dash_emoji_mart import DashEmojiMart

layout = dmc.Popover(
    [
        dmc.PopoverTarget(dmc.Button("Add reaction", id="trigger")),
        dmc.PopoverDropdown(DashEmojiMart(id="picker", previewPosition="none")),
    ],
    id="popover",
    opened=False,
    position="bottom-start",
    withArrow=True,
)

# Opening is client-side — dmc.Popover does it. This closes it after a pick.
@callback(
    Output("out", "children"),
    Output("popover", "opened"),
    Output("picker", "value"),
    Input("picker", "value"),
    prevent_initial_call=True,
)
def close_on_pick(value):
    if not value:      # our own reset landing back here — see below
        raise PreventUpdate
    return value, False, None
```

.. admonition::Clear `value` on the way out, or the second identical pick does nothing
    :icon: radix-icons:exclamation-triangle
    :color: orange

    Closing the popover does not reset the picker — unmounting it does not clear the prop
    in Dash's store. So picking 🎉 twice in a row writes the same `value` the second time,
    Dash sees no change, and no callback fires: the popover just sits there open.

    Writing `None` back to `value` makes every pick a change. The `PreventUpdate` guard is
    what keeps that write from re-entering the callback and blanking the reaction it just
    set.

.. admonition::Do NOT add a callback that toggles opened from the trigger
    :icon: radix-icons:exclamation-triangle
    :color: red

    It is the one mistake that makes this whole pattern look broken, and the symptom is
    a trigger that appears to do nothing at all. Details below.

### Why there is no toggle callback

`dmc.Popover` wraps whatever you hand `PopoverTarget` in a Box carrying its own click
handler, so opening happens client-side before any callback runs:

```javascript
// dash_mantine_components — Popover
if (type === "PopoverTarget")
    return <Popover.Target>
             <Box onClick={() => setProps({opened: !opened})}>{child}</Box>
           </Popover.Target>
```

A `toggle` callback on the trigger's `n_clicks` that reads `State("popover", "opened")`
therefore sees the *already flipped* `True`, returns `not True` → `False`, and shuts the
popover in the same round trip that opened it.

Closing is covered too. Mantine's `closeOnClickOutside` and `closeOnEscape` both route
through the Popover's `onChange`, which DMC wires to `setProps({opened: False})` — so a
dismissal without a pick needs no Python either.

.. admonition::Popover, not HoverCard
    :icon: radix-icons:info-circled

    `dmc.HoverCard` is hover-triggered, so it closes the moment the pointer leaves the
    trigger on its way to the picker. `dmc.Popover` supports click triggering and a
    controlled `opened`, with the same styling.

.. admonition::Leave `keepMounted` off
    :icon: radix-icons:exclamation-triangle
    :color: orange

    With `keepMounted=True` every picker in the page mounts on load — a full emoji
    dataset and ~1500 buttons each — for popovers the reader may never open. On the
    three-row demo above that is three pickers built up front instead of zero.

### Outside clicks without dmc.Popover

`clickedOutside` is a counter the picker bumps whenever a click lands outside its own
wrapper. Inside a `dmc.Popover` you do not need it — Mantine's own outside-click
handling already fires. It is for the case where you rolled your own panel:

```python
layout = html.Div(
    [
        dmc.Button("Add reaction", id="trigger"),
        dmc.Collapse(DashEmojiMart(id="picker"), id="panel", opened=False),
    ]
)

@callback(
    Output("panel", "opened", allow_duplicate=True),
    Input("picker", "clickedOutside"),
    prevent_initial_call=True,
)
def close_on_outside(_n):
    return False
```

.. admonition::`allow_duplicate=True` when two callbacks write the same prop
    :icon: radix-icons:info-circled

    Add it to every writer past the first — a close-on-pick and a close-on-outside
    callback both targeting `opened`, say. Each one also needs
    `prevent_initial_call=True` alongside it.

### Trimming the picker down

In a popover the picker is the whole surface, so the chrome that helps in a full-page
layout mostly gets in the way:

```python
DashEmojiMart(
    id="picker",
    previewPosition="none",     # drop the 40px preview footer
    skinTonePosition="search",  # tuck the tone selector into the search bar
    maxFrequentRows=1,
    perLine=8,
    emojiSize=22,
)
```

### Reaction bars

For a per-row reaction picker, give each picker a pattern-matching id and let one `MATCH`
callback serve all of them — see [Callbacks & props](/callbacks#pattern-matching-ids). The
demo above does this for its three message rows, and adding a fourth row needs no new
callback code.

### Source

.. source::docs/popover/example.py
    :defaultExpanded: false
    :withExpandedButton: true
