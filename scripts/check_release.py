#!/usr/bin/env python
"""Release-consistency checks for dash-emoji-mart.

None of these break a test run, which is exactly why they need their own gate —
each one produces a package that installs fine and is quietly wrong:

1. **Version drift.** The version lives in FOUR places: ``pyproject.toml``,
   ``package.json``, the generated ``dash_emoji_mart/package-info.json``, and
   ``lib/constants.APP_VERSION``. ``__init__.py`` reads its ``__version__``
   from package-info.json, so a bump that misses that file publishes a wheel
   labelled 0.2.0 whose ``dash_emoji_mart.__version__`` still says 0.1.0.

2. **Stale bundle.** ``dash_emoji_mart/dash_emoji_mart.min.js`` is committed —
   that is what makes the package installable without Node. If ``src/`` has
   been committed more recently than the bundle, the published component is
   built from older source than the repo shows.

3. **Packaging leaks.** ``metadata.json`` is a build-time react-docgen artifact
   that nothing loads at runtime; the docs site (docs/, pages/, lib/, ...) is
   not part of the distribution. Both are excluded in pyproject/MANIFEST, and
   this asserts the exclusions still hold.

4. **Empty LICENSE.** The 0.0.x releases shipped a zero-byte LICENSE file.

Usage:
    python scripts/check_release.py

Exit code 0 when everything is consistent, 1 otherwise.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

failures: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print(f"  FAIL  {message}")


def ok(message: str) -> None:
    print(f"  PASS  {message}")


def note(message: str) -> None:
    notes.append(message)
    print(f"  ....  {message}")


# ---------------------------------------------------------------------------
# 1. Versions
# ---------------------------------------------------------------------------
def check_versions() -> None:
    print("\n[versions]")

    pyproject = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    if not match:
        fail("no version found in pyproject.toml")
        return
    canonical = match.group(1)

    sources = {
        "pyproject.toml": canonical,
        "package.json": json.loads((ROOT / "package.json").read_text())["version"],
        "dash_emoji_mart/package-info.json": json.loads(
            (ROOT / "dash_emoji_mart" / "package-info.json").read_text()
        )["version"],
    }

    constants = (ROOT / "lib" / "constants.py").read_text()
    app_version = re.search(r'^APP_VERSION = "([^"]+)"', constants, re.M)
    sources["lib/constants.APP_VERSION"] = (
        app_version.group(1) if app_version else "<missing>"
    )

    drifted = {name: v for name, v in sources.items() if v != canonical}
    if drifted:
        for name, value in drifted.items():
            fail(f"{name} is {value}, expected {canonical}")
    else:
        ok(f"all four sources agree on {canonical}")


# ---------------------------------------------------------------------------
# 2. Bundle freshness
# ---------------------------------------------------------------------------
def _git_commit_time(path: Path) -> int | None:
    """Unix timestamp of the last commit touching `path`, or None."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    stamp = out.stdout.strip()
    return int(stamp) if stamp.isdigit() else None


def check_bundle() -> None:
    print("\n[bundle]")

    bundle = ROOT / "dash_emoji_mart" / "dash_emoji_mart.min.js"
    if not bundle.exists():
        fail("dash_emoji_mart/dash_emoji_mart.min.js is missing — run `npm run build`")
        return
    ok(f"bundle present ({bundle.stat().st_size // 1024} KB)")

    generated = ROOT / "dash_emoji_mart" / "DashEmojiMart.py"
    if not generated.exists():
        fail("dash_emoji_mart/DashEmojiMart.py is missing — run `npm run build:backends`")
    else:
        ok("generated component class present")

    bundle_time = _git_commit_time(bundle)
    src_time = _git_commit_time(ROOT / "src")
    if bundle_time is None or src_time is None:
        note("no git history for src/ or the bundle — freshness not checked")
    elif src_time > bundle_time:
        fail(
            "src/ was committed more recently than the bundle — "
            "run `npm run build` and commit the result"
        )
    else:
        ok("bundle is at least as new as src/")


# ---------------------------------------------------------------------------
# 3. Packaging surface
# ---------------------------------------------------------------------------
def check_packaging() -> None:
    print("\n[packaging]")

    pyproject = (ROOT / "pyproject.toml").read_text()
    manifest = (ROOT / "MANIFEST.in").read_text()

    # metadata.json must not be packaged, and must not be committed.
    if "metadata.json" in pyproject.split("[tool.setuptools.package-data]")[-1]:
        fail("metadata.json appears in [tool.setuptools.package-data]")
    else:
        ok("metadata.json is not in package-data")

    if "exclude dash_emoji_mart/metadata.json" not in manifest:
        fail("MANIFEST.in does not exclude dash_emoji_mart/metadata.json")
    else:
        ok("MANIFEST.in excludes metadata.json")

    tracked = subprocess.run(
        ["git", "ls-files", "dash_emoji_mart/metadata.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if tracked:
        fail("dash_emoji_mart/metadata.json is tracked by git — it should be ignored")
    else:
        ok("metadata.json is untracked")

    # Only the component package ships.
    packages = re.search(r"^packages = \[([^\]]+)\]", pyproject, re.M)
    listed = packages.group(1).replace('"', "").strip() if packages else ""
    if listed != "dash_emoji_mart":
        fail(f"[tool.setuptools] packages is {listed!r}, expected 'dash_emoji_mart'")
    else:
        ok("only dash_emoji_mart is packaged")

    unpruned = [
        d
        for d in ("docs", "pages", "lib", "components", "assets", "templates", "scripts")
        if f"prune {d}" not in manifest
    ]
    if unpruned:
        fail("MANIFEST.in does not prune: " + ", ".join(f"{d}/" for d in unpruned))
    else:
        ok("MANIFEST.in prunes the documentation site")


# ---------------------------------------------------------------------------
# 4. Legal / metadata files
# ---------------------------------------------------------------------------
def check_files() -> None:
    print("\n[files]")

    for name in ("README.md", "LICENSE", "CHANGELOG.md"):
        path = ROOT / name
        if not path.exists():
            fail(f"{name} is missing")
        elif path.stat().st_size == 0:
            fail(f"{name} is empty")
        else:
            ok(f"{name} present ({path.stat().st_size} bytes)")

    # The CHANGELOG must carry an entry for the version about to ship.
    match = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M)
    if match and (ROOT / "CHANGELOG.md").exists():
        version = match.group(1)
        if f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text():
            ok(f"CHANGELOG has a [{version}] section")
        else:
            fail(f"CHANGELOG.md has no '## [{version}]' section")


def main() -> int:
    print("=" * 74)
    print(" dash-emoji-mart release consistency")
    print("=" * 74)

    check_versions()
    check_bundle()
    check_packaging()
    check_files()

    print()
    print("-" * 74)
    if failures:
        print(f" {len(failures)} problem(s) found")
        print("-" * 74)
        return 1
    print(" all checks passed" + (f" ({len(notes)} skipped)" if notes else ""))
    print("-" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
