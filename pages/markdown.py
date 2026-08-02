"""Markdown-driven page loader — the single source of routing for this site.

Walks ``docs/**/*.md``, parses each file's YAML frontmatter, renders the body
with markdown2dash and registers the result as a Dash page. The `.. exec::`
directive inside a page imports the sibling ``example.py`` to embed the live
demo, so a new page is a directory with two files in it and no Python edits
anywhere else.

This is the dash-documentation-boilerplate loader with the visibility gate
removed: dash-emoji-mart's documentation is entirely public, so there is no
Clerk dependency, no per-page tier and no admin control board. Pages register
their layout directly and llms.txt prose goes straight to dash-improve-my-llms.
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
from pydantic import BaseModel

from lib import markdown_inline
from lib.ad_client import inject_ad_into_aside
from lib.constants import (
    NAME_CONTENT_MAP,
    OG_IMAGE_URL,
    PAGE_TITLE_PREFIX,
    SITE_BRAND,
)
from lib.directives.kwargs import Kwargs
from lib.directives.llms_copy import LlmsCopy
from lib.directives.props import Props
from lib.directives.source import SC
from lib.directives.toc import TOC

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


def _expand_source_directives(markdown_content: str) -> str:
    """Inline `.. source::path` directives with the referenced file's content.

    This produces the prose dash-improve-my-llms serves at `/<page>/llms.txt`.
    Substituting the real file is what makes that output self-contained for the
    "paste the page into a chat window" audience — a bare directive name would
    be useless there.
    """

    def replace(match: "re.Match") -> str:
        file_path = match.group("path").strip()
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

    return _SOURCE_DIRECTIVE.sub(replace, markdown_content)


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

    # The "copy for LLMs" button reads the raw markdown back out of here.
    NAME_CONTENT_MAP[metadata.name] = content

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
        layout=layout,
        category=metadata.category,
        icon=metadata.icon,
    )

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
        llms_doc=_build_llms_doc(
            metadata.name, metadata.description, expanded, metadata.endpoint
        ),
    )
