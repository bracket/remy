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
@click.pass_context
def query(ctx, query_expr, where_clause, show_all, output_format, pretty_print, order_by_key, reverse_order, limit):
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

    # Format and output
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
@click.pass_context
def index_list(ctx, output_format, pretty_print):
    """List all available field index names.
    
    Lists all field indices configured in the cache's PARSER_BY_FIELD_NAME dictionary.
    
    Examples:
      remy --cache /path/to/notes index list
      remy --cache /path/to/notes index list --format json
      remy --cache /path/to/notes index list --format json --pretty-print
    """
    cache = ctx.obj['cache']
    
    try:
        # Get field names from config
        field_names = list(cache.config_module.PARSER_BY_FIELD_NAME.keys())
    except AttributeError:
        click.echo(
            "Error: Configuration file missing or PARSER_BY_FIELD_NAME not defined.\n"
            "Please check your '.remy/config.py' file.",
            err=True
        )
        sys.exit(1)
    
    # Sort field names for consistent output
    field_names.sort()
    
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
