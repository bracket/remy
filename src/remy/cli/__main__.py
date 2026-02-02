import click
import sys
import json
import csv
from io import StringIO

notecard_cache = None


def format_notecard_raw(card):
    """Format a notecard in raw notecard format for output."""
    # Start with NOTECARD line and labels
    output = "NOTECARD " + " ".join(card.labels) + "\n"
    # Add the content (which already includes fields and text)
    output += card.content
    return output


def format_notecards_raw(cards):
    """Format multiple notecards in raw format."""
    return "".join(format_notecard_raw(card) for card in cards)


def parse_fields_option(fields_str):
    """
    Parse the --fields option string into a list of field names.
    
    Args:
        fields_str: Comma-separated field names
        
    Returns:
        List of field names (preserving original case)
    """
    if not fields_str:
        return []
    return [f.strip() for f in fields_str.split(',') if f.strip()]


def extract_field_values(card, field_names, cache):
    """
    Extract requested field values from a notecard.
    
    Args:
        card: Notecard instance
        field_names: List of field names to extract (case-insensitive)
        cache: NotecardCache instance for accessing field indices
        
    Returns:
        Dictionary mapping field names (original case) to lists of values
        Special pseudo-fields:
        - @primary-label or @id: The primary label
        - @label: All labels
        - @title or @first-block: First block of content
    """
    result = {}
    
    for field_name in field_names:
        # Handle special pseudo-fields (case-insensitive comparison)
        field_name_lower = field_name.lower()
        
        if field_name_lower in ('@primary-label', '@id'):
            result[field_name] = [card.primary_label]
        elif field_name_lower == '@label':
            result[field_name] = list(card.labels)
        elif field_name_lower in ('@title', '@first-block'):
            first_block = card.first_block
            result[field_name] = [first_block] if first_block else []
        else:
            # Extract regular metadata fields using field indices (case-insensitive)
            # This ensures we use the parsed values from the config parsers
            field_name_upper = field_name.upper()
            
            try:
                # Get the field index which applies user-supplied parsers
                field_index = cache.field_index(field_name_upper)
                # Get parsed values for this card's primary label
                values = field_index.inverse.get(card.primary_label, [])
                result[field_name] = list(values)
            except (KeyError, AttributeError):
                # Field doesn't exist in config - return empty list
                result[field_name] = []
    
    return result


def csv_quote(value):
    """
    Quote a value for CSV output if necessary.
    
    Args:
        value: Value to quote (will be converted to string)
        
    Returns:
        Quoted string if it contains special characters, otherwise the string value
    """
    if value is None:
        return ''
    
    # Convert to JSON-serializable format first (handles datetime/date objects)
    value = make_json_serializable(value)
    value_str = str(value)
    
    # Check if quoting is needed (contains comma, newline, or quote)
    if ',' in value_str or '\n' in value_str or '"' in value_str:
        # Escape quotes by doubling them
        escaped = value_str.replace('"', '""')
        return f'"{escaped}"'
    
    return value_str


def format_notecards_fields_raw(cards, field_names, cache):
    """
    Format notecards with selected fields in raw CSV format.
    
    Outputs comma-separated field values with CSV-style quoting.
    Uses cross-product behavior for multiple field values.
    
    Args:
        cards: List of Notecard instances
        field_names: List of field names to extract
        cache: NotecardCache instance for accessing field indices
        
    Returns:
        String with CSV-formatted output, one line per combination
    """
    import itertools
    
    lines = []
    
    for card in cards:
        field_values = extract_field_values(card, field_names, cache)
        
        # Get lists of values for each field
        value_lists = []
        for field_name in field_names:
            values = field_values.get(field_name, [])
            # If no values, use empty string for cross-product
            if not values:
                value_lists.append([''])
            else:
                value_lists.append(values)
        
        # Generate cross-product of all field values
        for value_combination in itertools.product(*value_lists):
            # Quote each value and join with commas
            quoted_values = [csv_quote(v) for v in value_combination]
            lines.append(','.join(quoted_values))
    
    return '\n'.join(lines) + ('\n' if lines else '')


def make_json_serializable(value):
    """
    Convert a value to a JSON-serializable format.
    
    Handles datetime and date objects by converting them to ISO format strings.
    
    Args:
        value: Any value that might not be JSON serializable
        
    Returns:
        JSON-serializable version of the value
    """
    from datetime import datetime, date
    
    if isinstance(value, datetime):
        # Convert datetime to ISO format string with timezone info
        return value.isoformat()
    elif isinstance(value, date):
        # Convert date to ISO format string
        return value.isoformat()
    else:
        # Return the value as-is (strings, numbers, etc.)
        return value


def format_notecards_fields_json(cards, field_names, cache):
    """
    Format notecards with selected fields in JSON format.
    
    Returns an array of objects, where each object represents a notecard
    with field names as keys and arrays of values as values.
    
    Args:
        cards: List of Notecard instances
        field_names: List of field names to extract
        cache: NotecardCache instance for accessing field indices
        
    Returns:
        List of dictionaries suitable for JSON serialization
    """
    result = []
    
    for card in cards:
        field_values = extract_field_values(card, field_names, cache)
        
        # Convert all field values to JSON-serializable format
        serializable_values = {}
        for field_name, values in field_values.items():
            serializable_values[field_name] = [make_json_serializable(v) for v in values]
        
        result.append(serializable_values)
    
    return result


def get_sort_key_for_card(card, cache, order_by_key):
    """
    Build a sort key for a notecard.
    
    Args:
        card: Notecard instance
        cache: NotecardCache instance
        order_by_key: Key to sort by ('id' or field name)
    
    Returns:
        Tuple for sorting:
        - For 'id': (primary_label, primary_label)
        - For field with value: (0, min_value, primary_label)
        - For missing/unparseable values: (1, None, primary_label) which sorts last
    """
    primary_label = card.primary_label
    
    if order_by_key == 'id':
        # Sort by primary label itself
        return (primary_label, primary_label)
    
    # Sort by a field value
    field_name_upper = order_by_key.upper()
    
    try:
        # Get the field index
        field_index = cache.field_index(field_name_upper)
        
        # Get values for this card's primary label from the inverse index
        values = field_index.inverse.get(primary_label, [])
        
        if not values:
            # No value for this field - sort last
            # Use (1, None, primary_label) where 1 > 0 ensures it comes after real values
            return (1, None, primary_label)
        
        # Use the minimum value for sorting (if multiple values exist)
        min_value = min(values)
        
        # Return (0, value, primary_label) - 0 ensures real values come before None
        return (0, min_value, primary_label)
        
    except (KeyError, AttributeError):
        # Field doesn't exist in config or other error - sort last
        return (1, None, primary_label)


def execute_query_filter(cache, query_string):
    """
    Execute a query filter and return matching notecards.
    
    Args:
        cache: NotecardCache instance
        query_string: Query expression string to parse and evaluate
    
    Returns:
        List of unique notecards matching the query
    
    Raises:
        RemyError: If query parsing or evaluation fails
    """
    from remy.query.parser import parse_query
    from remy.query.eval import evaluate_query, resolve_macros, parse_config_macros
    from remy.query.util import extract_field_names
    from remy.exceptions import RemyError
    
    # Parse the query into an AST
    ast = parse_query(query_string)
    
    # Load config macros if available
    config_macros = None
    try:
        config_module = cache.config_module
        if hasattr(config_module, 'MACROS'):
            # Parse config macro strings into MacroDefinition nodes
            config_macros = parse_config_macros(config_module.MACROS)
    except RemyError as e:
        # Config file not found - this is okay for the query command
        # Macros are optional
        if "Configuration file not found" in str(e):
            pass
        else:
            # Other RemyErrors (e.g., macro parsing errors) should propagate
            raise
    
    # Resolve macros before field extraction
    # This expands all macro definitions and returns the @main expression AST
    # Any MacroReference nodes left after this are pseudo-indices
    ast = resolve_macros(ast, config_macros)
    
    # Extract field names from the fully expanded AST
    # After macro expansion, anything with '@' is a field name (pseudo-index)
    field_names = extract_field_names(ast)
    
    # Build field indices dictionary
    # This will handle pseudo-indices like @id and @primary-label
    field_indices = cache.field_indices(field_names)
    
    # Evaluate the query to get matching primary labels
    matching_labels = evaluate_query(ast, field_indices)
    
    # Look up notecards for matching labels
    unique_cards = []
    for label in matching_labels:
        card = cache.cards_by_label.get(label)
        if card is not None:
            # Only add each card once (by primary label)
            unique_cards.append(card)
    
    # Deduplicate by primary label (in case we have multi-label cards)
    unique_cards = list({card.primary_label: card for card in unique_cards}.values())
    
    return unique_cards


@click.group()
@click.option('--cache', envvar='REMY_CACHE', help='Location of Remy notecard cache.')
@click.pass_context
def main(ctx, cache):
    """Remy notecard management system."""
    from remy import NotecardCache
    from remy.url import URL
    from pathlib import Path

    global notecard_cache

    # Store cache in context for subcommands
    ctx.ensure_object(dict)
    
    # Only load the cache if it's provided (some commands like 'complete' don't need it)
    if cache:
        url = URL(cache)

        if not url.scheme:
            url = URL(Path(cache))

        notecard_cache = NotecardCache(url)
        ctx.obj['cache'] = notecard_cache
    else:
        ctx.obj['cache'] = None


@main.command()
@click.argument('query_expr', required=False)
@click.option('--where', 'where_clause', help='Query expression (alternative to positional argument)')
@click.option('--all', 'show_all', is_flag=True, help='Return all notecards')
@click.option('--format', 'output_format',
              type=click.Choice(['raw', 'json'], case_sensitive=False),
              default='raw',
              help='Output format (default: raw)')
@click.option('--pretty-print', 'pretty_print', is_flag=True,
              help='Pretty-print JSON output (only applies to --format=json)')
@click.option('--order-by', 'order_by_key', default='id',
              help='Sort notecards by key: "id" for primary label (default), or any field name')
@click.option('--reverse', 'reverse_order', is_flag=True,
              help='Reverse the sort order')
@click.option('--limit', '-l', 'limit', type=click.IntRange(min=1),
              help='Limit the number of results returned (applied after sorting)')
@click.option('--fields', 'fields_option',
              help='Comma-separated list of field names to extract (supports @primary-label, @label, @title/@first-block)')
@click.pass_context
def query(ctx, query_expr, where_clause, show_all, output_format, pretty_print, order_by_key, reverse_order, limit, fields_option):
    """Query and filter notecards.

    Results are returned in deterministic order. By default, notecards are sorted
    by primary label (id). Use --order-by to sort by a metadata field instead.
    Use --reverse to reverse the sort order. Use --limit to restrict the number
    of results returned.

    Examples:
      remy --cache /path/to/notes query --all
      remy --cache /path/to/notes query "tag = 'inbox'"
      remy --cache /path/to/notes query --where "tag = 'inbox'"
      remy --cache /path/to/notes query --all --order-by priority
      remy --cache /path/to/notes query --all --order-by created --reverse
      remy --cache /path/to/notes query --all --order-by created --limit 1
    """
    cache = ctx.obj.get('cache')
    
    if cache is None:
        raise click.UsageError("The --cache option is required for this command.")

    # Validate input: must have either query_expr, where_clause, or --all
    if not query_expr and not where_clause and not show_all:
        raise click.UsageError(
            "Must provide a query expression, use --where flag, or specify --all flag.\n"
            "Examples:\n"
            "  remy --cache /path query --all\n"
            "  remy --cache /path query \"tag = 'inbox'\"\n"
            "  remy --cache /path query --where \"tag = 'inbox'\""
        )

    # Get the query expression (prefer positional over --where)
    final_query = query_expr or where_clause

    # Determine which notecards to return
    if show_all:
        # Return all notecards when --all flag is used
        unique_cards = list({card.primary_label: card for card in cache.cards_by_label.values()}.values())
    elif final_query:
        # Parse and evaluate the query expression
        from remy.exceptions import RemyError
        
        try:
            unique_cards = execute_query_filter(cache, final_query)
        except RemyError as e:
            # Parse or evaluation error - print message and exit
            click.echo(f"Error: {str(e)}", err=True)
            sys.exit(1)
        except Exception as e:
            # Unexpected error - print message and exit
            click.echo(f"Unexpected error: {str(e)}", err=True)
            sys.exit(1)
    else:
        # This shouldn't happen due to earlier validation, but handle it anyway
        unique_cards = []

    # Sort by primary label for consistent output
    unique_cards.sort(key=lambda c: get_sort_key_for_card(c, cache, order_by_key), reverse=reverse_order)

    # Apply limit if specified
    if limit is not None:
        unique_cards = unique_cards[:limit]

    # Parse fields if specified
    field_names = parse_fields_option(fields_option) if fields_option else None

    # Format and output
    if field_names:
        # Field selection mode
        if output_format.lower() == 'json':
            import json
            # Use field-specific JSON formatting
            result = format_notecards_fields_json(unique_cards, field_names, cache)
            
            if pretty_print:
                output = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                output = json.dumps(result, ensure_ascii=False)
            
            print(output)
        else:
            # Use field-specific raw (CSV) formatting
            output = format_notecards_fields_raw(unique_cards, field_names, cache)
            print(output, end='')
    else:
        # Standard full notecard output
        if output_format.lower() == 'json':
            import json
            # Collect full text of each notecard
            notecard_texts = []
            for card in unique_cards:
                full_text = format_notecard_raw(card)
                notecard_texts.append(full_text)
            
            # Serialize to JSON
            if pretty_print:
                output = json.dumps(notecard_texts, ensure_ascii=False, indent=2)
            else:
                output = json.dumps(notecard_texts, ensure_ascii=False)
            
            print(output)
        elif output_format.lower() == 'raw':
            output = format_notecards_raw(unique_cards)
            print(output, end='')


@main.group()
@click.pass_context
def index(ctx):
    """Manage and inspect notecard field indices."""
    pass


@index.command('list')
@click.option('--format', 'output_format',
              type=click.Choice(['raw', 'json'], case_sensitive=False),
              default='raw',
              help='Output format (default: raw)')
@click.option('--pretty-print', 'pretty_print', is_flag=True,
              help='Pretty-print JSON output (only applies to --format=json)')
@click.option('--include-all-fields', 'include_all_fields', is_flag=True,
              help='Include field names from cards that do not have parsers defined')
@click.pass_context
def index_list(ctx, output_format, pretty_print, include_all_fields):
    """List all available field index names.
    
    Lists all field indices configured in the cache's PARSER_BY_FIELD_NAME dictionary.
    With --include-all-fields, also includes field names found in cards that don't
    have parsers defined (this scans all cards and may be slower for large caches).
    
    Examples:
      remy --cache /path/to/notes index list
      remy --cache /path/to/notes index list --format json
      remy --cache /path/to/notes index list --format json --pretty-print
      remy --cache /path/to/notes index list --include-all-fields
    """
    cache = ctx.obj['cache']
    
    try:
        # Get field names from config
        field_names = set(cache.config_module.PARSER_BY_FIELD_NAME.keys())
    except AttributeError:
        click.echo(
            "Error: Configuration file missing or PARSER_BY_FIELD_NAME not defined.\n"
            "Please check your '.remy/config.py' file.",
            err=True
        )
        sys.exit(1)
    
    # If requested, also include field names from cards that don't have parsers
    if include_all_fields:
        from remy.ast.parse import parse_content
        from remy.ast import Field
        
        for label, card in cache.cards_by_label.items():
            # Only process each card once (by primary label)
            if label != card.primary_label:
                continue
            
            # Extract field names from card content
            for node in parse_content(card.content):
                if isinstance(node, Field):
                    field_names.add(node.label.upper())
    
    # Sort field names for consistent output
    field_names = sorted(field_names)
    
    # Format and output
    if output_format.lower() == 'json':
        if pretty_print:
            output = json.dumps(field_names, ensure_ascii=False, indent=2)
        else:
            output = json.dumps(field_names, ensure_ascii=False)
        print(output)
    else:  # raw format
        for name in field_names:
            print(name)


@index.command('dump')
@click.argument('index_name')
@click.option('--format', 'output_format',
              type=click.Choice(['raw', 'json'], case_sensitive=False),
              default='raw',
              help='Output format (default: raw)')
@click.option('--pretty-print', 'pretty_print', is_flag=True,
              help='Pretty-print JSON output (only applies to --format=json)')
@click.option('--full', 'output_mode', flag_value='full', default=True,
              help='Output (label, value) pairs (default)')
@click.option('--labels', 'output_mode', flag_value='labels',
              help='Output labels only')
@click.option('--values', 'output_mode', flag_value='values',
              help='Output values only')
@click.option('-d', '--delimiter', 'delimiter', default='comma',
              help='Delimiter for raw format: comma, tab, pipe, or literal character (default: comma)')
@click.option('-u', '--unique', 'unique', is_flag=True,
              help='Remove duplicate entries while maintaining sort order')
@click.pass_context
def index_dump(ctx, index_name, output_format, pretty_print, output_mode, delimiter, unique):
    """Dump the contents of a specific field index.
    
    Shows labels and/or values from the specified field index.
    The output is sorted according to the underlying index structure.
    
    Examples:
      remy --cache /path/to/notes index dump TAG
      remy --cache /path/to/notes index dump TAG --labels
      remy --cache /path/to/notes index dump TAG --values
      remy --cache /path/to/notes index dump TAG -d tab
      remy --cache /path/to/notes index dump TAG --unique
      remy --cache /path/to/notes index dump TAG --format json --pretty-print
    """
    cache = ctx.obj['cache']
    
    # Normalize delimiter - check named delimiters first, then allow literal characters
    named_delimiters = {
        'comma': ',',
        'tab': '\t',
        'pipe': '|',
    }
    
    if delimiter in named_delimiters:
        delimiter_char = named_delimiters[delimiter]
    elif delimiter in (',', '\t', '|'):
        delimiter_char = delimiter
    else:
        click.echo(
            f"Error: Unknown delimiter '{delimiter}'.\n"
            f"Supported delimiters: comma, tab, pipe, or literal characters (,, \\t, |)",
            err=True
        )
        sys.exit(1)
    
    # Get the field index
    try:
        field_index = cache.field_index(index_name)
    except KeyError:
        click.echo(
            f"Error: Field index '{index_name}' not found in configuration.\n"
            f"Please check your '.remy/config.py' file and ensure '{index_name}' "
            f"is defined in PARSER_BY_FIELD_NAME.",
            err=True
        )
        sys.exit(1)
    except AttributeError:
        click.echo(
            "Error: Configuration file missing or PARSER_BY_FIELD_NAME not defined.\n"
            "Please check your '.remy/config.py' file.",
            err=True
        )
        sys.exit(1)
    
    # Collect data based on output mode
    data = []
    
    if output_mode == 'full':
        # Output (label, value) pairs from forward index
        for (type_id, value), label in field_index.index:
            data.append((label, value))
    elif output_mode == 'labels':
        # Output labels only from forward index
        for (type_id, value), label in field_index.index:
            data.append(label)
    elif output_mode == 'values':
        # Output values only from forward index
        for (type_id, value), label in field_index.index:
            data.append(value)
    
    # Apply unique filter if requested
    if unique:
        seen = set()
        unique_data = []
        for item in data:
            # For tuples/lists, convert to tuple for hashing; for single values, use as-is
            # Convert non-hashable types to their string representation for hashing
            if isinstance(item, (list, tuple)):
                try:
                    hash_key = tuple(item)
                except TypeError:
                    # Handle non-hashable items in tuples (e.g., datetime objects)
                    hash_key = tuple(str(x) for x in item)
            else:
                try:
                    hash_key = item
                    # Test if hashable
                    hash(hash_key)
                except TypeError:
                    # Handle non-hashable single items
                    hash_key = str(item)
            
            if hash_key not in seen:
                seen.add(hash_key)
                unique_data.append(item)
        data = unique_data
    
    # Format and output
    if output_format.lower() == 'json':
        # Convert non-serializable types to strings
        serializable_data = []
        for item in data:
            if isinstance(item, (list, tuple)):
                serializable_item = []
                for val in item:
                    serializable_item.append(_make_json_serializable(val))
                serializable_data.append(serializable_item)
            else:
                serializable_data.append(_make_json_serializable(item))
        
        if pretty_print:
            output = json.dumps(serializable_data, ensure_ascii=False, indent=2)
        else:
            output = json.dumps(serializable_data, ensure_ascii=False)
        print(output)
    else:  # raw format
        for item in data:
            if isinstance(item, (list, tuple)):
                # Multiple values - use CSV writer for proper escaping
                output_buffer = StringIO()
                writer = csv.writer(output_buffer, delimiter=delimiter_char, lineterminator='')
                writer.writerow([str(val) for val in item])
                print(output_buffer.getvalue())
            else:
                # Single value - check if escaping is needed
                value_str = str(item)
                if delimiter_char in value_str or '"' in value_str or '\n' in value_str:
                    # Use CSV writer for proper escaping
                    output_buffer = StringIO()
                    writer = csv.writer(output_buffer, delimiter=delimiter_char, lineterminator='')
                    writer.writerow([value_str])
                    print(output_buffer.getvalue())
                else:
                    # No escaping needed
                    print(value_str)


def _make_json_serializable(value):
    """Convert non-JSON-serializable types to reasonable string representations."""
    from datetime import datetime, date, time, timedelta
    
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    elif isinstance(value, timedelta):
        return str(value)
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        # Fallback: convert to string
        return str(value)


@main.group()
@click.pass_context
def macro(ctx):
    """Manage and inspect query macros."""
    pass


@macro.command('list')
@click.option('--full', 'output_mode', flag_value='full',
              help='Display macro definitions in @NAME := DEFINITION format')
@click.option('--expand', 'output_mode', flag_value='expand',
              help='Display expanded macro forms after AST substitution')
@click.pass_context
def macro_list(ctx, output_mode):
    """List all configured macros from the config file.
    
    By default, displays macro names only, one per line.
    Use --full to show full definitions or --expand to show expanded forms.
    
    Examples:
      remy --cache /path/to/notes macro list
      remy --cache /path/to/notes macro list --full
      remy --cache /path/to/notes macro list --expand
    """
    from remy.query.eval import parse_config_macros, resolve_macros
    from remy.query.parser import parse_query
    from remy.exceptions import RemyError
    
    cache = ctx.obj['cache']
    
    if cache is None:
        click.echo(
            "Error: The --cache option is required for this command.",
            err=True
        )
        sys.exit(1)
    
    # Load macros from config
    try:
        config_macros_dict = cache.config_module.MACROS
    except AttributeError:
        # MACROS not defined in config
        config_macros_dict = {}
    
    if not config_macros_dict:
        # No macros defined - exit silently with no output
        return
    
    # Parse the config macros
    try:
        parsed_macros = parse_config_macros(config_macros_dict)
    except RemyError as e:
        click.echo(f"Error parsing config macros: {e}", err=True)
        sys.exit(1)
    
    # Sort macro names alphabetically
    macro_names = sorted(parsed_macros.keys())
    
    if not output_mode:
        # Default mode: just print macro names with @ prefix
        for name in macro_names:
            print(f"@{name}")
    
    elif output_mode == 'full':
        # Full mode: print @NAME := DEFINITION format
        for name in macro_names:
            # Get the original definition string from config
            # Find the matching entry in the original config dict
            original_def = None
            for key, value in config_macros_dict.items():
                # Parse this definition to check its name
                try:
                    temp_ast = parse_query(value)
                    from remy.query.ast_nodes import StatementList, MacroDefinition
                    if isinstance(temp_ast, StatementList) and len(temp_ast.statements) == 1:
                        temp_def = temp_ast.statements[0]
                    else:
                        temp_def = temp_ast
                    
                    if isinstance(temp_def, MacroDefinition) and temp_def.name == name:
                        original_def = value
                        break
                except Exception:
                    # If parsing fails, skip this entry
                    continue
            
            if original_def:
                print(original_def)
            else:
                # Fallback: reconstruct from parsed macro
                macro_def = parsed_macros[name]
                body_str = _format_ast_node(macro_def.body)
                if macro_def.parameters:
                    params = ', '.join(macro_def.parameters)
                    print(f"@{name}({params}) := {body_str}")
                else:
                    print(f"@{name} := {body_str}")
    
    elif output_mode == 'expand':
        # Expand mode: parse and expand each macro using resolve_macros
        for name in macro_names:
            macro_def = parsed_macros[name]
            
            try:
                # Create a macro reference to expand
                from remy.query.ast_nodes import MacroReference
                macro_ref = MacroReference(name, [])
                
                # Resolve the macro using all config macros
                expanded = resolve_macros(macro_ref, parsed_macros)
                
                # Format the expanded AST
                expanded_str = _format_ast_node(expanded)
                print(f"@{name} := {expanded_str}")
                
            except RemyError as e:
                click.echo(f"Error expanding macro @{name}: {e}", err=True)
                sys.exit(1)


def _format_ast_node(node):
    """
    Format an AST node as a string for display.
    
    Args:
        node: AST node to format
        
    Returns:
        String representation of the node
    """
    from remy.query.ast_nodes import (
        Literal, Identifier, Compare, And, Or, Not, In,
        BinaryOp, MacroReference
    )
    
    if isinstance(node, Literal):
        # Format literals with proper quoting
        if isinstance(node.value, str):
            return f'"{node.value}"'
        else:
            return str(node.value)
    
    elif isinstance(node, Identifier):
        return node.name
    
    elif isinstance(node, Compare):
        left = _format_ast_node(node.left)
        right = _format_ast_node(node.right)
        return f"{left}{node.operator}{right}"
    
    elif isinstance(node, And):
        left = _format_ast_node(node.left)
        right = _format_ast_node(node.right)
        return f"({left} AND {right})"
    
    elif isinstance(node, Or):
        left = _format_ast_node(node.left)
        right = _format_ast_node(node.right)
        return f"({left} OR {right})"
    
    elif isinstance(node, Not):
        operand = _format_ast_node(node.operand)
        return f"NOT {operand}"
    
    elif isinstance(node, In):
        left = _format_ast_node(node.left)
        values = ', '.join(_format_ast_node(v) for v in node.values)
        return f"{left} IN ({values})"
    
    elif isinstance(node, BinaryOp):
        left = _format_ast_node(node.left)
        right = _format_ast_node(node.right)
        return f"({left} {node.operator} {right})"
    
    elif isinstance(node, MacroReference):
        if node.arguments:
            args = ', '.join(_format_ast_node(arg) for arg in node.arguments)
            return f"@{node.name}({args})"
        else:
            return f"@{node.name}"
    
    else:
        # Fallback for other node types
        return str(node)


@main.command()
@click.option('-o', '--output', 'output_file', type=click.Path(), help='Output file path for completion script')
@click.argument('output_path', required=False, type=click.Path())
def complete(output_file, output_path):
    """Generate bash completion script for remy.

    Without arguments, prints the script to stdout.
    Use -o/--output or a positional argument to write to a file.

    Examples:
      remy complete > ~/.bash_completion.d/remy
      remy complete -o ~/.bash_completion.d/remy
      remy complete ~/.bash_completion.d/remy
    """
    import click.shell_completion as sc
    from pathlib import Path

    # Validate that both output methods are not specified
    if output_file and output_path:
        raise click.UsageError(
            "Cannot specify both -o/--output option and positional argument. "
            "Use one or the other to specify the output file."
        )

    # Determine the output destination
    output_dest = output_file or output_path

    # Generate the bash completion script
    bash_complete = sc.BashComplete(None, {}, "remy", "_REMY_COMPLETE")
    script = bash_complete.source()

    # Add installation instructions header
    header = """# Bash completion script for remy
#
# Installation Instructions:
# -------------------------
# 1. Ensure you have bash-completion package installed:
#    - Ubuntu/Debian: sudo apt-get install bash-completion
#    - macOS (with Homebrew): brew install bash-completion
#
# 2. Install this completion script by one of these methods:
#
#    Method A - System-wide (requires root):
#      sudo cp this_file /etc/bash_completion.d/remy
#
#    Method B - User-specific:
#      mkdir -p ~/.bash_completion.d
#      cp this_file ~/.bash_completion.d/remy
#      Add this line to your ~/.bashrc:
#        source ~/.bash_completion.d/remy
#
#    Method C - Inline in .bashrc:
#      Simply add the contents of this file to your ~/.bashrc
#
# 3. Reload your shell or run: source ~/.bashrc
#
# After installation, you can use tab completion with remy commands:
#   remy <TAB>           # Shows available commands
#   remy query --<TAB>   # Shows available options
#

"""

    full_script = header + script

    # Write to file or stdout
    if output_dest:
        try:
            output_path_obj = Path(output_dest)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            output_path_obj.write_text(full_script)
            click.echo(f"Bash completion script written to: {output_dest}")
        except OSError as e:
            raise click.ClickException(f"Failed to write completion script to '{output_dest}': {e}")
    else:
        # Output to stdout
        click.echo(full_script)


@main.command()
@click.argument('label', required=False)
@click.pass_context
def edit(ctx, label):
    """Edit a notecard by label or create a new notecard.

    When LABEL is provided, opens the corresponding notecard in Vim.
    When no LABEL is provided, creates a new dated notecard file and opens it in Vim.

    Examples:
      remy --cache /path/to/notes edit task1
      remy --cache /path/to/notes edit
    """
    import os
    from datetime import datetime, UTC
    from pathlib import Path
    from remy.url import URL
    
    cache = ctx.obj.get('cache')
    
    if cache is None:
        raise click.UsageError("The --cache option is required for this command.")
    
    cache_url = cache.url

    if cache_url.scheme != 'file':
        click.echo(
            f"Error: Unable to open local cache for editing. cache: '{cache_url.geturl()}'",
            err=True
        )
        sys.exit(1)

    if label:
        card = cache.find_card_by_label(label)

        if not card:
            click.echo(
                f"Error: Unable to find card for label in cache. cache: '{cache_url.geturl()}' label: '{label}'",
                err=True
            )
            sys.exit(1)

        source_url = card.source_url
        source_path = source_url.path
        line_no = int(source_url.fragment) + 1
    else:
        now = datetime.now(UTC)
        source_path = cache_url.path / f'{now.year:04}/{now.month:02}/{now.day:02}.ntc'
        line_no = 0

    source_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        'vim',
        str(source_path),
    ]

    if line_no:
        command.append(f"+{line_no}")
        command.append('+normal ztzo')
    elif source_path.exists():
        command.append('+normal G')

    os.execvp(command[0], command)


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
