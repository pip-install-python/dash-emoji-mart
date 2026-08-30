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

## Declared posture

What this host actually serves, homed in the repo that serves it
rather than in a table on the hub that ages out of sight. Nothing
validates the numbers but a probe — re-measure when you change what
this host serves. `tests/test_claude_kit.py` validates the SHAPE only.

    ai_bots   the status an AI-crawler UA receives per path, measured
              with a real vendor UA (ClaudeBot here — NOT a UA-less
              curl, which is classified separately). The asymmetry IS
              the posture: the browser document is refused while the
              agent surfaces stay open, and it is invisible from a
              browser.
    healthz   `full` — the fleet payload (app, backend, build,
              dash_version, geo, ok, python). Not `minimal`; this host
              has no lockdown divergence.
    runtime   `docker` — render.yaml's service runtime, which is why
              PYTHON_VERSION is deliberately ABSENT there (sync item 5).
    deploy    `release-branch` — Render deploys `release`, which only
              CD writes after a green matrix (template 1.6.35, sync
              item 13). `build` on /healthz is HEAD of `release`, and
              `main` ahead of it is an uncertified push PENDING — never
              drift, never a reason to deploy by hand. ABSENT would
              read as `main`.

Measured on emojimart.2plot.dev, 2026-08-30T14:18Z, build 53bc5e8 —
the ai_bots row with a real vendor UA (ClaudeBot AND GPTBot, both
identical: 403 / 200 / 403), the healthz row from the live payload,
the runtime and deploy rows from render.yaml in this commit.

**This ai_bots row is INTERIM and will be wrong the moment this work
deploys.** The training wall is retired in `run.py`
(`block_ai_training=False`, the posture flip) but that commit is not
on the wire yet: in-process, after the flip, both UAs get 200 on all
three paths and robots.txt carries no `Disallow` at all. Re-measure
the six lines and re-date this block on the first promote — and if
`/` still 403s on the wire while in-process answers 200, that
difference is something in FRONT of the app, not the app: name it and
hand it to the owner rather than editing `run.py` again.

```yaml posture
ai_bots: {"/": 403, "/llms.txt": 200, "/healthz": 403}
healthz: full
runtime: docker
deploy: release-branch
```

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

### 9. The docs-site CI window keeps its FLOOR leg, not two adjacent minors

`.github/workflows/ci.yml`, `tests/test_python_version.py`

SYNC-1.6.22-1.6.29 item 5 wants the `smoke` matrix three wide around
the fleet Python: the main leg at X.Y and two includes at X.Y-1 and
X.Y-2. Around 3.14 that is 3.14 / 3.13 / 3.12.

This repo runs 3.14 / 3.13 / **3.10**. The low leg is the docs
site's declared FLOOR, not an adjacent minor: `python-frontmatter`
1.3 imports `typing.TypeGuard`, so the site genuinely requires 3.10+,
and ci.yml's header has said so since before this item existed. Under
the template's rule that boundary would drop out of CI entirely the
moment the fleet moved past 3.12 — a floor nothing tests is a floor
nobody can trust, and the next dependency that quietly needs 3.11
would be found by a user rather than a run.

The rest of item 5 is adopted unchanged, including the parts that
make this leg safe to keep: one Python per fork everywhere it is
DECLARED, sourced from the Dockerfile's FROM tag, with the site lane
(`smoke`, `container`, `audit`, and cd.yml's `verify`) held to it and
the package lane — the wheel's own 3.9–3.13 `requires-python` window
— explicitly held apart. `tests/test_python_version.py` pins the leg
to the floor by name, so this stays a stated divergence rather than a
leg nobody re-examined.

Not a byte-owned path: `ci.yml` is not in any spec's `sync-verbatim`
block, so the fence below is unaffected.

### 10. Resources declares TWO upstreams, not one

`lib/constants.py` — `UPSTREAM`, `UPSTREAM_SECONDARY`, `resources()`

SYNC-1.6.22-1.6.38 item 16 contract (5) gives a fork ONE `UPSTREAM =
{"name", "url"}` and renders it as the last Resources link. This
component has two genuine upstreams: **emoji-mart**, which it wraps,
and **Iconify**, whose sets `dash_emoji_mart.iconify` and the whole
`/iconify` page are built on. A reader looking at an Iconify icon name
has nowhere else to go for what the names mean.

Both are third-party, which is the actual rule the section enforces,
and the drop that ported item 16 here allowed a declared second
upstream explicitly. `resources()` iterates the two rather than naming
one, so a fork with a single upstream gets the template's behaviour by
leaving `UPSTREAM_SECONDARY = None`.

**A sync must not collapse these back to one** without deciding which
of the two upstreams this site stops citing.

### 11. `SAME_AS` keeps its PyPI vertex

`lib/constants.py`

Item 16 wants `SAME_AS = [GITHUB_URL]` so the repo URL is written once.
The single-source half is adopted — the GitHub entry IS `GITHUB_URL`,
not a second copy of the string — but the list keeps
`https://pypi.org/project/dash-emoji-mart/` beside it. This fork
documents a PUBLISHED package: docs ↔ repo ↔ PyPI pointing at each
other is the strongest statement of which origin is the package's
canonical docs home, and the template has no package to make that
statement about.

### 12. Two nav-contract test assertions are inverted here, and one is corrected

`tests/test_nav_contract.py`

Copied from the template at 1.6.39, with three adaptations recorded
because two of them are FORK STATE and one is a defect in the
template's own copy:

- `test_resources_are_third_party_only` upstream bans the substring
  `"github.com"` in a Resources URL. That passes only where `UPSTREAM`
  is None, as it is on the template. Every component fork in the fleet
  wraps a project hosted on GitHub — emoji-mart here; Leaflet, React
  Flow, FlexLayout, Excalidraw, model-viewer and Pannellum elsewhere —
  so the ban forbids the single link item 16 exists to add. This copy
  bans the OWNER's links by value (repo, profile, Discord, YouTube,
  `pip-install-python`, `2plot`) plus the two named removals, which is
  what the requirement actually says. **Filed upstream as a spec
  correction, not a local workaround.**
- `test_api_page_is_not_registered_when_no_package_is_declared` asserts
  `API_PACKAGES == []` ("the template documents no component package").
  This fork documents `dash_emoji_mart`, so the same contract line is
  tested from its other side —
  `test_the_api_page_is_registered_for_this_fork` — asserting `/api` is
  registered and carries `DashEmojiMart`'s props.
- the aside and sitemap positive controls name the template's
  endpoints (`/backend-comparison`, `/getting-started`); this copy
  names `/configuration` and `/custom-emojis`.

### 13. The wide-content CSS carries a `.m2d-block-props` selector

`assets/main.css`

Template 1.6.39 widened `table.m2d-table` to `table.m2d-block-kwargs`
after measuring that `.. kwargs::` tables were never matched by the
original rule. Measured the same way here, this repo's own `..
props::` directive (§7) stamps `m2d-block-props` on the wrapping Box —
not on the table — so it needs a selector of its own, which has no
counterpart upstream because the directive has none. The comment above
the rule previously CLAIMED it covered both; it never did.

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

Re-audited 2026-08-26 at template 1.6.29 (5589318), after the F3b
fan-out landed the 1.6.22-1.6.28 block here (PR #6, e0687b5). The set
above is unchanged: `scripts/smoke_live.py` joined the block at 1.6.28
and was pulled back out at 1.6.29 after exactly one live round, so it
never becomes a fence question — and this fork does not own it anyway.
Its bytes here are the template's at 5589318, verified by digest. The
new §9 names `.github/workflows/ci.yml`, which no spec byte-copies.
Still empty, still by audit.

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
