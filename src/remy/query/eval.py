"""
Query evaluator for set-based label filtering.

This module evaluates parsed query ASTs against NotecardIndex objects to return
sets of matching notecard primary labels using efficient set-based operations.

Example usage:
    >>> from remy.query.parser import parse_query
    >>> from remy.query.eval import evaluate_query
    >>>
    >>> # Parse a query
    >>> ast = parse_query("status = 'active' AND priority = 'high'")
    >>>
    >>> # Evaluate against field indices
    >>> field_indices = {
    ...     'STATUS': status_index,
    ...     'PRIORITY': priority_index
    ... }
    >>> matching_labels = evaluate_query(ast, field_indices)
"""

from remy.exceptions import RemyError
from remy.query.ast_nodes import (
    ASTNode, Literal, Identifier, Compare, In, And, Or, Not,
    DateTimeLiteral, DateLiteral
)
from typing import TYPE_CHECKING, Dict, Set

if TYPE_CHECKING:
    from remy.notecard_index import NotecardIndex


def evaluate_query(ast: ASTNode, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate a query AST against field indices and return matching primary labels.

    This function evaluates query expressions using set-based operations over
    NotecardIndex lookups. It does not scan notecard objects or content directly.

    Args:
        ast: The parsed query AST node to evaluate
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels (strings) that match the query criteria

    Raises:
        RemyError: If the query uses unsupported operators or constructs

    Supported operations:
        - Compare with '=' operator: field = value
        - And: intersection of two sub-queries
        - Or: union of two sub-queries

    Not yet supported (will raise RemyError):
        - Compare with !=, <, <=, >, >= operators
        - Not: logical negation
        - In: membership testing

    Examples:
        >>> # Simple equality
        >>> ast = Compare('=', Identifier('status'), Literal('active'))
        >>> result = evaluate_query(ast, {'STATUS': status_index})

        >>> # AND operation
        >>> ast = And(
        ...     Compare('=', Identifier('status'), Literal('active')),
        ...     Compare('=', Identifier('priority'), Literal('high'))
        ... )
        >>> result = evaluate_query(ast, field_indices)

        >>> # OR operation
        >>> ast = Or(
        ...     Compare('=', Identifier('status'), Literal('active')),
        ...     Compare('=', Identifier('status'), Literal('pending'))
        ... )
        >>> result = evaluate_query(ast, field_indices)
    """
    if isinstance(ast, Compare):
        return _evaluate_compare(ast, field_indices)
    elif isinstance(ast, And):
        return _evaluate_and(ast, field_indices)
    elif isinstance(ast, Or):
        return _evaluate_or(ast, field_indices)
    elif isinstance(ast, Not):
        raise RemyError("NOT operator is not yet supported in query evaluation")
    elif isinstance(ast, In):
        raise RemyError("IN operator is not yet supported in query evaluation")
    else:
        raise RemyError(f"Unsupported AST node type: {type(ast).__name__}")


def _evaluate_compare(ast: Compare, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate a comparison operation.

    Args:
        ast: Compare AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels matching the comparison

    Raises:
        RemyError: If operands have wrong types
    """
    # Check for unsupported operators first
    if ast.operator == '!=':
        raise RemyError(
            f"Comparison operator '!=' is not yet supported."
        )
    
    # Left side must be an Identifier (field name)
    if not isinstance(ast.left, Identifier):
        raise RemyError(
            f"Left operand of comparison must be an Identifier (field name), "
            f"got {type(ast.left).__name__}"
        )

    # Right side must be a Literal (value to match) or temporal literal
    if not isinstance(ast.right, (Literal, DateTimeLiteral, DateLiteral)):
        raise RemyError(
            f"Right operand of comparison must be a Literal (value), "
            f"got {type(ast.right).__name__}"
        )

    field_name = ast.left.name.upper()
    
    # Extract the value from the literal
    value = ast.right.value

    # If the field doesn't exist in indices, return empty set
    # (fields are dynamic and optional)
    if field_name not in field_indices:
        return set()

    index = field_indices[field_name]

    # Handle different comparison operators
    if ast.operator == '=':
        # Exact match: find(low=value, high=value)
        return {label for _, label in index.find(low=value, high=value)}
    elif ast.operator == '<':
        # Less than: find all values up to (but not including) value
        # Use find() to get all values <= value, then filter out exact matches
        result = set()
        for field_value, label in index.find(high=value):
            if field_value < value:
                result.add(label)
        return result
    elif ast.operator == '<=':
        # Less than or equal: find all values up to and including value
        return {label for _, label in index.find(high=value)}
    elif ast.operator == '>':
        # Greater than: find all values from (but not including) value
        # Use find() to get all values >= value, then filter out exact matches
        result = set()
        for field_value, label in index.find(low=value):
            if field_value > value:
                result.add(label)
        return result
    elif ast.operator == '>=':
        # Greater than or equal: find all values from value onwards
        return {label for _, label in index.find(low=value)}
    else:
        raise RemyError(
            f"Unsupported comparison operator: '{ast.operator}'"
        )


def _evaluate_and(ast: And, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate an AND operation (set intersection).

    Args:
        ast: And AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels matching both sub-queries
    """
    left_result = evaluate_query(ast.left, field_indices)
    right_result = evaluate_query(ast.right, field_indices)

    # AND is set intersection
    return left_result & right_result


def _evaluate_or(ast: Or, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate an OR operation (set union).

    Args:
        ast: Or AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels matching either sub-query
    """
    left_result = evaluate_query(ast.left, field_indices)
    right_result = evaluate_query(ast.right, field_indices)

    # OR is set union
    return left_result | right_result
