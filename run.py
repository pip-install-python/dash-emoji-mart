"""dash-emoji-mart documentation site — emoji-mart on Dash 4, markdown-driven.

The shell is the dash-documentation-boilerplate AppShell (DMC header + navbar +
markdown-loaded docs). Each `docs/<slug>/<slug>.md` registers as a Dash page; the
body is rendered by markdown2dash and its `.. exec::docs.<slug>.example` directive
imports the sibling `example.py` to embed the live demo.

`pages/markdown.py` is the single source of routing — the examples themselves
carry no `dash.register_page` call.

This is the PUBLIC mirror of the dash-emoji-mart project, deployed at
https://emojimart.2plot.dev as a 2plot network satellite:

  * directory — lib/network_directory.py  → the cross-host graph in /llms.txt
  * ads       — lib/ad_client.py          → 2plot.dev/api/ad-network/serve
  * traffic   — lib/analytics_tracker.py  → the local ledger
                lib/traffic_rollup.py     → daily rollup from that ledger
                lib/satellite_reporter.py → 2plot.ai/api/satellite/traffic
                lib/pageview_beacon.py    → the SPA half of the ledger

Ads and traffic reporting are dormant without their env keys, so a plain
`python run.py` gives you the same local docs site either way. The directory is
always on — it needs no credentials.

Unlike the dash-leaflet2 sibling this app has NO auth layer and no admin control
board: every page here is public, so nothing is mark_hidden().

Run:
    python run.py                          # FastAPI backend (default)
    DASH_BACKEND=flask python run.py       # Flask fallback
    # open http://127.0.0.1:8050
"""

import os
import sys

from dotenv import load_dotenv

# Load env before Dash imports run — the satellite/ad keys are read at import.
load_dotenv()

# THE FORK POINT — claim this app's network identity before any hub-facing
# module imports.
#
# Every module that names this app (satellite_reporter, ad_client, hub_client,
# bulletin) carries its own fallback default, and after a template sync those
# defaults DISAGREE: lib/satellite_reporter.py is byte-copied from the
# boilerplate and its fallback therefore says "boilerplate", while this fork's
# other modules say "emojimart". An unset SATELLITE_APP_KEY then files THIS
# site's traffic under the TEMPLATE's row on the hub — found live on pannellum,
# 2026-08-21, and the same class as the flows-reported-as-boilerplate
# contamination already in the hub's history.
#
# Keeping the reporter byte-identical is the acceptance check for the whole
# sync (`shasum` against the boilerplate's copy), so the identity claim has to
# live out here instead. setdefault: a real value from the Render dashboard or
# .env always wins — this line only closes the unset gap.
#
# FORKS CHANGE THIS ONE STRING.
os.environ.setdefault("SATELLITE_APP_KEY", "emojimart")

import dash
from dash import Dash, _dash_renderer

# AI/LLM integration & SEO via dash-improve-my-llms.
from dash_improve_my_llms import (
    LLMSConfig,
    RobotsConfig,
    add_llms_routes,
    register_page_metadata,
)

from lib import network_directory
from lib.analytics_tracker import tracker
from lib.backend import get_backend_info, resolve_backend
from lib.constants import (
    APP_VERSION,
    BASE_URL,
    OG_IMAGE_ALT,
    OG_IMAGE_HEIGHT,
    OG_IMAGE_URL,
    OG_IMAGE_WIDTH,
    PUBLISHER,
    SAME_AS,
    SITE_BRAND,
    SITE_DESCRIPTION,
    SITE_TITLE,
    require_owned_base_url,
)

# ----------------------------------------------------------------------------
# Hard floor on dash-improve-my-llms. This is a startup ERROR, not a warning,
# because running below it produces a site that boots cleanly, looks perfect in
# a browser, and is broken in exactly the ways nobody looks at:
#
#   * < 2.2 uses ASSIGN semantics for register_page_metadata, so the root call
#     further down DELETES the home page's prose that pages/markdown.py just
#     registered. `/llms.txt` then serves
#     "_No `LLMS_DOC` registered for `/`._" — a stub on the single most valuable
#     URL on the site. Four sites in this fleet shipped that way for months.
#   * < 2.1 has no register_network, so lib/network_directory.apply() warns and
#     returns and the whole `## Network` section silently disappears.
#   * < 2.3.4 has no `resolve_site_title`, so the /llms.txt H1 and the llms
#     viewer's brand chip fall back to a nav label or Dash's own default
#     instead of SITE_BRAND — the site publishes an identity it never chose.
#
# All three failures are invisible unless you specifically fetch /llms.txt,
# which is how a stale interpreter went unnoticed here: a server started before
# the venv was rebuilt keeps its already-imported 2.0.0 in memory and happily
# serves the stub. Version drift this consequential should announce itself.
#
# 2.5.1 was the network's 402-instrumentation floor (1.3.x sync): it adds
# `configure_access` / `configure_viewer_identity` — what lib/access.py hands
# the tier policy to — and the tiered corpus documents (/llms-small.txt,
# /llms-full.txt) that the LLMS_SMALL_TIER / LLMS_FULL_TIER knobs govern.
# Below it the tier registrations further down are dead code and nothing says so.
#
#   * 2.6.1 makes the universal prerender visible to non-JS consumers: at
#     2.6.0 the injected block shipped with a literal `hidden` attribute, so
#     text extractors saw "Loading..." and nothing else while the prose sat in
#     the markup unread. Browsers were never affected — React's mount wipes the
#     block either way — which is exactly why it went unnoticed for so long.
#   * 2.6.0 is the gate-wave floor, and it belongs in this list for the same
#     reason as the rest: below it `lastmod=` on register_page_metadata is
#     swallowed into **kwargs and SILENTLY IGNORED, so every real date this
#     repo stamps in frontmatter is discarded and <lastmod> reverts to invented
#     build dates on every URL — a sitemap that lies daily, and the exact thing
#     2.6.0 exists to end. It also brings icon autodiscovery (this site still
#     declares configure_seo(icons=) explicitly; tests/test_seo_icons.py pins
#     that the two sets agree) and the JSON-LD publisher logo.
# ----------------------------------------------------------------------------
_DIMLL_FLOOR = (2, 6, 1)


def _check_dimll_version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        raw = version("dash-improve-my-llms")
    except PackageNotFoundError:  # pragma: no cover — import above would fail first
        raise RuntimeError("dash-improve-my-llms is not installed") from None

    # Compare only the numeric release segment; a dev/rc suffix is fine.
    parts = []
    for chunk in raw.split(".")[:3]:
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    if tuple(parts) < _DIMLL_FLOOR:
        floor = ".".join(str(n) for n in _DIMLL_FLOOR)
        raise RuntimeError(
            f"dash-improve-my-llms {raw} is installed, but this site needs "
            f">= {floor}.\n"
            f"  Below {floor} the home page serves a stub to crawlers and the "
            f"network directory vanishes — both silently.\n"
            f"  Interpreter: {sys.executable}\n"
            f"  Fix: pip install -r requirements.txt   (and RESTART the server; "
            f"a running process keeps the old version in memory)"
        )
    return raw


DIMLL_VERSION = _check_dimll_version()

# Imported AFTER the floor fires, deliberately: on a pre-2.5.0 package this
# name does not exist, and the floor's diagnosis above is a far better error
# than a bare ImportError from the import block at the top of the file.
from dash_improve_my_llms import configure_seo  # noqa: E402

# ----------------------------------------------------------------------------
# Pluggable backend (Dash 4.1+). FastAPI by default; DASH_BACKEND=flask is what
# the Docker image uses, because gunicorn serves WSGI and FastAPI is ASGI.
# ----------------------------------------------------------------------------
BACKEND = resolve_backend()
BACKEND_INFO = get_backend_info(BACKEND)

# DMC 2.x targets React 18.2; Dash 4 ships 18.3.1 — pin to keep DMC happy.
# The dash_emoji_mart bundle declares react ^18.2 as a peer, so it is fine either way.
_dash_renderer._set_react_version("18.2.0")

print(
    f"[dash-emoji-mart] v{APP_VERSION} on Dash {dash.__version__} "
    f"· dash-improve-my-llms {DIMLL_VERSION} · backend='{BACKEND}'"
)
# The interpreter path, because "which venv is this server actually running?"
# is the question a stale process makes you ask, and the answer is never
# visible from the browser.
print(f"[dash-emoji-mart] interpreter: {sys.executable}")

# ----------------------------------------------------------------------------
# Clerk satellite auth. MUST run BEFORE Dash(...) — register_clerk_auth
# installs @dash.hooks callbacks that fire during app construction, so calling
# it afterwards silently does nothing at all.
#
# Fully optional and OFF here today: with no CLERK_* keys in the environment
# this registers nothing and the site runs exactly as public as it always has.
# The wiring exists so the phase-4 flip is an env change on the service and not
# a redeploy of this file. See lib/auth.py, which also boot-guards the two
# CLERK_SATELLITE_SIGN_IN_REDIRECT mistakes (unset strands authenticated users
# on the primary; a truthy non-URL renders a 404ing Sign In button).
# ----------------------------------------------------------------------------
from lib import auth as _auth  # noqa: E402

CLERK_ENABLED = _auth.register()

# ----------------------------------------------------------------------------
# Dash app
# ----------------------------------------------------------------------------
_dash_kwargs = dict(
    use_pages=True,
    suppress_callback_exceptions=True,
    update_title=None,
    title=SITE_TITLE,
    index_string=open("templates/index.html").read(),
)

# `backend=` landed in Dash 4.2, NOT 4.1 as the release notes imply. The
# dash_emoji_mart PACKAGE only needs `dash>=4.1`, so this fallback is what lets
# the docs site keep running on the package's own support floor rather than
# quietly raising it.
try:
    app = Dash(__name__, backend=BACKEND, **_dash_kwargs)
except TypeError:
    print(
        f"[dash-emoji-mart] Dash {dash.__version__} has no `backend=` parameter "
        "(added in 4.2) — falling back to the bundled Flask backend."
    )
    BACKEND = "flask"
    BACKEND_INFO = get_backend_info(BACKEND)
    app = Dash(__name__, **_dash_kwargs)

app._backend_info = BACKEND_INFO

# dash-clerk-auth splits its setup either side of Dash(...): sessions, the
# /api/auth/* routes and per-request identity are wired here. No-op when off.
_auth.configure_app(app)

# ----------------------------------------------------------------------------
# AI/LLM & SEO configuration
# ----------------------------------------------------------------------------
# Public origin. Drives <link rel="canonical">, sitemap.xml and the absolute
# URLs in llms.txt — see lib/constants.py for why a production boot that never
# set its origin explicitly must refuse rather than claim this repo's default.
require_owned_base_url()
app._base_url = BASE_URL
# block_ai_training=True is the network-wide posture, and on 2.3.2/2.3.3 it is
# finally the safe one. The taxonomy was corrected so True disallows the genuine
# bulk training crawlers (GPTBot, ClaudeBot, CCBot) while still ALLOWING the
# user-initiated fetchers (Claude-User, Claude-SearchBot, ChatGPT-User,
# OAI-SearchBot) — so the old reason to run False, that True broke claude.ai
# fetches through the legacy aliases, is gone.
#
# This is what produces the >=2.3.3 fleet fingerprint the deploy battery checks:
#   ClaudeBot     -> Disallow    (bulk training)
#   OAI-SearchBot -> Allow       (user-initiated retrieval)
# The docs stay fully reachable by anything a person actually asked to fetch
# them; only unattended corpus scraping is refused. Flip the flag and this
# comment together if that ever changes.
# ----------------------------------------------------------------------------
# Site identity for the CRAWLER document (dash-improve-my-llms >= 2.5.0).
#
# Until 2.5.0 the generated crawler HTML carried this page's content signals
# and none of its identity: a browser got the icon links, og:image and the
# twitter card from templates/index.html while Googlebot got none of them, on
# every host in this network — which is why search showed a generic globe next
# to a site that has had its own mark for months. Content may differ between
# the crawler document and the browser document; identity may not.
#
# It also claims the root icon paths (`root_icons`, on by default): /favicon.ico
# is where Google looks when a document declares no icon, and Dash's page
# catch-all was answering it with the app shell — 200 text/html where an image
# belongs, which is an actively poisoned fallback rather than a missing one.
# 2.6.0 redirects it to the .ico declared below, so this repo needs no second
# copy of that file at the assets root (see scripts/make_brand_assets.py, which
# explains why the duplicate that once lived there was removed).
configure_seo(
    icons=[
        # The SAME four files templates/index.html links, so the browser head
        # and the crawler head cannot drift apart — and deliberately the same
        # set 2.6.0's autodiscovery finds in assets/favicon/, which
        # tests/test_seo_icons.py pins as set-equality. That agreement is the
        # proof the fleet can eventually rely on discovery alone.
        #
        # These are this site's own names, not the boilerplate's
        # (`android-chrome-192x192.png` and friends): the pixels here are
        # already this app's, generated by scripts/make_brand_assets.py from
        # Noto's U+1F920, and renaming correct art to match a template would
        # buy nothing while breaking the generator, its --check guard and
        # tests/test_social_card.py. Discovery reads the sizes off these names
        # correctly (`favicon-192.png` -> 192x192).
        "/assets/favicon/favicon.ico",
        {"href": "/assets/favicon/favicon-192.png", "sizes": "192x192"},
        {"href": "/assets/favicon/favicon-512.png", "sizes": "512x512"},
        {"href": "/assets/favicon/apple-touch-icon.png",
         "rel": "apple-touch-icon", "sizes": "180x180"},
    ],
    social_image=OG_IMAGE_URL,
    social_image_alt=OG_IMAGE_ALT,
    social_image_width=OG_IMAGE_WIDTH,
    social_image_height=OG_IMAGE_HEIGHT,
    publisher=PUBLISHER,
    same_as=SAME_AS,
)

app._robots_config = RobotsConfig(
    block_ai_training=True,
    allow_ai_search=True,
    allow_traditional=True,
    crawl_delay=10,
)

# Root metadata. Safe to call AFTER pages/markdown.py has registered the home
# page's prose only because dash-improve-my-llms >= 2.2 MERGES here — 2.0's
# assign semantics made this exact call blank the home page's llms_doc, which
# is why four sites in the fleet were serving crawlers a "requires JavaScript"
# stub on their most valuable URL. The >=2.3.4 floor in requirements.txt is
# what keeps this call safe; do not lower it.
#
# `name=SITE_BRAND` is load-bearing beyond this page: dimll 2.3.4's
# `resolve_site_title` reads it for the /llms.txt H1 and the llms viewer's
# brand chip, and it SKIPS generic candidates — so a root registered as "Home"
# publishes Dash's default instead, silently.
# No `image_url=` here: this is dimll's prose registry, not Dash's page
# registry. The root's og:image comes from docs/home/home.md, which
# pages/markdown.py registers at "/" through `dash.register_page(image_url=...)`
# like every other page.
register_page_metadata(
    path="/",
    name=SITE_BRAND,
    description=SITE_DESCRIPTION,
)

# ----------------------------------------------------------------------------
# 2plot network directory — cross-host <link rel="related"> tags, the
# `## Network` section in /llms.txt, and followed links in the prerendered
# body. lib/network_directory.py is copied verbatim from the boilerplate so
# every satellite advertises the same graph; it strips this app from its own
# peer list. MUST precede add_llms_routes, which is what emits the directory.
# ----------------------------------------------------------------------------
network_directory.apply(BASE_URL)

# ----------------------------------------------------------------------------
# Pages: pages/markdown.py walks docs/**/*.md and registers each one. Dash's
# use_pages=True auto-imports everything under pages/ during Dash(...)
# construction, so it must NOT be imported again here — doing so registers
# every page twice, which surfaces as "Duplicate options are not supported"
# from the header's search Select.
# ----------------------------------------------------------------------------

# ----------------------------------------------------------------------------
# Native routes — mounted BEFORE add_llms_routes, which installs a catch-all
# that would otherwise claim them.
#
#   /healthz       the 2plot.ai hub's hourly sweep probes this; it is also
#                  render.yaml's healthCheckPath, so it must exist whether or
#                  not reporting is configured.
#   /api/pageview  the SPA page-view beacon's sink (lib/pageview_beacon.py).
# ----------------------------------------------------------------------------
from lib.health import register_health_route  # noqa: E402
from lib.pageview_beacon import register_pageview_beacon, register_routes  # noqa: E402

register_health_route(app, BACKEND)
register_routes(app, BACKEND)
register_pageview_beacon()

# ----------------------------------------------------------------------------
# Per-request analytics — ORDER IS LOAD-BEARING, and it differs by backend.
#
# The package's bot middleware SHORT-CIRCUITS AI crawlers (ClaudeBot,
# ChatGPT-User, PerplexityBot, ...) with its own response. Whichever hook runs
# second never sees them, and `bot_hits` in the rollup we POST to 2plot.ai is
# quietly too low — which is exactly the metric a docs site cares most about.
#
#   Flask/Quart: `before_request` hooks run in REGISTRATION order, so ours must
#                be registered BEFORE add_llms_routes (below).
#   FastAPI:     Starlette runs the LAST-added middleware OUTERMOST, so ours is
#                registered AFTER add_llms_routes (further down).
#
# Production runs Flask (DASH_BACKEND=flask in the Dockerfile, because gunicorn
# is WSGI), so the branch immediately below is the one that ships.
# ----------------------------------------------------------------------------
if BACKEND in ("flask", "quart"):
    from flask import request as _request  # noqa: E402

    @app.server.before_request
    def _track_visitor():
        try:
            # Headers are passed so the tracker reads the REAL client IP and
            # country from the proxy: behind Render, remote_addr is the proxy
            # and every visitor would geolocate to one datacentre.
            tracker.track_visit(
                _request.path,
                _request.headers.get("User-Agent", ""),
                _request.remote_addr,
                headers=dict(_request.headers),
            )
        except Exception:
            # Analytics must never turn into a 500 on a page being read.
            pass

# ----------------------------------------------------------------------------
# Network bulletin — hub-published tips and announcements, rendered in the
# header of the llms.txt viewer so a twenty-site network says "here is what
# changed" once instead of in twenty repositories.
#
# Configured BEFORE add_llms_routes, which is what mounts the viewer that reads
# it. Opt-in: with NETWORK_BULLETIN_URL unset this makes no request and the
# header still renders on the package's built-in defaults — which is exactly
# why it needs a boot line. An unwired bulletin has no failure mode, only an
# announcement that never appears, and the variable has to be set on the Render
# SERVICE because blueprint envVars apply on Blueprint sync, not on git-push
# autodeploys (LESSONS §10).
# ----------------------------------------------------------------------------
from lib import bulletin as _bulletin  # noqa: E402

BULLETIN_ENABLED = _bulletin.configure()
print(
    f"[dash-emoji-mart] network bulletin: {_bulletin.url()} "
    f"(app='{_bulletin.app_id()}')"
    if BULLETIN_ENABLED else
    "[dash-emoji-mart] network bulletin: off — set NETWORK_BULLETIN_URL="
    f"{_bulletin.HUB_BULLETIN_URL} to render the hub's announcements"
)

# ----------------------------------------------------------------------------
# Access control (dash-improve-my-llms 2.5+). Reads the tiers the pages just
# declared, so it must run after they are registered and before the routes are
# attached. Stays OFF unless some page declares a non-public tier — every page
# here is public today, so this wiring is inert instrumentation: it exists so
# the 402 experiment can tighten the corpus documents per-satellite via env
# (or the hub's page-tier ceilings) with no code change here. The policy and
# the reasoning live in lib/access.py.
# ----------------------------------------------------------------------------
from lib import access as _access  # noqa: E402
from lib import page_tiers as _page_tiers  # noqa: E402
from lib import page_visibility as _page_visibility  # noqa: E402

# Tiered corpus documents (dash-improve-my-llms >= 2.4.0). Pseudo-paths:
# they never enter dash.page_registry, so they cannot leak into listings —
# registering them here lets this satellite tier its compact briefing and
# full corpus via env (LLMS_SMALL_TIER / LLMS_FULL_TIER; unset = the
# default tier, i.e. public), and the hub can tighten either network-wide
# through its page-tier ceilings with no redeploy here. Inert on older
# package versions.
# The explicit `or "public"` matters: these registered under the
# PAGE_DEFAULT_TIER fallback before, which meant flipping that env to gate the
# INTERACTIVE site would silently gate the corpus documents too. Their tier is
# now always a deliberate setting and never an ambient default.
_page_tiers.register("/llms-small.txt",
                     os.environ.get("LLMS_SMALL_TIER") or "public")
_page_tiers.register("/llms-full.txt",
                     os.environ.get("LLMS_FULL_TIER") or "public")

# The home page's own tier, stated rather than inherited. docs/home/home.md
# declares no `tier` in its frontmatter, so under PAGE_DEFAULT_TIER=auth the
# front door would silently join the gate. The funnel's entrance stays public,
# always — a sign-in card on `/` is not a dark launch, it is an outage.
_page_tiers.register("/", "public")

# force= when either gate env is present. With every tier still public the
# auto-detect would skip the wiring entirely, but a host that flips by env
# needs the verdict plumbing — and the prerender's use of it — live during the
# DARK launch, not first exercised at the moment of the flip.
ACCESS_ENABLED = _access.configure(
    force=bool(os.environ.get("PAGE_DEFAULT_TIER")
               or os.environ.get("LLMS_PUBLIC_DEFAULT"))
)

# /llms.txt, /<page>/llms.txt, /robots.txt, /sitemap.xml, the universal
# prerender and the bot middleware. dash-improve-my-llms auto-detects the
# active backend and dispatches to the matching adapter.
#
# warn_missing_llms_doc=True on purpose: the warning names every page serving a
# stub body, which is the to-do list. Silencing it hides the list rather than
# clearing it — mark_hidden() anything genuinely internal instead.
add_llms_routes(app, LLMSConfig(warn_missing_llms_doc=True))

# The FastAPI mirror of the tracking hook above — see the ordering note there.
if BACKEND == "fastapi":
    from lib.asgi_middleware import register_asgi_middleware  # noqa: E402

    register_asgi_middleware(app)

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------
from components.appshell import create_appshell  # noqa: E402  (needs the registry)

app.layout = create_appshell(dash.page_registry.values())
server = app.server

# ----------------------------------------------------------------------------
# The person→agent handoff: /api/agent-key turns the browser's Clerk session
# into a portable `?key=` for copied llms.txt URLs (lib/agent_key.py, and the
# fetch in assets/llms_copy.js). 204 for everyone until Clerk and the hub are
# configured, so it is safe to mount unconditionally.
# ----------------------------------------------------------------------------
from lib.agent_key import register_agent_key_route  # noqa: E402

register_agent_key_route(app, BACKEND)

# The gate's boot line. Its PRESENCE is one of the four things the gate wave
# accepts a host on, read from the deploy log alone — the other three being the
# ABSENCE of the [visibility] and [auth] warnings. Printed even when everything
# is public, because "the wiring is present and says public" and "there is no
# wiring" are the two states this line exists to tell apart.
_non_public = sum(1 for t in _page_tiers.registered().values() if t != "public")
print(
    f"[emojimart] interactive gate: default tier "
    f"'{os.environ.get('PAGE_DEFAULT_TIER') or 'public'}', "
    f"{_non_public} non-public page(s), machine surfaces "
    f"{'GATED' if not _page_tiers.get_llms_public('/__probe__') else 'open'} "
    f"by default (LLMS_PUBLIC_DEFAULT), access wiring "
    f"{'ON' if ACCESS_ENABLED else 'off'}, control board at "
    f"/admin/control-board ({_page_visibility.override_count()} live "
    f"override(s))."
)

# ----------------------------------------------------------------------------
# Hourly signed traffic rollup POSTed to https://2plot.ai/api/satellite/traffic
# so the hub's owner-only /traffic dashboard can chart this app alongside the
# rest of the network. No-op without CROSS_APP_WEBHOOK_SECRET.
#
# Reports under SATELLITE_APP_KEY — "emojimart", this app's key in the hub's
# network directory.
#
# That key is claimed at the FORK POINT at the top of this file, not in the
# reporter. lib/satellite_reporter.py is byte-copied from the boilerplate and
# must STAY byte-identical (shasum against the template's copy is the sync's
# acceptance check), so its own fallback necessarily still reads "boilerplate";
# localising it here — which is what this site used to do — is exactly the edit
# the next template sync would silently revert, putting this app's traffic back
# on the boilerplate's hub row.
# ----------------------------------------------------------------------------
from lib.satellite_reporter import start_reporter  # noqa: E402

start_reporter()


if __name__ == "__main__":
    app.run(
        debug=os.getenv("DASH_DEBUG", "true").lower() not in ("0", "false", "no"),
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8050")),
    )
