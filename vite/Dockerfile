FROM alpine:latest AS remy-vite

# Build mode: 'compile' to build from source, 'restore' to use snapshot
ARG BUILD_MODE=restore

ENV ASDF_DIR /asdf

RUN apk add bash curl git \
    && git clone https://github.com/asdf-vm/asdf.git /asdf --branch v0.14.0

RUN . /asdf/asdf.sh \
    && apk add build-base sqlite sqlite-dev zlib-dev bzip2-dev openssl-dev xz-dev linux-headers \
               ncurses-dev libffi-dev readline-dev \
    && asdf plugin add python

RUN . /asdf/asdf.sh \
    && apk add gawk gpg \
    && asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git

# Compile mode: Build Python and Node.js from source (takes ~85 minutes)
# This is used by the snapshot-builder service to create root_asdf.tbz2
# MAKE_OPTS can be set to control parallelism (e.g., -j2 to limit to 2 cores)
RUN if [ "$BUILD_MODE" = "compile" ]; then \
        . /asdf/asdf.sh \
        && asdf install python 3.13.11 \
        && asdf global python 3.13.11 \
        && ASDF_NODEJS_FORCE_COMPILE=1 MAKE_OPTS="${MAKE_OPTS:--j2}" asdf install nodejs 24.13.0 \
        && asdf global nodejs 24.13.0; \
    fi

# Restore mode: Extract pre-built interpreters from snapshot (fast)
# This is the default mode used by standard builds
RUN --mount=type=bind,target=/mnt/build \
    if [ "$BUILD_MODE" = "restore" ]; then \
        if [ ! -f /mnt/build/root_asdf.tbz2 ]; then \
            echo "ERROR: Snapshot file root_asdf.tbz2 not found in vite/ directory."; \
            echo "Please run: docker-compose run --rm snapshot-builder"; \
            echo "This will take approximately 85 minutes to compile Python and Node.js."; \
            exit 1; \
        fi; \
        cd / && tar -xjvf /mnt/build/root_asdf.tbz2; \
    fi

# RUN --mount=type=bind,target=/mnt/build \
#    cd / && tar -xjvf /mnt/build/remy_vite.tbz2

COPY vite/ /app

RUN . /asdf/asdf.sh \
    && cd /app \
    && npm install

CMD sleep infinity
