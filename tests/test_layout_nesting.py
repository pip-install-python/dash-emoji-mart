"""No page layout nests a list directly inside a children list.

THE DEFECT (modelviewer, found on the wire 2026-08-30, reported by the
ops seat): a page composed its layout as

    children=[hero, create_parser(...)(content)]

markdown2dash's parser returns a **list**, so that expression puts a
list *inside* a children list. Dash does not descend into a nested
list — React logs #31 and the page subtree renders EMPTY while the app
shell around it looks perfectly healthy. The suite was green. Every
smoke check was green. The page was blank.

That combination is why this pin exists rather than a code review note:
nothing else in the battery can see it. A blank page still returns 200,
still carries its canonical, still serves its crawler document (the
prerender is built from the markdown, not from the Dash tree), and
still passes an h1 count. The only surface that shows it is a browser.

THIS REPO IS NOT VULNERABLE THROUGH THAT PATH — pages/markdown.py
CONCATENATES (`[Title, Text] + parse(content)`) rather than nesting, so
the parsed list is flattened into the children list by construction.
The pin is here so that stays true: `+ layout` and `[..., layout]` are
one character apart in intent and worlds apart in outcome, and the
failure is silent.

The walk covers every registered page, including the ones that are not
markdown at all (/changelog, /api, the admin pages), because the defect
is about how ANY layout is composed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dash.development.base_component import Component

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _walk(node, path: str, findings: list) -> None:
    """Depth-first, recording any list found as a direct element of a
    children list. `path` mirrors the shape the modelviewer report used:
    `/.Container.children[1]`."""
    if isinstance(node, (list, tuple)):
        for i, child in enumerate(node):
            _walk(child, f"{path}[{i}]", findings)
        return
    if not isinstance(node, Component):
        return
    children = getattr(node, "children", None)
    here = f"{path}.{type(node).__name__}"
    if isinstance(children, (list, tuple)):
        for i, child in enumerate(children):
            if isinstance(child, (list, tuple)):
                findings.append(f"{here}.children[{i}]")
                # Keep walking it — one nest can hide another.
            _walk(child, f"{here}.children[{i}]", findings)
    elif children is not None:
        _walk(children, f"{here}.children", findings)


def _resolve(layout):
    """Page layouts may be values or callables (this repo wraps every docs
    page in `gate_layouts.gated_layout`, which decides per render)."""
    return layout() if callable(layout) else layout


def test_the_walk_itself_sees_a_nested_list():
    """NON-VACUITY, ported from the template's 1.6.42 copy — the half this
    fork verified by hand and never pinned. A guard that cannot go red
    guards nothing, so the walk must flag the modelviewer shape on demand."""
    import dash_mantine_components as dmc

    bad = dmc.Container([dmc.Title("Hero"), [dmc.Text("parsed"), dmc.Text("list")]])
    findings: list = []
    _walk(bad, "/fixture", findings)
    assert findings == ["/fixture.Container.children[1]"]


@pytest.fixture(scope="module")
def registry(app_module):
    import dash

    return dict(dash.page_registry)


def test_no_page_nests_a_list_inside_a_children_list(registry):
    findings: list[str] = []
    unresolved: list[str] = []

    for page in registry.values():
        path = page.get("path") or page.get("module")
        try:
            layout = _resolve(page.get("layout"))
        except Exception as exc:  # a layout needing a request context
            unresolved.append(f"{path}: {type(exc).__name__}")
            continue
        page_findings: list[str] = []
        _walk(layout, path, page_findings)
        findings.extend(page_findings)

    assert not findings, (
        "a list nested directly inside a children list renders EMPTY and "
        "says nothing about it (Dash does not descend; React #31). Splat it "
        f"(`*parsed`) or concatenate (`[...] + parsed`): {findings}"
    )
    # Not a silent skip: if a layout could not be built, say which, so this
    # test cannot pass by having walked nothing.
    assert len(unresolved) < len(registry), f"nothing walked; all failed: {unresolved}"


def test_the_docs_pages_really_carry_their_parsed_content(registry):
    """The positive control. The assertion above passes vacuously on a page
    whose layout is empty for some *other* reason — which is the same
    symptom the defect produces. So: a real docs page must render a tree
    with real depth, and its heading must be in it."""
    # DERIVED FROM THE REGISTRY, never named (template 1.6.42): the first
    # page that registered a TOC. Naming a page here made this file the one
    # thing in the pin that a fork has to edit, and a renamed page turned a
    # real control into a KeyError.
    # Derived from the REGISTRY ALONE (template 1.6.43, filed by clerkhook,
    # which has no lib/aside to import). Admin and `/` excluded — and that
    # exclusion, which this fork added for its own reason, is now the
    # template's too: this site's root heads itself with SITE_BRAND rather
    # than its nav label, so `page["name"] in str(layout)` is false there by
    # design. The fork rule and the fleet rule turned out to be one rule.
    by_path = {p.get("path"): p for p in registry.values()}
    docs = sorted(p for p in by_path
                  if p and p != "/" and not p.startswith("/admin/")
                  and p not in ("/404", "/api", "/changelog"))
    assert docs, "no docs page registered"
    page = by_path[docs[0]]
    layout = _resolve(page["layout"])

    nodes: list = []

    def count(node):
        if isinstance(node, (list, tuple)):
            for c in node:
                count(c)
            return
        if isinstance(node, Component):
            nodes.append(node)
            children = getattr(node, "children", None)
            if children is not None:
                count(children)

    count(layout)
    assert len(nodes) > 20, f"only {len(nodes)} components — is the page empty?"
    assert page["name"] in str(layout), "the page's own heading is missing"


def test_the_markdown_page_builder_concatenates_rather_than_nesting():
    """The source pin, because the walk above can only see the pages that
    exist today. `parse()` returns a LIST; the builder must flatten it."""
    import ast

    src = (REPO_ROOT / "pages" / "markdown.py").read_text()
    tree = ast.parse(src)

    nested = []
    for node in ast.walk(tree):
        # `[..., parse(content), ...]` — a call to parse() sitting as an
        # ELEMENT of a list display is the modelviewer shape exactly.
        if not isinstance(node, ast.List):
            continue
        for element in node.elts:
            if (isinstance(element, ast.Call)
                    and isinstance(element.func, ast.Name)
                    and element.func.id == "parse"):
                nested.append(ast.dump(element)[:80])
    assert not nested, (
        "parse() returns a list; putting that call directly inside a list "
        f"display nests it and the page renders blank: {nested}"
    )
    assert "] + layout" in src or "*layout" in src, (
        "the parsed list must be concatenated or splatted into the page's "
        "children, never nested"
    )
