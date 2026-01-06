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


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
