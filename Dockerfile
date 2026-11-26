# =============================================================================
# Open Revoke: one Dockerfile that builds everything
#
# Targets:
#   app          backend (API, worker, migrations) and frontend in one container
#   backend-dev  backend with ruff, code mounted from the host (compose.dev.yaml)
#   browser      Chromium on Xvnc with noVNC and CDP (browser connectors)
#
# PostgreSQL and Redis are official images (compose.yaml). No time zone is baked
# in: TZ comes from .env (install.sh takes it from the host), default UTC.
# Version: --build-arg OPEN_REVOKE_VERSION=0.1.0 (scripts/build-release.sh).
#
# The build context is this folder.
# =============================================================================


# --- Source of the Bun binary (copied into the final image) -----------------
FROM oven/bun:1.4.5@sha256:3aa040e5445efa09d75bb428a64ba50db13e2b3ac9b6b0c7f145615f62b2ee18 AS bun-binary


# --- Frontend build: Next.js in standalone mode ------------------------------
# IMPORTANT: the work directories of the build stages must match the paths in
# the final image. The uv virtual environment writes absolute paths into
# shebangs, so moving it to another directory breaks it.
FROM oven/bun:1.4.5@sha256:3aa040e5445efa09d75bb428a64ba50db13e2b3ac9b6b0c7f145615f62b2ee18 AS frontend-build

USER root
WORKDIR /app/frontend

ENV NODE_ENV=production

# Dependencies first: a separate, cached layer
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build


# --- Backend build: Python dependencies and the app code --------------------
FROM ghcr.io/astral-sh/uv:0.13.10-python3.14-trixie-slim@sha256:b093dbbd7963c765325ecdf866d42915f5327e135569f9dae9c77cac63559bf2 AS backend-build

WORKDIR /app/backend

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Dependencies first: a separate, cached layer
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY backend/ ./
RUN uv sync --frozen --no-dev


# --- Backend dev: hot reload with the code mounted from the host ------------
# Used by the development stack (compose.dev.yaml): api runs `uvicorn --reload`, worker runs under `watchfiles`. The venv
# lives outside the mounted /app/backend (/opt/venv) so the mount does not hide
# it. The services run `uv sync --frozen` at start, so a new dependency needs
# only a restart of the service, not a rebuild.
# libatomic1: the Node.js driver bundled with playwright (connect_over_cdp).
FROM ghcr.io/astral-sh/uv:0.13.10-python3.14-trixie-slim@sha256:b093dbbd7963c765325ecdf866d42915f5327e135569f9dae9c77cac63559bf2 AS backend-dev

ENV TZ=UTC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update \
    && apt-get install --yes --no-install-recommends tzdata libatomic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project


# --- Final image: backend and frontend under one supervisor ----------------
FROM ghcr.io/astral-sh/uv:0.13.10-python3.14-trixie-slim@sha256:b093dbbd7963c765325ecdf866d42915f5327e135569f9dae9c77cac63559bf2 AS app

ENV TZ=UTC \
    PYTHONUNBUFFERED=1 \
    NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    PATH="/app/backend/.venv/bin:${PATH}"

# libatomic1: the Node.js driver bundled with the playwright package needs it
# (connect_over_cdp to the browser container; no browser is downloaded here).
RUN apt-get update \
    && apt-get install --yes --no-install-recommends tzdata supervisor libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Fixed ids: the Helm chart runs the container as this user (runAsNonRoot needs a numeric user).
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app app

# pip is not used at runtime: uv installs the dependencies at build time and
# the app starts from the ready venv (/app/backend/.venv). Removing pip removes
# its vendored libraries, which bring CVEs with them.
RUN rm -rf /usr/local/lib/python3.14/site-packages/pip \
           /usr/local/lib/python3.14/site-packages/pip-*.dist-info \
    && rm -f /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.14

# JS runtime: a single binary, no full Node or Bun image
COPY --from=bun-binary /usr/local/bin/bun /usr/local/bin/bun

# Backend: code and the ready virtual environment
COPY --from=backend-build --chown=app:app /app/backend /app/backend

# Frontend: output of `next build --output standalone`
COPY --from=frontend-build --chown=app:app /app/frontend/.next/standalone /app/frontend
COPY --from=frontend-build --chown=app:app /app/frontend/.next/static /app/frontend/.next/static
COPY --from=frontend-build --chown=app:app /app/frontend/public /app/frontend/public

COPY docker/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Version last: a new number does not invalidate the cache of the layers above.
ARG OPEN_REVOKE_VERSION=dev
ENV OPEN_REVOKE_VERSION=${OPEN_REVOKE_VERSION}
LABEL org.opencontainers.image.title="Open Revoke" \
      org.opencontainers.image.version="${OPEN_REVOKE_VERSION}" \
      org.opencontainers.image.source="https://github.com/Take-Group/openrevoke" \
      org.opencontainers.image.licenses="MIT"

USER app
WORKDIR /app

# 8000: API (FastAPI), 3000: frontend (Next.js)
EXPOSE 8000 3000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["supervisord", "--nodaemon", "--configuration", "/etc/supervisor/supervisord.conf"]


# --- Browser: Chromium on Xvnc (TigerVNC), live view through noVNC -----------
# Debian trixie has the `chromium` package for arm64 and amd64 (Google Chrome is
# amd64 only). CDP: 127.0.0.1:9222 in the container, socat exposes it on :9223 in
# the compose network. noVNC: :6080. Details and traps: skills/backend/browser.md.
FROM debian:trixie-slim@sha256:8aa5a7bf5a1955bddbe7d74fcdd0b91ab30e74362a8b73af672b0481b35b44a0 AS browser

ENV TZ=UTC \
    DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:99 \
    LANG=C.UTF-8

# Debian packages from docker/browser/packages.txt. BROWSER_PACKAGES_HASH is a hash of the package
# versions apt would install now (scripts/browser-packages-key.sh, passed by the release
# workflows): the same key reuses the cached layer, a new Chromium or any other Debian fix changes
# the key and rebuilds it. Without the key (a local build) Docker's cache decides as usual.
ARG BROWSER_PACKAGES_HASH=local
COPY docker/browser/packages.txt /tmp/browser-packages.txt
RUN echo "Debian packages key: $BROWSER_PACKAGES_HASH" \
    && apt-get update \
    && xargs -a /tmp/browser-packages.txt apt-get install --yes --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* /tmp/browser-packages.txt

# /profile is the mount point of the `browser-profile` volume. A new named
# volume copies the owner of this directory, so the non-root user can write it.
RUN groupadd --gid 1000 browser \
    && useradd --uid 1000 --gid browser --create-home --home-dir /home/browser browser \
    && mkdir -p /profile /tmp/.X11-unix \
    && chown browser:browser /profile \
    && chmod 1777 /tmp/.X11-unix

COPY docker/browser/supervisord.conf /etc/supervisor/browser.conf
# The panel's live view: the screen only, without noVNC's menu (served next to vnc.html).
COPY docker/browser/live.html /usr/share/novnc/live.html
# Chromium policies: Google as the search engine (Debian's build defaults to DuckDuckGo).
COPY docker/browser/chromium-policies.json /etc/chromium/policies/managed/open-revoke.json
# start-chromium.sh and policy-sync.sh (run as the browser user) write password-manager.json
# here from the panel API, so the managed-policy directory must be writable by them.
RUN chown browser:browser /etc/chromium/policies/managed
COPY docker/browser/entrypoint.sh docker/browser/start-chromium.sh docker/browser/start-wm.sh \
     docker/browser/apply-password-manager.sh docker/browser/policy-sync.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/start-chromium.sh /usr/local/bin/start-wm.sh \
    /usr/local/bin/apply-password-manager.sh /usr/local/bin/policy-sync.sh

USER browser
WORKDIR /home/browser

# 6080: noVNC (for the live view proxy in the API; the dev stack publishes it on 127.0.0.1:18412), 9223: CDP for the compose network
EXPOSE 6080 9223

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=6 \
    CMD curl -fsS http://127.0.0.1:9222/json/version > /dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["supervisord", "--nodaemon", "--configuration", "/etc/supervisor/browser.conf"]
