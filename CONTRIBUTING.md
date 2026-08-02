# Contributing

Thanks for taking the time. This is a small component with a large documentation site
around it, so the setup is a little unusual — this file covers what you need to know.

## Repository layout

```
dash_emoji_mart/          the shipped Python package: generated component
                          classes, the committed webpack bundle, iconify.py
src/lib/components/       the React source the bundle is built from
docs/<slug>/              one folder per documentation page: <slug>.md + example.py
pages/markdown.py         walks docs/ and registers every page — the only router
lib/ components/ assets/  the documentation site's shell
scripts/                  smoke_test.py, check_release.py
```

Everything outside `dash_emoji_mart/` is the documentation site and is explicitly
**not** packaged — `MANIFEST.in` prunes it and CI asserts the built wheel is clean.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # installs the component from the tree with `-e .`
npm install
```

Requires Python 3.10+ to run the docs site (`python-frontmatter` needs
`typing.TypeGuard`). The package itself supports 3.9+, which is what CI measures.

## The build

```bash
npm run build          # build:js + build:backends
npm run watch          # rebuild the bundle on change, during React work
```

`build:js` runs webpack over `src/lib/index.js` and writes
`dash_emoji_mart/dash_emoji_mart.min.js`. `build:backends` runs
`dash-generate-components` over `src/lib/components/` and writes
`dash_emoji_mart/DashEmojiMart.py`, `_imports_.py` and `package-info.json`.

**Both outputs are committed.** That is not an oversight: the committed bundle is what
makes `pip install dash-emoji-mart` work without Node, and what lets the Docker image
build without a JS toolchain. If you change anything under `src/`, run `npm run build` and
commit `dash_emoji_mart/` in the same commit. CI has a job that fails if the generated
component class no longer matches `src/`.

`dash_emoji_mart/metadata.json` is a build byproduct — gitignored, never packaged.

## Changing props

Props are declared once, in `DashEmojiMart.propTypes`, and everything downstream is
generated from them: the Python signature, the docstring, the `.. kwargs::` table on the
API reference page. Write the JSDoc comment above each prop as if it were user
documentation, because it is.

Two things to keep in mind:

- **`value` is a compatibility contract.** dash-leaflet2 vendors this component and reads
  `value`. Add props freely; changing what `value` contains is a breaking change.
- **Function-typed props do not work in Dash.** Props are serialised to JSON and a Python
  function is not serialisable, so a `PropTypes.func` prop can only ever be `None`. 0.2.0
  removed four of them for exactly this reason. If you need a callback-shaped signal,
  surface it as a counter the way `clickedOutside` does.

## Adding a documentation page

Create a folder under `docs/` with two files:

```
docs/my-page/my-page.md      frontmatter + prose
docs/my-page/example.py      must define `component = ...`
```

The frontmatter needs `name`, `description` and `endpoint`; `category` and `icon` control
where it lands in the navbar (see `CATEGORY_ORDER` in `components/navbar.py`). Embed the
demo with:

```
.. exec::docs.my-page.example
    :code: false

.. source::docs/my-page/example.py
    :defaultExpanded: false
    :withExpandedButton: true
```

No Python registration anywhere — `pages/markdown.py` finds it.

The example module must define `component`, not `layout`, and must **not** call
`dash.register_page`.

## Before you open a PR

```bash
python scripts/smoke_test.py      # renders every page, checks every route
python scripts/check_release.py   # version drift, stale bundle, packaging leaks
```

`smoke_test.py` is the same harness CI runs against each Dash version. It renders and
serialises every page layout, which is where a broken example actually surfaces — and it
syntax-checks every clientside callback with `node`, because Dash ships those strings to
the browser verbatim and a syntax error is completely silent server-side.

Install `node` locally if you can; without it that check reports SKIPPED rather than
failing, and a broken clientside callback would sail through.

## Code style

Match the surrounding code. Comments should explain *why* — a comment restating what the
line does is noise, and a comment that captures a non-obvious constraint (a Dash version
boundary, an emoji-mart initialisation quirk) is the most valuable thing in the file.

## Releasing

See [RELEASING.md](./RELEASING.md).
