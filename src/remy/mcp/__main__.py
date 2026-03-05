"""Entry point for the Remy MCP server.

Run with:
    python -m remy.mcp

The server uses streamable-HTTP transport and listens on the host and port
configured via the REMY_MCP_HOST and REMY_MCP_PORT environment variables
(defaults: localhost:8080).  The MCP endpoint is available at /mcp.
"""

import uvicorn
from . import mcp, MCP_HOST, MCP_PORT

class FixAcceptHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            if headers.get(b"accept") == b"*/*":
                scope["headers"] = [
                    (b"accept", b"application/json, text/event-stream")
                    if k == b"accept" else (k, v)
                    for k, v in scope["headers"]
                ]
        await self.app(scope, receive, send)

class DebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Capture request
        method = scope.get("method", "?")
        path = scope.get("path", "?")
        headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
        print(f">>> {method} {path}")
        print(f"    Request headers: {headers}")

        # Capture request body
        request_body = b""
        async def capture_receive():
            nonlocal request_body
            message = await receive()
            if message.get("type") == "http.request":
                request_body += message.get("body", b"")
            return message

        # Capture response
        status_code = None
        response_headers = {}
        response_body = b""

        async def capture_send(message):
            nonlocal status_code, response_headers, response_body
            if message.get("type") == "http.response.start":
                status_code = message.get("status")
                response_headers = {
                    k.decode(): v.decode()
                    for k, v in message.get("headers", [])
                }
            elif message.get("type") == "http.response.body":
                response_body += message.get("body", b"")
            await send(message)

        await self.app(scope, capture_receive, capture_send)

        print(f"    Request body: {request_body.decode(errors='replace')}")
        print(f"<<< {status_code}")
        print(f"    Response headers: {response_headers}")
        print(f"    Response body: {response_body.decode(errors='replace')}")
        print()

def main():
    app = mcp.http_app(path="/mcp")
    app = FixAcceptHeaderMiddleware(app)
    app = DebugMiddleware(app)

    uvicorn.run(app, host=MCP_HOST, port=MCP_PORT)

if __name__ == "__main__":
    main()
