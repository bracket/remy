"""Entry point for the Remy MCP server.

Run with:
    python -m remy.mcp

The server uses streamable-HTTP transport and listens on the host and port
configured via the REMY_MCP_HOST and REMY_MCP_PORT environment variables
(defaults: localhost:8080).  The MCP endpoint is available at /mcp.
"""

from . import mcp, MCP_HOST, MCP_PORT

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=MCP_HOST, port=MCP_PORT, path="/mcp")
