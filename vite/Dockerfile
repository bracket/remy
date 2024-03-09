FROM alpine:latest as base

ENV ASDF_DIR /asdf

RUN apk add bash curl git \
    && git clone https://github.com/asdf-vm/asdf.git /asdf --branch v0.14.0

RUN . /asdf/asdf.sh \
    && apk add build-base sqlite zlib-dev bzip2-dev openssl-dev xz-dev linux-headers \
    && asdf plugin add python

RUN . /asdf/asdf.sh \
    && apk add gawk gpg \
    && asdf plugin add nodejs https://github.com/asdf-vm/asdf-nodejs.git


# NOTE: This RUN step builds node from scratch, which takes about 85 minutes on
# my machine.  The tarball in the next COPY/RUN is a precompiled version of the
# python and node interpreters but needs to be rebuilt when versions change.
# The tarball can be created with the 'tar_snapshot.sh' script
# 
# TODO: Check this compiles with optimization
#
# RUN . /asdf/asdf.sh \
#     && asdf install python 3.12.2 \
#     && asdf global python 3.12.2 \
#     && ASDF_NODEJS_FORCE_COMPILE=1 asdf install nodejs 21.6.2 \
#     && asdf global nodejs 21.6.2

RUN --mount=type=bind,target=/mnt/build \
    cd / && tar -xjvf /mnt/build/root_asdf.tbz2


# RUN --mount=type=bind,target=/mnt/build \
#    cd / && tar -xjvf /mnt/build/remy_vite.tbz2

COPY /vite /app

CMD sleep infinity
