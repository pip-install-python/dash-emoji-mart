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

              STANDING: **clicked**, not merely declared — the owner set
              the service's Branch field to `release` on 2026-08-30,
              after this round's first green promote. Until then
              `render.yaml`'s `branch:` line was documentation and the
              dashboard was the switch.

              STILL UNPROVEN, and say so rather than rounding up: the
              wire cannot yet show WHICH branch it follows. Every green
              push leaves `main` and `release` holding the same sha, so
              autoDeploy-from-main and autoDeploy-from-release produce
              an identical /healthz. The discriminating observation is
              the next push to `main` that goes RED — `release` must not
              move and the wire must not change. Record it here when it
              happens; that is the read that closes this row.

Measured on emojimart.2plot.dev, **2026-08-30T21:22Z, build 252967e**
— the ai_bots row with real vendor UAs (ClaudeBot AND GPTBot, both
identical: 200 / 200 / 200), the healthz row from the live payload,
the runtime and deploy rows from render.yaml in this commit.

This row was 403 / 200 / 403 until this deploy, and the change is the
posture flip landing, not drift. Two things worth keeping from the
measurement:

- **There is no edge wall on this host.** In-process after the flip and
  on the wire after the deploy agree exactly — 200/200/200 both times,
  and `robots.txt` serves zero `Disallow` lines. Every 403 this host
  ever returned to a training crawler was the package's own middleware.
  Nothing sits in front of the app changing these answers.
- **Re-measure and re-date this block on any deploy that touches
  `RobotsConfig`.** A stale `ai_bots` row is indistinguishable from a
  measured one, and the hub reads it.

```yaml posture
ai_bots: {"/": 200, "/llms.txt": 200, "/healthz": 200}
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

### 14. There is a THIRD live tool: `scripts/verify_network.py`

The template ships two (`scripts/network_smoke.py`,
`scripts/smoke_live.py`). This repo has a third, fork-original and
predating these records: an IN-PROCESS verifier that drives
`run.app.server.test_client()` rather than a URL, so it can assert
things the wire cannot show — directive leakage in every page's
`llms.txt`, the canonical shim collision, the peer directory stripping
this app from its own peer list.

Recorded now because it is load-bearing for the same contracts the
other two carry, and each round has found it holding a stale copy of
one:

- the crawler-posture fingerprint (item 15) — it had its own
  `ClaudeBot -> Disallow` assert, in neither tool the item named;
- the browser-lane default UA (item 17) — it sent NO User-Agent at
  all, which is the crawler lane at dimll ≥ 2.8.

**A sync must not delete it, and must not assume two tools where the
files list says two.** When a spec moves a lane, a fingerprint or a
floor in the live tools, it moves in three places here.

Its one real hazard is recorded with it: it is wired into neither CI
nor CD, so nothing but a person running it ever reports its result.
Both defects above were RED on `main` for an unknown period before
this round found them by hand. Pinning what can be pinned offline is
the mitigation — `tests/test_network_lanes.py` holds its UA lane, and
its assertions now count from the page registry rather than from
literals that go stale silently.

### 15. `/api` reads the component's DOCSTRING, because this repo has no shipped `metadata.json`

`lib/api_reference.py` — `_from_docstrings`, and the fallback in
`load_package`

SYNC-1.6.22-1.6.38 item 16 contract (7) generates the `/api` page from
the component package's `metadata.json`. **This repo excludes that file
in three places on purpose** — `.gitignore`, `MANIFEST.in` and
`pyproject.toml`, each stating that nothing loads it at runtime — so it
exists only in a working tree that has run `dash-generate-components`
and is absent from every clean checkout, both CI runners, and the
Docker image that serves production.

The template's loader returns `[]` there, silently. That is the same
empty-table failure §7 already records for `.. kwargs::`: the page
builds, every smoke check passes, and the table is empty. It reached CD
before anything caught it — run 33335469726, `deploy` correctly
skipped.

So the docstring is the fallback and, on this host, the only source
that ever runs. It is parsed by `lib/directives/props.py`'s
`_parse_dash_docstring` — the parser this fork already wrote for this
exact docstring shape — rather than a second implementation that could
drift from the first. Measured: 34 props via `metadata.json`, 33 via
the docstring. The difference is `style`, which the component's own
docstring never declares (it appears only inside another prop's prose)
— a property of the docstring, not of the parser, and pinned as such.

The three exclusions were NOT reversed to make the page work. They are
a deliberate, documented decision of this repo, and "nothing loads it
at runtime" stopped being true the moment `/api` existed — but the
right answer to that is a loader that reads what this host actually
ships, not a fourth place to keep a build artifact in sync.

**Consequence for the byte-identity audit:** `lib/api_reference.py` was
reported byte-identical to the template at `519d496` in the item 16
report. It is no longer, and it should not be — a byte copy renders an
empty page here. Nine files remained byte-identical at that sha, not
ten; re-measured at `4ac02e0` the count is eleven (see item 18).

### 15a. What item 18 changed here — the contract adopted, the bytes still declined

Template 1.6.41 answered this defect on the template's own side, and
its answer is BETTER than the one recorded above: a COMMITTED EXTRACT,
`<package>/api_metadata.json`, written by `scripts/build_api_metadata.py`
from the react-docgen artifact. It is a DIFFERENT file from
`metadata.json`, so it sidesteps this repo's three exclusions instead
of arguing with them, and it carries a `generated` date that is /api's
sitemap lastmod.

**Adopted in full.** `load_package` is now a three-rung ladder —
`metadata.json` (a rebuilt tree) → the committed extract → the
docstrings — plus `slim_generated_on`, `_cell` pipe-escaping, and a
named `_from_metadata` seam so `scripts/build_api_metadata.py` is
byte-identical cargo here. Two things this bought, measured:

- **/api serves 34 props on a clean checkout, not 33.** `style` is
  declared in `metadata.json` and never in the component's docstring,
  so the docstring rung alone could not reach it. The gap reported at
  item 17 is closed rather than merely explained.
- **/api carries a lastmod** (`2026-08-30`), which the docstring rung
  cannot honestly produce.

**The bytes are still declined**, and the reason is narrower than it
was: template 1.6.41's `lib/api_reference.py` carries its OWN
`_from_docstrings`. Adopting the file would put a second docstring
parser in this tree beside `lib/directives/props._parse_dash_docstring`,
which exists for this same component's docstring shape and drives
`.. props::` on /api-reference. Two parsers for one format drift, and
the one that drifts is the one nobody is looking at. Recorded in the
`byte-owned` fence below with item 14's `# declined:` grammar.

The docstring rung is now genuinely a last resort here rather than the
only road — which is the right place for it, and is why this decline is
about one function and not about the item.

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

NO LONGER EMPTY, as of item 18. One declined entry — the grammar is
item 14's: `- <path>  # declined: <reason>`, and the reason is
mandatory.

```yaml byte-owned
- lib/api_reference.py  # declined: template 1.6.41's copy carries its own _from_docstrings; this tree already has that parser in lib/directives/props.py for the same component's docstring shape, and two parsers for one format drift. DIVERGENCES §15. The CONTRACT is adopted in full — the metadata.json -> committed extract -> docstring ladder, slim_generated_on, _cell escaping and the named _from_metadata seam the generator imports — so scripts/build_api_metadata.py is byte-identical cargo here. Only the bytes are refused.
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
