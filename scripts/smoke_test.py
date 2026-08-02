#!/usr/bin/env python
"""Headless smoke test for the dash-emoji-mart documentation site.

Boots ``run.py`` in-process and drives it through the backend's **test client**
— real request/response handling, no socket bind — then reports one line per
check. CI runs this against every supported Dash version, so what passes here is
what the compatibility matrix measures.

What it checks
--------------
1. **Package** — ``dash_emoji_mart`` imports, its version agrees with
   ``pyproject.toml``, and the JS bundle it registers actually exists on disk.
2. **Import** — ``run.py`` imports and constructs the Dash app.
3. **Registration** — every ``docs/<slug>/<slug>.md`` became a page, with no
   duplicate paths (a duplicate is what makes the DMC search Select blow up
   with "Duplicate options are not supported").
4. **Layout render** — every page's layout is invoked and the whole component
   tree is serialised with Dash's own JSON encoder. This is where a broken
   example.py, a bad prop or a missing component actually surfaces.
5. **HTTP** — ``GET`` each page path plus ``/_dash-layout``,
   ``/_dash-dependencies``, ``/healthz``, ``/llms.txt``, ``/robots.txt`` and
   ``/sitemap.xml``.
6. **Clientside JS** — every inline clientside callback is syntax-checked with
   ``node``. Dash ships those strings to the browser verbatim, so a syntax
   error is completely silent server-side and the callback simply never runs.

Usage
-----
    python scripts/smoke_test.py                 # human-readable table
    python scripts/smoke_test.py --json out.json # machine-readable
    python scripts/smoke_test.py --quiet         # only failures

Exit code is 0 when every check passed, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Flask's test client is the only backend whose in-process client needs no extra
# dependency, and every check here is backend-independent.
os.environ.setdefault("DASH_BACKEND", "flask")
# Never let a smoke run beacon traffic at the live 2plot.ai hub.
os.environ.setdefault("SATELLITE_ANALYTICS_DRY_RUN", "1")
os.environ.pop("CROSS_APP_WEBHOOK_SECRET", None)
# Unreachable ad server → the slot hides instead of adding a timeout per page.
os.environ.setdefault("AD_SERVER_URL", "http://127.0.0.1:1")
# Keep the Iconify page off the network in CI: with the API unreachable the
# loader returns [] and the page renders its "unreachable" branch, which is a
# state worth exercising anyway. Set SMOKE_ALLOW_NETWORK=1 to let it through.
if os.environ.get("SMOKE_ALLOW_NETWORK") != "1":
    os.environ.setdefault("DASH_EMOJI_MART_CACHE_DIR", str(PROJECT_ROOT / ".iconify_cache"))


class Results:
    def __init__(self) -> None:
        self.checks: list[dict] = []

    def add(self, group: str, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append({"group": group, "name": name, "ok": ok, "detail": detail})

    @property
    def failures(self) -> list[dict]:
        return [c for c in self.checks if not c["ok"]]

    def summary(self) -> dict:
        return {
            "total": len(self.checks),
            "passed": len(self.checks) - len(self.failures),
            "failed": len(self.failures),
        }


def _pyproject_version() -> str | None:
    match = re.search(
        r'^version = "([^"]+)"', Path("pyproject.toml").read_text(), re.M
    )
    return match.group(1) if match else None


def _check_package(res: Results) -> None:
    """The component itself, before anything that depends on it."""
    try:
        import dash_emoji_mart as dem
    except Exception:
        res.add("package", "dash_emoji_mart imports", False, traceback.format_exc(limit=6))
        return
    res.add("package", "dash_emoji_mart imports", True, f"v{dem.__version__}")

    expected = _pyproject_version()
    res.add(
        "package",
        "version matches pyproject.toml",
        dem.__version__ == expected,
        f"package={dem.__version__} pyproject={expected}",
    )

    # __init__ registers the bundle by relative path; if that file is missing,
    # every picker renders as an empty div with no server-side error at all.
    pkg_dir = Path(dem.__file__).parent
    missing = [
        entry["relative_package_path"]
        for entry in dem._js_dist
        if not (pkg_dir / entry["relative_package_path"]).exists()
    ]
    bundle = pkg_dir / "dash_emoji_mart.min.js"
    size = f"{bundle.stat().st_size // 1024} KB" if bundle.exists() else "absent"
    res.add(
        "package",
        "registered JS bundle exists",
        not missing,
        size if not missing else f"missing: {', '.join(missing)}",
    )

    res.add(
        "package",
        "DashEmojiMart is exported",
        "DashEmojiMart" in dem.__all__,
        ", ".join(dem.__all__),
    )

    # The 0.2.0 selection contract. A regeneration that dropped either prop
    # would break every callback on the docs site silently.
    props = dem.DashEmojiMart(id="probe").available_properties
    required = {"value", "selectedEmoji", "clickedOutside", "custom", "categoryIcons"}
    absent = sorted(required - set(props))
    res.add(
        "package",
        "selection props present",
        not absent,
        f"{len(props)} props" if not absent else f"missing: {', '.join(absent)}",
    )


def _import_app(res: Results):
    """Import run.py and hand back (module, dash)."""
    t0 = time.time()
    try:
        import dash

        import run

        res.add("import", "run.py imports", True, f"{time.time() - t0:.1f}s")
        return run, dash
    except Exception:
        res.add("import", "run.py imports", False, traceback.format_exc(limit=8))
        return None, None


def _check_registration(res: Results, dash_mod) -> None:
    registry = dash_mod.page_registry
    md_files = sorted(Path("docs").glob("**/*.md"))
    res.add("pages", "markdown files discovered", bool(md_files), f"{len(md_files)} files")

    paths = [entry["path"] for entry in registry.values()]
    dupes = {p for p in paths if paths.count(p) > 1}
    res.add(
        "pages", "no duplicate page paths", not dupes, ", ".join(sorted(dupes)) or "clean"
    )

    missing = []
    for md in md_files:
        try:
            import frontmatter

            meta, _ = frontmatter.parse(md.read_text())
            endpoint = meta.get("endpoint")
            if endpoint and endpoint not in paths:
                missing.append(f"{md} → {endpoint}")
        except Exception as exc:  # noqa: BLE001
            missing.append(f"{md} (frontmatter unreadable: {exc})")
    res.add(
        "pages",
        "every .md registered a route",
        not missing,
        "; ".join(missing) or "all present",
    )


def _render_layouts(res: Results, dash_mod) -> None:
    """Invoke and serialise every page layout — where broken examples surface."""
    from dash._utils import to_json

    for entry in dash_mod.page_registry.values():
        path, name = entry["path"], entry["name"]
        try:
            layout = entry["layout"]
            if callable(layout):
                layout = layout()
            to_json(layout)  # Dash's own encoder — catches invalid components
            res.add("layout", f"{path}", True, name)
        except Exception as exc:  # noqa: BLE001
            res.add("layout", f"{path}", False, f"{type(exc).__name__}: {exc}")


def _check_picker_mounted(res: Results, dash_mod) -> None:
    """At least one real DashEmojiMart has to appear in the rendered layouts.

    Every other check here would still pass if the examples quietly stopped
    instantiating the component — which is precisely the regression this repo
    exists to prevent.
    """
    from dash._utils import to_json

    found = 0
    for entry in dash_mod.page_registry.values():
        layout = entry["layout"]
        if callable(layout):
            layout = layout()
        if '"DashEmojiMart"' in to_json(layout):
            found += 1
    res.add(
        "component",
        "pages mounting a DashEmojiMart",
        found > 0,
        f"{found} page(s)",
    )


def _http_checks(res: Results, run_mod, dash_mod) -> None:
    server = run_mod.app.server
    try:
        client = server.test_client()
    except Exception as exc:  # noqa: BLE001
        res.add("http", "test client available", False, str(exc))
        return
    res.add("http", "test client available", True, type(server).__name__)

    def get(url: str, group: str, expect=(200,), label: str | None = None):
        try:
            resp = client.get(url)
            ok = resp.status_code in expect
            res.add(group, label or url, ok, f"HTTP {resp.status_code}")
            return resp
        except Exception as exc:  # noqa: BLE001
            res.add(group, label or url, False, f"{type(exc).__name__}: {exc}")
            return None

    # Dash plumbing first — if these fail nothing else matters.
    get("/_dash-layout", "http")
    get("/_dash-dependencies", "http")

    # Network + SEO endpoints.
    get("/healthz", "endpoints")
    get("/llms.txt", "endpoints")
    get("/robots.txt", "endpoints")
    get("/sitemap.xml", "endpoints")

    # Every page path. A Dash SPA returns the same index HTML for all of them,
    # so a non-200 means routing or the index template broke.
    for entry in dash_mod.page_registry.values():
        get(entry["path"], "routes")


def _check_callbacks(res: Results, run_mod) -> None:
    try:
        count = len(run_mod.app.callback_map)
        res.add("callbacks", "callbacks registered", count > 0, f"{count} callbacks")
    except Exception as exc:  # noqa: BLE001
        res.add("callbacks", "callbacks registered", False, str(exc))


def _check_clientside_js(res: Results, run_mod) -> None:
    """Syntax-check every inline clientside callback with node.

    Python-side tests cannot catch a malformed clientside callback: Dash ships
    the string to the browser verbatim, so a syntax error is silent server-side
    and the callback simply never runs.
    """
    scripts = getattr(run_mod.app, "_inline_scripts", [])
    if not scripts:
        res.add("clientside", "inline scripts collected", False, "none found")
        return
    res.add("clientside", "inline scripts collected", True, f"{len(scripts)} scripts")

    if not shutil.which("node"):
        res.add("clientside", "javascript parses", True, "SKIPPED — node not installed")
        return

    bad: list[str] = []
    for i, src in enumerate(scripts):
        proc = subprocess.run(
            ["node", "--check", "-"],
            input=src,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if proc.returncode:
            first = next((ln for ln in proc.stderr.splitlines() if ln.strip()), "")
            bad.append(f"script[{i}]: {first[:120]}")

    res.add(
        "clientside",
        "javascript parses",
        not bad,
        "all valid" if not bad else f"{len(bad)} invalid — " + "; ".join(bad[:3]),
    )


def _check_asset_js(res: Results) -> None:
    """Syntax-check assets/*.js individually AND concatenated.

    The concatenated pass is the one that matters. Dash serves everything in
    `assets/` as separate classic <script> tags sharing ONE global lexical
    scope — so a top-level `const log` in two files is a SyntaxError in the
    second, and every handler in it silently never registers. Checking files
    one at a time cannot see that; concatenating reproduces the browser.
    """
    assets = sorted(Path("assets").glob("*.js"))
    if not assets:
        return
    if not shutil.which("node"):
        res.add("assets", "javascript parses", True, "SKIPPED — node not installed")
        return

    bad = []
    for f in assets:
        proc = subprocess.run(
            ["node", "--check", str(f)], capture_output=True, text=True, timeout=20
        )
        if proc.returncode:
            first = next((ln for ln in proc.stderr.splitlines() if "Error" in ln), "")
            bad.append(f"{f.name}: {first[:80]}")
    res.add(
        "assets",
        f"each of {len(assets)} files parses",
        not bad,
        "all valid" if not bad else "; ".join(bad[:3]),
    )

    combined = "\n".join(f.read_text() for f in assets)
    proc = subprocess.run(
        ["node", "--check", "-"], input=combined, capture_output=True, text=True, timeout=30
    )
    ok = proc.returncode == 0
    detail = "no global collisions"
    if not ok:
        detail = next(
            (ln for ln in proc.stderr.splitlines() if "Error" in ln), "see node output"
        )[:120]
    res.add("assets", "no collisions in shared global scope", ok, detail)


def run_all() -> Results:
    res = Results()
    _check_package(res)
    run_mod, dash_mod = _import_app(res)
    if run_mod is None:
        return res
    _check_registration(res, dash_mod)
    _render_layouts(res, dash_mod)
    _check_picker_mounted(res, dash_mod)
    _http_checks(res, run_mod, dash_mod)
    _check_callbacks(res, run_mod)
    _check_clientside_js(res, run_mod)
    _check_asset_js(res)
    return res


def report(res: Results, quiet: bool = False) -> None:
    import dash

    width = 78
    print()
    print("=" * width)
    print(
        f" dash-emoji-mart smoke test · Dash {dash.__version__} "
        f"· Python {sys.version.split()[0]}"
    )
    print("=" * width)

    current = None
    for c in res.checks:
        if quiet and c["ok"]:
            continue
        if c["group"] != current:
            current = c["group"]
            print(f"\n[{current}]")
        mark = "PASS" if c["ok"] else "FAIL"
        detail = c["detail"].replace("\n", "\n        ") if c["detail"] else ""
        print(f"  {mark}  {c['name']:<34} {detail}")

    s = res.summary()
    print()
    print("-" * width)
    print(
        f" {s['passed']}/{s['total']} checks passed"
        + (f" · {s['failed']} FAILED" if s["failed"] else "")
    )
    print("-" * width)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", metavar="PATH", help="write machine-readable results here")
    ap.add_argument("--quiet", action="store_true", help="print only failures")
    args = ap.parse_args()

    res = run_all()
    report(res, quiet=args.quiet)

    if args.json:
        import dash

        Path(args.json).write_text(
            json.dumps(
                {
                    "dash_version": getattr(dash, "__version__", "unknown"),
                    "python": sys.version.split()[0],
                    "summary": res.summary(),
                    "checks": res.checks,
                },
                indent=2,
            )
        )
        print(f"\nWrote {args.json}")

    return 0 if not res.failures else 1


if __name__ == "__main__":
    sys.exit(main())
