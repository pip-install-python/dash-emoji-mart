import os

# ---------------------------------------------------------------------------
# Site identity — one string, every surface
# ---------------------------------------------------------------------------
# The network standard: a site states what it is, in the same words, on every
# surface an agent or a reader can reach. The surfaces, and what serves each:
#
#   Dash(title=SITE_BRAND)              -> <title>, and the fallback identity
#   register_page_metadata(path="/",    -> the /llms.txt H1 and the llms
#       name=SITE_BRAND)                   viewer's brand chip, both via
#                                          dash-improve-my-llms 2.3.4's
#                                          `resolve_site_title`
#   docs/home/home.md's opening `# `    -> the home page's own prose
#
# tests/test_site_identity.py pins all of them to this constant, because the
# failure is silent: `resolve_site_title` skips generic candidates ("Home",
# "Index", Dash's default "Dash"), so a site that never states its identity
# publishes a nav label or a framework default and nothing looks broken.
#
# Naming rules, from the network standard:
#   - the PACKAGE NAME leads, because for a component library the package IS
#     what a reader came to find. Same shape as leaflet.2plot.dev
#     ("dash-leaflet2 — Leaflet 2 maps for Dash") and email.2plot.dev
#     ("dash-email — email components for Dash"). The boilerplate keeps its
#     package name out of its brand for the opposite reason: nobody installs a
#     template;
#   - "Pip Install Python" is the BYLINE (who made it), never the site name.
SITE_BRAND = "dash-emoji-mart — emoji picker for Dash"

SITE_DESCRIPTION = (
    "dash-emoji-mart — an emoji picker for Plotly Dash 4. Wraps emoji-mart as "
    "a single Dash component: search, six skin tones, a frequently-used row, "
    "22 locales, custom image/GIF/SVG categories and any of Iconify's 150+ "
    "icon sets. The emoji data set ships inside the bundle, so the picker "
    "works offline and makes no requests of its own. By Pip Install Python."
)

# Resolves the fallback <title> in templates/index.html, which is what the
# served HTML carries when dash-improve-my-llms is not rewriting the title per
# page (LLMSConfig(prerender=False), the documented rollback).
APP_TITLE = SITE_BRAND

# Retained name — run.py has passed SITE_TITLE to Dash(title=) since 0.0.x and
# the two must not become separate strings that can disagree. One value.
SITE_TITLE = SITE_BRAND

# The brand without its tagline, for the places that prefix something else and
# would otherwise run past every platform's truncation point.
SITE_SHORT_NAME = "dash-emoji-mart"

# Prefixed to every per-page title (pages/markdown.py), and therefore NOT only
# a browser-tab string: Dash passes the page title straight into `og:title` and
# `twitter:title` (dash/_pages.py `_page_meta_tags`), so this is the headline
# on every share card the site produces. Derived rather than retyped so the two
# cannot drift apart; tests/test_site_identity.py pins the relationship.
PAGE_TITLE_PREFIX = f"{SITE_SHORT_NAME} | "

PRIMARY_COLOR = "yellow"

# Keep in step with pyproject.toml, package.json and dash_emoji_mart/
# package-info.json when cutting a release. scripts/check_release.py fails CI if
# these four ever drift apart.
APP_VERSION = "0.2.1"

# The upstream picker this component wraps, as pinned in package.json.
EMOJI_MART_VERSION = "5.6.0"

# ---------------------------------------------------------------------------
# This app's id on every 2plot hub surface
# ---------------------------------------------------------------------------
# The network rule (STANDARD §5) is ONE short id per app, and it is the
# directory key — the subdomain slug. Every hub-facing identifier folds to it:
# AD_APP_ID (ad network), SATELLITE_APP_KEY (traffic rollup), and the bulletin
# app_id. The hub folds legacy spellings at ingest (`canonical_app_id`), so an
# old build keeps working, but a repo that keeps two spellings alive is a repo
# whose /admin rows split in half the first time one of them is missed.
#
# This app's ad client defaulted to "dash-emoji-mart" — the PyPI package name,
# not the directory key — while the traffic reporter already said "emojimart".
APP_KEY = "emojimart"

# ---------------------------------------------------------------------------
# The network's internal-traffic contract
# ---------------------------------------------------------------------------
# The point of truth is https://2plot.ai/docs/satellite-analytics ("Internal
# traffic"): any request whose User-Agent contains INTERNAL_UA_TOKEN is 2plot
# network machinery talking to itself — the hub's hourly health sweep, CI smoke
# batteries, the heartbeat, this app's own server-to-server calls. It is
# counted NOWHERE.
#
# Two halves, and both are required for the contract to hold:
#
#   inbound  — every tracker drops a token-carrying request at WRITE time,
#              before device detection and before bot classification, so it
#              never reaches the ledger the hourly rollup is built from;
#   outbound — every call this host makes to another network host sends
#              INTERNAL_UA, so the far side can apply the same rule.
#
# The outbound half is the one that was missing here: lib/ad_client.py and
# lib/satellite_reporter.py both called 2plot hosts as bare `python-requests`,
# which the receiving tracker classifies as a bot — so every page view on this
# satellite was inflating 2plot.dev's `bot_hits`.
#
# The token string must stay byte-identical across the network; it mirrors
# 2plotai/lib/constants.py and pip-docs+/lib/constants.py.
INTERNAL_UA_TOKEN = "2plot-internal"
INTERNAL_UA = "2plot-internal/1.0 (+https://2plot.ai/docs/satellite-analytics)"


def internal_ua(caller: str = "") -> str:
    """``INTERNAL_UA`` with a caller suffix, e.g. ``"ad-client"``.

    The suffix is for reading logs on the far side; only the token matters to
    the contract, and it stays intact whatever the suffix says.
    """
    caller = (caller or "").strip()
    return f"{INTERNAL_UA} {caller}" if caller else INTERNAL_UA


# ---------------------------------------------------------------------------
# Public origin
# ---------------------------------------------------------------------------
# Drives <link rel="canonical"> on every page, the absolute URLs in sitemap.xml
# and the "this app" entry in /llms.txt — the single highest-consequence value
# in the repo. Point it at the wrong host and this site tells Google it is a
# duplicate of that one.
#
# TWO env names, on purpose. `APP_BASE_URL` is the network-wide name every
# other satellite reads (the boilerplate, leaflet, email, the hub) and it wins;
# `DASH_EMOJI_MART_BASE_URL` is this repo's original name and stays honoured
# because render.yaml has carried it since before the first deploy. Renaming in
# one place and not the other is how a host quietly starts advertising the
# wrong canonical origin (LESSONS §12) — so both stay live, one value.
DEFAULT_BASE_URL = "https://emojimart.2plot.dev"
BASE_URL = (
    os.environ.get("APP_BASE_URL")
    or os.environ.get("DASH_EMOJI_MART_BASE_URL")
    or DEFAULT_BASE_URL
).rstrip("/")


def require_owned_base_url(base_url: str = BASE_URL) -> None:
    """Fail fast in production when BASE_URL isn't this app's real origin.

    Only enforced when a hosting platform is detected (Render sets ``RENDER``;
    ``APP_ENV=production`` works anywhere else), so local development and the
    test suite are unaffected.

    Two failures are caught:

    1. **No base-URL env set in production.** A fork of this repo inherits
       ``DEFAULT_BASE_URL`` and quietly claims https://emojimart.2plot.dev as
       its canonical origin — Google then treats the fork as the original's
       duplicate, or worse, the other way around. There is no safe guess to
       make on a fork's behalf, so this raises. Either env name satisfies the
       check, because this repo honours both (see the block above).
    2. **A platform-generated hostname.** ``*.onrender.com`` /
       ``*.herokuapp.com`` still resolve after a custom domain is attached, so
       canonicals pointing there split link equity across two hostnames for as
       long as nobody notices.
    """
    in_production = bool(os.environ.get("RENDER") or os.environ.get("APP_ENV") == "production")
    if not in_production:
        return

    if not (os.environ.get("APP_BASE_URL") or os.environ.get("DASH_EMOJI_MART_BASE_URL")):
        raise RuntimeError(
            "APP_BASE_URL is not set. This app would serve "
            f"<link rel='canonical' href='{DEFAULT_BASE_URL}'> on every page, "
            "telling search engines it is a duplicate of dash-emoji-mart's "
            "documentation site. Set APP_BASE_URL to this deployment's real "
            "origin (e.g. https://emojimart.2plot.dev)."
        )

    for platform_host in ("onrender.com", "herokuapp.com", "railway.app", "fly.dev"):
        if platform_host in base_url:
            raise RuntimeError(
                f"APP_BASE_URL={base_url!r} is a platform-generated hostname. "
                "Canonical tags, sitemap.xml and llms.txt would all point at it "
                "instead of the custom domain, splitting link equity across two "
                "hosts. Set APP_BASE_URL to the public domain."
            )

# ---------------------------------------------------------------------------
# The social card
# ---------------------------------------------------------------------------
# Dash builds `og:image` and `twitter:image` for EVERY page from
# `register_page(image_url=...)`, and emits `content=""` when it finds neither
# an explicit URL nor an inferable asset (dash/_pages.py). An empty tag unfurls
# WORSE than no tag, because scrapers take the declared-but-blank value and
# render an empty card — and because Dash's tags land late in the document,
# that empty value beats any good static tag earlier in the head. So
# `image_url=` AND `description=` go at every single register_page call.
#
# THE CARD LIVES ON THE CDN, NOT IN assets/. Network rule, and it is about cold
# starts rather than tidiness: a card served by the app is fetched by the
# scraper at unfurl time, and on a cold free-tier container that request lands
# mid-wake and times out. The preview renders blank ONCE and the platform
# caches the miss — the first person to share the link poisons it for everyone.
# The CDN has no cold start.
#
# Rendered by `scripts/make_social_card.py` (1200x630 = 1.91:1, the Open Graph
# ideal, which also degrades cleanly into Twitter's 2:1 slot) and uploaded BY
# HAND to the Cloudflare bucket. There is no automated path to that bucket, and
# the upload must land and verify BEFORE this URL ships — a 404 card is worse
# than none, and `scripts/smoke_live.py::social_card_real_pixels` fails the
# deploy while it 404s, deliberately.
#
# The width and height MUST match the file. A declared size that disagrees is
# worse than declaring none, because the platform reserves that box and crops
# into it. tests/test_social_card.py pins these against templates/index.html,
# and smoke_live.py reads the real file's IHDR after every deploy — the only
# check that catches the CDN object being replaced with a different shape.
OG_IMAGE_URL = "https://cdn.2plot.ai/github_assets/emojimart.2plot.dev.png"
OG_IMAGE_WIDTH = 1200
OG_IMAGE_HEIGHT = 630
OG_IMAGE_TYPE = "image/png"
OG_IMAGE_ALT = SITE_BRAND

# 2plot network links, surfaced in the README and the docs header/navbar.
GITHUB_URL = "https://github.com/pip-install-python/dash-emoji-mart"
DISCORD_URL = "https://discord.gg/WEnZR35mrK"
YOUTUBE_URL = "https://www.youtube.com/channel/UC6Bmo0t0ZUpU_xKBYW0bJuQ"

# Populated by pages/markdown.py as it loads each documentation file; the
# "copy for LLMs" button reads the raw markdown back out of it.
NAME_CONTENT_MAP = {}

# Mantine style props, filtered out of the `.. kwargs::` prop tables so a
# component's own API is not buried under 60 inherited spacing shorthands.
PROPS_TO_EXCLUDE = [
    "unstyled",
    "m", "my", "mx", "mt", "mb", "ms", "me", "ml", "mr",
    "p", "py", "px", "pt", "pb", "ps", "pe", "pl", "pr",
    "bg", "c", "opacity",
    "ff", "fz", "fw", "lts", "ta", "lh", "fs", "tt", "td",
    "w", "miw", "maw", "h", "mih", "mah",
    "bgsz", "bgp", "bgr", "bga",
    "pos", "top", "left", "bottom", "right", "inset",
    "display", "flex",
]
