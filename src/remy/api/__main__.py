"""
Entry point for running the Remy FastAPI HTTP API server.

Usage:
    python -m remy.api [--cache PATH] [--host HOST] [--port PORT]

The cache location can be provided via the --cache argument or the REMY_CACHE
environment variable.
"""

import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Remy FastAPI HTTP API server",
        prog="python -m remy.api",
    )
    parser.add_argument(
        "--cache",
        default=os.environ.get("REMY_CACHE", ""),
        help="Location of the Remy notecard cache (default: $REMY_CACHE)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5000, help="Bind port (default: 5000)")
    args = parser.parse_args()

    cache_path = args.cache
    if not cache_path:
        print(
            "Error: No cache location specified. "
            "Use --cache or set the REMY_CACHE environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load the notecard cache and inject it into the app module
    from pathlib import Path
    from remy import NotecardCache
    from remy.url import URL
    import remy.api.app as app_module

    url = URL(cache_path)
    if not url.scheme:
        url = URL(Path(cache_path))

    app_module.notecard_cache = NotecardCache(url)

    import uvicorn
    uvicorn.run(app_module.app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
