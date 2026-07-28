# Remy Design Overview

## Introduction

Remy is a notecard organization system designed around a simple principle: **notecards should be stored in flat text files that are human-readable, easy to edit, and version-control friendly.**

The system enables users to:
- Write **multiple notecards per file** using a minimal, unobtrusive format
- Add **arbitrary metadata** to each notecard using a simple `:KEY: VALUE` syntax
- **Reference other notecards** and external resources using bracket notation
- **Search and filter notecards** based on content and metadata using a SQL-like query language
- **Browse and edit notecards** through both CLI and web interfaces

### Core Design Philosophy

1. **Human-First Format**: Notecards are plain text that can be read, written, and understood without any tools
2. **Minimal Syntax**: The format uses the least syntax necessary to structure content
3. **Flexibility**: Support arbitrary metadata fields without predefined schemas
4. **Composability**: Allow multiple notecards per file for related content
5. **Linkability**: Enable rich interconnections between notecards and external resources
6. **Searchability**: Provide powerful querying capabilities over both content and metadata

---

## File Format

### Basic Structure

Notecards use a simple text format with three main components:

```text
NOTECARD <identifier> [additional identifiers...]
:FIELD_NAME: field value
:ANOTHER_FIELD: another value

Content goes here.
This is the notecard's body text.
It can span multiple lines and paragraphs.

Links to other cards: [note://other_card_label]
External links: [https://example.com]
```

#### Components

1. **NOTECARD line**: Marks the beginning of a new notecard
   - Must start with the keyword `NOTECARD`
   - Followed by one or more whitespace-separated identifiers (labels)
   - The first label is the "primary label"
   - Additional labels serve as aliases for the same notecard

2. **Field lines**: Define metadata for the notecard
   - Format: `:KEY: VALUE`
   - Must start with a colon, followed by the field name, another colon, and the value
   - Field names are case-insensitive (stored as uppercase internally)
   - Common fields: `:CREATED:`, `:TAGS:`, `:SPOTTED:`, `:COMPLETED:`
   - Fields are completely extensible - any key can be used

3. **Content**: Everything else is the notecard's body
   - Plain text, markdown, or any format you prefer
   - Can include inline references using bracket notation
   - No specific formatting requirements

### Multiple Notecards Per File

A key design decision is allowing multiple notecards in a single file:

```text
NOTECARD project_overview main
:CREATED: 2022-03-26 04:30:01
:TAGS: overview, planning

# Project Snapshot
* [note://organize_tasks]
* [note://data_journal]

NOTECARD organize_tasks
:CREATED: 2022-03-26 05:15:00
:TAGS: planning, tasks

## Task Organization
- Define priorities
- Create weekly sprints
```

This allows:
- **Grouping related content** in a single file
- **Batch operations** on related notecards
- **Better version control** (related changes in one commit)
- **Easier navigation** when browsing files directly

### Reference Syntax

References use bracket notation and support various URL schemes:

```text
[note://card_label]                    # Link to another notecard
[https://example.com]                  # External web link
[rfc822msgid://message_id]            # Gmail message reference
[file:///path/to/file.txt]            # Local file reference
```

The `note://` scheme is special - it references other notecards by their label.

---

## Architecture

### Component Overview

Remy consists of four main components:

```
┌─────────────────────────────────────────────────┐
│               Python Backend                    │
│  ┌───────────────────────────────────────────┐  │
│  │ Notecard Parsing & AST                    │  │
│  │ - Grammar definitions                     │  │
│  │ - Content parsing                         │  │
│  │ - AST nodes (Text, Field, Reference)      │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │ NotecardCache & Indexing                  │  │
│  │ - Load notecards from filesystem          │  │
│  │ - Label-based lookup                      │  │
│  │ - Field-based indexes                     │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │ Query Language                            │  │
│  │ - SQL-like WHERE clause parsing           │  │
│  │ - AST-based query representation          │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐    ┌──────────────────────┐
│   CLI Interface     │    │   Web Interface      │
│   (Click-based)     │    │   (FastAPI)          │
└─────────────────────┘    └──────────────────────┘
```

### Core Python Backend

#### 1. Notecard Parsing (`notecard.py`, `grammar.py`)

The parsing layer converts text files into structured notecard objects.

**Grammar Definition** (`grammar.py`):
```python
g['prefix']          = r'NOTECARD'
g['label']           = r'[-_0-9a-zA-Z]+'
g['field']           = r':{label}:\s*{field_content}{endline}'
g['reference']       = r'\[\s*{url}\s*\]'
```

The grammar is defined declaratively and expanded using pattern substitution. This approach:
- Makes patterns composable and reusable
- Allows easy modification without changing parser logic
- Can be compiled to regex or used for other parsers

**Notecard Class**:
```python
class Notecard:
    - primary_label: str        # First label
    - labels: List[str]         # All labels (including aliases)
    - content: str              # Raw content
    - source_url: URL           # Where it was loaded from
```

**File Parsing**:
- `from_file(path)`: Parse all notecards in a single file
- `from_path(path)`: Recursively parse a directory
- `from_url(url)`: Parse from a URL (currently only `file://` scheme)

#### 2. Abstract Syntax Tree (`ast/`)

The content of each notecard is parsed into an AST with three node types:

- **Text**: Plain text content
- **Field**: Metadata field (`:KEY: VALUE`)
- **Reference**: Inline reference (`[url]`)

This design:
- **Separates structure from presentation**: AST can be rendered to HTML, plain text, or other formats
- **Enables content analysis**: Easy to extract fields, find references, etc.
- **Supports rich processing**: Can transform or validate content programmatically

Example:
```python
from remy.ast.parse import parse_content

for node in parse_content(card.content):
    if isinstance(node, Field):
        print(f"Field: {node.label} = {node.value}")
    elif isinstance(node, Reference):
        print(f"Link to: {node.url}")
```

#### 3. NotecardCache (`notecard_cache.py`)

The `NotecardCache` class provides the main interface for working with notecards:

```python
cache = NotecardCache(URL('file:///path/to/notes'))

# Label-based lookup
card = cache.cards_by_label['my_card_label']

# Field-based indexing
tag_index = cache.field_index('TAGS')
cards = tag_index.find('python')
```

**Design decisions**:
- **Lazy loading**: Indexes are built on first access
- **Memoization**: Expensive computations are cached using `@property` pattern
- **Configurable parsing**: Field parsers defined in `.remy/config.py`

#### 4. Field Indexing (`notecard_index.py`)

`NotecardIndex` provides efficient field-based lookups using sorted data structures:

```python
# Find all notecards with TAGS containing 'python'
tag_index = cache.field_index('TAGS')
for value, label in tag_index.find('python'):
    card = cache.cards_by_label[label]
```

Uses `sortedcontainers.SortedSet` for:
- **O(log n) lookups**
- **Range queries**: Find all cards with timestamp between two dates
- **Ordered iteration**: Traverse cards by field value

**Configurable Parsers**: Each field type can have a custom parser (defined in `.remy/config.py`):
- `tags_parser`: Split comma-separated tags into tuple
- `timestamp_parser`: Parse ISO 8601 timestamps
- Custom parsers for domain-specific fields

#### 5. Query Language (`query/`)

**Current Implementation** (using Lark):

The query language uses SQL-like WHERE clause syntax:

```sql
tags = 'python' AND created > '2024-01-01'
status IN ['active', 'pending'] OR priority >= 5
NOT completed AND (tags = 'urgent' OR priority > 8)
```

**Grammar Features**:
- **Comparison operators**: `=`, `!=`, `<`, `<=`, `>`, `>=`
- **Logical operators**: `AND`, `OR`, `NOT`
- **Membership testing**: `IN [value1, value2, ...]`
- **Literals**: strings (single/double quoted), numbers, booleans, null
- **Identifiers**: field names, supports dotted paths for future extensions

**AST Nodes** (`ast_nodes.py`):
```python
@dataclass
class Compare(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode

@dataclass  
class And(ASTNode):
    left: ASTNode
    right: ASTNode
```

The query AST is designed to be:
- **Evaluable**: Each node can be evaluated against a notecard
- **Optimizable**: AST can be transformed for better performance
- **Inspectable**: Easy to analyze query structure

---

## CLI Interface

The command-line tool (`cli/__main__.py`) provides direct access to the notecard system.

**Current Implementation**:
```bash
remy --cache /path/to/notes
```

Uses Click for command parsing with:
- `--cache` option to specify notecard directory
- Environment variable support: `REMY_CACHE`

**Current Behavior**:
- Loads all notecards from the cache
- Prints the parsed AST for each notecard

**Planned Features**:
- Search/filter notecards with query language
- Display notecard content in various formats
- Create/edit/delete notecards
- Export notecards to different formats
- Validate notecard syntax
- Show statistics (counts, field distributions, etc.)

---



---

## Configuration System

### `.remy/config.py`

The configuration file allows customization of notecard behavior:

**Location**: Must be in the `.remy` directory at the root of the notecard directory (`.remy/config.py`)

**Purpose**:
- Define field parsers for custom metadata types
- Configure how fields are indexed
- Extend system behavior without modifying core code

**Example** (`docs/examples/config.py`):
```python
def tags_parser(field):
    return tuple(f.strip().lower() for f in field.split(','))

def timestamp_parser(field):
    from dateutil.parser import parse
    from pytz import utc
    timestamp = parse(field.split(',')[0].strip())
    timestamp = timestamp.astimezone(utc)
    return (timestamp,)

PARSER_BY_FIELD_NAME = {
    'TAGS'      : tags_parser,
    'SPOTTED'   : timestamp_parser,
    'COMPLETED' : timestamp_parser,
}
```

**Design Decisions**:
- Python file for maximum flexibility
- Loaded dynamically using `importlib`
- Falls back to default behavior if not present
- Parsers return tuples to support multi-valued fields

---

## Key Design Patterns

### 1. Grammar-Based Parsing

Remy uses a declarative grammar system:

```python
g = {
    'label': r'[-_0-9a-zA-Z]+',
    'labels': r'{label}(?:\s+{label})*',
}
expanded = expand_grammar(g)  # Recursively expand patterns
```

**Benefits**:
- Easy to understand and modify
- Can generate different parser types (regex, Lark, etc.)
- Self-documenting code
- Reusable patterns

### 2. Lazy Initialization with Properties

Expensive computations are deferred and cached:

```python
@property
def cards_by_label(self):
    if self.__cards_by_label is not None:
        return self.__cards_by_label
    
    # Expensive computation
    self.__cards_by_label = self._build_label_index()
    return self.__cards_by_label
```

**Benefits**:
- Only compute when needed
- Transparent caching
- Memory efficient for large repositories

### 3. URL-Based Resource Identification

Everything has a URL:

```python
card.source_url = URL('file:///path/notes.txt#123')
                      #  scheme, path, fragment
```

**Benefits**:
- Uniform resource identification
- Line number tracking (fragment)
- Extensible to remote resources (HTTP, S3, etc.)
- Interoperable with web standards

### 4. AST-Based Content Model

Content is parsed into a tree structure:

```
Notecard Content → [Text, Field, Reference, Text, ...]
```

**Benefits**:
- Separate structure from presentation
- Enable rich content transformations
- Support multiple output formats
- Easy content analysis

### 5. Sorted Indexing for Efficient Queries

Field indexes use `sortedcontainers.SortedSet`:

```python
index.find(low='2024-01-01', high='2024-12-31')
```

**Benefits**:
- O(log n) lookup time
- Range queries
- Order preservation
- Memory efficient

---

## Current Features

### ✅ Implemented

1. **File Format**
   - Multi-notecard files
   - Field metadata (`:KEY: VALUE`)
   - Reference syntax (`[url]`)
   - Label aliases

2. **Parsing & Loading**
   - Grammar-based parsing
   - Recursive directory loading
   - AST generation for content
   - URL-based resource tracking

3. **Caching & Indexing**
   - Label-based lookup
   - Field-based indexes
   - Configurable field parsers
   - Lazy loading and memoization

4. **Query Language**
   - SQL-like WHERE clause syntax
   - Comparison operators
   - Logical operators (AND, OR, NOT)
   - IN operator for membership testing
   - Lark-based parser with full AST

5. **Configuration**
   - `.remy/config.py` support
   - Custom field parsers
   - Dynamic loading

---

## Planned Features

### 🚧 In Progress / Planned

#### Query Language Enhancements

1. **Query Evaluation**
   - Implement evaluator for query AST
   - Support field access on notecards
   - Handle missing fields gracefully
   - Optimize query execution

2. **Advanced Query Features**
   - Full-text search: `content CONTAINS 'keyword'`
   - Regex matching: `label MATCHES '^project_.*'`
   - Array operations: `'python' IN tags`
   - Exists operator: `completed EXISTS`
   - Date/time functions: `created > NOW() - DAYS(7)`

3. **Query Builder**
   - Visual query builder in web interface
   - Query templates for common searches
   - Query history and saved searches

#### CLI Enhancements

1. **Search Commands**
   ```bash
   remy search "tags = 'python'"
   remy find --tag python --created-after 2024-01-01
   remy list --format json
   ```

2. **CRUD Operations**
   ```bash
   remy create --label new_card --tag python
   remy edit card_label
   remy delete card_label
   remy add-field card_label KEY VALUE
   ```

3. **Utilities**
   ```bash
   remy validate           # Check syntax errors
   remy stats             # Show repository statistics
   remy graph             # Visualize notecard relationships
   remy export --format markdown
   ```

#### Web Interface Enhancements

1. **Search & Browse**
   - Advanced search interface
   - Filter by fields, tags, dates
   - Full-text search
   - Search result highlighting

2. **Editing**
   - In-browser notecard editor
   - Syntax highlighting
   - Live preview
   - Validation feedback

3. **Visualization**
   - Graph view of notecard relationships
   - Timeline view of notecards
   - Tag clouds
   - Field statistics

4. **Export & Integration**
   - Export to various formats (Markdown, JSON, HTML)
   - Import from other systems
   - API for external tools

#### Advanced Features

1. **Version Control Integration**
   - Track notecard history
   - Show diffs between versions
   - Restore previous versions

2. **Collaboration**
   - Multi-user access control
   - Concurrent editing
   - Change notifications

3. **Synchronization**
   - Sync between devices
   - Cloud storage backends
   - Offline support

4. **Plugins & Extensions**
   - Plugin API for custom behavior
   - Custom field types
   - Custom renderers
   - Custom query functions

5. **AI/ML Features**
   - Automatic tagging suggestions
   - Related notecard recommendations
   - Semantic search
   - Summary generation

---

## Implementation Notes

### Testing Strategy

Remy uses pytest for testing:

```
tests/
├── test_notecard.py         # Notecard parsing
├── test_notecard_cache.py   # Cache & indexing
├── test_query.py            # Query language
├── test_url.py              # URL handling
└── data/                    # Test fixtures
    └── test_notes/
```

**Testing Principles**:
- Test data in `tests/data/` directory
- Use absolute paths from `Path(__file__).parent / 'data'`
- Test both happy paths and error cases
- Test grammar patterns separately from full parsing

### Performance Considerations

1. **Lazy Loading**: Don't load all notecards until needed
2. **Memoization**: Cache expensive computations using `@property`
3. **Sorted Indexes**: Use `sortedcontainers` for O(log n) lookups
4. **Incremental Parsing**: Parse files individually, not all at once
5. **Field Parsers**: Parse fields only when indexed

### Error Handling

Remy defines a custom exception class:

```python
from remy.exceptions import RemyError

raise RemyError("descriptive message with context")
```

**Principles**:
- Use `RemyError` for all domain-specific errors
- Include context (URLs, labels, field names) in error messages
- Fail fast on configuration errors
- Provide actionable error messages

### Code Organization

```
src/remy/
├── Core System
│   ├── notecard.py          # Notecard class & file parsing
│   ├── notecard_cache.py    # Cache & loading
│   ├── notecard_index.py    # Field indexing
│   ├── grammar.py           # Grammar definitions
│   └── url.py               # URL handling
├── AST Layer
│   └── ast/
│       ├── node.py          # Base Node class
│       ├── parse.py         # Content parsing
│       ├── text.py          # Text nodes
│       ├── field.py         # Field nodes
│       └── reference.py     # Reference nodes
├── Query System
│   └── query/
│       ├── grammar.py       # Lark grammar definition
│       ├── parser.py        # Query parser
│       └── ast_nodes.py     # Query AST nodes
├── Interfaces
│   ├── cli/                 # Command-line interface
│   └── www/                 # Web application
└── Utilities
    ├── exceptions.py        # Custom exceptions
    └── util.py              # Helper functions
```

---

## Technology Stack

### Backend
- **Python 3.12+**: Core language
- **Lark**: Parser generator for query language
- **sortedcontainers**: Efficient sorted data structures
- **Click**: CLI framework
- **FastAPI**: HTTP API framework
- **pytest**: Testing framework

### Infrastructure
- **Docker**: Containerization
- **Alpine Linux**: Minimal container base
- **asdf**: Version management

---

## Design Rationale

### Why Plain Text Files?

**Advantages**:
- Human-readable without special tools
- Version control friendly (git works great)
- No proprietary formats or databases
- Easy backup and sync
- Platform independent
- Future-proof

**Trade-offs**:
- Not optimized for huge datasets (10,000+ cards)
- Full-text search requires indexing
- Concurrent writes need careful handling

### Why Multiple Notecards Per File?

**Advantages**:
- Group related content naturally
- Batch operations (edit related cards together)
- Better git diffs (related changes in one commit)
- Easier navigation in file browser

**Trade-offs**:
- Must parse entire file to extract one card
- Conflicts harder to resolve in multi-card files

### Why Minimal Syntax?

The format uses only three special syntaxes:
1. `NOTECARD ...` (start marker)
2. `:KEY: VALUE` (metadata)
3. `[url]` (references)

**Philosophy**: 
- Syntax should be invisible to humans
- Content should be readable as-is
- Adding structure should not obscure meaning

### Why AST-Based Content Model?

**Advantages**:
- Separate content structure from presentation
- Enable multiple output formats (HTML, Markdown, plain text)
- Support rich content transformations
- Easy to analyze and validate content

**Trade-offs**:
- Additional complexity in parsing
- Need to maintain consistent grammar

### Why SQL-Like Query Language?

**Advantages**:
- Familiar to many users
- Expressive and powerful
- Natural for filtering operations
- Easy to extend

**Trade-offs**:
- More complex than simple keyword search
- Requires parser implementation
- Learning curve for users

---

## Future Directions

### Possible Extensions

1. **Multi-Backend Support**
   - S3/Cloud storage backends
   - Database backends for large collections
   - Git integration for version tracking

2. **Advanced Content Types**
   - Embedded images
   - Code blocks with syntax highlighting
   - Mathematical equations
   - Task lists with checkboxes

3. **Real-Time Collaboration**
   - WebSocket-based updates
   - Operational transforms for concurrent editing
   - Presence indicators

4. **Mobile Support**
   - Native mobile apps
   - Progressive Web App (PWA)
   - Offline-first architecture

5. **AI Integration**
   - Natural language queries
   - Automatic linking suggestions
   - Content summarization
   - Semantic search

### Open Questions

1. **Scale**: How to handle 100,000+ notecards efficiently?
2. **Collaboration**: How to handle concurrent edits?
3. **Encryption**: How to support encrypted notecards?
4. **Versioning**: Should we track fine-grained edit history?
5. **Search**: Full-text search implementation strategy?

---

## Conclusion

Remy is designed around the principle that **tools should adapt to human thinking, not the other way around**. By using plain text files with minimal syntax, Remy provides powerful organization and search capabilities while keeping notecards readable and editable in any text editor.

The architecture separates concerns cleanly:
- **Format layer**: Simple, human-readable syntax
- **Parsing layer**: Grammar-based, extensible parsing
- **Storage layer**: Efficient caching and indexing
- **Query layer**: Expressive filtering language
- **Interface layer**: CLI and web access

This design enables both simple use cases (editing files directly) and advanced features (complex queries, web interface) without sacrificing simplicity or flexibility.

---

## References

- Repository: https://github.com/bracket/remy
- Configuration docs: [docs/remy_config.md](../remy_config.md)
- Example config: [docs/examples/config.py](../examples/config.py)
- Test fixtures: `tests/data/test_notes/`
