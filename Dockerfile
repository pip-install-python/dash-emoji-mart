# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------------
# dash-emoji-mart documentation site (run.py) — production image for
# https://emojimart.2plot.dev.
#
# The component bundle (dash_emoji_mart/dash_emoji_mart.min.js) is committed, so
# no Node/webpack build is needed: this is a pure-Python image serving the
# pre-built Dash app with gunicorn. node_modules/ is excluded via .dockerignore.
# ---------------------------------------------------------------------------
FROM python:3.12-slim

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

# Dependencies first so this layer caches across app-code changes.
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

# Documentation only; the process actually binds to $PORT (below).
EXPOSE 8050

# run:server is the Flask WSGI callable (run.py: `server = app.server`).
# Shell form so ${PORT} / ${WEB_CONCURRENCY} expand when the container starts.
CMD gunicorn run:server --bind "0.0.0.0:${PORT}" --workers "${WEB_CONCURRENCY:-2}" --threads 4 --timeout 120 --access-logfile - --error-logfile -
