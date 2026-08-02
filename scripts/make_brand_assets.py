#!/usr/bin/env python3
"""Render this site's favicon set and web app manifest from one source glyph.

    python scripts/make_brand_assets.py            # regenerate everything
    python scripts/make_brand_assets.py --check    # verify, change nothing

WHY A SCRIPT AND NOT A ONE-OFF EXPORT
-------------------------------------
The boilerplate's `tests/test_social_card.py` pins a whole installable-app
surface — the manifest names the site, every icon it declares resolves, the
apple-touch-icon resolves, and the theme colour agrees with the manifest. Four
files and a JSON document have to stay consistent with `lib/constants.py` and
with each other. Hand-exported icons drift the first time the brand changes and
nobody notices, because a wrong manifest produces no error: the browser simply
declines to offer an install.

So the icons are DERIVED, here, from a single committed source, and the
constants are read rather than retyped.

THE SOURCE GLYPH
----------------
`assets/brand/cowboy-hat-face.png` — Noto Emoji U+1F920, 512x512, Apache-2.0
(https://github.com/googlefonts/noto-emoji). Committed rather than fetched at
build time so this script works offline and the output cannot change under us
when upstream redraws the emoji.

Noto specifically, because it is the same family the site's own navigation mark
uses: `components/header.py` renders `noto:cowboy-hat-face` through Iconify. The
tab icon, the header mark and the share card are then the same drawing rather
than three vendors' idea of the same emoji, which is the sort of mismatch you
only notice in a screenshot months later.

Pillow is a build-time dependency only, deliberately absent from
requirements.txt: nothing at runtime renders images.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# Pillow is imported INSIDE the render path, not here.
#
# `--check` only compares a JSON document against lib/constants.py and stats a
# few files — no pixels involved. Importing Pillow at module scope made the
# check impossible to run anywhere Pillow is absent, which is everywhere that
# matters: Pillow is deliberately not in requirements.txt (nothing at runtime
# renders images), so CI, the container and a fresh contributor checkout all
# lack it. The suite calls `--check`, so a top-level import turned a build-time
# dependency into a test-time one and failed every CI job.
def _pillow():
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - the one dependency, named clearly
        sys.exit("This script needs Pillow:\n    pip install Pillow")
    return Image

SOURCE = REPO_ROOT / "assets" / "brand" / "cowboy-hat-face.png"
OUT_DIR = REPO_ROOT / "assets" / "favicon"

# The dark surface the site actually renders on, so a maskable icon and the
# install splash do not flash white. Matches templates/index.html's theme-color
# neighbourhood and scripts/make_social_card.py's BG_TOP.
BG = (26, 27, 30, 255)

# PNG icons the manifest declares. 192 and 512 are the two sizes Chrome
# requires before it will offer an install prompt at all.
PNG_SIZES = (192, 512)

# iOS ignores the manifest entirely and uses this. It also composites onto a
# WHITE background if the image has alpha, so this one is flattened onto BG —
# a transparent apple-touch-icon is how a dark-themed site ends up with a
# glaring white tile on someone's home screen.
APPLE_SIZE = 180

# .ico carries several sizes in one file; browsers pick. 48 is for Windows
# taskbar pinning, 16/32 are the tab.
ICO_SIZES = (16, 32, 48)

# Padding as a fraction of the canvas, so the glyph is not flush to the edge in
# a rounded tab-icon slot. The source has ~0 margin of its own.
PAD_FRACTION = 0.08


def _load_source():
    Image = _pillow()
    if not SOURCE.exists():
        sys.exit(f"source glyph missing: {SOURCE.relative_to(REPO_ROOT)}")
    art = Image.open(SOURCE).convert("RGBA")
    bbox = art.getchannel("A").getbbox()
    return art.crop(bbox) if bbox else art


def _tile(art, size: int, *, opaque: bool):
    """The glyph centred on a square canvas, padded, optionally flattened.

    `opaque=True` returns RGB — the alpha channel is DROPPED, not merely filled.
    A fully-opaque RGBA file still declares colour type 6 in its PNG header, and
    "is this icon opaque?" then needs Pillow to answer. Emitting RGB makes the
    answer structural: colour type 2, readable from the IHDR with the standard
    library, which is what tests/test_social_card.py does.
    """
    Image = _pillow()
    canvas = Image.new("RGBA", (size, size), BG if opaque else (0, 0, 0, 0))
    inner = max(1, int(size * (1 - 2 * PAD_FRACTION)))
    glyph = art.copy()
    glyph.thumbnail((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(
        glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2)
    )
    return canvas.convert("RGB") if opaque else canvas


def _manifest() -> dict:
    """The manifest document, derived from the constants. No pixels involved."""
    from lib.constants import SITE_BRAND, SITE_SHORT_NAME

    return {
        "name": SITE_BRAND,
        "short_name": SITE_SHORT_NAME,
        "description": (
            "An emoji picker for Plotly Dash 4 — emoji-mart wrapped as a "
            "single Dash component."
        ),
        "start_url": "/",
        "display": "standalone",
        # Must equal templates/index.html's theme-color and the card's ACCENT;
        # tests/test_social_card.py pins the pair.
        "theme_color": "#fab005",
        "background_color": "#1a1b1e",
        "icons": [
            {
                "src": f"/assets/favicon/favicon-{size}.png",
                "sizes": f"{size}x{size}",
                "type": "image/png",
                "purpose": "any",
            }
            for size in PNG_SIZES
        ],
    }


GENERATED = (
    [f"favicon-{size}.png" for size in PNG_SIZES]
    + ["apple-touch-icon.png", "favicon.ico", "site.webmanifest"]
)


def check() -> int:
    """Verify without rendering — and therefore without Pillow.

    Deliberately separate from `render()` rather than a flag threaded through
    it. The suite runs this, and the suite runs where Pillow is not installed;
    sharing a code path with the renderer is what put a `from PIL import Image`
    on the check's critical path and failed every CI job.
    """
    problems = []
    for name in GENERATED:
        if not (OUT_DIR / name).exists():
            problems.append(f"{name} MISSING")

    manifest_path = OUT_DIR / "site.webmanifest"
    if manifest_path.exists():
        try:
            on_disk = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as exc:
            problems.append(f"site.webmanifest UNREADABLE ({exc})")
        else:
            if on_disk != _manifest():
                problems.append(
                    "site.webmanifest STALE — it disagrees with lib/constants.py"
                )

    if problems:
        for problem in problems:
            print(f"[brand] {problem}", file=sys.stderr)
        print("[brand] run: python scripts/make_brand_assets.py", file=sys.stderr)
        return 1

    print("[brand] every generated asset is present and current")
    return 0


def render() -> int:
    art = _load_source()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[tuple[str, str]] = []

    def emit(path: Path, image, **save_kwargs) -> None:
        image.save(path, **save_kwargs)
        written.append((path.name, f"{image.width}x{image.height}"))

    # Transparent PNGs — the manifest icons. `purpose: any` in the manifest, so
    # transparency is correct here: the launcher supplies its own backdrop.
    for size in PNG_SIZES:
        emit(OUT_DIR / f"favicon-{size}.png", _tile(art, size, opaque=False),
             format="PNG", optimize=True)

    # Opaque, and RGB rather than filled RGBA — see _tile and APPLE_SIZE.
    emit(OUT_DIR / "apple-touch-icon.png", _tile(art, APPLE_SIZE, opaque=True),
         format="PNG", optimize=True)

    # The .ico. Pillow writes every requested size into the one file.
    #
    # One copy, in this subdirectory. Dash's {%favicon%} placeholder scans the
    # whole assets tree for a file named favicon.ico rather than only the
    # assets root, so it finds this one and emits its own <link rel="icon">
    # pointing here — measured, not assumed. An extra copy at assets/favicon.ico
    # was written at first and never served.
    emit(OUT_DIR / "favicon.ico", _tile(art, max(ICO_SIZES), opaque=False),
         format="ICO", sizes=[(s, s) for s in ICO_SIZES])

    (OUT_DIR / "site.webmanifest").write_text(
        json.dumps(_manifest(), indent=2) + "\n"
    )
    written.append(("site.webmanifest", "ok"))

    for name, detail in written:
        print(f"[brand] {name:24} {detail}")
    print(f"[brand] source: {SOURCE.relative_to(REPO_ROOT)} (Noto Emoji, Apache-2.0)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the generated files exist and the manifest "
                         "matches the constants; write nothing")
    return check() if ap.parse_args().check else render()


if __name__ == "__main__":
    sys.exit(main())
