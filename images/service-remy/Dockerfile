# service-remy: remy installed at a pinned version from the private devpi index,
# on the relocatable CPython runtime base. Self-contained — the package (and its
# dependencies) are baked in at build time, so the running container does not need
# devpi reachable.
FROM ghcr.io/bracket/base-service-python:1.0.0

ARG REMY_VERSION

# The authenticated devpi extra-index URL (token embedded) arrives via a
# BuildKit secret, mounted only for this RUN. It is sourced into the shell so
# pip picks it up as PIP_EXTRA_INDEX_URL from the environment — neither the URL
# nor the token appears in build-args or `docker history`. PIP_TRUSTED_HOST is
# required because the tunnelled index is served over http.
RUN --mount=type=secret,id=build_env \
    . /run/secrets/build_env \
    && export PIP_EXTRA_INDEX_URL \
    && PIP_TRUSTED_HOST=host.docker.internal \
       pip install --no-cache-dir "remy==${REMY_VERSION}"

# The image ships remy importable with both entry points (remy.api, remy.mcp)
# available; the compose file selects which one to run per service via `command`.
CMD ["sleep", "infinity"]
