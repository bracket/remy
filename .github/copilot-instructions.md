# Remy Copilot Instructions

## Repository Overview

Remy is a notecard organization system that manages notecards in flat text files with metadata. The system enables users to:

- **Write multiple notecards per file** using a simple, human-readable format
- **Add arbitrary metadata** to each notecard using `:KEY: VALUE` syntax
- **Search and filter notecards** based on content and metadata using a custom query language
- **Browse and edit notecards** through a web interface

### Notecard Format

Notecards follow this format:

```text
NOTECARD <identifier> [optional additional identifiers]
:KEY: VALUE

Content goes here...

NOTECARD <another-identifier>
:ANOTHER_KEY: another value

More content...
```

- **NOTECARD line**: Starts a new notecard with one or more unique identifiers (labels)
- **Field lines**: Lines beginning with `:KEY:` define metadata fields
- **Content**: All other lines are the notecard's text content
- **References**: Inline references use bracket syntax `[url]`

### Architecture Overview

The project consists of three main components:

1. **Python Backend** (`src/remy/`): Core notecard parsing, indexing, caching, and query system
2. **CLI Tool** (`src/remy/cli/`): Command-line interface for managing notecards
3. **Web Interface**: Flask backend (`src/remy/www/`) with Vue.js frontend (`vite/vite/src/`)

---

## Technologies and Best Practices

### Python 3.x

**Version**: Python 3.12+ recommended (based on Docker configuration)

**Code Style and Formatting**:
- Follow PEP 8 style guidelines
- Use 4 spaces for indentation
- Maximum line length of 120 characters preferred
- Use snake_case for functions and variables
- Use PascalCase for class names
- Use UPPER_CASE for constants

**Import Organization**:
```python
# Standard library imports
from pathlib import Path
import functools

# Third-party imports
from flask import Flask
from sortedcontainers import SortedSet

# Local imports
from .notecard import Notecard
from remy.ast.parse import parse_content
```

**Error Handling**:
- Use the `RemyError` exception class (from `remy.exceptions`) for domain-specific errors
- Provide descriptive error messages with context (e.g., include the URL or label that caused the error)
- Example: `raise RemyError("only 'file' scheme is currently supported for URLs. url: '{}'".format(url))`

**Caching and Memoization**:
- Use `functools.lru_cache()` for memoization of expensive computations
- The codebase defines a `memoize` alias: `memoize = functools.lru_cache()`
- Use lazy initialization with `__property` pattern for cached attributes

**Module Organization**:
- Core functionality in `src/remy/`
- AST nodes and parsing in `src/remy/ast/`
- CLI commands in `src/remy/cli/`
- Query language in `src/remy/query/`
- Web application in `src/remy/www/`

### pytest

**Test File Naming**:
- Test files are named `test_<module>.py`
- Located in the `tests/` directory

**Test Function Naming**:
- Use `test_<functionality>` naming convention
- Be descriptive about what is being tested

**Test Data**:
- Test data files are stored in `tests/data/`
- Use `Path(__file__).absolute().parent / 'data'` to locate test data

**Running Tests**:
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_notecard.py

# Run with verbose output
pytest -v

# Run a specific test function
pytest tests/test_query.py::test_query_tokenizer
```

### Flask

**Application Factory Pattern**:
- Use `create_app()` function to create Flask application instances
- Configure the app with static and template folders

**Route Conventions**:
- API routes are prefixed with `/api/`
- Return JSON for API endpoints
- Use appropriate HTTP status codes

**Global State**:
- Use module-level variables for shared state (e.g., `notecard_cache`)
- Initialize state in the application factory

### Vue.js 3

**Component Design**:
- Use Composition API with `<script setup>` syntax
- Define props using `defineProps<T>()`
- Use `ref()` for reactive state
- Use `onMounted()` for lifecycle hooks

**Project Structure**:
- Components in `src/components/`
- Views (page-level components) in `src/views/`
- Router configuration in `src/router/`
- API functions in `src/api.ts`
- Shared utilities in separate `.ts` files

**Template Conventions**:
- Use `v-html` carefully for rendering HTML content
- Use `router-link` for internal navigation
- Use `router-view` for rendering routed components

### TypeScript

**Type Safety**:
- Enable strict mode in `tsconfig.json`
- Define interfaces for component props
- Use type annotations for function parameters and return values

**Configuration** (from `tsconfig.json`):
- Target: ES2020
- Module: ESNext
- Strict mode enabled
- No unused locals/parameters

### Vite

**Development Server**:
- Port 3000 for development
- Proxy configuration for API calls to Flask backend

**Build Commands**:
```bash
npm run dev      # Start development server
npm run build    # Build for production (runs vue-tsc first)
npm run preview  # Preview production build
```

**Configuration**:
- Vue plugin enabled
- API proxy to Flask backend at port 5000

### Docker

**Development Setup**:
- Use `dev-docker-compose.yml` for development with hot reloading
- Vite sources are bind-mounted for live updates
- Node modules are mounted separately for performance

**Production Build**:
- Use `docker-compose.yml` for production builds
- Based on Alpine Linux with asdf for version management
- Builds Node.js and Python from source

**Commands**:
```bash
# Development
cd vite
docker-compose -f dev-docker-compose.yml up

# Production build
cd vite
docker-compose up
```

### Custom Parsers

**Grammar-Based Parsing**:
- Grammars are defined as dictionaries with pattern names as keys
- Patterns use `{pattern_name}` for substitution
- Use `expand_grammar()` to recursively expand patterns
- Compile to regex with named capture groups

**Notecard Grammar** (`src/remy/grammar.py`):
- Defines patterns for notecard format: `prefix`, `labels`, `field`, `reference`, etc.
- Memoized to avoid recompilation

**Query Grammar** (`src/remy/query/grammar.py`):
- Tokenizer for query language
- Supports identifiers, literals (strings, numbers), and structural tokens

**Parser Combinator** (`src/remy/query/payer.py`):
- Language classes: `null`, `epsilon`, `Terminal`, `Union`, `Concat`, `Repeat`, `Named`
- Smart constructors: `terminal()`, `union()`, `concat()`, `named()`, `optional()`
- Parse method yields `(offset, tree)` tuples

---

## Setup Instructions

### Python Environment Setup

**Prerequisites**:
- Python 3.12 or later
- pip (Python package manager)

**Installation Steps**:

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd remy
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

   This installs:
   - `flake8` - Linting
   - `pytest` - Testing
   - `sphinx` - Documentation

5. Verify installation:
   ```bash
   python -c "from remy import Notecard, NotecardCache; print('OK')"
   ```

### Frontend Development Setup

**Prerequisites**:
- Node.js 21.x or later
- npm (Node package manager)

**Installation Steps**:

1. Navigate to the frontend directory:
   ```bash
   cd vite/vite
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```
   The development server runs on http://localhost:3000

4. Build for production:
   ```bash
   npm run build
   ```

### Docker Setup (Alternative)

For containerized development:

1. Navigate to the vite directory:
   ```bash
   cd vite
   ```

2. Start development environment:
   ```bash
   docker-compose -f dev-docker-compose.yml up
   ```

---

## Code Structure

### Python Backend (`src/remy/`)

```
src/remy/
├── __init__.py           # Package exports: Notecard, NotecardCache
├── exceptions.py         # RemyError exception class
├── grammar.py            # Notecard grammar definition and expansion
├── notecard.py           # Notecard class and file parsing (from_file, from_path, from_url)
├── notecard_cache.py     # NotecardCache class for loading and indexing notecards
├── notecard_index.py     # NotecardIndex class for field-based indexing
├── url.py                # URL class extending ParseResult for URL handling
├── util.py               # Utility functions (generate_unique_label)
│
├── ast/                  # Abstract Syntax Tree for notecard content
│   ├── __init__.py       # Exports: Field, Node, Reference, Text
│   ├── field.py          # Field node (metadata key-value pairs)
│   ├── node.py           # Base Node class
│   ├── parse.py          # parse_content() function for parsing notecard content
│   ├── reference.py      # Reference node (inline URLs)
│   └── text.py           # Text node (plain content)
│
├── cli/                  # Command-line interface
│   └── __main__.py       # CLI entry point using Click
│
├── query/                # Query language for searching notecards
│   ├── grammar.py        # Query tokenizer and grammar
│   ├── parser.py         # Query parser using parser combinators
│   └── payer.py          # Parser combinator library
│
└── www/                  # Web application
    ├── __main__.py       # Web server entry point using Click
    ├── app.py            # Flask application and API routes
    └── static/           # Static files (Vite build output)
```

### Frontend (`vite/vite/src/`)

```
vite/vite/src/
├── App.vue               # Root Vue component with router-view
├── api.ts                # API client for Flask backend
├── main.ts               # Application entry point
├── parser.ts             # Client-side notecard parser (mirrors Python grammar)
├── style.css             # Global styles
├── vite-env.d.ts         # Vite type declarations
│
├── assets/               # Static assets
│   └── styles/           # Stylesheets
│       └── base.css      # Base styles
│
├── components/           # Reusable Vue components
│   ├── HelloWorld.vue    # Example component
│   └── RemyCard.vue      # Notecard display component
│
├── router/               # Vue Router configuration
│   └── index.ts          # Route definitions
│
└── views/                # Page-level components
    └── HomeView.vue      # Home page view
```

### Tests (`tests/`)

```
tests/
├── data/                 # Test data files
│   └── test_notes/       # Sample notecard files
├── test_notecard.py      # Notecard parsing tests
├── test_notecard_cache.py # NotecardCache tests
├── test_query.py         # Query grammar and parser tests
├── test_url.py           # URL class tests
└── test_util.py          # Utility function tests
```

---

## Testing Instructions

### Running Tests

**Run all tests**:
```bash
pytest
```

**Run with verbose output**:
```bash
pytest -v
```

**Run a specific test file**:
```bash
pytest tests/test_notecard.py
```

**Run a specific test function**:
```bash
pytest tests/test_query.py::test_query_tokenizer
```

**Run tests with print output**:
```bash
pytest -s
```

### Test Organization

- **test_notecard.py**: Tests for parsing notecards from files and directories
- **test_notecard_cache.py**: Tests for the NotecardCache class
- **test_query.py**: Tests for query tokenization and parsing
- **test_url.py**: Tests for URL handling
- **test_util.py**: Tests for utility functions

### Writing New Tests

1. Create a test file named `test_<module>.py` in the `tests/` directory
2. Import the module being tested
3. Define test functions with `test_` prefix
4. Use test data from `tests/data/` when needed

**Example**:
```python
from pathlib import Path

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'

def test_example_feature():
    from remy import Notecard
    
    # Test implementation
    assert True
```

---

## Coding Standards

### Python Style Guide

**General Guidelines**:
- Follow PEP 8 for code style
- Use meaningful variable and function names
- Keep functions focused and small
- Document complex logic with comments

**Naming Conventions**:
| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `notecard_cache.py` |
| Classes | PascalCase | `NotecardCache`, `RemyError` |
| Functions | snake_case | `from_file()`, `parse_content()` |
| Variables | snake_case | `notecard_cache`, `field_name` |
| Constants | UPPER_CASE | `FILE`, `HERE`, `DATA` |
| Private attributes | `__` prefix | `__cards_by_label`, `__first_block` |

**Imports**:
- Group imports: standard library, third-party, local
- Use relative imports within the package (e.g., `from .notecard import Notecard`)
- Use absolute imports for cross-package references (e.g., `from remy.ast.parse import parse_content`)

**Properties and Lazy Initialization**:
```python
@property
def cards_by_label(self):
    if self.__cards_by_label is not None:
        return self.__cards_by_label
    
    # Compute and cache
    self.__cards_by_label = computed_value
    return self.__cards_by_label
```

**Sentinel Values**:
```python
null = object()  # Use for distinguishing None from "not computed"
```

### Frontend Coding Standards

**TypeScript**:
- Enable strict mode
- Use explicit type annotations for function parameters
- Define interfaces for complex object types

**Vue Components**:
- Use Composition API with `<script setup>` syntax
- Define props with TypeScript generics
- Keep template logic minimal

### Error Handling

**Python**:
- Raise `RemyError` for domain-specific errors
- Include context in error messages
- Use appropriate exception handling

**Frontend**:
- Handle API errors gracefully
- Provide user feedback for errors

### Linting

**Python**:
```bash
flake8 src/remy tests
```

**Frontend** (if ESLint is configured):
```bash
npm run lint
```

---

## Development Workflow

### Running the CLI Tool

```bash
# From the project root with virtual environment activated
python -m remy.cli --cache /path/to/notecards/directory
```

The `--cache` option specifies the directory containing notecard files.

Environment variable: `REMY_CACHE` can be set instead of passing `--cache`.

### Running the Web Interface

1. Start the Flask backend:
   ```bash
   python -m remy.www --cache /path/to/notecards/directory --host 0.0.0.0
   ```
   The Flask server runs on http://localhost:5000

2. Start the Vite development server (in a separate terminal):
   ```bash
   cd vite/vite
   npm run dev
   ```
   The frontend runs on http://localhost:3000 and proxies API calls to Flask.

### Development with Docker

```bash
cd vite
docker-compose -f dev-docker-compose.yml up
```

This starts the Vite development server with hot reloading.

### Common Development Tasks

**Adding a new AST node type**:
1. Create a new file in `src/remy/ast/` (e.g., `newnode.py`)
2. Extend the `Node` base class
3. Export from `src/remy/ast/__init__.py`
4. Update `parse_content()` in `src/remy/ast/parse.py` to handle the new node
5. Add tests in `tests/`

**Adding a new API endpoint**:
1. Add a route function in `src/remy/www/app.py`
2. Decorate with `@app.route('/api/...')`
3. Return JSON data
4. Update frontend API client in `vite/vite/src/api.ts`

**Adding a new CLI command**:
1. Add a Click command in `src/remy/cli/__main__.py`
2. Use `@click.command` and `@click.option` decorators
3. Access the notecard cache through the global variable

**Modifying the notecard grammar**:
1. Update patterns in `src/remy/grammar.py`
2. Update the TypeScript mirror in `vite/vite/src/parser.ts`
3. Add tests for new patterns
