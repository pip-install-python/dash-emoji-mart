---
name: "Callbacks & Props"
description: "value vs selectedEmoji, reacting to outside clicks, and persisting a selection across reloads."
endpoint: "/callbacks"
package: dash-emoji-mart
category: "Dash integration"
icon: "tabler:arrows-exchange"
---

.. llms_copy::Callbacks & Props

.. toc::

### Two ways to read a selection

Every pick writes **both** props in one update, so a callback with both as `Input`s fires
once, not twice.

| Prop | Type | Contents |
|------|------|----------|
| `value` | `str` | `emoji.native` for a built-in emoji (`"😀"`), or `emoji.src` — the image URL — for a custom one. |
| `selectedEmoji` | `dict` | The whole emoji-mart object. |

`value` is the 0.0.x contract and is unchanged, so existing callbacks keep working.
`selectedEmoji` was added in 0.2.0 for callbacks that need more than the glyph:

```python
{
    "id": "grinning",
    "name": "Grinning Face",
    "native": "😀",
    "unified": "1f600",
    "keywords": ["face", "smile", "happy", "joy", "grin"],
    "shortcodes": ":grinning:",
    "skin": 1,
    "aliases": ["grinning_face"],
}
```

A custom or Iconify emoji carries `src` instead of `native` — which is the cleanest way to
tell the two apart:

```python
@callback(Output("out", "children"), Input("picker", "selectedEmoji"))
def show(emoji):
    if not emoji:
        return "Nothing picked"
    if emoji.get("src"):
        return html.Img(src=emoji["src"], style={"height": 32})
    return emoji["native"]
```

### Live demo

.. exec::docs.callbacks.example
    :code: false

### Reacting to a click outside

emoji-mart hands its `onClickOutside` handler a DOM event, which cannot cross into Python.
The component surfaces it as `clickedOutside`, a counter with the same shape as
`n_clicks` — it increments on each outside click:

```python
@callback(
    Output("popover", "opened", allow_duplicate=True),
    Input("picker", "clickedOutside"),
    prevent_initial_call=True,
)
def close(_n):
    return False
```

.. admonition::Use it as a trigger, not a value
    :icon: radix-icons:info-circled

    Only the *change* matters; the number itself is meaningless. Pair it with
    `prevent_initial_call=True` so a fresh mount does not fire the callback.

.. admonition::Not needed inside a `dmc.Popover`
    :icon: radix-icons:info-circled

    `dmc.Popover` already dismisses itself on an outside click and writes `opened=False`
    back to Dash, so `clickedOutside` earns its keep on panels you built yourself — a
    `dmc.Collapse`, a styled `html.Div`, an absolutely-positioned card. See
    [Picker in a Popover](/popover) for what the popover case does and does not need.

.. admonition::"Outside" means outside the whole picker
    :icon: radix-icons:check-circled
    :color: green

    Clicking an emoji, the search box or a category tab does **not** increment it, and
    neither does the click that opened the picker.

    Both are worth stating because emoji-mart's own `onClickOutside` does the opposite on
    both counts: it fires whenever the event target is not exactly the picker's root
    element — so every emoji click counts as "outside" — and it registers its listener
    during mount, while the opening click is still bubbling, so it reports an outside
    click before the user has clicked anything. Wired to a popover, that closed the
    popover on the same click that opened it. `clickedOutside` is measured against the
    component's wrapper and bound one task after mount, so neither happens.

### Persistence

`value` is persisted by default once `persistence` is switched on, using Dash's standard
persistence machinery:

```python
DashEmojiMart(
    id="picker",
    persistence=True,
    persisted_props=["value", "selectedEmoji"],
    persistence_type="local",   # "local" | "session" | "memory"
)
```

`persisted_props` defaults to `["value"]` and `persistence_type` to `"local"`.

.. admonition::"Frequently used" persists separately
    :icon: radix-icons:info-circled

    emoji-mart keeps its own frequently-used tally in `localStorage` under its own key,
    independently of Dash persistence. It survives a reload whether or not `persistence`
    is set; `maxFrequentRows=0` is what turns it off.

### Pattern-matching ids

`id` accepts a dict, so pickers work inside `ALL`/`MATCH` callbacks like any other
component:

```python
DashEmojiMart(id={"type": "emoji-picker", "index": row_id})

@callback(
    Output({"type": "emoji-out", "index": MATCH}, "children"),
    Input({"type": "emoji-picker", "index": MATCH}, "value"),
)
def show(value):
    return value
```

### Props that need a remount

Most props update in place. Three are read only when emoji-mart builds its internal store,
so changing them on a mounted picker has no visible effect:

| Prop | Why |
|------|-----|
| `set` | Selects the spritesheet, loaded at init. |
| `locale` | Builds the translated search index at init. |
| `custom` | Merged into the emoji store at init. |

Force a remount by varying the **id** of a wrapper:

```python
return html.Div(DashEmojiMart(id="picker", set=chosen_set), id=f"mount-{chosen_set}")
```

Dash's renderer keys each child on its id, so a new wrapper id is a new React key and the
subtree is thrown away rather than patched. A `key=` prop does not work for this — it is
accepted by html components but never read during reconciliation, and it surfaces in the
console as `` `key` is not a prop ``.

.. admonition::A remount is not enough for `categories` + `custom`
    :icon: radix-icons:exclamation-triangle
    :color: red

    emoji-mart's store is module-global, not per-component, and `categories` is filtered
    against a snapshot taken on the *first* initialisation in the page's lifetime. A
    remount runs a *later* initialisation, which is exactly the case where custom ids no
    longer resolve — so remounting does not rescue the combination, it triggers the
    failure. Omit `categories` when you pass `custom`. See
    [Custom emojis](/custom-emojis#ordering-custom-categories).

### Source

.. source::docs/callbacks/example.py
    :defaultExpanded: false
    :withExpandedButton: true
