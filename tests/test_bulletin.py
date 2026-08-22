"""The network bulletin wiring — `lib/bulletin.py`.

TEMPLATE FILE: satellites copy this verbatim.

The failure this exists to prevent already happened once, and it is the
quietest kind: the wiring sat COMMENTED OUT in `run.py` while
`NETWORK_BULLETIN_URL` was set in production. `configure_bulletin` is opt-in,
so an unwired app makes no request at all and the viewer header renders
perfectly well on the package's built-in defaults. Nothing errored, nothing
logged, no dashboard changed — the announcements simply never appeared, which
is not something anyone goes looking for.

These tests are deliberately about the WIRING rather than about rendering a
bulletin. The suite is secretless and offline (conftest pins
`NETWORK_BULLETIN_URL` to `""` and disables the geo lookup for the same
reason), so fetching a real bulletin here would make the suite depend on the
hub being up. What can be pinned offline is that the env var is read, that the
app identifies itself with the right directory key, and that the feature
fails open in both directions.
"""

from __future__ import annotations

import pytest

# Site suite, not package suite: these need the docs-site dependency set
# (requirements.txt). CI's package-only compat matrix installs just the wheel,
# and without this guard that matrix fails on an import error that says nothing
# about the package under test — LESSONS §19.
pytest.importorskip("dash_mantine_components")
pytest.importorskip("dash_improve_my_llms")

from conftest import REPO_ROOT
from lib import bulletin


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """conftest pins these empty; make each test state its own posture."""
    monkeypatch.delenv("NETWORK_BULLETIN_URL", raising=False)
    monkeypatch.delenv("NETWORK_BULLETIN_TTL_S", raising=False)


# ------------------------------------------------------------- the wiring --


def test_no_url_means_the_feature_is_off(monkeypatch):
    assert bulletin.url() is None
    assert bulletin.configure() is False


def test_an_empty_url_is_off_not_a_request_to_the_empty_string(monkeypatch):
    """Render writes `KEY=` for an unset variable; `""` must read as absent."""
    monkeypatch.setenv("NETWORK_BULLETIN_URL", "")
    assert bulletin.url() is None
    assert bulletin.configure() is False


def test_a_url_wires_the_package(monkeypatch):
    """The whole point: the env var must reach `configure_bulletin`."""
    seen = {}

    def fake(url=None, ttl=None, timeout=None, enabled=True, app_id=None):
        seen.update(url=url, ttl=ttl, app_id=app_id)

    monkeypatch.setattr("dash_improve_my_llms.configure_bulletin", fake)
    monkeypatch.setenv("NETWORK_BULLETIN_URL", bulletin.HUB_BULLETIN_URL)

    assert bulletin.configure() is True
    assert seen["url"] == bulletin.HUB_BULLETIN_URL
    assert seen["ttl"] == bulletin.DEFAULT_TTL_S


def test_the_ttl_is_configurable_and_floored(monkeypatch):
    """A tiny TTL would hammer the hub once per llms.txt view."""
    seen = {}
    monkeypatch.setattr(
        "dash_improve_my_llms.configure_bulletin",
        lambda **kw: seen.update(kw),
    )
    monkeypatch.setenv("NETWORK_BULLETIN_URL", bulletin.HUB_BULLETIN_URL)

    monkeypatch.setenv("NETWORK_BULLETIN_TTL_S", "1800")
    bulletin.configure()
    assert seen["ttl"] == 1800.0

    monkeypatch.setenv("NETWORK_BULLETIN_TTL_S", "5")
    bulletin.configure()
    assert seen["ttl"] == 60.0, "a 5s TTL would refetch on nearly every view"

    monkeypatch.setenv("NETWORK_BULLETIN_TTL_S", "not-a-number")
    bulletin.configure()
    assert seen["ttl"] == bulletin.DEFAULT_TTL_S, "junk must not raise at boot"


# ------------------------------------------------------------- identity ----


def test_the_app_id_is_this_satellite_not_the_template(monkeypatch):
    """A fork announcing itself as "boilerplate" gets the template's news.

    The hub scopes announcements by `?app=` and uses it to see which
    satellites actually render the bulletin, so a wrong key is wrong twice.
    """
    monkeypatch.setenv("SATELLITE_APP_KEY", "leaflet")
    assert bulletin.app_id() == "leaflet"


def test_the_fork_point_claims_this_repos_directory_key():
    """run.py owns the identity claim, and this pins the line that makes it.

    The gate wave moved this guarantee. lib/satellite_reporter.py is byte-copied
    from the boilerplate and must STAY byte-identical — `shasum` against the
    template's copy is the sync's acceptance check — so its own fallback reads
    "boilerplate" and always will. Localising it here, which is what this repo
    used to do, is precisely the edit the next template sync reverts silently,
    putting this app's traffic back on the boilerplate's hub row.

    So the claim lives at the FORK POINT in run.py instead: a setdefault that
    runs before any hub-facing import. A real env value still wins; the line
    only closes the unset gap. It is one string, it is easy to forget when
    forking, and its absence is invisible until someone reads the hub's board —
    which is the entire reason it is pinned from the test suite.
    """
    source = (REPO_ROOT / "run.py").read_text()
    assert 'os.environ.setdefault("SATELLITE_APP_KEY", "emojimart")' in source, (
        "run.py no longer claims this app's network identity — an unset "
        "SATELLITE_APP_KEY now files emojimart's traffic under the template's "
        "row on the hub."
    )


def test_the_donor_fallback_is_left_alone(monkeypatch):
    """The byte-copied reporter still says "boilerplate", and that is correct.

    Asserted rather than merely tolerated: a well-meaning future reader who
    "fixes" this fallback breaks the shasum acceptance check, and the failure
    surfaces a release later as traffic on the wrong hub row. The fork point
    above is the sanctioned fix; this is the guard rail beside it.
    """
    from lib import satellite_reporter

    monkeypatch.delenv("SATELLITE_APP_KEY", raising=False)
    assert satellite_reporter.app_key() == "boilerplate"


def test_the_app_id_matches_the_traffic_reporters(monkeypatch):
    """One notion of "which satellite am I", not two that can disagree."""
    from lib import satellite_reporter

    monkeypatch.setenv("SATELLITE_APP_KEY", "email")
    assert bulletin.app_id() == satellite_reporter.app_key()


def test_every_hub_surface_names_this_app_the_same_way(monkeypatch):
    """Ads, traffic and the bulletin all say "emojimart".

    Three modules present an identity to the hub and each has its own fallback,
    so they can drift apart without anything failing — the symptom is a column
    on /admin/ad-board that does not line up with /traffic, which nobody
    reconciles. That drift was live here: `ad_client.APP_ID` defaulted to
    "dash-emoji-mart" (the PyPI package name) while `satellite_reporter` and
    render.yaml already said "emojimart".

    lib/hub_client.py presents a fourth (the gate wave ported it); its own
    fallback already says "emojimart".
    """
    from lib import ad_client, satellite_reporter
    from lib.constants import APP_KEY

    # As a BOOTED app has them: run.py's fork point sets SATELLITE_APP_KEY
    # before any of these modules import, so this is the real deployed state
    # and not a contrivance. AD_APP_ID stays unset — ad_client falls back to
    # this repo's own APP_KEY, which is the drift this test was written for.
    monkeypatch.delenv("AD_APP_ID", raising=False)
    monkeypatch.setenv("SATELLITE_APP_KEY", "emojimart")

    assert APP_KEY == "emojimart"
    assert ad_client.APP_ID == "emojimart"
    assert satellite_reporter.app_key() == "emojimart"
    assert bulletin.app_id() == "emojimart"


def test_the_directory_key_is_not_the_package_name():
    """The two are different strings here, and only one is the hub's id.

    `dash-emoji-mart` is what you `pip install`; `emojimart` is the subdomain
    slug and the hub's directory key. STANDARD §5 wants the second everywhere
    a hub surface is addressed, and the ad client shipped the first.
    """
    from lib.constants import APP_KEY, SITE_SHORT_NAME

    assert APP_KEY == "emojimart"
    assert SITE_SHORT_NAME == "dash-emoji-mart"
    assert APP_KEY != SITE_SHORT_NAME


# ------------------------------------------------------------ fail-open ----


def test_a_broken_package_does_not_stop_the_boot(monkeypatch):
    """A hub feature must never be able to take the documentation down."""
    monkeypatch.setenv("NETWORK_BULLETIN_URL", bulletin.HUB_BULLETIN_URL)

    def explode(**_kwargs):
        raise RuntimeError("hub client blew up")

    monkeypatch.setattr("dash_improve_my_llms.configure_bulletin", explode)
    with pytest.raises(RuntimeError):
        # Documenting the CURRENT contract honestly: configure() does not
        # swallow this. It runs at import time, before any request is served,
        # so a raise here is a loud boot failure rather than a broken page —
        # which is the right trade for a misconfiguration. The fail-open that
        # matters is at FETCH time, and that lives inside the package.
        bulletin.configure()


# --------------------------------------------------------------- run.py ----


def test_run_py_wires_it_rather_than_leaving_it_commented_out(app_module):
    """The regression itself.

    The suite boots secretless, so the flag is False here — what is asserted
    is that `run.py` EXPOSES the decision at all. Commented-out wiring cannot
    define this name, so this test fails the moment someone comments it out
    again.
    """
    assert hasattr(app_module, "BULLETIN_ENABLED")
    assert app_module.BULLETIN_ENABLED is False, (
        "conftest pins NETWORK_BULLETIN_URL empty; a True here means the "
        "suite is reaching the hub"
    )


def test_the_documented_hub_endpoint_is_the_one_the_hub_serves():
    """`.env.example` and the boot message both quote this constant."""
    assert bulletin.HUB_BULLETIN_URL == "https://2plot.dev/api/network/bulletin"
