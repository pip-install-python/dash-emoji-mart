"""`.. props::<module>.<Component>` — a prop table generated from the component.

markdown2dash ships a `.. kwargs::` directive, but it only understands NUMPY-style
docstrings ("Parameters\\n----------"), which is what Dash Mantine Components emits.
Components produced by `dash-generate-components` use a different shape entirely:

    Keyword arguments:

    - id (string | dict; optional):
        The ID used to identify this component in Dash callbacks.

    - perLine (number; default 9):
        Emojis per row.

Pointing `.. kwargs::` at one of those silently yields an EMPTY table — it finds no
"----------" marker, falls into its `attrs["kwargs"] = []` branch and renders nothing. The
page still builds and every smoke check still passes, which is exactly why this needed its
own directive rather than a bug report.

Usage in a markdown file:

    .. props::dash_emoji_mart.DashEmojiMart

The table is read from the live component at page-load time, so it cannot drift from the
installed version the way a hand-written table does.
"""

from __future__ import annotations

import importlib
import inspect
import re

import dash_mantine_components as dmc
from dash.development.base_component import Component

from markdown2dash.src.directives.base import BaseDirective

# "- name (type; optional):" / "- name (type; default X):" — the trailing colon is
# absent when a prop has no description, so it is optional here.
_PROP = re.compile(r"^- (\w+) \(([^)]*)\):?\s*$")


def _parse_dash_docstring(docstring: str) -> list[dict]:
    """Pull (name, type, default, description) out of a Dash component docstring."""
    if not docstring or "Keyword arguments:" not in docstring:
        return []

    body = docstring.split("Keyword arguments:", 1)[1]
    props: list[dict] = []
    current: dict | None = None

    for line in body.splitlines():
        match = _PROP.match(line.strip()) if line.startswith("- ") else None
        if match:
            if current:
                props.append(current)
            name, spec = match.groups()
            # The spec is "<type>; optional" or "<type>; default <value>".
            if ";" in spec:
                type_part, _, qualifier = spec.partition(";")
            else:
                type_part, qualifier = spec, ""
            qualifier = qualifier.strip()
            default = (
                qualifier[len("default ") :].strip()
                if qualifier.startswith("default ")
                else ""
            )
            current = {
                "name": name,
                "type": type_part.strip(),
                "default": default,
                "description": "",
            }
        elif current is not None and line.strip():
            current["description"] = (current["description"] + " " + line.strip()).strip()

    if current:
        props.append(current)
    return props


class Props(BaseDirective):
    NAME = "props"

    def render(self, renderer, title: str, content: str, **options) -> Component:
        module_path, _, component_name = title.strip().rpartition(".")
        try:
            component = getattr(importlib.import_module(module_path), component_name)
            props = _parse_dash_docstring(inspect.getdoc(component))
        except Exception as exc:  # noqa: BLE001 - a docs page must still render
            return dmc.Alert(
                f"Could not introspect {title}: {type(exc).__name__}: {exc}",
                title="Prop table unavailable",
                color="red",
            )

        if not props:
            return dmc.Alert(
                f"{title} exposes no documented props.",
                title="Prop table empty",
                color="orange",
            )

        rows = [
            dmc.TableTr(
                [
                    dmc.TableTd(dmc.Code(p["name"])),
                    dmc.TableTd(dmc.Text(p["type"], size="sm", c="dimmed")),
                    dmc.TableTd(
                        dmc.Code(p["default"]) if p["default"] else dmc.Text("—", c="dimmed")
                    ),
                    dmc.TableTd(dmc.Text(p["description"], size="sm")),
                ]
            )
            for p in props
        ]

        return dmc.Box(
            dmc.Table(
                [
                    dmc.TableThead(
                        dmc.TableTr(
                            [
                                dmc.TableTh("Prop"),
                                dmc.TableTh("Type"),
                                dmc.TableTh("Default"),
                                dmc.TableTh("Description"),
                            ]
                        )
                    ),
                    dmc.TableTbody(rows),
                ],
                striped=True,
                withTableBorder=True,
                highlightOnHover=True,
                verticalSpacing="sm",
            ),
            # Long type unions widen the table past the content column on
            # narrow viewports; scroll the table rather than the page.
            style={"overflowX": "auto"},
        )
