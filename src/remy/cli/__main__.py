import click
import sys

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
    from remy.query.eval import evaluate_query
    from remy.query.util import extract_field_names
    
    # Parse the query into an AST
    ast = parse_query(query_string)
    
    # Extract field names from the AST
    field_names = extract_field_names(ast)
    
    # Build field indices dictionary
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
@click.option('--cache', envvar='REMY_CACHE', help='Location of Remy notecard cache.', required=True)
@click.pass_context
def main(ctx, cache):
    """Remy notecard management system."""
    from remy import NotecardCache
    from remy.url import URL
    from pathlib import Path

    global notecard_cache

    url = URL(cache)

    if not url.scheme:
        url = URL(Path(cache))

    notecard_cache = NotecardCache(url)

    # Store cache in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['cache'] = notecard_cache


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
    cache = ctx.obj['cache']

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
    
    cache = ctx.obj['cache']
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
