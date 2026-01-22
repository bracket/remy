FROM alpine:latest AS remy-vite

# Build mode: 'compile' to build from source, 'restore' to use snapshot
ARG BUILD_MODE=restore

ENV ASDF_DIR /asdf

RUN apk add bash curl git \
    && git clone https://github.com/asdf-vm/asdf.git /asdf --branch v0.14.0

RUN . /asdf/asdf.sh \
    && apk add build-base sqlite zlib-dev bzip2-dev openssl-dev xz-dev linux-headers \
    && asdf plugin add python

RUN . /asdf/asdf.sh \
    && apk add gawk gpg \
    && asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git

# Compile mode: Build Python and Node.js from source (takes ~85 minutes)
# This is used by the snapshot-builder service to create root_asdf.tbz2
RUN if [ "$BUILD_MODE" = "compile" ]; then \
        . /asdf/asdf.sh \
        && asdf install python 3.12.2 \
        && asdf global python 3.12.2 \
        && ASDF_NODEJS_FORCE_COMPILE=1 asdf install nodejs 21.6.2 \
        && asdf global nodejs 21.6.2; \
    fi

# Restore mode: Extract pre-built interpreters from snapshot (fast)
# This is the default mode used by standard builds
RUN if [ "$BUILD_MODE" = "restore" ]; then \
        --mount=type=bind,target=/mnt/build \
        cd / && tar -xjvf /mnt/build/root_asdf.tbz2; \
    fi

# RUN --mount=type=bind,target=/mnt/build \
#    cd / && tar -xjvf /mnt/build/remy_vite.tbz2

COPY vite/ /app

RUN . /asdf/asdf.sh \
    && cd /app \
    && npm install

CMD sleep infinity
