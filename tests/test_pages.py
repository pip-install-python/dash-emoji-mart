"""Page structure on the MACHINE lane, pinned for every page.

The browser lane is well covered elsewhere. This file watches the document a
generic client receives — the one crawlers and text extractors read — because
that lane fails silently: nothing renders wrong, nobody sees it, and the only
symptom is an SEO audit months later.
"""

import re


def test_prerender_single_h1_and_deduped_footer_llms_links(client, page_paths):
    """What the >=2.7.1 floor buys, pinned from the app's side, on EVERY page.

    Below dimll 2.7.0 every page served TWO h1s to a generic client — the
    injected prerender header plus the document body's own markdown H1, a
    duplicate-H1 page in every crawler's eyes — and the home footer printed its
    /llms.txt link twice (on "/" the per-page link equals the root's; subpages
    legitimately carry both, and those are DISTINCT).

    The sweep also catches app-side H1 pollution, which is the more interesting
    half. On the template this test's first run found a tutorial page's machine
    lane serving FIVE h1s, because the source-directive expansion had rewritten
    a `.. source::` example sitting inside a ```markdown teaching fence: the
    injected ```python fence closed the outer fence early, and from there the
    inlined Python file was parsed as markdown, turning every `# comment` line
    into a heading. This site does not currently teach the directive inside a
    fence, so that defect is latent here rather than live — which is exactly
    why it is worth a pin rather than a one-off fix.

    HTML comments are stripped before counting: templates/index.html
    legitimately SAYS "<h1>" inside the comment explaining its noscript block.
    Admin pages are skipped — they are hidden from machine surfaces and carry
    no prerender.
    """
    for path in page_paths:
        if path.startswith("/admin"):
            continue
        html = client.get(path).text  # default UA — the universal lane
        stripped = re.sub(r"<!--.*?-->", "", html, flags=re.S)

        h1s = re.findall(r"<h1[\s>]", stripped)
        assert len(h1s) == 1, (
            f"{path}: {len(h1s)} h1 elements in the generic-lane document — "
            "either the pre-2.7.0 prerender-header duplicate or app-side "
            "markdown leaking headings (the fence-expansion class)"
        )

        footer = re.search(r"<footer.*?</footer>", stripped, re.S)
        assert footer, f"{path}: no prerender footer in the generic-lane document"
        llms_links = re.findall(r'href="([^"]*llms\.txt)"', footer.group(0))
        assert len(llms_links) == len(set(llms_links)), (
            f"{path}: duplicate llms.txt links in the prerender footer "
            f"({llms_links}) — 2.7.0 dedups the per-page link when it equals "
            "the root"
        )
        if path == "/":
            assert llms_links == ["/llms.txt"], (
                f"home footer llms links {llms_links} — expected exactly the "
                "root link once"
            )


def test_source_expansion_is_fence_aware(app):
    """A `.. source::` inside a fenced block is documentation, not a directive.

    Expanding one injects a ```python fence inside the already-open fence,
    closing it early; from there the inlined file renders as markdown on the
    machine lane and every `# comment` line becomes an <h1>.

    The `app` fixture is requested only so pages/markdown.py is already
    imported with the repo root as the working directory — the expansion
    resolves paths relative to it.
    """
    import sys

    expand = sys.modules["pages.markdown"]._expand_source_directives

    expanded = expand(".. source::requirements.txt")
    assert "# File: requirements.txt" in expanded, "real directive not expanded"
    assert "```" in expanded, "expansion lost its fence"

    taught = "```markdown\n.. source::requirements.txt\n```"
    assert expand(taught) == taught, "a fenced example was expanded"

    tilde = "~~~\n.. source::requirements.txt\n~~~"
    assert expand(tilde) == tilde, "a tilde-fenced example was expanded"


def test_source_expansion_still_consumes_directive_options(app):
    """Fence-awareness must not cost the option-stripping this repo added.

    This site's `.. source::` directives carry indented `:option: value` lines.
    The expansion replaces the directive with a fenced code block, after which
    dash-improve-my-llms' directive stripper no longer recognises a directive
    there — so any options left behind ship into every page's llms.txt as
    orphaned `    :defaultExpanded: false` noise. The two behaviours are
    independent and both have to survive.
    """
    import sys

    expand = sys.modules["pages.markdown"]._expand_source_directives

    out = expand(
        ".. source::requirements.txt\n    :defaultExpanded: false\n\ntail text"
    )
    assert "# File: requirements.txt" in out, "directive not expanded"
    assert ":defaultExpanded:" not in out, "directive option leaked into the prose"
    assert "tail text" in out, "content after the directive was swallowed"


def test_noscript_block_carries_no_h1():
    """A static pin beside the sweep above, for the same defect.

    Crawlers run no JavaScript and PARSE noscript content, so an h1 there is a
    second site-wide h1 on every page. The sweep catches it, but only with a
    booted app; this catches it from the file alone, which is what a reader
    editing templates/index.html will trip first.

    Comments are stripped before the check, so the explanatory comment inside
    the block — which necessarily says "<h1>" — cannot trip its own guard. That
    is the marker-in-comment lesson applied to our own pin.
    """
    import re
    from pathlib import Path

    html = Path(__file__).resolve().parent.parent / "templates" / "index.html"
    text = re.sub(r"<!--.*?-->", "", html.read_text(), flags=re.S)
    block = re.search(r"<noscript>(.*?)</noscript>", text, re.S)
    assert block, "no <noscript> block in templates/index.html"
    assert "<h1" not in block.group(1), (
        "the noscript block declares an <h1> — crawlers parse noscript, so "
        "this becomes a second site-wide h1 on every page. Start the block's "
        "heading hierarchy at h2."
    )
