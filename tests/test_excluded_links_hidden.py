"""Admin pages hide from BOTH audiences — the llms-2plot-dev footgun, kept.

Before 1.6.8, a path hidden from the sidebar (then `excluded_links`) stayed
in sitemap.xml, /llms.txt, the tier corpora, MCP and the prerender; a fork
"hid" the template's tutorials and kept publishing them to every crawler
as its own documentation. 1.6.38 deleted `excluded_links` (the sidebar is
built from frontmatter now) — what remains hidden-by-rule is `/admin/*`,
and this suite pins the parity from both ends: the mechanism (every admin
path is in dimll's hidden state) and the surfaces (none appears in the
sitemap or /llms.txt, none in the sidebar tree, while a control page does
— so an empty sitemap can never pass this vacuously).
"""

from __future__ import annotations


def _admin_paths():
    import dash

    return [p["path"] for p in dash.page_registry.values() if p["path"].startswith("/admin/")]


def test_every_admin_path_is_machine_hidden(app):
    from dash_improve_my_llms import is_hidden

    paths = _admin_paths()
    assert paths, "no admin pages registered — the pin would be vacuous"
    not_hidden = [p for p in paths if not is_hidden(p)]
    assert not_hidden == [], (
        f"in the app but NOT hidden from the machine surfaces: {not_hidden} — "
        "the page's mark_hidden wiring is broken or was removed"
    )


def test_admin_paths_absent_from_sitemap_llms_and_sidebar(client, app):
    import dash

    from components.navbar import create_content

    sitemap = client.get("/sitemap.xml").text
    tree = str(create_content(dash.page_registry.values()))

    # THE WHOLE CORPUS, not just the index (template 1.6.42, llms's note 75):
    # PROSE CAN LEAK WHAT STRUCTURE HIDES. On llms.2plot.dev, hyperlinking
    # /admin/control-board in five docs pages put the path into /llms.txt
    # while every navbar, sitemap and tier pin passed — the page was hidden
    # and its address published anyway. The tier documents concatenate page
    # bodies, so they carry any such link too; sweeping only the index is
    # how that went unseen. The seat swept twelve hosts and only llms leaked,
    # which is exactly why the pin has to outlive the one host that failed.
    corpus = {}
    for doc in ("/llms.txt", "/llms-small.txt", "/llms-full.txt"):
        r = client.get(doc)
        if r.status == 200:
            corpus[doc] = r.text
    assert "/llms.txt" in corpus, "the site index must be served"

    leaked = []
    for path in _admin_paths():
        if f"{path}</loc>" in sitemap:
            leaked.append(f"{path} in sitemap.xml")
        for doc, text in corpus.items():
            # LINK-SHAPED, not any mention — the template's match, applied
            # across the corpus rather than only the index. `](/admin/x)` or
            # `(/admin/x)` is an address an agent can follow; `/admin/x`
            # inside a backticked code span in a changelog is documentation.
            # Broadening this to a substring made it fire on THIS repo's own
            # CHANGELOG, which describes the admin pages in the same entry
            # that hid them — a true statement about the site, not a leak,
            # and a pin that forbids writing prose about your own admin
            # pages will be deleted by the first person it inconveniences.
            if f"{path})" in text or f"{path}/llms.txt" in text:
                leaked.append(f"{path} in {doc}")
        if path in tree:
            leaked.append(f"{path} in the startup sidebar tree")
    assert leaked == [], f"admin pages published: {leaked}"

    # Positive control: a real page IS listed, so an empty sitemap or a
    # broken llms.txt cannot make the assertions above pass vacuously.
    # Derived from the sidebar's own first page (template 1.6.41), never
    # named, so this file is fork-invariant.
    from components.navbar import sections_for

    sections = sections_for(dash.page_registry.values())
    assert sections, "the sidebar has no docs section"
    control = sections[0][1][0]["path"]
    assert f"{control}</loc>" in sitemap
    assert control in corpus["/llms.txt"]
    assert control in tree
    # And the corpus really was swept: a tier doc that 404s would make the
    # loop above pass by iterating one document.
    assert len(corpus) > 1, f"only {sorted(corpus)} served — tier docs off?"
