"""Make markdown2dash's inline formatters emit `<span>` instead of `<p>`.

markdown2dash's DashRenderer maps `paragraph` to `dmc.Text` — which renders a
`<p>` — and then maps the *inline* runs `**bold**`, `*italic*` and `~~struck~~`
to `dmc.Text` as well. Nesting the second inside the first is invalid HTML, and
React says so on every page that has an emphasised word in a paragraph::

    Warning: validateDOMNesting(...): <p> cannot appear as a descendant of <p>
        at p
        at ss   (dmc.Text)
        at p
        at ss   (dmc.Text)

`display="inline"` — which the library already passes — changes how the box is
painted but not what the tag is, so it does not resolve the nesting.
`dmc.Text(span=True)` renders a `<span>` with the same typography.

Patching the three methods on the class, rather than subclassing, deliberately
leaves ``markdown2dash.create_parser`` as the single source of the plugin list:
this module has no opinion about anything except the tag name.

Import for side effect BEFORE the parser is built — see pages/markdown.py.
"""

from dash.development.base_component import Component
from markdown2dash.src.decorators import class_name
from markdown2dash.src.renderer import DashRenderer

import dash_mantine_components as dmc


@class_name  # keeps the .m2d-emphasis className the site CSS targets
def emphasis(self, text: str) -> Component:
    return dmc.Text(text, fs="italic", span=True)


@class_name  # .m2d-strong carries font-weight: 500 in assets/m2d.css
def strong(self, text: str) -> Component:
    return dmc.Text(text, fw="bold", span=True)


@class_name
def strikethrough(self, text: str) -> Component:
    return dmc.Text(text, td="line-through", span=True)


def apply() -> None:
    """Rebind the inline formatters. Idempotent."""
    DashRenderer.emphasis = emphasis
    DashRenderer.strong = strong
    DashRenderer.strikethrough = strikethrough
