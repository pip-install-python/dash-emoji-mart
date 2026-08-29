# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — the docs site

Nothing here changes `pip install dash-emoji-mart`; this is the site.
Consumed template SYNC-1.6.22-1.6.35 items 12 and 13 (template `4c63992`).

### Changed

- **`human_hits` DROPS and `bot_hits` RISES from the day this deploys, and
  that is the number becoming true, not a regression.** `lib/analytics_tracker`
  carried its own User-Agent lists for a year. They filed ClaudeBot —
  Anthropic's *training* crawler — under "search"; they still named the
  retired `anthropic-ai` / `claude-web` tokens; and they counted every UA-less
  or library client (`httpx`, `Go-http-client`, `node-fetch`, an empty
  User-Agent) as a desktop human. Those clients now land on the crawler lane,
  where they always belonged. Expect a visible step in the hub's day-over-day
  view for this app on the adoption date; nothing before it was re-scored.
- **There is ONE classifier: `dash_improve_my_llms.classify()`.** `is_bot` and
  `detect_bot_type` keep their names and signatures for callers and delegate;
  the module ends with zero User-Agent strings, and
  `tests/test_analytics_classifier.py` greps it for the old tokens. A token the
  package's registry lacks is a pushback to the package, never a list here.
- **The dash-improve-my-llms floor moves 2.7.1 → 2.8.0**, in all five
  encodings (`requirements.txt`, `run.py`'s `_DIMLL_FLOOR` and its boot
  diagnosis, `tests/test_site_identity.py`, and both `ci.yml` asserts).
- **Render deploys `release`, and only CD writes `release`.** A push to `main`
  is a candidate, not a deploy: `cd.yml`'s `deploy` job fast-forward-pushes the
  run's own sha to `release` after the CI matrix is green, and Render's
  autoDeploy reacts to that branch. `main` ahead of `release` means an
  uncertified push is pending. `verify` now runs only on a *successful* deploy
  and asserts `/healthz build == github.sha` itself — the old
  `always() && != 'cancelled' && != 'skipped'` admitted `failure`, and a verify
  that passes when nothing deployed must not exist.

### Added

- **The ledger's second table, `reads`.** dash-improve-my-llms 2.8.0 emits one
  event per corpus document it serves (`on_document_read`); `run.py` registers
  it once into `AnalyticsTracker.record_read`, which keeps every
  `_ledger.EVENT_FIELDS` key in a `reads` list in the same analytics file —
  same buffer, lock, flush cadence and retention as `visits`, with `client_ip`
  dropped unless `ANALYTICS_KEEP_CLIENT_IP=1`. It is a second table JOINED by
  the rollup, never summed into `human_hits` / `bot_hits` / `pages`.
- **Rollup v4, additive.** On a day with reads the payload gains
  `vendors[{key, class, verified, policy, hits, bytes, tiers{…}}]` (one row per
  `(key, verified, policy)`, the null key kept as the unverifiable bulk, capped
  at 40) and `reads` = `sum(vendors[].hits)`. Every v3 key is byte-identical,
  and a reads-only day is reported.
- **`/admin/traffic`** (`pages/traffic.py`) — this host's own ledger behind the
  control board's exact gate, failing closed without Clerk: vendor × day,
  vendor → tier for the picked day, top paths per vendor, and the v3 headline
  numbers alongside. Plain tables, no charts, no interval callback. `verified`
  is `n/a` where the operator publishes no IP ranges — Anthropic publishes
  none, so ClaudeBot is *always* `n/a` here, and that is a property of the
  vendor, not a defect on this host.
- **A declared posture fence** in `DIVERGENCES.md`, measured on the wire
  2026-08-29: `ai_bots {"/": 403, "/llms.txt": 200, "/healthz": 403}`,
  `healthz: full`, `runtime: docker`, `deploy: release-branch`.

## [0.2.1] — 2026-08-01

Two things: a picker bug that made whole custom categories invisible, and this
site joining the 2plot network properly. Only the first affects
`pip install dash-emoji-mart`.

**This is the first 0.2.x anyone can install.** 0.2.0 below was written, dated
and never shipped — no `v0.2.0` tag was ever pushed and nothing was uploaded, so
the newest thing `pip install dash-emoji-mart` has ever returned is still
`0.0.3` from 2024. Read the two sections together: 0.2.0 is what changed in the
repository, 0.2.1 is what changed since, and a single `v0.2.1` tag publishes
both at once.

### Fixed — the component

- **Custom emojis whose `src` is a dimensionless SVG rendered as nothing.**
  emoji-mart sizes a custom emoji's image with `max-width`/`max-height` and
  nothing else. A raster source has intrinsic dimensions and scales down to
  fit; an SVG carrying only a `viewBox` has no intrinsic size, so `width: auto`
  under a bare `max-width` resolves to zero. The emoji was in the DOM,
  focusable and clickable — and 0×0.

  It looked arbitrary rather than systematic, because it depended only on what
  the author happened to link. Iconify's API SVGs ship `width="1em"` and were
  always fine; SVGs straight off a repo were not. On the docs site's own
  custom-emoji demo that meant one category rendered and the next two were
  blank strips under their headings.

  The component now adopts a stylesheet into the picker's shadow root giving
  custom-emoji images `width: 1em; height: 1em; object-fit: contain`. `1em` is
  the size emoji-mart already intends — it sets font-size to `emojiSize` on
  each grid button and to the larger preview size in the footer — so one rule
  is right in both places, non-square artwork is not distorted, and raster
  sources render exactly as before.

- **`theme="auto"` follows the APP, then the OS — in that order.** emoji-mart's
  "auto" reads `prefers-color-scheme` and nothing else, which is the wrong
  signal in a Dash app: almost every one ships a theme toggle, and a toggle
  does not touch the OS. On a machine set to dark, flipping a Dash Mantine app
  to light left every picker dark against a white page — and it looked like the
  component ignoring its own `theme` prop.

  The component now prefers `data-mantine-color-scheme` on `<html>` when the
  document advertises one, and falls back to the media query otherwise. Reading
  an attribute adds no dependency on DMC: an app that does not set it behaves
  exactly as before. An explicit `theme="light"`/`"dark"` is still passed
  straight through, and the resolution re-runs on a toggle without a remount.

  This is why the docs site had the bug on six of its pages: only
  `/theming` wired the clientside callback its own prose recommends. That
  callback still works and is still the right answer for a non-Mantine toggle —
  it is just no longer needed for the common case.

- **`dynamicWidth` made the picker collapse instead of fill.** emoji-mart
  implements the option by setting `width: 100%` on a `<section>` inside its
  shadow root and never touches the `<em-emoji-picker>` host. A custom element
  has no author width, so it sizes to its content — and its content is that
  section asking for 100% of the host. The constraint is circular and resolves
  at min-content: measured, turning the switch on took the picker from 532px to
  **216px** inside a 482px parent, and the grid reflowed under the pointer,
  which reads as the component glitching on hover.

  The component now sizes the host itself when `dynamicWidth` is on, and clears
  the width when it is off. It has to happen outside the shadow root: the host
  is in the light DOM, so no shadow stylesheet reaches it, and `className` /
  `style` apply to our wrapper rather than to it. Measured after: 352px → 482px
  (the full container), 9 → 13 emoji per row, and it reverts cleanly.

  The container still needs a width of its own for "100%" to mean anything —
  a shrink-to-fit flex item gives 100% of nothing — so
  `docs/configuration/example.py` now gives the mount `flex: 1; minWidth: 0`
  and says why.

### Fixed — the documentation site

- **The popover example never opened.** `dmc.Popover` toggles `opened` itself
  when its target is clicked, so the example's extra `toggle` callback read the
  already-flipped value as `State` and returned `not True` — closing the
  popover in the same round trip that opened it. The symptom was a trigger that
  appeared to do nothing. Down to one callback, and the page now documents the
  trap rather than demonstrating it.
- **Inline `**bold**` and `*italic*` put a `<p>` inside a `<p>`.**
  markdown2dash renders paragraphs and inline emphasis with the same
  `dmc.Text`. `lib/markdown_inline.py` rebinds the three inline formatters to
  `span=True`. Five invalid nestings across the site, now none.

### Added — a visual identity of its own

The site's mark was `noto:grinning-face-with-smiling-eyes` — the generic yellow
smiley, which is every emoji library's placeholder and named nothing about this
one. It is now **🤠 U+1F920**, and the same drawing reaches every surface.

- **Header, favicon and share card are one glyph.** `assets/brand/cowboy-hat-face.png`
  (Noto Emoji, Apache-2.0) is committed as the single source; the header renders
  `noto:cowboy-hat-face` through Iconify, so the tab icon, the navigation mark
  and an unfurl are the same drawing rather than three vendors' idea of it.
- **`scripts/make_brand_assets.py`** derives the favicon set and the web app
  manifest from that source: `favicon.ico` (16/32/48), 192 and 512 PNGs, an
  apple-touch-icon flattened onto the dark surface because iOS backs a
  transparent icon with white, and `site.webmanifest` whose name, short name
  and theme colour are read from `lib/constants.py` rather than retyped.
  `--check` re-derives and compares, so a hand-edit or a stale run fails.
- **The manifest tests are no longer stubbed.** 0.2.1 shipped this file with a
  block explaining that the donor's seven installable-app assertions had no
  surface to test here. They do now: the manifest is linked and served, names
  this site, is installable, every icon it declares resolves, the
  apple-touch-icon resolves and is opaque, and the theme colour agrees. Suite
  is 92 → 99.
- **The social card exists.** 1200x630, the fleet layout — accent rule, brand,
  three-line tagline, mono domain — with the cowboy on the right, matching how
  `email.2plot.dev` frames its artwork. `make_social_card.py` now WARNS when a
  tagline overflows its three-line budget instead of silently slicing it; the
  first render of this card read "...custom image and SVG categories, and" and
  stopped mid-clause, which is precisely the kind of thing nobody catches on an
  asset they never see.
- **`github_assets/` is gone.** The 2.9 MB README demo GIF now comes from
  `cdn.2plot.ai/github_assets/github-demo.gif`, so cloning the repo no longer
  drags it along.

### Changed — the 2plot network standard

Brings this host onto the standard proven on 2plot.ai, 2plot.dev, boilerplate,
leaflet, email, flexlayout and llms. Nothing here changes the package.

- **One brand, every surface.** `SITE_BRAND = "dash-emoji-mart — emoji picker
  for Dash"` now reaches `Dash(title=)`, the `/llms.txt` H1 and viewer chip
  (via dimll 2.3.4's `resolve_site_title`), the template's fallback `<title>`,
  the README and the home page's own heading. The package name leads, because
  for a component library the package is what a reader came to find; "Pip
  Install Python" is the byline and lives in the description.
- **One short app id.** `AD_APP_ID` defaulted to `dash-emoji-mart` — the PyPI
  name — while the traffic reporter already said `emojimart`, so the same app
  would have reached the hub under two ids and its ad rows would never have
  lined up with its traffic rows. Everything now folds to `lib.constants.APP_KEY`.
- **The internal-traffic contract, both halves.** Requests carrying
  `2plot-internal` are dropped at WRITE time, before bot classification, so the
  hub's health sweep and CI batteries cannot land in `bot_hits`; `/healthz` is
  never a visit. Outbound, the ad client and the traffic reporter now identify
  themselves — the ad fetch runs once per page view and was arriving at
  2plot.dev as `python-requests`, which its tracker counts as a bot, so this
  site's readers were inflating the hub's crawler numbers.
- **The social card.** An OG block in `lib/constants.py`, `image_url=` and
  `description=` at every `register_page`, and the auxiliary tags Dash never
  emits in the template. One missing `image_url=` makes Dash emit
  `content=""`, and an empty tag late in the document beats a good one earlier.
- **`lib/bulletin.py`**, wired through `NETWORK_BULLETIN_URL` with a boot line
  that says which state the process is in — an unwired bulletin has no failure
  mode, only an announcement that never appears.
- **`gunicorn>=23`.** The floor was `>=21.2,<22`, a ceiling inherited wholesale
  from markdown2dash's dependency block, holding this image on a gunicorn
  affected by CVE-2024-6827 and CVE-2024-1135. markdown2dash now installs
  `--no-deps` at every install site and CI asserts the resolved version inside
  the built image.
- **dash-improve-my-llms `>=2.3.4`**, the floor that delivers `resolve_site_title`.
- **CI/CD.** `cd.yml` owns `main` and calls `ci.yml` via `uses:` so merges stop
  running everything twice; actionlint runs first; a container job builds the
  real image, boots it, asserts dependency fingerprints inside it and runs the
  network battery against it; the deploy waits for five consecutive `/healthz`
  successes rather than one, because Render swaps instances and the old one
  answers throughout.

### Measured, not fixed — three upstream findings

All verified on this host and recorded so the next pass does not rediscover
them.

- **Removing a category is one-way for the lifetime of the page.** Setting
  `maxFrequentRows` to `0` drops the Frequently-used section and setting it
  back does not restore it; picking a few `categories` and then clearing the
  field does not restore "all of them" either. Same cause: `init()` builds
  `Data.categories` once and mutates that array in place, `splice`-ing out any
  category that ends up empty, and the only path that rebuilds it from
  `Data.originalCategories` is the one that runs when `categories` is passed.
  The state is a module global that outlives the component, every remount and
  every SPA navigation; a page reload is the only reset. Documented on the
  configuration page.
- **`noCountryFlags` and `exceptEmojis` filter the grid, not the search**
  (emoji-mart 5.6.0). Both remove the emoji from `category.emojis` while
  `SearchIndex.search` matches over `Object.values(Data.emojis)` — the
  unfiltered map — with no category filter of its own. Measured: with
  `noCountryFlags` on, the flags category shrinks to the safe list and typing
  "united" still returns 🇬🇧 🇺🇸 🇦🇪 🇺🇳, identically to having it off.

  Not worked around, deliberately. emoji-mart loads its data into a
  module-global exactly once per page (`if (!Data) Data = props.data`), so
  pre-filtering the data for one picker would silently change every other
  picker on the page and every page after it in a Dash SPA — the same aliasing
  trap `categories` + `custom` already carries a red warning about. A visible
  search result beats an invisible, mount-order-dependent one. Documented on
  both props, in the README table, and on the configuration page; pinned by
  `tests/test_component.py` so a regeneration cannot quietly drop the caveat.

- **The prerender overwrites Dash's per-page `<title>` and appends its own
  `og:title`,** both from the page's registered `name`. `PAGE_TITLE_PREFIX`
  therefore never reaches `<title>` or the scraper-winning `og:title` on any
  page of any satellite — they read "Picker in a Popover", not
  "dash-emoji-mart | Picker in a Popover". Registering the prefixed string as
  `name` would fix the tags and wreck the `## Pages` index in `/llms.txt`,
  which lists that same value inside a document already headed by the brand.
  Left as-is and pinned by a test that fails when the behaviour changes.
- **`og:image` for crawler-classified UAs is still open (LESSONS §6), and the
  obvious fix is a trap.** 2.3.4's prerender *does* emit `og:image` when the
  page metadata carries an `og_image` key, and passing it measurably works —
  but Dash already emitted one, so the page ends up with two `og:image` tags
  and `scripts/smoke_live.py` requires exactly one. Duplicate `og:image` is how
  the fleet previously shipped an SVG card that beat a good one on tag order,
  so the rule is right and the per-site fix is wrong. Closing this needs the
  prerender to emit `og:image` only when the document does not already carry
  one. Separately, Slackbot and Twitterbot are served
  `html_generator.py`'s hard-coded head, which has no `og:image` and no hook
  for one at all.

## [0.2.0] — 2026-07-31 (never published)

**Not on PyPI.** This section was written and dated but no `v0.2.0` tag was
pushed, so nothing was ever built or uploaded under this number. It is kept as
the record of the restructure rather than rewritten into 0.2.1, because the
"On the version number" reasoning below is what explains the jump from `0.0.3`
and is still the reasoning. Everything described here ships as part of `0.2.1`.

The repository housekeeping release. 0.0.x was a `dash-component-boilerplate`
scaffold with a demo app bolted on; 0.2.0 is a packaged component with a hosted
documentation site, a compatibility matrix and a release pipeline.

### On the version number

**0.2.0 deliberately skips ahead of both existing lineages.** Two different
"current" versions have been in circulation:

- **PyPI** holds `0.0.1`, `0.0.2` and `0.0.3`. `0.0.3` (2024) is the newest
  thing `pip install dash-emoji-mart` has ever returned, and it raises on import
  under Dash 4 with React 18.2 — it predates both.
- **`0.0.5`** is the build that actually works, but it was never published. It
  exists only as a tarball vendored into sibling projects (`dash-leaflet2`
  installs it from `vendor/dash_emoji_mart-0.0.5.tar.gz`), so no PyPI user has
  ever been able to get it.

A `0.0.6` would have been ambiguous against both. `0.2.0` is unambiguous, and
the jump is a signal rather than a cost: this is a `0.x` project, and the gap
between `0.0.3` on PyPI and what this release contains is not a patch-level gap.
This is the first release where the PyPI artifact, the vendored tarball and the
repository all describe the same software.

Consumers vendoring `0.0.5` keep working — a local tarball install is unaffected
by anything published here — but should move to `dash-emoji-mart>=0.2.0` from
PyPI and drop the vendored copy. That vendoring only ever existed because PyPI's
`0.0.3` was broken.

### Added

- **`selectedEmoji`** — the full emoji-mart object for the current selection
  (`id`, `name`, `native`, `unified`, `shortcodes`, `keywords`, `skin`, and
  `src` for custom emojis). Written in the same `setProps` call as `value`, so a
  callback taking both fires once per pick rather than twice.
- **`clickedOutside`** — an `n_clicks`-style counter that increments each time
  the user clicks outside the picker. emoji-mart's own `onClickOutside` hands
  its handler a DOM event, which cannot cross into Python; this makes the signal
  usable for dismissing a hand-rolled panel. (Inside a `dmc.Popover` it is not
  needed — Mantine already closes on an outside click and writes `opened` back.)

  It is measured against the component's own wrapper rather than delegated to
  emoji-mart, because emoji-mart's version is wrong in two ways for this use.
  It fires whenever the event target is not *exactly* the picker's root element,
  so clicking an emoji counts as an outside click; and it registers its document
  listener during mount, while the click that opened the picker is still
  bubbling toward `document`, so it reports an outside click before the user has
  clicked anything. Wired to a popover, that closed the popover on the same
  click that opened it. This implementation containment-tests against the
  wrapper and binds one task after mount, so neither happens.
- **`className` and `style`** on the wrapper element, so the picker can be
  positioned and themed (emoji-mart's `--em-rgb-*` custom properties) without a
  wrapping `html.Div`.
- **Dash persistence** — `persistence`, `persisted_props` (default `["value"]`)
  and `persistence_type` (default `"local"`).
- **`dash_emoji_mart.iconify`** — the Iconify loader, previously a loose
  `iconify_loader.py` in the repo root, now ships inside the package. Converts
  any of Iconify's 150+ icon sets into `custom=` categories. `requests` is an
  opt-in extra (`pip install "dash-emoji-mart[iconify]"`) and imports lazily, so
  the core package still depends on nothing but `dash`.
- **Documentation site** at <https://emojimart.2plot.dev> — eight
  markdown-driven pages with live, editable examples, `llms.txt` for every page,
  a sitemap and robots.txt.
- **2plot network membership.** The site now publishes the cross-host directory
  (`lib/network_directory.py`, copied verbatim from the documentation
  boilerplate so every satellite advertises the same graph): `rel="related"`
  tags in `<head>`, a `## Network` section in `/llms.txt`, and followed links in
  the prerendered body. Search engines follow cross-host links weakly and agents
  do not follow them at all, so without this an agent landing here sees one
  library and nothing saying the rest of the network exists.
- **Traffic reporting to the 2plot.ai hub** — `lib/analytics_tracker.py` (the
  visitor ledger), `lib/traffic_rollup.py` (daily rollup) and
  `lib/satellite_reporter.py` (the signed hourly POST), replacing the
  hand-rolled `lib/satellite_analytics.py`. Dormant without
  `CROSS_APP_WEBHOOK_SECRET`.
- **`scripts/verify_network.py`** — the 2plot migration battery (canonical
  count, robots fingerprint, directive leakage, peer reachability) runnable
  in-process against the Flask test client.
- **CI** — every push runs the docs smoke suite against Dash 4.1.0, 4.2.0,
  4.3.0 and 4.4.1, builds the wheel, installs it into a clean venv with nothing
  but `dash` present, and imports it on Python 3.9 through 3.13.
- **`scripts/smoke_test.py`** and **`scripts/check_release.py`** — the same
  checks CI runs, runnable locally.

### Changed

- **Requires `dash>=4.1` and Python >=3.9.** The Python component classes are
  now generated by `dash-generate-components` under Dash 4; 0.0.x was generated
  under Dash 3. The CI matrix measures the whole claimed range on every push.
- **The documentation site requires `dash-improve-my-llms[flask]>=2.3.3**
  (site-only; the package's own dependency list is untouched and still just
  `dash>=4.1`). Three things in that range are load-bearing here: merge
  semantics for `register_page_metadata` (2.2.0), without which `run.py`'s root
  re-registration silently blanked the home page's prose and served crawlers a
  "requires JavaScript" stub on the site's most valuable URL; the universal
  prerender that writes canonical/OpenGraph/`<title>` server-side per page
  (2.2/2.3); and the corrected AI-crawler taxonomy (2.3.2/2.3.3).
- **`block_ai_training` is now `True`.** Before 2.3.2 this flag also blocked
  the user-initiated fetchers through legacy agent aliases, which broke
  claude.ai fetches — so the site ran `False`. The taxonomy fix means `True`
  now refuses only bulk training crawlers (GPTBot, ClaudeBot, CCBot) while
  Claude-User, Claude-SearchBot, ChatGPT-User and OAI-SearchBot stay allowed.
  The docs remain reachable by anything a person actually asked to fetch them.
- **`SATELLITE_APP_ID` → `SATELLITE_APP_KEY`** in `render.yaml`. The new
  reporter reads the latter and defaulted to the boilerplate's own directory
  key, so a deploy that kept the old variable name would have reported this
  app's traffic as the boilerplate's and overwritten its rows on the hub.

### Fixed (documentation site)

- **Retired the canonical shim in `templates/index.html`** — a hard-coded
  `<link rel="canonical">` plus a ~40-line `history.pushState` monkey-patch
  that rewrote the canonical and URL meta tags client-side from a hard-coded
  origin, ignoring `DASH_EMOJI_MART_BASE_URL`. The prerender does this
  server-side, per page; keeping the shim would have emitted two canonical tags
  on every page.
- **The prerender was silently disabled by an HTML comment.** Its idempotency
  guard is a substring test for its marker attribute across the whole document,
  and HTML comments are part of the document — so a comment *describing* the
  marker convinced the injector it had already run. Every page served with no
  canonical tag, no OpenGraph tags and no prerendered body for crawlers, while
  looking perfectly normal in a browser. `scripts/verify_network.py` now
  regression-tests for it, and the template comment describes the attribute
  without spelling it.
- SPA page views are counted again after the analytics swap. The boilerplate's
  tracker skips `/_dash-update-component` and ships no beacon, so a
  straight replacement would have counted only entry pages and reported every
  session as single-page. `lib/pageview_beacon.py` ports the old beacon onto
  the new tracker, feeding the same ledger.
- **The site index no longer prints its tagline twice.** `/llms.txt` emits
  `# <name>` and `> <description>` from the page metadata, then splices in the
  root page's prose — stripping a leading H1 from it, but not a leading
  blockquote. The loader's preamble therefore surfaced as the same tagline
  repeated at the top of the index. The preamble is now skipped for `/` only;
  per-page docs still carry their own title and tagline, because the package
  returns those verbatim and they would otherwise arrive untitled.
- **`run.py` refuses to start on `dash-improve-my-llms` below 2.3.3**, and
  prints the resolved package version and interpreter path at startup. Below
  the floor the site boots cleanly and is broken only where nobody looks: on
  <2.2 the root `register_page_metadata` call blanks the home page's prose so
  `/llms.txt` serves `_No LLMS_DOC registered for /._`, and on <2.1 the whole
  `## Network` section silently disappears. A server started before a
  dependency upgrade keeps the old version in memory and serves exactly that,
  indefinitely, with no signal — which is precisely how it was found.
- **Directive options no longer leak into `llms.txt`.** The loader expanded
  `.. source::path` into a fenced code block but left the directive's indented
  `:defaultExpanded:` / `:withExpandedButton:` lines behind — and with the
  directive line gone, the package's own stripper had no block to recognise, so
  the orphaned options shipped as noise in every page's agent-facing markdown.
  The loader now consumes the option lines with the directive, and
  `scripts/verify_network.py` checks for orphaned options as well as for
  unexpanded directive lines (the runbook's `^\.\. \w+::` pattern matches only
  the latter, which is why this got through).
- **The documentation examples no longer pass `categories` alongside `custom`.**
  The combination is only safe on the first picker initialised in a page's
  lifetime — see the note below — so the Iconify page rendered its default set
  and then an empty grid for every set switched to afterwards, and the
  custom-emoji page rendered correctly or not depending on which page the
  visitor had opened first.
- **Packaging moved from `setup.py` to `pyproject.toml`.** The distribution now
  contains only the component package — the documentation site, the JS source
  and the react-docgen `metadata.json` no longer ship. CI asserts this against
  the built wheel.
- **Repository layout flattened.** The project lived in a nested
  `emoji_mart/dash_emoji_mart/` directory; everything is now at the repository
  root, matching the `dash-leaflet2` layout.
- `LICENSE` was a zero-byte file in 0.0.x. It now contains the MIT licence the
  package has always claimed.

### Known upstream limitation

- **`categories` cannot be combined with `custom`.** emoji-mart filters the
  `categories` prop against an internal `originalCategories` array that it
  captures **by reference** on the first `init()` in a page's lifetime. Custom
  categories pushed during that first init land in it through the aliasing, so
  the pair appears to work. Every later init rebuilds the category list as a new
  array, breaking the alias, and the filter then runs against a stale list that
  cannot contain the custom ids — dropping every custom category silently.

  A remount does not help; it is what triggers the failure. There is no
  `categories` value that avoids it. Omit the prop when passing `custom`, and
  your categories are appended after the built-ins. Documented on
  [Custom emojis](https://emojimart.2plot.dev/custom-emojis), the API reference
  and the README.

### Removed

- **The R and Julia backends.** `R/`, `man/`, `inst/`, `NAMESPACE`,
  `DESCRIPTION`, `Project.toml` and `src/jl/` were half-generated and never
  regenerated after the first release. `dash-generate-components` now runs
  Python-only.
- **Four unusable props: `onEmojiSelect`, `onClickOutside`, `onAddCustomEmoji`
  and `getSpritesheetURL`.** All four were declared `PropTypes.func`. Dash
  serialises props to JSON and a Python function is not serialisable, so passing
  any of them raised — they were always `None` in practice. Use
  `Input(id, "value")` / `Input(id, "selectedEmoji")` and
  `Input(id, "clickedOutside")` instead.
- **`ramda`** from the JS dependencies — nothing imported it.
- The React-only demo harness (`src/demo/`, `webpack.serve.config.js`,
  `index.html`). `python run.py` is now the single way to run the component
  locally.

### Fixed

- **Custom emojis whose `src` is a dimensionless SVG are no longer invisible.**
  emoji-mart sizes a custom emoji's image with `max-width`/`max-height` and
  nothing else. A raster source has intrinsic dimensions and scales down to fit;
  an SVG whose root element carries only a `viewBox` — no `width`/`height` — has
  no intrinsic size, so `width: auto` under a bare `max-width` resolves to zero
  and the emoji renders as a 0×0 box: in the DOM, focusable, clickable,
  invisible.

  The failure looked arbitrary rather than systematic, because it depends only on
  what the author happened to link. Iconify's API SVGs ship `width="1em"
  height="1em"` and were always fine; SVGs straight off a repo (devicons and most
  icon projects) were not — so one custom category would render and the next
  would be a blank strip under its heading.

  The component now adopts a stylesheet into the picker's shadow root giving
  custom-emoji images `width: 1em; height: 1em; object-fit: contain`. `1em` is
  the size emoji-mart already intends — it sets font-size to `emojiSize` on each
  grid button and to the larger preview size in the footer — so one rule is
  correct in both places, non-square artwork is not distorted, and raster sources
  render exactly as before.
- **The Iconify cache no longer writes inside the installed package.**
  `iconify_loader.py` cached API responses to `Path(__file__).parent /
  ".iconify_cache"`, which is inside `site-packages` for an installed package
  and typically not writable. The cache now lives under the system temp
  directory, relocatable with `DASH_EMOJI_MART_CACHE_DIR`.
- **`__init__.py` no longer registers resources that do not exist.** It
  advertised `async-*.js` chunks the webpack config never emits, and a
  `.js.map` entry Dash serves on demand anyway.
- Iconify network failures are now contained: a request that fails logs a
  warning and returns empty, so a picker renders without its optional icon set
  rather than the page erroring.

## [0.0.5] — 2026-01-08

### Fixed

- Multiple custom emoji categories can be set at once.

## [0.0.3]

- Initial PyPI release, and still the newest version on PyPI until `v0.2.1` is
  tagged. Errors on import under Dash 4 with React 18.2; use 0.2.1.

[0.2.1]: https://github.com/pip-install-python/dash-emoji-mart/releases/tag/v0.2.1
[0.0.5]: https://github.com/pip-install-python/dash-emoji-mart/releases/tag/v0.0.5
[0.0.3]: https://github.com/pip-install-python/dash-emoji-mart/releases/tag/v0.0.3
