"""Package-level tests — no browser, no server.

These cover the contract the generated component class is supposed to satisfy. The
documentation site is exercised separately by ``scripts/smoke_test.py``, which is what
CI runs against every supported Dash version.

    pip install pytest && pytest
"""

import json
import re
from pathlib import Path

import pytest

import dash_emoji_mart as dem

ROOT = Path(__file__).resolve().parent.parent


def test_exports_exactly_one_component():
    assert dem.__all__ == ["DashEmojiMart"]


def test_version_matches_pyproject():
    """__version__ is read from package-info.json, which npm regenerates.

    A bump that edits pyproject.toml but skips `npm run build:backends` publishes a
    distribution labelled with the new version whose __version__ still reports the old
    one. That is invisible until someone reports a bug against the wrong version.
    """
    declared = re.search(
        r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M
    ).group(1)
    assert dem.__version__ == declared


def test_js_dist_points_at_a_file_that_exists():
    """Dash serves the bundle by relative path; a missing file yields an empty div."""
    pkg_dir = Path(dem.__file__).parent
    assert dem._js_dist, "no JS resources registered"
    for entry in dem._js_dist:
        assert (pkg_dir / entry["relative_package_path"]).exists(), entry


def test_no_css_dist():
    """emoji-mart injects its own styles from inside the bundle."""
    assert dem._css_dist == []


@pytest.mark.parametrize(
    "prop",
    [
        # The 0.0.x contract dash-leaflet2 depends on.
        "value",
        # Added in 0.2.0.
        "selectedEmoji",
        "clickedOutside",
        "className",
        "style",
        "persistence",
        "persisted_props",
        "persistence_type",
        # Core emoji-mart surface.
        "custom",
        "categoryIcons",
        "categories",
        "perLine",
        "theme",
        "set",
        "locale",
    ],
)
def test_prop_is_available(prop):
    assert prop in dem.DashEmojiMart(id="probe").available_properties


@pytest.mark.parametrize(
    "prop", ["onEmojiSelect", "onClickOutside", "onAddCustomEmoji", "getSpritesheetURL"]
)
def test_function_props_are_gone(prop):
    """Removed in 0.2.0 — Dash cannot serialise a Python function, so these could
    only ever be None. Their continued absence is part of the API contract."""
    assert prop not in dem.DashEmojiMart(id="probe").available_properties


def test_pattern_matching_id_is_accepted():
    component = dem.DashEmojiMart(id={"type": "picker", "index": 3})
    assert component.id == {"type": "picker", "index": 3}


def test_component_serialises_with_custom_emojis():
    from dash import html
    from dash._utils import to_json

    layout = html.Div(
        dem.DashEmojiMart(
            id="picker",
            custom=[
                {
                    "id": "team",
                    "name": "Team",
                    "emojis": [
                        {
                            "id": "logo",
                            "name": "Logo",
                            "native": "",
                            "unified": "custom",
                            "skins": [{"src": "https://example.com/logo.png"}],
                        }
                    ],
                }
            ],
            categoryIcons={"team": {"svg": "<svg/>"}},
            persistence=True,
        )
    )
    payload = json.loads(to_json(layout))
    assert payload["props"]["children"]["type"] == "DashEmojiMart"


def test_click_outside_is_not_delegated_to_emoji_mart():
    """`onClickOutside` must NOT be handed to emoji-mart's Picker.

    Its handler fires whenever the event target is not exactly the picker root —
    so every emoji click reads as "outside" — and it binds during mount while the
    opening click is still bubbling, so it reports an outside click before the
    user has clicked anything. Wired to a popover that closed it on the same
    click that opened it. The component uses its own containment-tested,
    deferred listener instead; this guards against a refactor handing the prop
    back to emoji-mart.
    """
    source = (ROOT / "src" / "lib" / "components" / "DashEmojiMart.react.js").read_text()
    assert "onClickOutside: handleClickOutside" not in source
    assert "wrapperRef" in source, "the containment check needs a wrapper ref"
    assert "node.contains(event.target)" in source, "outside must mean outside the wrapper"


def test_examples_never_pass_categories_with_custom():
    """`categories` + `custom` only works on the first picker of a page's life.

    emoji-mart filters `categories` against a snapshot aliased on the first
    init(); later inits filter against a stale list that cannot contain custom
    ids, so every custom category is dropped. Any docs example doing both would
    render correctly on a cold load and empty afterwards — the kind of bug that
    depends on which page the reader opened first.
    """
    offenders = []
    for example in sorted((ROOT / "docs").glob("*/example.py")):
        source = example.read_text()
        # Only count real keyword arguments, not prose in comments/docstrings.
        code = "\n".join(
            line for line in source.splitlines() if not line.lstrip().startswith("#")
        )
        if "custom=" in code and re.search(r"^\s*categories=", code, re.M):
            offenders.append(example.relative_to(ROOT).as_posix())
    assert not offenders, f"pass one or the other, not both: {offenders}"


def test_iconify_cache_is_not_inside_the_package():
    """A pip-installed package lives in site-packages and is usually not writable.

    0.0.x cached Iconify responses to `Path(__file__).parent / ".iconify_cache"`, which
    silently failed (or worse, succeeded) depending on how the package was installed.
    """
    from dash_emoji_mart.iconify import _cache_dir

    assert not str(_cache_dir()).startswith(str(Path(dem.__file__).parent))


def test_iconify_conversion_shape(monkeypatch):
    """iconify_to_emoji_mart must emit exactly what `custom=` expects — checked
    against a stubbed API response so the test never touches the network."""
    from dash_emoji_mart import iconify

    monkeypatch.setattr(
        iconify,
        "get_collection_info",
        lambda prefix: {
            "title": "Test Set",
            "categories": {"Faces": ["grin", "wink"], "Hidden": ["secret"]},
        },
    )

    categories = iconify.iconify_to_emoji_mart("testset", exclude_categories=["hidden"])

    assert len(categories) == 1
    category = categories[0]
    assert category["id"] == "testset-faces"
    assert category["name"] == "Test Set: Faces"
    assert [e["id"] for e in category["emojis"]] == ["testset-grin", "testset-wink"]

    emoji = category["emojis"][0]
    assert emoji["skins"] == [{"src": "https://api.iconify.design/testset/grin.svg"}]
    assert emoji["native"] == ""
    assert emoji["unified"] == "custom"


def test_iconify_max_icons_per_category(monkeypatch):
    from dash_emoji_mart import iconify

    monkeypatch.setattr(
        iconify,
        "get_collection_info",
        lambda prefix: {"title": "Big", "categories": {"All": [f"i{n}" for n in range(50)]}},
    )
    (category,) = iconify.iconify_to_emoji_mart("big", max_icons_per_category=5)
    assert len(category["emojis"]) == 5


def test_iconify_survives_an_unreachable_api(monkeypatch):
    """A dead Iconify must cost an empty list, not an exception — a picker without
    its optional icon set beats a page that 500s."""
    from dash_emoji_mart import iconify

    monkeypatch.setattr(iconify, "get_collection_info", lambda prefix: {})
    assert iconify.iconify_to_emoji_mart(["twemoji", "noto"]) == []
