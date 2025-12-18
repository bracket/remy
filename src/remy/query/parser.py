"""
Lark-based parser for WHERE clause query language.

This module provides the parse_query function that converts SQL-like WHERE clauses
into an abstract syntax tree (AST) for later evaluation.
"""

from lark import Transformer, exceptions as lark_exceptions
from datetime import datetime, date

from remy.exceptions import RemyError
from remy.query.grammar import get_parser
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, In, And, Or, Not,
    DateTimeLiteral, DateLiteral
)


class QueryTransformer(Transformer):
    """
    Transforms Lark parse tree into AST nodes.

    Each method corresponds to a rule in the grammar and transforms
    the matched tree into the appropriate AST node.
    """

    def or_op(self, args):
        """Transform OR expression."""
        left, right = args
        return Or(left, right)

    def and_op(self, args):
        """Transform AND expression."""
        left, right = args
        return And(left, right)

    def not_op(self, args):
        """Transform NOT expression."""
        operand = args[0]
        return Not(operand)

    def compare(self, args):
        """Transform comparison expression."""
        left, op_token, right = args
        return Compare(str(op_token), left, right)

    def in_op(self, args):
        """Transform IN expression."""
        left, values = args
        return In(left, values)

    def identifier(self, args):
        """Transform identifier."""
        name = str(args[0])
        return Identifier(name)

    def literal(self, args):
        """Transform literal value."""
        token = args[0]

        if token.type == 'STRING':
            # Remove quotes and process escape sequences
            value = str(token)[1:-1]  # Remove surrounding quotes
            # Process basic escape sequences - order matters!
            value = value.replace('\\\\', '\x00')  # Temporarily store escaped backslash
            value = value.replace("\\'", "'")      # Replace escaped single quote
            value = value.replace('\\"', '"')      # Replace escaped double quote
            value = value.replace('\x00', '\\')    # Restore backslash
            return Literal(value)
        elif token.type == 'NUMBER':
            # Parse as int or float
            num_str = str(token)
            if '.' in num_str or 'e' in num_str.lower():
                return Literal(float(num_str))
            else:
                return Literal(int(num_str))
        elif token.type == 'TRUE':
            return Literal(True)
        elif token.type == 'FALSE':
            return Literal(False)
        elif token.type == 'NULL':
            return Literal(None)
        else:
            raise RemyError(f"Unknown literal type: {token}")

    def list_literal(self, args):
        """Transform list literal."""
        # Filter out None values (from optional empty lists)
        return [item for item in args if item is not None]

    def datetime_literal(self, args):
        """Transform datetime literal (e.g., '2024-01-31 15:30:00'::timestamp)."""
        string_token = args[0]
        # Remove quotes from the string
        datetime_str = str(string_token)[1:-1]
        
        try:
            # Try to parse datetime - fromisoformat handles timezone automatically
            dt = datetime.fromisoformat(datetime_str)
            # Convert to UTC if timezone-aware
            if dt.tzinfo is not None:
                # Convert to UTC and make naive
                dt = dt.astimezone(tz=None).replace(tzinfo=None)
            return DateTimeLiteral(dt)
        except ValueError as e:
            raise RemyError(
                f"Invalid datetime format: '{datetime_str}'. "
                f"Expected ISO format 'YYYY-MM-DD HH:MM:SS' with optional timezone. "
                f"Error: {str(e)}"
            )

    def date_literal(self, args):
        """Transform date literal (e.g., '2024-01-31'::date)."""
        string_token = args[0]
        # Remove quotes from the string
        date_str = str(string_token)[1:-1]
        
        try:
            # Parse date in ISO format
            dt = date.fromisoformat(date_str)
            return DateLiteral(dt)
        except ValueError as e:
            raise RemyError(
                f"Invalid date format: '{date_str}'. "
                f"Expected ISO format 'YYYY-MM-DD'. "
                f"Error: {str(e)}"
            )


def parse_query(query):
    """
    Parse a WHERE clause query string into an AST.

    Args:
        query: A string containing a SQL-like WHERE clause

    Returns:
        An AST node representing the parsed query

    Raises:
        RemyError: If the query is malformed or cannot be parsed

    Examples:
        >>> parse_query("status = 'active'")
        Compare('=', Identifier('status'), Literal('active'))

        >>> parse_query("age > 18 AND name = 'Alice'")
        And(Compare('>', Identifier('age'), Literal(18)),
            Compare('=', Identifier('name'), Literal('Alice')))
    """
    if not query or not query.strip():
        raise RemyError("Query cannot be empty")

    try:
        parser = get_parser()
        tree = parser.parse(query)
        transformer = QueryTransformer()
        ast = transformer.transform(tree)
        return ast
    except lark_exceptions.LarkError as e:
        # Convert Lark exceptions to RemyError with helpful messages
        raise RemyError(f"Failed to parse query: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors
        raise RemyError(f"Unexpected error parsing query: {str(e)}")
