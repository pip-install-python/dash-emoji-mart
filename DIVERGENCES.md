# Divergences from the template

Every DELIBERATE difference between this repo and
dash-documentation-boilerplate, with its reason. This file is the
boundary between design and drift:

- Template syncs read this file FIRST and must not "restore" anything
  recorded here.
- A difference not recorded here is treated as drift and will be
  synced away.
- Record the divergence in the SAME commit that creates it — one
  line: what differs, why, and what the template would otherwise do.
- An empty list is a statement too: it means this repo intends to
  match the template exactly.

Fleet precedents for what belongs here: flexlayout's own-source
`_build_llms_doc` dedup and app-key sourcing; flows' own
`_health_body` payload shape (ports the healthz CONTRACT, not the
template's file); clerkhook's minimal `{ok, app, build}` healthz and
its heartbeat-as-before_request (the single anonymous 200 on a locked
host); muischeduler's no-npm dependabot scope.

## This repo's divergences

### 1. `.. source::` expansion is line-walked, and consumes the directive's options

`pages/markdown.py` — `_expand_source_directives`

The template matches the directive with a single-line regex
(`_SOURCE_DIRECTIVE`) and substitutes it. This repo's directives carry
indented `:option: value` lines beneath them, and the expansion has to
consume those too: once the directive is replaced by a fenced code
block, dash-improve-my-llms' directive stripper no longer recognises a
directive there, so anything left behind ships into every page's
llms.txt as orphaned `    :defaultExpanded: false` noise.

The template's 1.6.11 fence-awareness CONTRACT is fully present — the
loop tracks ``` and ~~~ at depth zero and leaves a `.. source::`
inside a fence alone. Only the shape differs (a line walker rather
than a regex substitution), because the two behaviours have to
survive together. Both are pinned: `tests/test_pages.py`
`test_source_expansion_is_fence_aware` and
`test_source_expansion_still_consumes_directive_options`.

**A sync must not restore the regex form.** Doing so re-opens the
options leak this repo already fixed.

### 2. The root page's llms doc carries no preamble

`pages/markdown.py` — `_build_llms_doc` returns `/` unwrapped

This is this repo's own answer to the same defect template 1.6.16
solved with `lib/page_visibility.published_name()`. Both exist to stop
the machine lane's home page carrying two disagreeing top-level
headings; they differ in which side gives way.

`/llms.txt` (the site index) has already emitted `# <name>` and
`> <description>` from the page metadata before splicing this doc in.
It strips a leading H1 — but NOT a leading blockquote — so a preamble
here surfaces as the same tagline printed twice at the top of the
index. Skipping the preamble for `/` gets a clean index while keeping
a markdown-driven home page. The template's fix (publish SITE_BRAND
as the root's name) addresses the H1 half only.

Pinned by `tests/test_pages.py`'s every-page sweep, which asserts
exactly one `<h1>` on `/` and exactly one `/llms.txt` link in its
footer. Verified on the wire: the live `/llms.txt` opens with
`# dash-emoji-mart — emoji picker for Dash` and one tagline.

**A sync must not add `published_name()` here** without first
deciding which of the two mechanisms wins; running both is untested.

### 3. The container's HEALTHCHECK probes with python, not curl

`Dockerfile`

The template's block is `CMD curl -fsS http://localhost:${PORT:-8550}/healthz`,
with `curl` apt-installed for it. This image apt-installs NOTHING —
it is a pure-Python docs site, the component's JS bundle is committed
rather than built, and there is no Node layer either — so adding an
apt layer for one probe binary costs a package index refresh and
~10MB on every build. python is already PID 1's interpreter.

The 1.6.14 sync spec names this alternative explicitly ("or a
python-urllib probe like clerkhook's"). The contract is identical:
`${PORT:-8050}`, never a hardcoded port, agreeing with the CMD.

### 4. This repo's port is 8050

`Dockerfile`, `render.yaml`

The template uses 8550 throughout. This repo has used 8050 since
before the fork and both encodings (the CMD bind and the HEALTHCHECK
probe) agree on it. The 1.6.14 contract is "shell-form CMD, defaulted
at the point of use, never hardcoded" — which this satisfies; only
the number differs.

### 5. The rescued aside gap is margin-only

`assets/main.css` — `aside.mantine-AppShell-aside { margin-top: 15px; }`

When the hashed `.m_9cdde9a` fossil was removed, the template's
rescue also carried `z-index: 10 !important`. This site ships the
INVERSE header variant (`header.mantine-AppShell-header { z-index:
150 !important; }`), and the handbook forbids merging the two
variants, so only the intentful 15px was rescued. The z-index half
would fight a rule this repo deliberately holds.

### 6. The FastAPI healthz lane lives in `lib/health.py`

There is no `lib/asgi_routes.py` in this repo. Template items that
name that file port their contract into `register_health_route()`'s
`backend == "fastapi"` branch instead, which builds its response from
the same `health_payload()` every other backend uses and hands
Starlette's own request headers to the geo resolver. Pinned by
`tests/test_health.py::test_fastapi_healthz_renders_from_the_shared_payload`.

Production runs Flask; the FastAPI lane is pinned rather than
deployed.

### 7. `.. props::` — a fork-original directive

`lib/directives/props.py`

The template has no equivalent. markdown2dash's `.. kwargs::` parses
NUMPY-style docstrings (what Dash Mantine Components emits) and
renders an EMPTY TABLE — silently, with every smoke check still
passing — for `dash-generate-components` output, which is what this
repo's own component produces. `.. kwargs::` is kept for DMC;
`.. props::` documents `DashEmojiMart`.

## Byte-owned paths

Paths this fork owns byte-for-byte. The F3b fan-out never overwrites
a path listed here; everything else in the spec's `sync-verbatim`
block is the template's to update mechanically. Prose above explains
divergences; this block is the machine answer.

Repo-relative paths, one per line, `#` comments, no `..`; exactly one
block. An EMPTY block means "the template owns every sync-verbatim
path here" — present so the absence is a statement. When the block
exists it is authoritative; a fork without it gets the conservative
mention heuristic (over-flags, never restores).

EMPTY here is an audited result, not a default. The sync-verbatim
paths across all three live specs are the three `.claude/skills/*/
SKILL.md` files, `tests/test_claude_kit.py`, `.github/dependabot.yml`
and `tests/test_auth_demos.py`; every divergence above names a file
in none of those sets. The one that did — §8, on the kit test — was
upstreamed in 1.6.18 and is retired below, and that file's bytes now
match the template's exactly. Fork the template's bytes on any of
them and this block is where you say so, in the same commit.

```yaml byte-owned
```

## Retired

Retirements are marked here, never deleted, so an older report
describing a divergence as live can still be reconciled.

### 8. `tests/test_claude_kit.py` skips the sync-spec pin

The template's `test_sync_specs_are_specifiable` asserts that
`sync/README.md` and at least one `SYNC-*.md` exist and that every
item carries class/detect/acceptance. That is a pin on the AUTHOR of
sync specs. This repo consumes them; it publishes no releases and
authors no specs, so the pin is skipped when `sync/` is absent rather
than deleted — if this repo ever grows a `sync/` directory, the pin
activates on its own.

**Retired 2026-08-26** — upstreamed by the template at 1.6.18 and
carried into the bytes read at 1.6.27 (055363e): the template's own
`test_sync_specs_are_specifiable` now skips on a missing `sync/`,
crediting this fork's F2 correction by name. The behavior this entry
protected is now the template's, so the file is byte-verbatim again
and this is no longer a divergence. Nothing to defend on the next
sync.
