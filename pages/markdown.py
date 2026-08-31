"""Markdown-driven page loader — the single source of routing for this site.

Walks ``docs/**/*.md``, parses each file's YAML frontmatter, renders the body
with markdown2dash and registers the result as a Dash page. The `.. exec::`
directive inside a page imports the sibling ``example.py`` to embed the live
demo, so a new page is a directory with two files in it and no Python edits
anywhere else.

This is the dash-documentation-boilerplate loader. dash-emoji-mart's
documentation is entirely public today, so every page's `tier` frontmatter is
absent and resolves to public — but the tier is recorded per page
(lib/page_tiers.py) all the same, so the network's 402 experiment can tighten
a document via frontmatter or the hub's ceilings without touching this loader.
llms.txt prose goes straight to dash-improve-my-llms.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

import dash
import dash_mantine_components as dmc
import frontmatter
from dash_improve_my_llms import register_page_metadata
from markdown2dash import Admonition, BlockExec, Divider, Image, create_parser
from pydantic import BaseModel, field_validator

from lib import gate_layouts, markdown_inline, page_tiers, page_visibility
from lib.ad_client import inject_ad_into_aside
from lib.constants import (
    NAME_CONTENT_MAP,
    OG_IMAGE_URL,
    PAGE_TITLE_PREFIX,
    SITE_BRAND,
)
from lib import aside
from lib.directives.headings import patch_renderer
from lib.directives.kwargs import Kwargs
from lib.directives.llms_copy import LlmsCopy
from lib.directives.props import Props
from lib.directives.source import SC
from lib.directives.toc import TOC
from lib.versions import substitute_versions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

directory = "docs"

files = sorted(Path(directory).glob("**/*.md"))


class Meta(BaseModel):
    name: str
    description: str
    endpoint: str
    package: str = "dash-emoji-mart"
    category: Optional[str] = None
    icon: Optional[str] = None
    # Sidebar position within its category; ties break on name.
    order: int = 1000
    # Short sidebar label (template 1.6.41); default = name. Shortening
    # `name:` instead would churn <title>, og:title and the llms.txt
    # heading — this is the seam that changes only the sidebar and search.
    nav: Optional[str] = None
    # Who may read this page: public | auth | admin | hidden. Absent means
    # the deployment default (PAGE_DEFAULT_TIER, else public) — see
    # lib/page_tiers.py for the tier model and why the default is open.
    # Enforced only when access control is wired in run.py.
    tier: Optional[str] = None
    # The second axis: does the machine twin (/<page>/llms.txt, crawler HTML,
    # the prerender) stay open while the interactive page is gated? Absent
    # defers to LLMS_PUBLIC_DEFAULT (unset = open — the data-window posture,
    # which is how this site ships). Only meaningful on `auth` pages; see
    # lib/page_tiers.get_llms_public.
    llms_public: Optional[bool] = None
    # Sitemap <lastmod>, YYYY-MM-DD, emitted VERBATIM by dash-improve-my-llms
    # >= 2.6.0 and omitted entirely when absent. Truth or silence: set it when
    # the page's content genuinely changes, so the frontmatter edit rides the
    # same commit as the prose. Never script it from file mtimes — those reset
    # on every Docker build, which is precisely the invented daily "today"
    # 2.6.0 exists to end. The validator exists because YAML parses a bare
    # `lastmod: 2026-08-21` into datetime.date before pydantic ever sees it.
    lastmod: Optional[str] = None

    @field_validator("lastmod", mode="before")
    @classmethod
    def _lastmod_to_iso(cls, value):
        return value.isoformat() if hasattr(value, "isoformat") else value


# The directive line AND the indented `:option: value` lines that belong to it.
#
# Matching only the directive line leaves its options behind as loose text: the
# expansion replaces `.. source::path` with a fenced code block, after which
# dash-improve-my-llms' directive stripper no longer sees a directive block
# there — just orphaned `    :defaultExpanded: false` lines, which it has no
# reason to touch. They then ship inside every page's llms.txt as noise.
_SOURCE_DIRECTIVE = re.compile(
    r"^\.\. source::(?P<path>.+?)$(?:\n[ \t]+:[^\n]*)*",
    re.MULTILINE,
)
_LANG_MAP = {
    "py": "python", "pyi": "python",
    "js": "javascript", "jsx": "jsx",
    "ts": "typescript", "tsx": "tsx",
    "css": "css", "scss": "scss", "sass": "sass", "less": "less",
    "html": "html", "htm": "html", "xml": "xml",
    "json": "json",
    "yaml": "yaml", "yml": "yaml",
    "md": "markdown", "rst": "rst", "txt": "text",
    "sh": "bash", "bash": "bash",
    "sql": "sql", "r": "r",
    "toml": "toml", "ini": "ini", "conf": "conf",
}


_DIRECTIVE_OPTION = re.compile(r"^[ \t]+:[^\n]*$")


def _expand_source_directives(markdown_content: str) -> str:
    """Inline `.. source::path` directives with the referenced file's content.

    This produces the prose dash-improve-my-llms serves at `/<page>/llms.txt`.
    Substituting the real file is what makes that output self-contained for the
    "paste the page into a chat window" audience — a bare directive name would
    be useless there.

    FENCE-AWARE, and it has to be. A `.. source::` inside a fenced code block
    is documentation SHOWING the syntax, not a directive to run. Expanding it
    injects a ```python fence inside the already-open fence, which closes that
    fence early — and from there the inlined Python file is parsed as markdown,
    so every `# comment` line becomes an <h1> and the page's machine lane
    serves broken structure. The browser lane never showed it, because
    markdown2dash parses fences properly; only /llms.txt and the prerender
    were wrong. tests/test_pages.py's single-h1 pin is what catches a
    regression here.

    This site's docs do not currently teach the directive inside a fence, so
    today the guard is inert — it is ported because the failure is silent, and
    a tutorial page is exactly the kind of thing a docs site adds later.

    Line-walked rather than regex-substituted, because this repo's directive
    match spans the directive line PLUS its indented `:option:` lines (see
    _SOURCE_DIRECTIVE — leaving those behind ships them into llms.txt as
    orphaned noise). Both behaviours have to survive together.
    """

    def expand(file_path: str) -> str:
        try:
            full = Path(file_path)
            content = full.read_text()
            lang = _LANG_MAP.get(full.suffix.lstrip(".").lower(), "text")
            tail = "" if content.endswith("\n") else "\n"
            return f"\n```{lang}\n# File: {file_path}\n\n{content}{tail}```\n"
        except FileNotFoundError:
            return f"\n<!-- Error: File not found: {file_path} -->\n"
        except Exception as exc:  # noqa: BLE001 - never break page registration
            return f"\n<!-- Error reading {file_path}: {exc} -->\n"

    def exec_target_file(module_path: str) -> str:
        """`docs.iconify.example` -> `docs/iconify/example.py`."""
        return module_path.strip().split("\n")[0].strip().replace(".", "/") + ".py"

    lines = markdown_content.split("\n")

    # THE EXEC LANE (template 1.6.43, owner's decision 0aa). `.. exec::`
    # renders a component into the React tree; the machine lane is built from
    # this markdown, where the directive line is stripped — so a page could
    # describe a demo whose code appears nowhere in the document an agent
    # reads. Expanding the module's SOURCE is what an agent can actually use:
    # a component cannot be serialised into markdown, and a screenshot is
    # worse than nothing to a reader who cannot render it.
    #
    # DEDUPE, on the PAIRING axis: skipped where the page already carries a
    # `.. source::` for the SAME target — the hand-authored road seven of
    # this fork's eight exec-using pages already take — and NOT skipped for a
    # `.. source::` naming a different file. Measured before porting: 8
    # unfenced `.. exec::`, 7 already paired, one unpaired
    # (docs/api-reference/example.py), which is the only page this changes.
    paired = set()
    _fence = None
    for probe in lines:
        _head = probe.lstrip()[:3]
        if _fence is None and _head in ("```", "~~~"):
            _fence = _head
        elif _fence is not None and _head == _fence:
            _fence = None
        elif _fence is None and probe.startswith(".. source::"):
            paired.add(probe[len(".. source::"):].strip().split()[0]
                       if probe[len(".. source::"):].strip() else "")

    out: List[str] = []
    fence = None  # the marker that opened the block we are inside, if any
    i = 0
    while i < len(lines):
        line = lines[i]
        head = line.lstrip()[:3]

        if fence is None and head in ("```", "~~~"):
            fence = head
        elif fence is not None and head == fence:
            fence = None
        elif fence is None and line.startswith(".. exec::"):
            module_path = line[len(".. exec::"):].strip()
            target = exec_target_file(module_path)
            i += 1
            while i < len(lines) and _DIRECTIVE_OPTION.match(lines[i]):
                i += 1
            # The directive line itself is dropped either way — it is noise in
            # the machine lane. Only the expansion is conditional.
            if target not in paired:
                out.append(expand(target))
            continue
        elif fence is None and line.startswith(".. source::"):
            path_text = line[len(".. source::"):].strip()
            i += 1
            # Consume the directive's own indented options so they do not
            # survive as loose text once the directive itself is gone.
            while i < len(lines) and _DIRECTIVE_OPTION.match(lines[i]):
                i += 1
            out.append(expand(path_text))
            continue

        out.append(line)
        i += 1

    return "\n".join(out)


def _build_llms_doc(name: str, description: str, expanded: str, path: str) -> str:
    """Wrap expanded markdown in the preamble `/<page>/llms.txt` readers expect.

    The root page is deliberately NOT wrapped, because the two consumers of this
    string treat it differently:

      * ``/<page>/llms.txt`` returns the doc verbatim, so it needs its own H1 and
        tagline or the page arrives untitled.
      * ``/llms.txt`` (the index) has already emitted ``# <name>`` and
        ``> <description>`` from the page metadata before splicing this in. It
        strips a leading H1 to avoid two top-level headings — but it does NOT
        strip a leading blockquote, so a preamble here surfaces as the SAME
        tagline printed twice at the top of the site index.

    dash-email's index reads cleanly because it has no ``docs/home/`` at all and
    hand-writes its root prose; flexlayout-dash, which uses this same loader with
    a home page, shows the doubled tagline. Skipping the preamble for ``/`` gets
    the clean result without giving up a markdown-driven home page.
    """
    if path == "/":
        return expanded.rstrip() + "\n"

    parts: List[str] = [f"# {name}\n"]
    if description:
        parts.append(f"> {description}\n")
    parts.append("---\n")
    parts.append(expanded.rstrip() + "\n")
    parts.append("\n---\n")
    parts.append(f"*Source: {path}*\n")
    return "\n".join(parts)


# `**bold**` and `*italic*` render as dmc.Text, same as a paragraph, so without
# this every emphasised run puts a <p> inside a <p>. Must precede create_parser,
# which instantiates the renderer.
markdown_inline.apply()

# Headings containing inline code or emphasis crash markdown2dash's renderer
# and, when they don't, get an id their own TOC anchor does not match; and
# inline `![alt](src)` has no renderer at all, so mistune's HTML fallback runs
# and raises on the DMC child list. Both are fixed here. Disjoint from
# markdown_inline above (heading/image vs emphasis/strong/strikethrough), so
# the two patches compose; both must precede create_parser.
patch_renderer()

# Kwargs() stays for DMC components (numpy docstrings); Props() handles
# dash-generate-components output, which Kwargs silently renders as an empty
# table. See lib/directives/props.py.
directives = [
    Admonition(), BlockExec(), Divider(), Image(), Kwargs(), LlmsCopy(), Props(),
    SC(), TOC(),
]
parse = create_parser(directives)

for file in files:
    logger.info("Loading %s..", file)
    metadata, content = frontmatter.parse(file.read_text())
    metadata = Meta(**metadata)

    # Substitute derived facts BEFORE any consumer sees the text, so the
    # browser page, the copy button, and /<page>/llms.txt all publish the
    # same truth. A doc writes {{VERSION:<distribution>}} instead of a
    # version number — any installed package, so this site documents
    # dash-emoji-mart the same way. See lib/versions.py for why.
    content = substitute_versions(content, source=str(file))

    # The "copy for LLMs" button reads the raw markdown back out of here.
    NAME_CONTENT_MAP[metadata.name] = content

    # Pages with a `.. toc::` fill the right-hand aside; the shell collapses
    # that column for every other page (lib/aside.py) — otherwise /changelog
    # and /api render inside the docs column with an empty right gutter.
    if ".. toc::" in content:
        aside.register(metadata.endpoint)

    layout = parse(content)

    # The root page states the BRAND as its heading, not its nav label.
    #
    # Every other page heads itself with its frontmatter `name`, which is also
    # its sidebar label — correct, because "Configuration" is what that page is.
    # The home page's label is "Home", which names nothing: it would leave the
    # single most-linked URL on the site as the only page that never says what
    # the site is. STANDARD §1 counts the home page's own H1 as one of the
    # surfaces the brand has to reach, alongside `Dash(title=)` and the
    # `register_page_metadata(path="/")` name that feeds /llms.txt.
    #
    # Only the heading changes. The nav keeps "Home", and so does the <title>
    # ("dash-emoji-mart | Home"), which already carries the brand via the prefix.
    heading = SITE_BRAND if metadata.endpoint == "/" else metadata.name

    layout = [
        dmc.Title(heading, order=2, className="m2d-heading"),
        dmc.Text(metadata.description, className="m2d-paragraph"),
    ] + layout

    # 2plot.dev ad network: the slot joins the Stack inside the `.. toc::`
    # aside so it scrolls with the table of contents. Pages without a TOC get
    # no ad, and the call is fail-silent — an ad must never break registration.
    inject_ad_into_aside(layout, metadata.endpoint)

    # `image_url` and `description` are BOTH required on every page, not just
    # the ones somebody expects to be shared. Dash emits og:image and
    # twitter:image for each registered page and writes content="" when it has
    # neither an explicit URL nor an inferable asset (dash/_pages.py
    # `_page_meta_tags`) — and those tags land LATE in the document, so a single
    # page missing `image_url=` beats the good static tags in the head and
    # unfurls as a blank card. That is the exact failure the hub carried for
    # weeks. See lib/constants.py's social-card block.
    dash.register_page(
        metadata.name,
        metadata.endpoint,
        name=metadata.name,
        title=PAGE_TITLE_PREFIX + metadata.name,
        description=metadata.description,
        image_url=OG_IMAGE_URL,
        # The tree above is still built once, here. gated_layout only decides
        # PER RENDER whether the visitor receives it or the sign-in/forbidden/
        # 404 card (lib/gate_layouts.py). With every tier public — how this
        # site ships — the verdict is a dict lookup that always says allow, so
        # an ungated deploy pays essentially nothing for the capability.
        layout=gate_layouts.gated_layout(
            metadata.endpoint, metadata.name, layout
        ),
        category=metadata.category,
        icon=metadata.icon,
        order=metadata.order,
        nav=metadata.nav,
    )

    # Record the declared tiers before the prose is registered, so a gate can
    # never be applied later than the content it is meant to gate.
    #
    # ONE declared value, TWO ledgers. The control board's row first —
    # overrides written there win at resolution time (lib.access.local_tier),
    # which is what makes a board toggle apply live rather than at the next
    # deploy. Then the network ledger: what the hub's tier ceiling compares
    # against, and what lib.access enforces underneath any override.
    page_visibility.register_default(metadata.endpoint, metadata.name,
                                     visibility=metadata.tier,
                                     llms_public=metadata.llms_public)
    page_tiers.register(metadata.endpoint, metadata.tier,
                        llms_public=metadata.llms_public)

    # Feed the directive-expanded markdown to dash-improve-my-llms so
    # /<page>/llms.txt serves real prose with the example source inlined.
    expanded = _expand_source_directives(content)
    # NO `og_image=` here, and the reason is worth the paragraph because the
    # obvious improvement is a trap.
    #
    # dash-improve-my-llms 2.3.4 DOES support it: `register_page_metadata`
    # documents `og_image` as a pass-through kwarg and `prerender.
    # build_head_tags` emits `<meta property="og:image">` from it. Passing it
    # measurably works — the prerender's tag appears, marked
    # `data-dimll-prerender="1"`, carrying the right URL.
    #
    # It also produces TWO og:image tags on every page, because Dash already
    # emitted one from `register_page(image_url=)` above. `scripts/
    # smoke_live.py` counts them in the raw document and requires exactly one:
    #
    #     check("og:image is declared exactly once", len(card_urls) == 1, ...)
    #
    # so passing it fails the post-deploy gate on every page. That rule is not
    # pedantry — duplicate og:image is precisely how the fleet shipped an SVG
    # card that beat a good one on tag order (LESSONS §1).
    #
    # So the crawler half of LESSONS §6 stays open here, and closing it needs a
    # coordinated upstream change rather than a per-site one: the prerender
    # should emit og:image only when the document does not already carry it.
    # Measured and written up on 2026-08-01; see the CHANGELOG entry.
    #
    # `name` stays the CLEAN page name on purpose. The prerender uses it for
    # both `<title>` and its own og:title, and it is also what the `## Pages`
    # index in /llms.txt lists — a document already headed by SITE_BRAND, where
    # prefixing every entry with "dash-emoji-mart | " would be pure noise.
    register_page_metadata(
        path=metadata.endpoint,
        name=metadata.name,
        description=metadata.description,
        # Emitted verbatim into <lastmod> by dash-improve-my-llms >= 2.6.0 —
        # the floor run.py enforces — and the tag is omitted entirely when
        # this is None. Truth or silence; tests/test_seo_icons.py pins that no
        # date reaches the sitemap that no page declared.
        lastmod=metadata.lastmod,
        llms_doc=_build_llms_doc(
            metadata.name, metadata.description, expanded, metadata.endpoint
        ),
    )
