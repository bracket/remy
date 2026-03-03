# Remy MCP Server Specification

## Overview

This document defines the design, architecture, and implementation requirements for an MCP (Model Context Protocol) server for Remy. The MCP server exposes Remy's notecard management functionality to LLM clients through standardized MCP tools.

The MCP server acts as a bridge between MCP clients (LLM assistants and AI agents) and the Remy FastAPI HTTP API, translating MCP tool calls into appropriate HTTP requests and returning results in a format suitable for LLM consumption.

**Related documentation:**
- [`docs/api_specification.md`](api_specification.md) — The FastAPI HTTP API the MCP server consumes
- [`docs/query_language_guide.md`](query_language_guide.md) — Query language syntax and semantics
- [`docs/remy_config.md`](remy_config.md) — Configuration file format

---

## Architecture

```
LLM Client (Claude, GPT, etc.)
        │
        │  MCP Protocol (stdio / SSE)
        ▼
┌───────────────────┐
│   Remy MCP Server  │
│   (fast_mcp)       │
└─────────┬─────────┘
          │  HTTP (JSON)
          ▼
┌───────────────────┐
│  Remy FastAPI API  │
│  (remy.api)        │
└─────────┬─────────┘
          │  Python
          ▼
┌───────────────────┐
│  Remy Core Library │
│  (notecard cache,  │
│   query engine)    │
└───────────────────┘
```

The MCP server:
1. Receives tool invocations from an MCP client over the MCP protocol
2. Translates tool parameters into HTTP requests to the Remy FastAPI HTTP API
3. Formats the HTTP responses into MCP tool results suitable for LLM consumption
4. Propagates any errors from the FastAPI API back to the MCP client

The FastAPI HTTP API must be running independently before the MCP server starts. The MCP server is stateless; all notecard data lives in the FastAPI API layer.

---

## Configuration

The MCP server is configured via environment variables or a configuration file.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REMY_API_URL` | No | `http://localhost:5000` | Base URL of the Remy FastAPI HTTP API |
| `REMY_MCP_TIMEOUT` | No | `30` | HTTP request timeout in seconds |
| `REMY_MCP_LOG_LEVEL` | No | `WARNING` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Example Configuration

```bash
export REMY_API_URL=http://localhost:5000
export REMY_MCP_TIMEOUT=30
python -m remy.mcp
```

### Running the MCP Server

```bash
# Start the MCP server (communicates over stdio by default)
python -m remy.mcp

# With a custom API URL
REMY_API_URL=http://myserver:5000 python -m remy.mcp
```

The FastAPI backend must be started separately:

```bash
python -m remy.api
```

---

## MCP Tools

The MCP server exposes the following tools. Tool names follow MCP conventions (lowercase with underscores). All parameters and return values are JSON-serializable.

---

### 1. `query_notecards`

Query and filter notecards using the Remy query language. Returns matching notecards as structured JSON objects.

**Description for LLM:**
> Search for notecards using the Remy query language. Use this tool to find notecards by field values (e.g., tags, status, priority), date ranges, or complex boolean expressions. Returns notecard labels, all labels, and the full raw text of each matching card.

**Input parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | No¹ | — | Query expression (e.g., `tag = 'inbox'`). See the query language guide for syntax. |
| `all` | boolean | No¹ | `false` | Return all notecards. Mutually exclusive with `query`. |
| `order_by` | string | No | `"id"` | Sort key: `"id"` (primary label) or any field name (e.g., `"created"`). |
| `reverse` | boolean | No | `false` | Reverse the sort order. |
| `limit` | integer | No | — | Maximum number of results to return. Must be ≥ 1. |
| `fields` | string | No | — | Comma-separated field names to extract instead of full notecard text. Supports pseudo-fields `@primary-label`, `@id`, `@label`, `@title`, `@first-block`. |

¹ Exactly one of `query` or `all=true` must be provided.

**Return value schema (no `fields`):**

```json
[
  {
    "label": "<primary label>",
    "labels": ["<label1>", "<label2>"],
    "raw": "<full notecard text>"
  }
]
```

**Return value schema (with `fields`):**

```json
[
  {
    "<field_name>": ["<value1>", "<value2>"]
  }
]
```

Each object in the array represents one notecard. Each key is a requested field name, and its value is an array of parsed field values for that notecard. Date/datetime values are ISO 8601 strings.

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Neither `query` nor `all=true` provided | `"Provide either a query expression or set all=true"` |
| Both `query` and `all=true` provided | `"query and all are mutually exclusive"` |
| Invalid query syntax | Forwarded from the API: `"<parse error description>"` |
| `fields` combined with `format=set` | Not applicable (tool always uses `format=json`) |

**Example 1 — Find all inbox notecards:**

```json
{
  "tool": "query_notecards",
  "input": {
    "query": "tag = 'inbox'"
  }
}
```

```json
[
  {
    "label": "note-2024-01-15",
    "labels": ["note-2024-01-15"],
    "raw": "NOTECARD note-2024-01-15\n:TAG: inbox\n\nCall dentist tomorrow.\n"
  },
  {
    "label": "note-2024-01-20",
    "labels": ["note-2024-01-20"],
    "raw": "NOTECARD note-2024-01-20\n:TAG: inbox\n\nReview pull request #42.\n"
  }
]
```

**Example 2 — Find recent high-priority work items, extract labels and tags:**

```json
{
  "tool": "query_notecards",
  "input": {
    "query": "tag = 'work' AND priority <= 2",
    "order_by": "created",
    "reverse": true,
    "limit": 5,
    "fields": "@primary-label,tag,priority"
  }
}
```

```json
[
  {
    "@primary-label": ["urgent-task-42"],
    "tag": ["work", "urgent"],
    "priority": [1]
  }
]
```

---

### 2. `get_notecard`

Retrieve a single notecard by its label.

**Description for LLM:**
> Retrieve a specific notecard by its exact label. Use this tool when you know the label of a notecard and want to read its full content. Returns the raw notecard text including all metadata fields.

**Input parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `label` | string | Yes | The notecard label to retrieve. |

**Return value schema:**

```json
{
  "label": "<string>",
  "raw": "<string>"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | The label used to look up the notecard |
| `raw` | string | The full raw text of the notecard (including NOTECARD header and content) |

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Notecard not found | `"Notecard '<label>' not found"` |

**Example — Retrieve a specific notecard:**

```json
{
  "tool": "get_notecard",
  "input": {
    "label": "my-project-notes"
  }
}
```

```json
{
  "label": "my-project-notes",
  "raw": "NOTECARD my-project-notes\n:TAG: work\n:PRIORITY: 1\n:STATUS: active\n\nProject planning notes for Q1.\n"
}
```

---

### 3. `list_field_indexes`

List all configured field index names.

**Description for LLM:**
> List all available field indexes configured in this Remy notecard collection. Field indexes are used in query expressions (e.g., `tag = 'work'`). Use this tool to discover what fields are available before writing a query.

**Input parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_all_fields` | boolean | No | `false` | If true, also include field names found in notecard content that have no configured parser (may be slow for large caches). |

**Return value schema:**

```json
["<field_name_1>", "<field_name_2>"]
```

An alphabetically sorted array of field index names (uppercase, as defined in `PARSER_BY_FIELD_NAME`).

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Config file missing or invalid | Forwarded from the API |

**Example — List all configured field indexes:**

```json
{
  "tool": "list_field_indexes",
  "input": {}
}
```

```json
["CREATED", "PRIORITY", "STATUS", "TAG"]
```

---

### 4. `dump_field_index`

Retrieve the contents of a specific field index, showing which notecards have which values for a field.

**Description for LLM:**
> Retrieve the contents of a specific field index, showing all (notecard label, field value) pairs. Useful for exploring what values are used for a particular field and which notecards have each value. Use `mode="values"` with `unique=true` to get a deduplicated list of all values in use for a field.

**Input parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `index_name` | string | Yes | — | The field index name (case-insensitive; e.g., `"TAG"`, `"tag"`, or `"Tag"`). |
| `mode` | string | No | `"full"` | Output mode: `"full"` (label+value pairs), `"labels"` (labels only), or `"values"` (values only). |
| `unique` | boolean | No | `false` | Remove duplicate entries while maintaining sort order. |
| `limit` | integer | No | — | Maximum number of entries to return. Must be ≥ 1. |

**Return value schema (`mode="full"`):**

```json
[
  ["<label>", "<value>"],
  ...
]
```

**Return value schema (`mode="labels"` or `mode="values"`):**

```json
["<value1>", "<value2>", ...]
```

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Index not found | `"Field index '<index_name>' not found"` |
| Invalid mode | `"Invalid mode: '<mode>'. Must be full, labels, or values."` |

**Example — List all unique tag values in use:**

```json
{
  "tool": "dump_field_index",
  "input": {
    "index_name": "TAG",
    "mode": "values",
    "unique": true
  }
}
```

```json
["archive", "inbox", "personal", "work"]
```

**Example — Get all notecards with their tag values:**

```json
{
  "tool": "dump_field_index",
  "input": {
    "index_name": "TAG",
    "mode": "full"
  }
}
```

```json
[
  ["my-note", "inbox"],
  ["my-note", "work"],
  ["other-note", "archive"]
]
```

---

### 5. `validate_field_index`

Validate field parsing for a specific field index, returning any errors found.

**Description for LLM:**
> Check for field parsing errors in a specific field index. Returns a list of notecards where the field value could not be parsed correctly. An empty array means no errors were found. Useful for diagnosing data quality issues before querying.

**Input parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `index_name` | string | Yes | — | The field index name to validate (case-insensitive). |
| `show_details` | boolean | No | `false` | If true, include the source file URI, field name, and raw field value in each error object. |

**Return value schema:**

```json
[
  {
    "label": "<notecard primary label>",
    "error_type": "<exception class name>",
    "error_message": "<error description>",
    "uri": "<source file URI>",
    "field_name": "<field name>",
    "field_value": "<raw value that failed to parse>"
  }
]
```

Fields `uri`, `field_name`, and `field_value` are only present when `show_details=true`.

An empty array `[]` indicates no validation errors.

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Index not found | `"Field index '<index_name>' not found"` |

**Example — Validate the PRIORITY index:**

```json
{
  "tool": "validate_field_index",
  "input": {
    "index_name": "PRIORITY",
    "show_details": true
  }
}
```

```json
[
  {
    "label": "some-note",
    "error_type": "ValueError",
    "error_message": "invalid literal for int() with base 10: 'high'",
    "uri": "file:///path/to/notes/file.txt#42",
    "field_name": "PRIORITY",
    "field_value": " high"
  }
]
```

---

### 6. `list_macros`

List all configured query macros.

**Description for LLM:**
> List all query macros configured for this Remy notecard collection. Macros are reusable query expressions that can be referenced in queries with `@macro_name` syntax. Use this tool to discover available macros before constructing a query.

**Input parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | string | No | `"names"` | Display mode: `"names"` (macro names only), `"full"` (definitions), or `"expand"` (expanded definitions). |
| `name` | string | No | — | Filter to a specific macro name (with or without leading `@`). |

**Return value schema (`mode="names"`):**

```json
["@macro1", "@macro2"]
```

**Return value schema (`mode="full"` or `mode="expand"`):**

```json
[
  {
    "name": "@<macro_name>",
    "definition": "<definition string>"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Macro name with `@` prefix |
| `definition` | string | Full definition string (e.g., `@inbox := tag = 'inbox'`) |

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Specific `name` not found | `"Macro '@<name>' not found"` |
| Invalid mode | Forwarded from the API |

**Example — List all macro names:**

```json
{
  "tool": "list_macros",
  "input": {}
}
```

```json
["@archive", "@inbox", "@work"]
```

**Example — Show expanded definition of a single macro:**

```json
{
  "tool": "list_macros",
  "input": {
    "name": "inbox",
    "mode": "expand"
  }
}
```

```json
[
  {
    "name": "@inbox",
    "definition": "@inbox := tag='inbox'"
  }
]
```

---

### 7. `query_set`

Execute a query expression and return the raw set result (PairSet, LabelSet, or ValueSet). Useful for exploring relationships between notecards and field values without fetching full notecard content.

**Description for LLM:**
> Execute a query expression and return the raw set result. Use `values(field)` expressions to enumerate all unique values for a field. Use `labels(expr)` to get just the notecard labels matching a query. Returns PairSet results as arrays of [label, value] pairs, and LabelSet/ValueSet results as arrays of strings or values.

**Input parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | A query expression whose result is a set (e.g., `values(tag)`, `labels(tag='work')`). |

**Return value schema (PairSet result):**

```json
[["<label>", "<value>"], ...]
```

**Return value schema (LabelSet or ValueSet result):**

```json
["<value1>", "<value2>", ...]
```

**Errors:**

| Condition | Error message |
|-----------|---------------|
| Invalid query syntax | Forwarded from the API |

**Example — List all unique tag values:**

```json
{
  "tool": "query_set",
  "input": {
    "query": "values(tag)"
  }
}
```

```json
["archive", "inbox", "personal", "work"]
```

**Example — Get all (notecard, tag) pairs for work-tagged cards:**

```json
{
  "tool": "query_set",
  "input": {
    "query": "tag = 'work'"
  }
}
```

```json
[
  ["project-alpha", "work"],
  ["project-beta", "work"],
  ["urgent-task-42", "work"]
]
```

---

## Usage Examples

This section provides complete end-to-end examples showing how an LLM client might use multiple tools together to accomplish a task.

### Example 1 — Explore and query by tag

An LLM that wants to find work-related notecards might first discover available field indexes, then query:

```
Step 1: list_field_indexes({}) → ["CREATED", "PRIORITY", "STATUS", "TAG"]
Step 2: query_set({"query": "values(tag)"}) → ["archive", "inbox", "personal", "work"]
Step 3: query_notecards({"query": "tag = 'work'", "limit": 10}) → [...]
```

### Example 2 — Retrieve a specific notecard by label

```
Step 1: get_notecard({"label": "project-alpha"})
→ {"label": "project-alpha", "raw": "NOTECARD project-alpha\n:TAG: work\n:STATUS: active\n\nProject alpha planning notes.\n"}
```

### Example 3 — Discover macros and use them in a query

```
Step 1: list_macros({}) → ["@inbox", "@work"]
Step 2: list_macros({"name": "inbox", "mode": "expand"})
→ [{"name": "@inbox", "definition": "@inbox := tag='inbox'"}]
Step 3: query_notecards({"query": "@inbox AND status = 'active'"})
→ [...]
```

### Example 4 — Explore field values before querying

```
Step 1: dump_field_index({"index_name": "STATUS", "mode": "values", "unique": true})
→ ["active", "completed", "on-hold"]
Step 2: query_notecards({"query": "status = 'active'", "order_by": "created", "reverse": true})
→ [...]
```

### Example 5 — Check data quality before querying

```
Step 1: validate_field_index({"index_name": "PRIORITY"})
→ []   (no errors)
Step 2: query_notecards({
  "query": "tag = 'work' AND priority <= 2",
  "order_by": "priority",
  "fields": "@primary-label,priority,status"
})
→ [{"@primary-label": ["urgent-task-42"], "priority": [1], "status": ["active"]}]
```

### Example 6 — Complex multi-step query using query language functions

```
Step 1: query_notecards({
  "query": "tag = 'work' AND NOT status = 'completed'",
  "order_by": "created",
  "reverse": true,
  "limit": 20,
  "fields": "@primary-label,tag,status,priority"
})
→ [...]
```

---

## Implementation Notes

### Server Initialization

```python
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("remy-mcp")

API_BASE_URL = os.environ.get("REMY_API_URL", "http://localhost:5000")
TIMEOUT = float(os.environ.get("REMY_MCP_TIMEOUT", "30"))

def get_client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)
```

### Tool Registration Pattern

Each MCP tool should be implemented as a Python function decorated with `@mcp.tool()`. The `fast_mcp` framework handles JSON serialization and MCP protocol encoding automatically.

```python
@mcp.tool()
def get_notecard(label: str) -> dict:
    """Retrieve a specific notecard by its exact label."""
    with get_client() as client:
        response = client.get(f"/api/notecard/{label}")
        if response.status_code == 404:
            raise ValueError(f"Notecard '{label}' not found")
        response.raise_for_status()
        return response.json()
```

### Error Handling

All tools should follow this error handling pattern:

1. **404 Not Found**: Raise `ValueError` with a descriptive message (e.g., `"Notecard 'foo' not found"`).
2. **400 Bad Request**: Raise `ValueError` with the `detail` field from the API response.
3. **422 Unprocessable Entity**: Raise `ValueError` indicating invalid parameters.
4. **500 Internal Server Error**: Raise `RuntimeError` with the `detail` field from the API response.
5. **Connection errors**: Let `httpx` exceptions propagate; `fast_mcp` will convert them to MCP errors.

```python
def handle_api_response(response: httpx.Response) -> dict:
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
```

### HTTP Client Lifecycle

Use `httpx.Client` as a context manager within each tool call, or create a module-level client and reuse it. Using a persistent client with connection pooling is preferred for performance:

```python
_client = None  # type: Optional[httpx.Client]

def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT)
    return _client
```

### Logging

Use Python's standard `logging` module. Log all HTTP requests and responses at `DEBUG` level; log errors at `ERROR` level.

```python
import logging

logger = logging.getLogger(__name__)

# In each tool:
logger.debug("GET /api/notecard/%s", label)
logger.debug("Response: %d", response.status_code)
```

### Module Entry Point

```python
# src/remy/mcp/__main__.py

from . import mcp

if __name__ == "__main__":
    mcp.run()
```

This enables running the server with:

```bash
python -m remy.mcp
```

### Running the MCP Server

The MCP server communicates over stdio by default (the standard for MCP servers used with desktop LLM clients). For server-sent events (SSE) transport, `fast_mcp` supports additional transports via `mcp.run(transport="sse")`.

### Testing Strategy

**Unit tests**: Mock the HTTP client and test each tool's parameter mapping and error handling independently.

```python
import pytest
from unittest.mock import patch, MagicMock

def test_get_notecard_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "Notecard 'foo' not found"}

    with patch("remy.mcp.tools.get_client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        with pytest.raises(ValueError, match="Notecard 'foo' not found"):
            get_notecard("foo")
```

**Integration tests**: Start both the FastAPI server and the MCP server, and test the full round-trip using the MCP Python SDK client.

**Manual testing**: Use the MCP Inspector tool (`npx @modelcontextprotocol/inspector python -m remy.mcp`) to interactively test tools during development.

---

## Design Decisions

### MCP Server as API bridge, not direct Python integration

The MCP server communicates with the Remy FastAPI HTTP API rather than importing Remy Python modules directly. This design provides several benefits:

- **Separation of concerns**: The MCP server does not need to manage the notecard cache lifecycle (loading, invalidation) — the FastAPI API handles that.
- **Deployment flexibility**: The MCP server can run on a different machine from the Remy API if needed.
- **Testability**: The MCP server can be tested by mocking HTTP responses without instantiating a real notecard cache.
- **Consistency**: All clients (web interface, CLI, MCP) share the same API layer and benefit from any improvements made there.

The tradeoff is additional latency for each tool call (one local HTTP round-trip). For typical notecard sizes and query result sets, this latency is negligible.

### Exposing the query language directly

The MCP tools expose the Remy query language directly through the `query` parameter rather than providing high-level abstractions (e.g., separate `filter_by_tag`, `filter_by_status` tools). This decision was made because:

- **Expressiveness**: The query language is powerful and composable; abstractions would be either too narrow (missing combinations) or too broad (replicating the query language itself).
- **LLM capability**: Modern LLMs can learn and use a domain-specific query language effectively when given good documentation and examples.
- **Simplicity**: A small number of general tools is easier to maintain and document than many narrow tools.

The `list_field_indexes` and `list_macros` tools provide the LLM with discovery capabilities so it can construct appropriate query expressions.

### Separate `query_notecards` and `query_set` tools

Two tools handle query results: `query_notecards` (for full notecard content, `format=json`) and `query_set` (for raw set results, `format=set`). This split is motivated by:

- **Distinct use cases**: `query_notecards` is used when the LLM needs to read notecard content; `query_set` is used for metadata exploration (e.g., enumerating all tag values with `values(tag)`).
- **Return type clarity**: Merging both into one tool would require the LLM to understand conditional return types, which is harder to document and reason about.

### `dump_field_index` includes a `limit` parameter not in the HTTP API

The `dump_field_index` tool adds a `limit` parameter that is not present in the `GET /api/index/{index_name}` endpoint. This is implemented in the MCP server by requesting the full index and truncating the result before returning it to the LLM. Large field indexes (thousands of entries) can overwhelm LLM context windows; the `limit` parameter allows the LLM to request a manageable subset.

### No streaming in MCP tools

The Remy FastAPI API supports streaming (NDJSON) for large result sets. MCP tools are not streamed: the MCP server collects the full response before returning it to the LLM client. Streaming MCP tool results is not yet standardized in the MCP protocol (as of the time of this writing). When MCP streaming support matures, `query_notecards` and `dump_field_index` are the primary candidates for streaming.

### Authentication

The MCP server inherits the FastAPI API's no-authentication model. Both are intended for local or private network use. If deployed in an environment requiring authentication, an external reverse proxy should handle it at the API layer; the MCP server does not need to implement credentials separately.

---

## Future Enhancements

### Streaming tool results

When MCP streaming is standardized, `query_notecards` and `dump_field_index` should be updated to stream results as they arrive from the FastAPI API. This will allow LLM clients to process large result sets incrementally.

### Write operations

The current specification is read-only, mirroring the read-only FastAPI API. Future versions could expose notecard creation, modification, and deletion if the FastAPI API adds write endpoints.

### Resource exposure

In addition to tools, MCP supports "resources" — URIs that clients can read directly. Remy notecards could be exposed as MCP resources with URIs like `remy://notecard/<label>`, allowing LLM clients to attach notecards as context without calling a tool explicitly.

### Prompt templates

`fast_mcp` supports "prompt" objects that provide reusable conversation templates. Remy could expose prompt templates for common workflows, such as:

- `remy_search`: A prompt that guides the LLM through discovering field indexes, constructing a query, and summarizing results.
- `remy_audit`: A prompt for running field validation and summarizing data quality issues.

### Caching layer in MCP server

For frequently-repeated queries (e.g., listing field indexes), the MCP server could cache results with a short TTL to reduce latency. This is a micro-optimization and should only be considered if profiling shows the API round-trip is a bottleneck.

### Multi-cache support

The current design assumes a single Remy cache. If users maintain multiple separate notecard collections, the MCP server could be extended to support a `cache` parameter that selects among multiple configured FastAPI API instances.
