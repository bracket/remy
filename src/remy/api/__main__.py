"""
Entry point for running the Remy FastAPI HTTP API server.

Usage:
    python -m remy.api [--cache PATH] [--host HOST] [--port PORT]

The cache location can be provided via the --cache argument or the REMY_CACHE
environment variable. The bind host can be provided via --host or the
REMY_API_HOST environment variable (default: 127.0.0.1). The bind port can be
provided via --port or the REMY_API_PORT environment variable (default: 42625).
"""

import argparse
import logging
import os
import sys


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

     #raise RuntimeError(sys.argv)

    host = os.environ.get("REMY_API_HOST", "127.0.0.1")
    port = int(os.environ.get("REMY_API_PORT", "42625"))
    cache_path = os.environ.get("REMY_CACHE")

    if not cache_path:
        print(
            "Error: No cache location specified. "
            "Set the REMY_CACHE environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Register the cache URL so get_cache() can (re)load it on demand
    from pathlib import Path
    from remy.url import URL
    import remy.api.app as app_module

    url = URL(cache_path)
    if not url.scheme:
        url = URL(Path(cache_path))

    app_module._cache_url = url

    # Register SIGHUP handler and start the file system watcher
    resolved_path = str(url.path) if url.path else cache_path
    _observer = app_module.setup_cache_invalidation(resolved_path)

    import uvicorn
    try:
        uvicorn.run(app_module.app, host=host, port=port)
    finally:
        if _observer is not None:
            _observer.stop()
            _observer.join()


if __name__ == "__main__":
    main()
