# Remy FastAPI HTTP API Specification

## Overview

This document defines the RESTful HTTP API for Remy, implemented using FastAPI. The API exposes the functionality of the Remy CLI commands (`query`, `index`, `macro`) as HTTP endpoints with JSON responses and provides automatic OpenAPI/Swagger documentation.

The API is read-only and mirrors the CLI's read capabilities. All responses are JSON. Streaming is supported for large result sets.

---

## Base URL and Versioning

```
http://<host>:<port>/api
```

The API does not currently use URL versioning. If versioning becomes necessary in the future, the prefix `/api/v1/` will be adopted without removing `/api/` aliases for backward compatibility.

**Running the server:**

```bash
python -m remy.api
```

`remy.api` is the new FastAPI module introduced by this specification (distinct from the existing `remy.www` Flask application). The cache location is configured via the `REMY_CACHE` environment variable or a server-startup argument.

---

## Authentication

No authentication is required. The API is intended for local or internal network use. If deployed in a broader network context, an external reverse proxy (e.g., nginx) should handle authentication and TLS termination.

---

## Common Conventions

- All responses are `application/json`.
- All error responses use a consistent JSON schema (see [Error Responses](#error-responses)).
- Field names in request parameters are `snake_case`.
- Path parameters that reference notecard labels are URL-encoded.
- HTTP status codes follow standard RESTful conventions.

---

## Error Responses

All error responses share the following JSON schema:

```json
{
  "detail": "<human-readable error message>"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| `400 Bad Request` | Invalid query expression, incompatible options, or malformed parameter |
| `404 Not Found` | Requested resource (notecard, index, macro) does not exist |
| `422 Unprocessable Entity` | FastAPI validation error (wrong parameter type, missing required field) |
| `500 Internal Server Error` | Unexpected server-side error |

**Example error response:**

```json
{
  "detail": "Field index 'UNKNOWN' not found in configuration."
}
```

---

## Endpoints

### 1. Health Check

#### `GET /api`

Returns a simple health-check response confirming the API is running.

**Request parameters:** None

**Response:** `204 No Content`

**Example:**

```bash
curl -i http://localhost:5000/api
```

---

### 2. Notecards

#### `GET /api/notecard/{card_label}`

Retrieve a single notecard by its label.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `card_label` | string | Yes | The notecard label (URL-encoded if it contains special characters) |

**Response schema:**

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

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Notecard found |
| `404 Not Found` | No notecard with the given label exists |

**Example:**

```bash
curl http://localhost:5000/api/notecard/my-note-label
```

```json
{
  "label": "my-note-label",
  "raw": "NOTECARD my-note-label\n:TAG: example\n\nThis is the notecard content.\n"
}
```

---

### 3. Query

#### `GET /api/query`

Query and filter notecards. Mirrors the `remy query` CLI command.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `q` | string | No¹ | — | Query expression (e.g., `tag = 'inbox'`) |
| `all` | boolean | No¹ | `false` | Return all notecards (alternative to `q`) |
| `format` | string | No | `json` | Output format: `json` or `set` |
| `order_by` | string | No | `id` | Sort key: `id` (primary label) or any field name |
| `reverse` | boolean | No | `false` | Reverse the sort order |
| `limit` | integer ≥ 1 | No | — | Maximum number of results |
| `fields` | string | No | — | Comma-separated list of field names to extract (see [Field Selection](#field-selection)) |
| `stream` | boolean | No | `false` | Stream results as newline-delimited JSON (NDJSON) |

¹ Exactly one of `q` or `all=true` must be provided.

**Constraints:**

- `fields` is incompatible with `format=set`.
- `order_by` (non-default) is incompatible with `format=set`.
- `all` and `q` are mutually exclusive.

**`format` values:**

| Value | Description |
|-------|-------------|
| `json` | JSON array of notecard objects (default) |
| `set` | Raw set result: PairSet as array of `[label, value]` pairs; LabelSet/ValueSet as array of strings |

**Response schema (`format=json`, no `fields`):**

```json
[
  {
    "label": "<primary label>",
    "labels": ["<label1>", "<label2>"],
    "raw": "<full notecard text>"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `label` | string | Primary label of the notecard |
| `labels` | array of strings | All labels for this notecard |
| `raw` | string | Full notecard text (NOTECARD header + content) |

**Response schema (`format=json`, with `fields`):**

```json
[
  {
    "<field_name>": ["<value1>", "<value2>"]
  }
]
```

Each object in the array represents one notecard. Each key is a requested field name, and its value is an array of parsed field values for that notecard. Date/datetime values are serialized as ISO 8601 strings.

**Pseudo-fields supported in `fields`:**

| Pseudo-field | Description |
|--------------|-------------|
| `@primary-label` or `@id` | The notecard's primary label |
| `@label` | All labels for the notecard |
| `@title` or `@first-block` | The first text block of the notecard content |

**Response schema (`format=set`):**

For a PairSet result (e.g., from `field = value` queries):

```json
[
  ["<label>", "<value>"],
  ...
]
```

For a LabelSet or ValueSet result:

```json
["<value1>", "<value2>", ...]
```

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Query executed successfully |
| `400 Bad Request` | Missing query expression, invalid query syntax, or incompatible options |
| `422 Unprocessable Entity` | Invalid parameter types |

**Examples:**

```bash
# Return all notecards
curl "http://localhost:5000/api/query?all=true"

# Filter by tag
curl "http://localhost:5000/api/query?q=tag%20%3D%20'inbox'"

# Filter, sort by date, limit to 10 most recent
curl "http://localhost:5000/api/query?q=tag%20%3D%20'inbox'&order_by=created&reverse=true&limit=10"

# Extract specific fields
curl "http://localhost:5000/api/query?all=true&fields=%40primary-label%2Ctag"

# Raw set output (e.g., list all tag values)
curl "http://localhost:5000/api/query?q=values(tag)&format=set"
```

**Example response (`format=json`, no `fields`):**

```json
[
  {
    "label": "my-note",
    "labels": ["my-note", "note-alias"],
    "raw": "NOTECARD my-note note-alias\n:TAG: example\n\nContent here.\n"
  }
]
```

**Example response (`format=json`, `fields=@primary-label,tag`):**

```json
[
  {
    "@primary-label": ["my-note"],
    "tag": ["example", "work"]
  }
]
```

**Example response (`format=set`, `q=values(tag)`):**

```json
["archive", "example", "inbox", "work"]
```

#### Streaming (`stream=true`)

When `stream=true`, the response uses `Transfer-Encoding: chunked` with newline-delimited JSON (NDJSON, `application/x-ndjson`). Each line is a complete JSON object representing one notecard (or one set item for `format=set`).

This is recommended for large result sets to avoid buffering the entire response in memory.

**Example NDJSON output (`format=json`, no `fields`):**

```
{"label": "card-a", "labels": ["card-a"], "raw": "NOTECARD card-a\n...\n"}
{"label": "card-b", "labels": ["card-b", "alias-b"], "raw": "NOTECARD card-b alias-b\n...\n"}
```

---

### 4. Index

#### `GET /api/index`

List all configured field index names. Mirrors `remy index list`.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_all_fields` | boolean | No | `false` | If true, also include field names found in notecard content that have no configured parser (may be slow for large caches) |

**Response schema:**

```json
["<field_name_1>", "<field_name_2>"]
```

An alphabetically sorted JSON array of field index names (uppercase, as defined in `PARSER_BY_FIELD_NAME`). When `include_all_fields=true`, additional field names discovered from card content are merged and sorted.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Success |
| `500 Internal Server Error` | Config file missing or `PARSER_BY_FIELD_NAME` not defined (see [remy_config.md](remy_config.md) for configuration details) |

```json
["CREATED", "PRIORITY", "STATUS", "TAG"]
```

```bash
curl "http://localhost:5000/api/index?include_all_fields=true"
```

```json
["CREATED", "NOTE", "PRIORITY", "STATUS", "TAG"]
```

---

#### `GET /api/index/{index_name}`

Dump the contents of a specific field index. Mirrors `remy index dump`.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `index_name` | string | Yes | The field index name (case-insensitive; normalized to uppercase internally) |

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | string | No | `full` | Output mode: `full` (label+value pairs), `labels` (labels only), or `values` (values only) |
| `unique` | boolean | No | `false` | Remove duplicate entries while maintaining sort order |
| `stream` | boolean | No | `false` | Stream results as NDJSON |

**Response schema (`mode=full`):**

```json
[
  ["<label>", "<value>"],
  ...
]
```

Each element is a two-element array `[label, value]`. Values that are dates or datetimes are serialized as ISO 8601 strings.

**Response schema (`mode=labels`):**

```json
["<label1>", "<label2>", ...]
```

**Response schema (`mode=values`):**

```json
["<value1>", "<value2>", ...]
```

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Success |
| `404 Not Found` | `index_name` not found in configuration |
| `422 Unprocessable Entity` | Invalid `mode` value |
| `500 Internal Server Error` | Config file missing or `PARSER_BY_FIELD_NAME` not defined (see [remy_config.md](remy_config.md)) |

**Examples:**

```bash
# Full dump (label + value pairs)
curl "http://localhost:5000/api/index/TAG"

# Values only, deduplicated
curl "http://localhost:5000/api/index/TAG?mode=values&unique=true"

# Labels only
curl "http://localhost:5000/api/index/TAG?mode=labels"
```

**Example response (`mode=full`):**

```json
[
  ["my-note", "example"],
  ["my-note", "work"],
  ["other-note", "archive"]
]
```

**Example response (`mode=values`, `unique=true`):**

```json
["archive", "example", "work"]
```

#### Streaming (`stream=true`)

When `stream=true`, results are streamed as NDJSON. For `mode=full`, each line is a JSON array `["<label>", "<value>"]`. For `mode=labels` or `mode=values`, each line is a JSON string.

---

#### `GET /api/index/{index_name}/validate`

Validate field parsing for a specific field index. Mirrors `remy index validate`.

Returns a list of parsing errors found across all notecards for the given field. If there are no errors, an empty array is returned.

**Path parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `index_name` | string | Yes | The field index name to validate (case-insensitive) |

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `show_uri` | boolean | No | `false` | Include source file URI in each error object |
| `show_line` | boolean | No | `false` | Include source URI, field name, and raw field value in each error object (implies `show_uri`) |

**Response schema:**

```json
[
  {
    "label": "<notecard primary label>",
    "error_type": "<exception class name>",
    "error_message": "<error description>",
    "uri": "<source file URI>",
    "field_name": "<field name as it appears in the card>",
    "field_value": "<raw field value that failed to parse>"
  }
]
```

Fields `uri`, `field_name`, and `field_value` are only present when `show_uri` or `show_line` is `true`.

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Validation completed (empty array if no errors) |
| `404 Not Found` | `index_name` not found in configuration |
| `500 Internal Server Error` | Config file missing or `PARSER_BY_FIELD_NAME` not defined (see [remy_config.md](remy_config.md)) |

**Note:** Unlike the CLI, the HTTP API always returns `200 OK` whether or not validation errors exist. The presence of errors is indicated by the array being non-empty.

**Examples:**

```bash
# Basic validation
curl "http://localhost:5000/api/index/PRIORITY/validate"

# Include source file URIs
curl "http://localhost:5000/api/index/PRIORITY/validate?show_uri=true"

# Full detail
curl "http://localhost:5000/api/index/PRIORITY/validate?show_line=true"
```

**Example response (with `show_line=true`):**

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

**Example response (no errors):**

```json
[]
```

---

### 5. Macros

#### `GET /api/macro`

List all configured query macros. Mirrors `remy macro list`.

**Query parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `mode` | string | No | `names` | Display mode: `names` (macro names only), `full` (definitions), or `expand` (expanded definitions) |
| `name` | string | No | — | Filter to a specific macro name (with or without leading `@`) |

**`mode` values:**

| Value | Description |
|-------|-------------|
| `names` | Return only macro names as an array of strings (default) |
| `full` | Return macro definitions in `@NAME := DEFINITION` format |
| `expand` | Return expanded macro definitions after AST substitution |

**Response schema (`mode=names`):**

```json
["@macro1", "@macro2"]
```

An alphabetically sorted array of macro names, each prefixed with `@`.

**Response schema (`mode=full` or `mode=expand`):**

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

**Status codes:**

| Code | Condition |
|------|-----------|
| `200 OK` | Success (empty array if no macros are configured) |
| `400 Bad Request` | Query macro parsing error |
| `404 Not Found` | Specific `name` not found among configured macros |
| `422 Unprocessable Entity` | Invalid `mode` value |

**Examples:**

```bash
# List macro names
curl "http://localhost:5000/api/macro"

# Show full definitions
curl "http://localhost:5000/api/macro?mode=full"

# Show expanded form of a single macro
curl "http://localhost:5000/api/macro?name=inbox&mode=expand"
```

**Example response (`mode=names`):**

```json
["@archive", "@inbox", "@work"]
```

**Example response (`mode=full`):**

```json
[
  {
    "name": "@archive",
    "definition": "@archive := tag = 'archive'"
  },
  {
    "name": "@inbox",
    "definition": "@inbox := tag = 'inbox'"
  }
]
```

**Example response (`mode=expand`, `name=inbox`):**

```json
[
  {
    "name": "@inbox",
    "definition": "@inbox := tag='inbox'"
  }
]
```

---

## Streaming Endpoints

The following endpoints support `stream=true` for streaming NDJSON responses:

| Endpoint | Notes |
|----------|-------|
| `GET /api/query` | Streams one notecard object per line (or one set item per line for `format=set`) |
| `GET /api/index/{index_name}` | Streams one entry per line |

When streaming is enabled:

- `Content-Type` is `application/x-ndjson`
- `Transfer-Encoding` is `chunked`
- Each line is a complete, independently parseable JSON value followed by `\n`
- The response ends when all results have been emitted

Streaming is recommended for queries that may return large numbers of notecards or index entries.

---

## OpenAPI / Swagger Documentation

FastAPI generates interactive documentation automatically:

| URL | Description |
|-----|-------------|
| `http://<host>:<port>/docs` | Swagger UI (interactive) |
| `http://<host>:<port>/redoc` | ReDoc UI (read-only) |
| `http://<host>:<port>/openapi.json` | Raw OpenAPI 3.x schema |

---

## Design Decisions

### Query expression as `q` parameter

The CLI accepts a positional argument or `--where` flag for the query expression. In the HTTP API, this is unified into a single `q` query parameter, which is the conventional name for a search/query string in REST APIs.

### `format=json` as the default for query

The CLI defaults to `format=raw` (human-readable notecard format). The HTTP API defaults to `format=json` because JSON is the natural format for a programmatic API. The `raw` format is omitted from the HTTP API; callers that need raw notecard text can use the `raw` field included in every notecard object in the JSON response.

### HTTP 200 for validate with errors

The CLI uses exit code 1 when validation errors are found. The HTTP API always returns `200 OK` with an array of errors (which may be empty). This follows REST conventions where the success or failure of the HTTP operation (running the validation scan) is separate from the domain result (whether errors were found).

### Case normalization for index names

The CLI accepts index names case-insensitively (normalizing to uppercase internally). The HTTP API does the same; callers may provide `tag`, `TAG`, or `Tag` and all resolve to the `TAG` index.

### No `raw` output format in HTTP API

The CLI supports `format=raw` which produces human-readable notecard text. This is not offered as a distinct format in the HTTP API; raw text is always available via the `raw` field in the JSON response objects. This keeps the API consistently JSON-based.

### Macro `mode=names` instead of default implicit behavior

The CLI prints macro names by default when no flag is given. The HTTP API makes this explicit via `mode=names` to produce a self-documenting and forward-compatible parameter.

### `delimiter` option for `index dump` not exposed

The CLI's `--delimiter` option for `index dump` (raw CSV output) is not included in the HTTP API because the HTTP API returns JSON arrays instead of delimited text. The delimiter concept does not apply to JSON.
