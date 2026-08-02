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

try:
    from PIL import Image
except ImportError:  # pragma: no cover - the one dependency, named clearly
    sys.exit("This script needs Pillow:\n    pip install Pillow")

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


def _load_source() -> Image.Image:
    if not SOURCE.exists():
        sys.exit(f"source glyph missing: {SOURCE.relative_to(REPO_ROOT)}")
    art = Image.open(SOURCE).convert("RGBA")
    bbox = art.getchannel("A").getbbox()
    return art.crop(bbox) if bbox else art


def _tile(art: Image.Image, size: int, *, opaque: bool) -> Image.Image:
    """The glyph centred on a square canvas, padded, optionally flattened."""
    canvas = Image.new("RGBA", (size, size), BG if opaque else (0, 0, 0, 0))
    inner = max(1, int(size * (1 - 2 * PAD_FRACTION)))
    glyph = art.copy()
    glyph.thumbnail((inner, inner), Image.LANCZOS)
    canvas.alpha_composite(
        glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2)
    )
    return canvas


def build(check: bool) -> int:
    from lib.constants import PRIMARY_COLOR, SITE_BRAND, SITE_SHORT_NAME  # noqa: F401

    art = _load_source()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    written: list[tuple[str, str]] = []

    def emit(path: Path, image: Image.Image, **save_kwargs) -> None:
        if check:
            if not path.exists():
                written.append((path.name, "MISSING"))
            return
        image.save(path, **save_kwargs)
        written.append((path.name, f"{image.width}x{image.height}"))

    # Transparent PNGs — the manifest icons. `purpose: any` in the manifest, so
    # transparency is correct here: the launcher supplies its own backdrop.
    for size in PNG_SIZES:
        emit(OUT_DIR / f"favicon-{size}.png", _tile(art, size, opaque=False),
             format="PNG", optimize=True)

    # Opaque — see APPLE_SIZE above.
    emit(OUT_DIR / "apple-touch-icon.png", _tile(art, APPLE_SIZE, opaque=True),
         format="PNG", optimize=True)

    # The .ico. Pillow writes every requested size into the one file.
    #
    # One copy, in this subdirectory. Dash's {%favicon%} placeholder scans the
    # whole assets tree for a file named favicon.ico rather than only the
    # assets root, so it finds this one and emits its own <link rel="icon">
    # pointing here — measured, not assumed. An extra copy at assets/favicon.ico
    # was written at first and never served.
    ico = _tile(art, max(ICO_SIZES), opaque=False)
    emit(OUT_DIR / "favicon.ico", ico, format="ICO",
         sizes=[(s, s) for s in ICO_SIZES])

    manifest = {
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
    manifest_path = OUT_DIR / "site.webmanifest"
    if check:
        if not manifest_path.exists():
            written.append((manifest_path.name, "MISSING"))
        elif json.loads(manifest_path.read_text()) != manifest:
            written.append((manifest_path.name, "STALE"))
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        written.append((manifest_path.name, "ok"))

    if check:
        stale = [name for name, state in written if state in ("MISSING", "STALE")]
        if stale:
            print("[brand] out of date: " + ", ".join(stale), file=sys.stderr)
            print("[brand] run: python scripts/make_brand_assets.py", file=sys.stderr)
            return 1
        print("[brand] every generated asset is present and current")
        return 0

    for name, detail in written:
        print(f"[brand] {name:24} {detail}")
    print(f"[brand] source: {SOURCE.relative_to(REPO_ROOT)} (Noto Emoji, Apache-2.0)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the generated files exist and the manifest "
                         "matches the constants; write nothing")
    return build(ap.parse_args().check)


if __name__ == "__main__":
    sys.exit(main())
