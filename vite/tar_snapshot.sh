#!/usr/bin/env bash

CONTAINER="$1"

if [ -z "$CONTAINER" ]; then
    echo "Must specify a container"
    exit 1
fi

docker exec "$CONTAINER" tar -cvjf /root_asdf.tbz2 /root/.asdf /root/.tool-versions \
    && docker cp "$CONTAINER:/root_asdf.tbz2" root_asdf.tbz2 \
    && docker exec "$CONTAINER"  rm -f /root_asdf.tbz2
