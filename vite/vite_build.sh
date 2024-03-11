#!/bin/bash

# /home/bracket/src/remy/src/remy/www
# /home/bracket/src/remy/vite


GIT_DIR="$(git rev-parse --show-toplevel)"
VITE_DIR="$GIT_DIR/src/remy/www/static/vite"

docker-compose run --volumes="$VITE_DIR:/app/dist" remy-vite
