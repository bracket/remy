"""
Remy MCP Server.

Exposes Remy's notecard management functionality to LLM clients through
standardized MCP tools.  All communication with the Remy backend goes
through the FastAPI HTTP API; this module does not import Remy Python
modules directly.

Configuration (environment variables):
    REMY_API_URL       — Base URL of the Remy FastAPI backend (default: http://localhost:5000)
    REMY_MCP_TIMEOUT   — HTTP request timeout in seconds (default: 30)
    REMY_MCP_LOG_LEVEL — Logging level (default: WARNING)
    REMY_MCP_HOST      — Host to bind the MCP server to (default: localhost)
    REMY_MCP_PORT      — Port to bind the MCP server to (default: 8080)
"""

import logging
import os
from typing import Optional

import httpx
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL: str = os.environ.get("REMY_API_URL", "http://localhost:5000")
TIMEOUT: float = float(os.environ.get("REMY_MCP_TIMEOUT", "30"))
LOG_LEVEL: str = os.environ.get("REMY_MCP_LOG_LEVEL", "WARNING").upper()
MCP_HOST: str = os.environ.get("REMY_MCP_HOST", "localhost")
MCP_PORT: int = int(os.environ.get("REMY_MCP_PORT", "8080"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.WARNING))
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP("remy-mcp")

# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

_client: Optional[httpx.Client] = None


def get_client() -> httpx.Client:
    """Return a persistent HTTP client with connection pooling."""
    global _client
    if _client is None:
        _client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)
    return _client


# ---------------------------------------------------------------------------
# Error handling helper
# ---------------------------------------------------------------------------

def handle_api_response(response: httpx.Response):
    """Raise an appropriate Python exception for non-2xx API responses."""
    if response.status_code == 404:
        detail = response.json().get("detail", "Resource not found")
        raise ValueError(detail)
    if response.status_code in (400, 422):
        detail = response.json().get("detail", "Bad request")
        raise ValueError(detail)
    if response.status_code >= 500:
        detail = response.json().get("detail", "Server error")
        raise RuntimeError(detail)
    response.raise_for_status()
    return response.json()


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def query_notecards(
    query: Optional[str] = None,
    all: bool = False,
    order_by: str = "id",
    reverse: bool = False,
    limit: Optional[int] = None,
    fields: Optional[str] = None,
) -> list:
    """Search for notecards using the Remy query language.

    Use this tool to find notecards by field values (e.g., tags, status,
    priority), date ranges, or complex boolean expressions. Returns notecard
    labels, all labels, and the full raw text of each matching card.

    Exactly one of `query` or `all=True` must be provided.

    Args:
        query: Query expression (e.g., "tag = 'inbox'"). See query language guide.
        all: Return all notecards. Mutually exclusive with `query`.
        order_by: Sort key: "id" (primary label) or any field name (e.g., "created").
        reverse: Reverse the sort order.
        limit: Maximum number of results to return. Must be >= 1.
        fields: Comma-separated field names to extract instead of full notecard text.
                Supports pseudo-fields @primary-label, @id, @label, @title, @first-block.
    """
    if not query and not all:
        raise ValueError("Provide either a query expression or set all=True")
    if query and all:
        raise ValueError("query and all are mutually exclusive")

    params: dict = {"format": "json", "order_by": order_by, "reverse": str(reverse).lower()}
    if query:
        params["q"] = query
    if all:
        params["all"] = "true"
    if limit is not None:
        params["limit"] = str(limit)
    if fields:
        params["fields"] = fields

    logger.debug("GET /api/query %s", params)
    response = get_client().get("/api/query", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def get_notecard(label: str) -> dict:
    """Retrieve a specific notecard by its exact label.

    Use this tool when you know the label of a notecard and want to read its
    full content. Returns the raw notecard text including all metadata fields.

    Args:
        label: The notecard label to retrieve.
    """
    logger.debug("GET /api/notecard/%s", label)
    response = get_client().get(f"/api/notecard/{label}")
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def list_field_indexes(include_all_fields: bool = False) -> list:
    """List all available field indexes configured in this Remy notecard collection.

    Field indexes are used in query expressions (e.g., `tag = 'work'`). Use
    this tool to discover what fields are available before writing a query.

    Args:
        include_all_fields: If True, also include field names found in notecard
            content that have no configured parser (may be slow for large caches).
    """
    params: dict = {}
    if include_all_fields:
        params["include_all_fields"] = "true"

    logger.debug("GET /api/index %s", params)
    response = get_client().get("/api/index", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def dump_field_index(
    index_name: str,
    mode: str = "full",
    unique: bool = False,
    limit: Optional[int] = None,
) -> list:
    """Retrieve the contents of a specific field index.

    Shows all (notecard label, field value) pairs. Useful for exploring what
    values are used for a particular field and which notecards have each value.
    Use `mode="values"` with `unique=True` to get a deduplicated list of all
    values in use for a field.

    Args:
        index_name: The field index name (case-insensitive; e.g., "TAG" or "tag").
        mode: Output mode: "full" (label+value pairs), "labels" (labels only),
              or "values" (values only).
        unique: Remove duplicate entries while maintaining sort order.
        limit: Maximum number of entries to return. Must be >= 1.
    """
    params: dict = {"mode": mode, "unique": str(unique).lower()}
    if limit is not None:
        params["limit"] = str(limit)

    logger.debug("GET /api/index/%s %s", index_name, params)
    response = get_client().get(f"/api/index/{index_name}", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def validate_field_index(index_name: str, show_details: bool = False) -> list:
    """Check for field parsing errors in a specific field index.

    Returns a list of notecards where the field value could not be parsed
    correctly. An empty array means no errors were found. Useful for
    diagnosing data quality issues before querying.

    Args:
        index_name: The field index name to validate (case-insensitive).
        show_details: If True, include the source file URI, field name, and
            raw field value in each error object.
    """
    params: dict = {}
    if show_details:
        params["show_line"] = "true"

    logger.debug("GET /api/index/%s/validate %s", index_name, params)
    response = get_client().get(f"/api/index/{index_name}/validate", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def list_macros(mode: str = "names", name: Optional[str] = None) -> list:
    """List all query macros configured for this Remy notecard collection.

    Macros are reusable query expressions that can be referenced in queries
    with `@macro_name` syntax. Use this tool to discover available macros
    before constructing a query.

    Args:
        mode: Display mode: "names" (macro names only), "full" (definitions),
              or "expand" (expanded definitions).
        name: Filter to a specific macro name (with or without leading "@").
    """
    params: dict = {"mode": mode}
    if name is not None:
        params["name"] = name

    logger.debug("GET /api/macro %s", params)
    response = get_client().get("/api/macro", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)


@mcp.tool()
def query_set(query: str) -> list:
    """Execute a query expression and return the raw set result.

    Use `values(field)` expressions to enumerate all unique values for a
    field. Use `labels(expr)` to get just the notecard labels matching a
    query. Returns PairSet results as arrays of [label, value] pairs, and
    LabelSet/ValueSet results as arrays of strings or values.

    Args:
        query: A query expression whose result is a set (e.g., `values(tag)`,
               `labels(tag='work')`).
    """
    params: dict = {"q": query, "format": "set"}

    logger.debug("GET /api/query %s", params)
    response = get_client().get("/api/query", params=params)
    logger.debug("Response: %d", response.status_code)
    return handle_api_response(response)
