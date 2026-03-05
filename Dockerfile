# ─── Shared base: Alpine + asdf ───────────────────────────────────────────────
FROM alpine:latest AS remy-base

ENV ASDF_DIR /asdf

RUN apk add bash curl git \
    && git clone https://github.com/asdf-vm/asdf.git /asdf --branch v0.14.0

# ─── Python-only stage (for remy-api and remy-mcp) ────────────────────────────
FROM remy-base AS remy-python

# Build mode: 'compile' to build from source, 'restore' to use snapshot
ARG BUILD_MODE=restore

RUN . /asdf/asdf.sh \
    && apk add build-base sqlite sqlite-dev zlib-dev bzip2-dev openssl-dev xz-dev linux-headers \
               ncurses-dev libffi-dev readline-dev \
    && asdf plugin add python

# Compile mode: Build Python from source
# Used by snapshot-builder-python to create root_asdf_python.tbz2
RUN if [ "$BUILD_MODE" = "compile" ]; then \
        . /asdf/asdf.sh \
        && asdf install python 3.13.11 \
        && asdf global python 3.13.11; \
    fi

# Restore mode: Extract pre-built Python from snapshot (fast)
RUN --mount=type=bind,target=/mnt/build \
    if [ "$BUILD_MODE" = "restore" ]; then \
        if [ ! -f /mnt/build/root_asdf_python.tbz2 ]; then \
            echo "ERROR: Snapshot file root_asdf_python.tbz2 not found in root directory."; \
            echo "Please run: docker compose run --rm snapshot-builder-python"; \
            echo "This will take approximately 85 minutes to compile Python."; \
            exit 1; \
        fi; \
        cd / && tar -xjvf /mnt/build/root_asdf_python.tbz2; \
    fi

COPY pyproject.toml setup.cfg requirements.txt /src/
COPY src/ /src/src/

RUN . /asdf/asdf.sh \
    && pip install /src

CMD sleep infinity

# ─── Node-only stage (for remy-vite) ──────────────────────────────────────────
FROM remy-base AS remy-vite

# Build mode: 'compile' to build from source, 'restore' to use snapshot
ARG BUILD_MODE=restore

RUN . /asdf/asdf.sh \
    && apk add gawk gpg \
    && asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git

# Compile mode: Build Node.js from source (takes ~85 minutes)
# Used by snapshot-builder-node to create root_asdf_node.tbz2
# Uses -j4 for parallel compilation
RUN if [ "$BUILD_MODE" = "compile" ]; then \
        . /asdf/asdf.sh \
        && export MAKE_OPTS="-j4" \
        && ASDF_NODEJS_FORCE_COMPILE=1 ASDF_NODEJS_CONCURRENCY=4 asdf install nodejs 24.13.0 \
        && asdf global nodejs 24.13.0; \
    fi

# Restore mode: Extract pre-built Node.js from snapshot (fast)
RUN --mount=type=bind,target=/mnt/build \
    if [ "$BUILD_MODE" = "restore" ]; then \
        if [ ! -f /mnt/build/root_asdf_node.tbz2 ]; then \
            echo "ERROR: Snapshot file root_asdf_node.tbz2 not found in root directory."; \
            echo "Please run: docker compose run --rm snapshot-builder-node"; \
            echo "This will take approximately 85 minutes to compile Node.js."; \
            exit 1; \
        fi; \
        cd / && tar -xjvf /mnt/build/root_asdf_node.tbz2; \
    fi

COPY vite/vite/ /app

RUN . /asdf/asdf.sh \
    && cd /app \
    && npm install

CMD sleep infinity
