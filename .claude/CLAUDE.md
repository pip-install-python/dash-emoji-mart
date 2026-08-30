# dash-emoji-mart — documentation site

## Project Overview

Two things live in this repo, and knowing which one a change touches
is the first thing to get right:

- **`dash_emoji_mart/`** — the published Python package: an emoji
  picker for Plotly Dash 4, wrapping [emoji-mart] as a single Dash
  component. Its JS bundle (`dash_emoji_mart.min.js`) is COMMITTED,
  built from a separate source tree, not by this repo's CI. Nothing
  here compiles it; the Docker image ships it as-is.
- **everything else** — the documentation site at
  **https://emojimart.2plot.dev**, a fork of
  `dash-documentation-boilerplate` serving that component's docs and
  reporting to the 2plot network as app key `emojimart`.

Versions, dependencies and history are deliberately not restated
here — they go stale. Read `requirements.txt` for the stack and
`CHANGELOG.md` for what changed and when.

[emoji-mart]: https://github.com/missive/emoji-mart

---

## Custom Directives

| Directive | Syntax | Purpose |
|-----------|--------|---------|
| `toc` | `.. toc::` | Generate table of contents |
| `exec` | `.. exec::module.path` | Render Python component |
| `source` | `.. source::file/path.py` | Inline a file's source |
| `kwargs` | `.. kwargs::ComponentName` | Prop table from a NUMPY docstring (DMC) |
| `props` | `.. props::module.Component` | Prop table from a `dash-generate-components` docstring |
| `llms_copy` | `.. llms_copy::Name` | The "copy this page for an LLM" control |

**`props` is not `kwargs`, and the difference is silent.**
markdown2dash's `.. kwargs::` only parses NUMPY-style docstrings
("Parameters\n----------"), which is what Dash Mantine Components
emits. `dash-generate-components` output — i.e. `DashEmojiMart`
itself — uses a different shape, so `.. kwargs::` finds no marker,
falls into its empty branch, and renders an EMPTY TABLE. The page
still builds and every smoke check still passes. That is why
`lib/directives/props.py` exists; point it at this repo's own
component and `.. kwargs::` at DMC's.

`.. source::` directives here carry indented `:option:` lines, and
the expansion in `pages/markdown.py` consumes them — see
DIVERGENCES.md, and do not "restore" the template's regex form.

---

## Configuration

### Customization Points

| File | Purpose |
|------|---------|
| `run.py` | The fork point (`SATELLITE_APP_KEY` default), the dimll boot floor, gate + SEO wiring |
| `lib/constants.py` | `SITE_BRAND`, `BASE_URL`, colors, titles — the identity every other module reads |
| `assets/main.css` | Custom CSS. Hashed Mantine `.m_*` selectors are EXTINCT here and pinned so by `tests/test_css_hygiene.py` |
| `templates/index.html` | HTML template (analytics, meta tags, SEO). Its `<noscript>` block is crawler-visible: headings start at `<h2>` |
| `components/appshell.py` | Theme configuration, MantineProvider settings |
| `components/navbar.py` | Navigation ordering, and the full-height mobile drawer |
| `components/header.py` | Header, Clerk avatar, the wordmark (`visibleFrom="sm"`) |
| `pages/control_board.py` | `/admin/control-board` — live per-page tier + llms.txt toggles (owner/admin-gated, fails closed) |
| `lib/page_visibility.py` | The board's override store (persists to `PAGE_VISIBILITY_FILE`; overrides beat frontmatter in `lib/access.py`) |
| `lib/auth_demos.py` | Live-demo teasers rendered inside the sign-in gate cards |

---

## Development Notes

### Adding New Documentation Pages
1. Create a folder in `docs/` (e.g. `docs/my-page/`)
2. Create a markdown file with frontmatter:
```markdown
---
name: My Page
description: Description of my page
endpoint: /my-page
icon: mdi:code-tags
---

.. toc::

## Overview
...
```
3. Add Python examples as needed
4. Reference with `.. exec::docs.my-page.example`
5. The page auto-registers and appears in navigation

Every new page is swept by `tests/test_pages.py`: it must serve
exactly one `<h1>` to a generic client, and its machine lane is a
different document from its browser lane.

### The component's JS bundle
`dash_emoji_mart/dash_emoji_mart.min.js` is committed and CI checks
it rebuilds reproducibly. There is no webpack step in the image and
`node_modules/` is excluded via `.dockerignore` — if you find
yourself adding a Node layer to the Dockerfile, stop and ask why.

---

## Resources

- [Dash Documentation](https://dash.plotly.com/)
- [Dash Mantine Components](https://www.dash-mantine-components.com/)
- [Mantine](https://mantine.dev/)
- [dash-improve-my-llms](https://pypi.org/project/dash-improve-my-llms/)
- [This package on PyPI](https://pypi.org/project/dash-emoji-mart/)
- [emoji-mart](https://github.com/missive/emoji-mart)
- [Template: dash-documentation-boilerplate](https://github.com/pip-install-python/Dash-Documentation-Boilerplate)

---

## Network role & the behavioral contract

This repo is a member of the 2plot network — either the template
itself (dash-documentation-boilerplate) or a fork of it serving one
component's documentation. **Identity derives from the repo, never
from this file**: the app key comes from `SATELLITE_APP_KEY` and
run.py's fork point, the host from `lib/constants.py`'s `BASE_URL`,
the deliberate differences from the template from `DIVERGENCES.md`
at the repo root. If those disagree with anything written here,
they win.

### The contract — every session, every prompt

1. **Check the prompt against this tree before executing.** Prompts
   are written from the template's perspective and your fork may
   legitimately differ — floors, backends, payload shapes, page
   sets. A prompt step that doesn't fit this repo is a finding to
   return, not an instruction to force.
2. **Corrections are your job, not scope creep.** If a prompt's
   reference list doesn't match its steps, if its assumed state is
   wrong, or if executing it as written would produce a
   green-but-vacuous result, say so and propose the corrected
   version before running it.
3. **Verify your own deploy on the wire before reporting.** A push
   is not a result. Run `/wire-verify` (or its manual equivalent)
   against production and paste what came back. If your sandbox
   cannot reach your own domain, say exactly that — an unverified
   claim marked as unverified is honest; the same claim unmarked is
   not.
4. **Report observed versus expected, with evidence.** Paste the
   JSON, the status code, the test count. "Should work" and summary
   claims without artifacts are not reports.
5. **Divergence is legitimate when written down.** Before syncing
   template changes, read `DIVERGENCES.md`; never let a sync
   "restore" a recorded deliberate difference. When you deliberately
   diverge, record it there in the same commit — an unrecorded
   divergence is indistinguishable from drift and will be treated
   as drift.
6. **Never touch**: environment variable VALUES, hosting dashboards,
   secrets, other repos' trees, or anything the prompt didn't put in
   scope. Enumerate what you cannot do (closing PRs, dashboard
   steps) for the owner instead of claiming it done.

### Verification traps (fleet-learned, keep them)

- A `>=` floor can never pull a new release through a Docker cache
  hit — the requirements line changing IS the cache bust, and floors
  live in several encodings (requirements, run.py's boot floor,
  tests, CI): grep the number, move every one.
- `/healthz` build == HEAD is the deploy proof; a missing geo block
  on dimll ≥2.7 means the cache trap fired (unless DIVERGENCES.md
  says this host's healthz is deliberately minimal).
- Probe with GET, not HEAD — HEAD responses omit the Link headers.
- Run-watchers keyed on a commit sha can match Dependabot's runs on
  the same sha — key on the workflow path (cd.yml) instead.
- The browser lane and the machine lane are different documents;
  a fix proven on one is unproven on the other.
- There is ONE classifier: `dash_improve_my_llms.classify()`. Never
  add a User-Agent list to this app — the tracker had one for a year
  (`lib/analytics_tracker.py`, until 1.6.34), it filed ClaudeBot as
  *search* (it is Anthropic's training crawler; the package's registry
  and this repo's own `run.py` comment both said so six lines from
  where the list ignored them), it still named the retired
  `anthropic-ai` / `claude-web` tokens, and it counted every UA-less or
  library client as a human. Every host in the fleet reported those
  numbers. A token the registry lacks is a pushback to the package
  seat, not a list here; `tests/test_analytics_classifier.py` greps the
  module for the old tokens and goes red if one comes back.
- `build == HEAD` on `/healthz` means HEAD of **`release`**, not main
  (1.6.35). Render deploys `release`; only cd.yml's `deploy` job writes
  it, fast-forward, after the CI matrix is green. `main` ahead of
  `release` is an uncertified push pending — its CD run is red or still
  running — never "drift" and never a reason to deploy by hand or to
  write `release` yourself (a non-fast-forward push fails the next run
  on purpose). Compare the wire against `git rev-parse origin/release`;
  the one measurement behind this: 2026-08-29 14:12Z, de0bcff pushed
  to main, built by Render inside the minute, red in CD at 14:13Z,
  served for ~6 minutes. A host whose DIVERGENCES.md posture fence has
  no `deploy:` key still watches main — there the trap is the old one.
