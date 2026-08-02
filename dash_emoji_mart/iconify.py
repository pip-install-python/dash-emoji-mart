"""Turn Iconify icon sets into emoji-mart custom categories.

Iconify hosts 150+ icon sets — including several emoji sets far larger than the
one emoji-mart bundles (twemoji has ~4,000 glyphs, openmoji ~4,200). This module
fetches a set's index from the Iconify API and reshapes it into the structure
``DashEmojiMart(custom=...)`` expects, so any of them can be picked from.

    from dash_emoji_mart import DashEmojiMart
    from dash_emoji_mart.iconify import iconify_to_emoji_mart

    DashEmojiMart(
        id="picker",
        custom=iconify_to_emoji_mart("twemoji", max_icons_per_category=60),
    )

`value` then comes back as the icon's SVG URL rather than a native glyph, the
same as for any other custom emoji.

This is the only part of the package that touches the network, so `requests` is
an OPT-IN dependency and is imported lazily — `import dash_emoji_mart` never
needs it:

    pip install "dash-emoji-mart[iconify]"

Responses are memoised in-process and cached on disk for 24 hours. The cache
lives outside the installed package (site-packages is frequently read-only);
set ``DASH_EMOJI_MART_CACHE_DIR`` to relocate it.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Union

ICONIFY_API = "https://api.iconify.design"
CACHE_DURATION = 86400  # 24 hours, in seconds


def _cache_dir() -> Path:
    """Where API responses are cached.

    Resolved per call rather than at import so ``DASH_EMOJI_MART_CACHE_DIR`` can
    be set after import (and so tests can redirect it). Never inside the package
    directory: a pip-installed package usually cannot be written to.
    """
    override = os.environ.get("DASH_EMOJI_MART_CACHE_DIR")
    if override:
        return Path(override)
    return Path(tempfile.gettempdir()) / "dash-emoji-mart-iconify-cache"


def _require_requests():
    """Import `requests` with an error that names the fix.

    Lazy on purpose: the core component has `dash` as its only dependency, and
    the bare ImportError ("No module named 'requests'") gives no hint that an
    extra exists.
    """
    try:
        import requests  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ImportError(
            "dash_emoji_mart.iconify needs the `requests` package.\n"
            '    pip install "dash-emoji-mart[iconify]"'
        ) from exc
    return requests


def _cache_path(key: str) -> Path:
    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # The key is a URL-ish string, so hash it into a safe filename. Not a
    # security boundary — md5 is used here purely as a short digest.
    hashed = hashlib.md5(key.encode()).hexdigest()  # noqa: S324
    return directory / f"{hashed}.json"


def _read_cache(key: str) -> Optional[Dict]:
    try:
        path = _cache_path(key)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as handle:
            cached = json.load(handle)
        if time.time() - cached.get("timestamp", 0) < CACHE_DURATION:
            return cached.get("data")
    except (json.JSONDecodeError, OSError):
        # A corrupt or unreadable cache entry is never fatal — refetch instead.
        pass
    return None


def _write_cache(key: str, data: Dict) -> None:
    try:
        with open(_cache_path(key), "w", encoding="utf-8") as handle:
            json.dump({"timestamp": time.time(), "data": data}, handle)
    except OSError:
        # A read-only or full disk degrades to "no cache", not a failure.
        pass


def _get_json(path: str, params: Optional[Dict] = None, timeout: int = 15) -> Dict:
    """GET one Iconify endpoint, disk cache first. `{}` on any failure."""
    requests = _require_requests()

    cache_key = f"{path}?{json.dumps(params or {}, sort_keys=True)}"
    cached = _read_cache(cache_key)
    if cached is not None:
        return cached

    try:
        response = requests.get(f"{ICONIFY_API}{path}", params=params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        # A picker that renders without an optional icon set beats a page that
        # 500s because api.iconify.design had a bad minute.
        print(f"Warning: Iconify request to {path} failed: {exc}")
        return {}

    _write_cache(cache_key, data)
    return data


@lru_cache(maxsize=64)
def get_all_collections() -> Dict:
    """Metadata for every icon set Iconify hosts, keyed by prefix."""
    return _get_json("/collections", timeout=10)


@lru_cache(maxsize=64)
def get_collection_info(prefix: str) -> Dict:
    """One icon set's index: title, categories and the icon names in each.

    Args:
        prefix: Iconify set prefix, e.g. ``"twemoji"`` or ``"noto"``.
    """
    return _get_json("/collection", params={"prefix": prefix})


def get_svg_url(prefix: str, icon: str) -> str:
    """The CDN URL for a single icon's SVG."""
    return f"{ICONIFY_API}/{prefix}/{icon}.svg"


def iconify_to_emoji_mart(
    prefixes: Union[str, List[str]],
    max_icons_per_category: int = 100,
    include_categories: Optional[List[str]] = None,
    exclude_categories: Optional[List[str]] = None,
    flatten: bool = False,
) -> List[Dict]:
    """Convert one or more Iconify sets into ``DashEmojiMart(custom=...)`` data.

    Args:
        prefixes: A single prefix or a list of them, e.g. ``"twemoji"`` or
            ``["twemoji", "noto", "pepicons-pop"]``.
        max_icons_per_category: Cap per category; -1 for no cap. The default of
            100 exists because a whole set can be several thousand icons, and
            every one of them becomes an ``<img>`` in the picker.
        include_categories: Keep only these categories (case-insensitive).
        exclude_categories: Drop these categories (case-insensitive).
        flatten: Merge each set's categories into one category per prefix.

    Returns:
        A list of ``{"id", "name", "emojis"}`` category dicts. Empty if every
        requested set failed to load.
    """
    if isinstance(prefixes, str):
        prefixes = [prefixes]

    include_cats = {c.lower() for c in include_categories} if include_categories else None
    exclude_cats = {c.lower() for c in exclude_categories} if exclude_categories else set()

    custom_categories = []

    for prefix in prefixes:
        info = get_collection_info(prefix)
        if not info:
            continue

        set_title = info.get("title", prefix.title())
        categories = info.get("categories", {})

        # Sets like fluent-emoji have no categories at all; their icons sit
        # under "uncategorized"/"hidden" instead.
        if not categories:
            all_icons = info.get("uncategorized", []) + info.get("hidden", [])
            if all_icons:
                categories = {"All": all_icons}

        if flatten:
            merged: List[str] = []
            for cat_icons in categories.values():
                merged.extend(cat_icons)
            categories = {"All": merged}

        for cat_name, icons in categories.items():
            cat_lower = cat_name.lower()

            if include_cats and cat_lower not in include_cats:
                continue
            if cat_lower in exclude_cats:
                continue
            if cat_lower == "hidden" or not icons:
                continue

            if max_icons_per_category > 0:
                icons = icons[:max_icons_per_category]

            emojis = [
                {
                    "id": f"{prefix}-{icon}",
                    "name": icon.replace("-", " ").replace("_", " ").title(),
                    "short_names": [icon, f"{prefix}:{icon}"],
                    "keywords": icon.replace("_", "-").split("-") + [prefix],
                    "skins": [{"src": get_svg_url(prefix, icon)}],
                    "native": "",
                    "unified": "custom",
                }
                for icon in icons
            ]

            if flatten or cat_name == "All":
                cat_id = prefix
                display_name = set_title
            else:
                cat_id = f"{prefix}-{cat_lower.replace(' ', '-').replace('&', 'and')}"
                display_name = f"{set_title}: {cat_name}"

            custom_categories.append(
                {"id": cat_id, "name": display_name, "emojis": emojis}
            )

    return custom_categories


def search_icons(
    query: str, prefix: Optional[str] = None, limit: int = 50
) -> List[Dict]:
    """Search Iconify and return matches as emoji-mart emoji dicts.

    Unlike :func:`iconify_to_emoji_mart` this returns bare emoji entries, not
    categories — wrap them in a category yourself to feed `custom`.
    """
    params: Dict[str, Union[str, int]] = {"query": query, "limit": limit}
    if prefix:
        params["prefix"] = prefix

    data = _get_json("/search", params=params, timeout=10)

    emojis = []
    for icon_full in data.get("icons", []):
        # Search results are fully qualified: "prefix:name".
        if ":" not in icon_full:
            continue
        icon_prefix, icon_name = icon_full.split(":", 1)
        emojis.append(
            {
                "id": f"{icon_prefix}-{icon_name}",
                "name": icon_name.replace("-", " ").title(),
                "short_names": [icon_name, icon_full],
                "keywords": icon_name.split("-") + [icon_prefix],
                "skins": [{"src": get_svg_url(icon_prefix, icon_name)}],
                "native": "",
                "unified": "custom",
            }
        )
    return emojis


def get_emoji_icon_sets() -> Dict[str, Dict]:
    """Curated emoji-style Iconify sets, keyed by prefix.

    Counts are the set sizes at the time of writing — indicative, not exact.
    """
    return {
        "twemoji": {
            "name": "Twitter Emoji",
            "total": 3988,
            "description": "Twitter's emoji set, colorful and widely recognized",
            "sample_icon": "grinning-face",
        },
        "noto": {
            "name": "Google Noto Emoji",
            "total": 3710,
            "description": "Google's comprehensive emoji set",
            "sample_icon": "grinning-face",
        },
        "emojione": {
            "name": "EmojiOne",
            "total": 1834,
            "description": "JoyPixels/EmojiOne colored emoji",
            "sample_icon": "grinning-face",
        },
        "fluent-emoji": {
            "name": "Fluent Emoji",
            "total": 3126,
            "description": "Microsoft's 3D-style emoji",
            "sample_icon": "grinning-face",
        },
        "fluent-emoji-flat": {
            "name": "Fluent Emoji Flat",
            "total": 1545,
            "description": "Microsoft's flat emoji variant",
            "sample_icon": "grinning-face",
        },
        "openmoji": {
            "name": "OpenMoji",
            "total": 4158,
            "description": "Open-source emoji project",
            "sample_icon": "grinning-face",
        },
        "fxemoji": {
            "name": "Firefox Emoji",
            "total": 1034,
            "description": "Mozilla Firefox emoji set",
            "sample_icon": "smilingfacewithsunglasses",
        },
        "streamline-emojis": {
            "name": "Streamline Emojis",
            "total": 816,
            "description": "Streamline's emoji collection",
            "sample_icon": "alien-1",
        },
        "noto-v1": {
            "name": "Noto Emoji (v1)",
            "total": 2038,
            "description": "Original Google Noto emoji",
            "sample_icon": "grinning-face",
        },
        "emojione-v1": {
            "name": "EmojiOne (v1)",
            "total": 1584,
            "description": "Original EmojiOne set",
            "sample_icon": "grinning-face",
        },
    }


def get_icon_sets() -> Dict[str, Dict]:
    """Curated general-purpose (non-emoji) Iconify sets, keyed by prefix."""
    return {
        "pepicons-pop": {
            "name": "Pepicons Pop",
            "total": 1275,
            "description": "Playful pop-style icons",
        },
        "game-icons": {
            "name": "Game Icons",
            "total": 4129,
            "description": "Icons for games and fantasy",
        },
        "mdi": {
            "name": "Material Design Icons",
            "total": 7447,
            "description": "Google Material Design icons",
        },
        "tabler": {
            "name": "Tabler Icons",
            "total": 5237,
            "description": "Minimal, beautiful icons",
        },
        "lucide": {
            "name": "Lucide",
            "total": 1500,
            "description": "Beautiful, consistent icons",
        },
        "carbon": {
            "name": "Carbon",
            "total": 2000,
            "description": "IBM Carbon Design System icons",
        },
        "ph": {
            "name": "Phosphor",
            "total": 7488,
            "description": "Flexible, beautiful icon family",
        },
        "ri": {
            "name": "Remix Icon",
            "total": 2860,
            "description": "Open-source neutral icon system",
        },
        "simple-icons": {
            "name": "Simple Icons",
            "total": 3000,
            "description": "Popular brand SVG icons",
        },
        "logos": {
            "name": "SVG Logos",
            "total": 1463,
            "description": "Company and product logos",
        },
    }


def clear_cache() -> None:
    """Drop both the on-disk cache and the in-process memoisation."""
    directory = _cache_dir()
    if directory.exists():
        for cache_file in directory.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError:
                pass
    get_all_collections.cache_clear()
    get_collection_info.cache_clear()
