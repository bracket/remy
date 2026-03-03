# Remy

Remy is a system for orgnanizing notecards in a flat text file format, making it possible to write multiple notecards per file,
add arbitrary metadata to each notecard, and easily search and filter notecards based on their content and metadata.

Notecards can be placed in any text file, the following format:
```text
NOTECARD <identifier> [optional additional identifiers]
:KEY: VALUE

NOTECARD <identifier>
:KEY: VALUE
```

Notecards are separated by the `NOTECARD <identifier>` line, where `<identifier>` is a unique identifier for the notecard.
All the content between two `NOTECARD` lines belongs to one notecard block.
Each line beginning with :KEY: is treated as metadata for the notecard, where
KEY is the metadata key and VALUE is the metadata value.

For a quick example, a single text file can hold multiple notecards:

```text
NOTECARD main
:CREATED: 2022-03-26 04:30:01
:TAGS: overview

# Project Snapshot

* [note://organize_tasks]
* [note://remy]
* [note://data_journal]
* [note://city_pool]
* [note://ml_research]
* [note://animation_club]
* [note://budgeting]


* [note://spotted_main]

NOTECARD 3664998a2bf54f0f6e4350ca424482aeef65378815e968420d4da6f13f5dd684 data_journal
:CREATED: 2022-03-30 09:40:24
:TAGS: Data Notes

Data journal topics
* Physics
* [note://chemistry]
* Molecular Biology
* Biology
* Neuroscience

NOTECARD e9b1dd7d1ffb57271cfd92bd951f008333aa8d3fb1141acdef810074234fa503 city_pool
:CREATED: 2022-03-30 09:41:38
:TAGS: Pools

Lap swim ideas

* Skillset plan
* Coaching
```

They `remy` command line tool can be used to manage and search notecards in a directory of text files.

## HTTP API

The Remy HTTP API (FastAPI) exposes read-only notecard operations as JSON endpoints.

```bash
# Start the API server (REMY_CACHE points to your notecard directory)
REMY_CACHE=/path/to/notes python -m remy.api
```

See `docs/api_specification.md` for full endpoint documentation.

## MCP Server

The Remy MCP server exposes notecard functionality to LLM clients (Claude, GPT, etc.) through the [Model Context Protocol](https://modelcontextprotocol.io/) over streamable-HTTP transport.

### Prerequisites

The FastAPI backend must be running before starting the MCP server:

```bash
REMY_CACHE=/path/to/notes python -m remy.api
```

### Starting the MCP Server

```bash
python -m remy.mcp
```

The server listens on `localhost:8080` by default.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REMY_API_URL` | `http://localhost:5000` | Base URL of the Remy FastAPI backend |
| `REMY_MCP_HOST` | `localhost` | Host to bind the MCP server to |
| `REMY_MCP_PORT` | `8080` | Port to bind the MCP server to |
| `REMY_MCP_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `REMY_MCP_LOG_LEVEL` | `WARNING` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Example Configuration

```bash
export REMY_API_URL=http://localhost:5000
export REMY_MCP_HOST=localhost
export REMY_MCP_PORT=8080
python -m remy.mcp
```

### MCP Client Configuration

To connect an MCP client to the Remy MCP server, configure the streamable-HTTP endpoint:

```
http://localhost:8080/mcp
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `query_notecards` | Search for notecards using the Remy query language |
| `get_notecard` | Retrieve a specific notecard by its exact label |
| `list_field_indexes` | List all configured field index names |
| `dump_field_index` | Retrieve the contents of a specific field index |
| `validate_field_index` | Check for field parsing errors in a specific field index |
| `list_macros` | List all configured query macros |
| `query_set` | Execute a query expression and return the raw set result |

See `docs/mcp_specification.md` for full tool documentation.
