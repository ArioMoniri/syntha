# syntha — multi-stage Docker image.
#
# Build:   docker build -t syntha:dev .
# Run:     docker run --rm -v "$PWD:/data" syntha:dev \
#              generate --input /data/source.csv --output /data/out --n 1000
#
# The release-published image lives at ghcr.io/ariomoniri/syntha:<tag>
# (see .github/workflows/docker.yml).

# ── Stage 1: builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build deps for any wheels that need compilation (scipy/numpy
# usually ship wheels on linux/amd64, but cover the manylinux gap).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what's needed to install the package, in dependency-order so
# Docker layer-caches stay warm across iterative builds.
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install to a relocatable virtualenv so we can copy it into the runtime
# image without dragging build deps.
RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --upgrade pip \
    && pip install .

# ── Stage 2: runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    SYNTHA_DOCKER=1

# Tiny: just the venv + libstdc++ / libgomp that numpy/scipy link against
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Run as a non-root user — never run installers / pipelines as root.
RUN useradd --create-home --shell /bin/bash --uid 1000 syntha
USER syntha
WORKDIR /home/syntha

# Healthcheck — verifies syntha CLI is wired correctly.
HEALTHCHECK --interval=30s --timeout=5s --retries=2 \
    CMD syntha --version || exit 1

# Default entrypoint exposes the full CLI; subcommand comes from `docker run` args.
ENTRYPOINT ["syntha"]
CMD ["--help"]

LABEL org.opencontainers.image.source="https://github.com/ArioMoniri/syntha" \
      org.opencontainers.image.description="Synthea-inspired hybrid synthetic patient record generator" \
      org.opencontainers.image.licenses="Apache-2.0"
