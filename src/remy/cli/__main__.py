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


def extract_field_names(ast):
    """
    Extract all field names (identifiers) from a query AST.
    
    Args:
        ast: The query AST node
    
    Returns:
        Set of uppercase field names referenced in the query
    """
    from remy.query.ast_nodes import Identifier, Compare, And, Or, Not, In
    
    field_names = set()
    
    def visit(node):
        if isinstance(node, Identifier):
            field_names.add(node.name.upper())
        elif isinstance(node, Compare):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, And) or isinstance(node, Or):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, Not):
            visit(node.operand)
        elif isinstance(node, In):
            visit(node.left)
            for value in node.values:
                visit(value)
    
    visit(ast)
    return field_names


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

    # Determine which notecards to return
    if show_all:
        # Return all notecards when --all flag is used
        unique_cards = list({card.primary_label: card for card in cache.cards_by_label.values()}.values())
    elif final_query:
        # Parse and evaluate the query expression
        from remy.query.parser import parse_query
        from remy.query.eval import evaluate_query
        from remy.exceptions import RemyError
        
        try:
            # Parse the query into an AST
            ast = parse_query(final_query)
            
            # Extract field names from the AST
            field_names = extract_field_names(ast)
            
            # Build field indices dictionary
            field_indices = {}
            for field_name in field_names:
                try:
                    field_indices[field_name] = cache.field_index(field_name)
                except (KeyError, AttributeError):
                    # Field doesn't exist in config - evaluator will return empty set
                    pass
            
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
