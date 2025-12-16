import click

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
@click.pass_context
def query(ctx, query_expr, where_clause, show_all, output_format):
    """Query and filter notecards.

    Examples:
      remy --cache /path/to/notes query --all
      remy --cache /path/to/notes query "tag = 'inbox'"
      remy --cache /path/to/notes query --where "tag = 'inbox'"
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

    # For now, ignore the query and return all notecards
    # (filtering will be implemented in a future issue)
    if final_query and not show_all:
        # Query expression provided but filtering not yet implemented
        # Just show all notecards for now
        pass

    # Get all unique notecards (deduplicate by primary label)
    # cards_by_label.values() contains duplicate references for multi-label cards
    unique_cards = list({card.primary_label: card for card in cache.cards_by_label.values()}.values())

    # Sort by primary label for consistent output
    unique_cards.sort(key=lambda c: c.primary_label)

    # Format and output
    if output_format.lower() == 'json':
        raise NotImplementedError(
            "JSON output format is not yet implemented. "
            "Please use '--format=raw' (the default) for now."
        )
    elif output_format.lower() == 'raw':
        output = format_notecards_raw(unique_cards)
        print(output, end='')


if __name__ == '__main__':
    main(auto_envvar_prefix='REMY')
