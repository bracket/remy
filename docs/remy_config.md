# remy config

The remy config file is a Python script which is loaded by remy at
runtime before loading and parsing notecard files.  It should be stored in the
`.remy` directory at the base of a notecard repository and named `config.py` (i.e., `.remy/config.py`).  A sample one is located in `docs/examples/config.py`.

## Configuration Options

### PARSER_BY_FIELD_NAME

A dictionary mapping uppercase field names to parser functions. Each parser function takes a field value string and returns a tuple of parsed values.

**Required**: Yes (for field indices to work)

**Example**:
```python
def tags_parser(field):
    return tuple(f.strip().lower() for f in field.split(','))

PARSER_BY_FIELD_NAME = {
    'TAGS': tags_parser,
    'STATUS': lambda field: (field.strip().lower(),),
}
```

### MACROS

A dictionary defining global query macros that are available in all queries. The dictionary keys are descriptive names (not used by the system), and the values are complete macro definition strings.

**Required**: No (optional)

**Format**: Each value must be a complete macro definition string in the form:
- Zero-arity macro: `@name := expression`
- Parametric macro: `@name(Param1, Param2) := expression`

**Constraints**:
- Macro names must start with lowercase letters (after the `@`)
- Cannot define `@main` in config (reserved for queries)
- Config macros can reference each other (forward references are supported)
- Duplicate macro names within config are not allowed
- Query-defined macros cannot override config macros
- Parameters in parametric must start with uppercase letters

**Example**:
```python
MACROS = {
    # Simple macro
    'WORK_BLOCKS': '@work_blocks := union(tags="focus_block", tags="activation_block")',
    
    # Parametric macro
    'PROJECT_BLOCKS': '@project_blocks(ProjectSet) := ProjectSet and @work_blocks',
    
    # Macro using another config macro
    'CLOSED_BLOCKS': '@closed_blocks := union(status="closed", flip(previous))',
    
    # Complex parametric macro
    'CHAIN_HEADS': '@chain_heads(ProjectSet) := difference_by_label(@project_blocks(ProjectSet), @closed_blocks)',
}
```

**Usage in queries**:
```bash
# Use config-defined macros directly in queries
remy --cache /path/to/notes query "@work_blocks"

# Combine with query-defined macros
remy --cache /path/to/notes query "@active := status='active'; @work_blocks AND @active"

# Use parametric config macros
remy --cache /path/to/notes query "@chain_heads(tags='alpha')"
```

**Benefits**:
- Define commonly-used query patterns once in config
- Share macros across all queries without repetition
- Simplify complex queries by breaking them into reusable components
- Maintain consistency in query logic across your notecard system
