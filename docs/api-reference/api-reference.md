---
name: "API Reference"
description: "Every prop on DashEmojiMart, generated from the component itself."
endpoint: "/api-reference"
package: dash-emoji-mart
category: "Start here"
order: 20
icon: "tabler:list-details"
lastmod: 2026-08-01
---

.. llms_copy::API Reference

.. toc::

### DashEmojiMart

The package exposes exactly one component. The table below is read from the installed
component at page load, so it always matches the version you have.

.. props::dash_emoji_mart.DashEmojiMart

### Selection props

`value` and `selectedEmoji` are written together on every pick; `clickedOutside` is a
counter. All three are outputs of the component — setting them from Python sets the
picker's idea of the current selection, but does not move the UI.

See [Callbacks & props](/callbacks) for what each one contains.

### Removed in 0.2.0

Four props existed in 0.0.x that no Dash app could ever use — Dash serialises props to
JSON, and a Python function is not serialisable, so passing any of them raised. They were
always `None` in practice:

| Removed prop | Replacement |
|--------------|-------------|
| `onEmojiSelect` | `Input("picker", "value")` or `Input("picker", "selectedEmoji")` |
| `onClickOutside` | `Input("picker", "clickedOutside")` |
| `onAddCustomEmoji` | no equivalent; open an issue if you need one |
| `getSpritesheetURL` | no equivalent; `set` covers the built-in spritesheets |

### Version

.. exec::docs.api-reference.example
    :code: false
