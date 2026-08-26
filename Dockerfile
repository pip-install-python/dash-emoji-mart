# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# dash-emoji-mart documentation site (run.py) — production image for
# https://emojimart.2plot.dev.
#
# The component bundle (dash_emoji_mart/dash_emoji_mart.min.js) is committed, so
# no Node/webpack build is needed: this is a pure-Python image serving the
# pre-built Dash app with gunicorn. node_modules/ is excluded via .dockerignore.
# ---------------------------------------------------------------------------
FROM python:3.14-slim

# PYTHONUNBUFFERED        -> stream logs straight to stdout (Render shows them live)
# PYTHONDONTWRITEBYTECODE -> no .pyc clutter in the image
# DASH_BACKEND=flask      -> WSGI backend served by gunicorn (not fastapi/ASGI)
# PORT                    -> local default; Render overrides this at runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DASH_BACKEND=flask \
    PORT=8050

WORKDIR /app

# Dependencies first so this layer caches across app-code changes — and that
# cache is a trap worth naming, because this repo has already fallen into it.
#
# Docker keys this layer on requirements.txt's CONTENTS. A commit that touches
# only application code is a cache hit: pip never re-resolves and the image
# silently keeps whatever version it was first built with. On 2026-08-22 a
# deploy meant to "pick up dash-improve-my-llms 2.6.1" shipped 2.6.0 for
# exactly this reason — the floor said `>=2.6.0`, which PERMITTED the new
# version without REQUIRING it.
#
# So: ship every dependency upgrade as a floor bump in requirements.txt, and
# grep the number first, because it lives in more than one place (run.py's
# _DIMLL_FLOOR and its boot message, and the tests that pin the requirements
# line). The bump IS the cache bust. The boot floor is the other half: it
# turns a stale image from a silent downgrade into a loud refusal to start.
#
# There is deliberately NO nodejs/npm in this image. The component bundle
# (dash_emoji_mart/dash_emoji_mart.min.js) is committed and CI rebuilds it as
# a separate job to prove the commit matches source, so nothing here needs a
# JS toolchain — this is a pure-Python image.
#
# requirements.txt contains `-e .`, which needs the package metadata and the
# package directory present at install time — hence the four COPYs rather than
# requirements.txt alone. dash_emoji_mart/ carries the committed JS bundle, so
# this is still a Node-free build.
#
# vendor/ is the fifth, and it is not optional: requirements.txt installs
# dash-clerk-auth from `./vendor/dash_clerk_auth-1.0.5.tar.gz` because that
# package has no PyPI release — the dist/ tarball IS the release. pip resolves
# that path against the BUILD CONTEXT's working directory, so without this line
# it reports the file as merely "looks like a filename" in a warning and then
# dies on the OSError several seconds later, which reads like a network problem
# and is not one.
COPY requirements.txt pyproject.toml MANIFEST.in README.md ./
COPY vendor/ ./vendor/
COPY dash_emoji_mart/ ./dash_emoji_mart/
RUN pip install --no-cache-dir -r requirements.txt

# markdown2dash 0.1.2 pins `gunicorn>=21.2.0,<22.0.0` — a markdown parser
# constraining a WSGI server, straight into the CVE-driven `gunicorn>=23` floor
# in requirements.txt (CVE-2024-6827, CVE-2024-1135). pip cannot satisfy both,
# so it is installed here WITHOUT its dependency set; every one it actually
# needs at runtime is already in the layer above. ci.yml asserts the resulting
# gunicorn version inside this image, which is what keeps the dodge honest.
RUN pip install --no-cache-dir --no-deps markdown2dash==0.1.2

# Copy the application. run.py resolves templates/, docs/, assets/, components/,
# lib/ and pages/ relative to the working directory, so it must run from /app —
# which it does under this WORKDIR.
COPY . .

# The Iconify loader caches API responses for 24h. Point it somewhere that
# exists and is writable in the container; without this it falls back to the
# system temp directory, which also works but is less obvious to operate.
ENV DASH_EMOJI_MART_CACHE_DIR=/tmp/iconify-cache

# The 2plot.ai hub sweeps /healthz hourly and render.yaml names it as this
# service's healthCheckPath; the container gets the same probe so an
# unhealthy process is visible to the orchestrator too, not only to the
# platform's external check.
#
# A python -c probe rather than the template's `curl -fsS`: this image
# apt-installs NOTHING (it is a pure-Python docs site — the component bundle
# is committed, so there is no Node layer either), and adding an apt layer
# for one probe binary costs a package index refresh and ~10MB on every
# build. python is already PID 1's interpreter. Sanctioned alternative in
# the 1.6.14 sync spec; recorded in DIVERGENCES.md.
#
# The probe and the CMD must agree on the port AND on what "empty" means.
# `os.environ.get('PORT', '8050')` returns '' for a var that is SET BUT
# EMPTY, while the shell's `${PORT:-8050}` treats empty as unset and uses
# the default — so `docker run -e PORT=` had gunicorn serving happily on
# 8050 while the probe requested `http://127.0.0.1:/healthz` and failed
# forever. The container reported unhealthy while being perfectly healthy,
# which is how an orchestrator restart-loops a working app. Measured, not
# reasoned: `docker inspect` said `healthy` for a normal run and `starting`
# -> failing for `-e PORT=`. `or` is the fix, because '' is falsy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+(os.environ.get('PORT') or '8050')+'/healthz', timeout=4).status==200 else 1)" || exit 1

# Documentation only; the process actually binds to $PORT (below).
EXPOSE 8050

# run:server is the Flask WSGI callable (run.py: `server = app.server`).
# Shell form so ${PORT} / ${WEB_CONCURRENCY} expand when the container starts
# — exec-form CMD never expands env, which is how a sibling image hardcoded
# its port no matter what the platform asked for (template 1.6.14).
#
# `${PORT:-8050}`, not bare `${PORT}`: the ENV above supplies the default for
# a normal run, but `docker run -e PORT= ` (or any orchestrator that passes
# the variable through empty) collapses the bind to "0.0.0.0:" and gunicorn
# dies at startup. The default belongs at the point of use.
CMD gunicorn run:server --bind "0.0.0.0:${PORT:-8050}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 120 --access-logfile - --error-logfile -
