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

from remy.exceptions import RemyError, InvalidComparison
from remy.notecard_index import null
from remy.query.ast_nodes import (
    ASTNode, Literal, Identifier, Compare, In, And, Or, Not,
    DateTimeLiteral, DateLiteral, TimedeltaLiteral, BinaryOp, Timedelta
)
from remy.query.util import (
    add_timedelta_to_date, add_timedelta_to_datetime,
    subtract_timedelta_from_date, subtract_timedelta_from_datetime
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
        - Compare with '<' operator: field < value
        - Compare with '<=' operator: field <= value
        - Compare with '>' operator: field > value
        - Compare with '>=' operator: field >= value
        - And: intersection of two sub-queries
        - Or: union of two sub-queries

    Not yet supported (will raise RemyError):
        - Compare with != operator
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


def _evaluate_binary_op(ast: BinaryOp):
    """
    Evaluate a binary arithmetic operation (+ or -) between date/timestamp and timedelta.
    
    Args:
        ast: BinaryOp AST node
        
    Returns:
        Evaluated date or datetime value
        
    Raises:
        RemyError: If operands are invalid or operation is not supported
        InvalidComparison: If attempting to compare timedeltas
    """
    from datetime import datetime, date
    
    # Extract values from left and right operands
    if isinstance(ast.left, DateLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, DateTimeLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, TimedeltaLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, BinaryOp):
        # Recursive evaluation for nested arithmetic
        left_value = _evaluate_binary_op(ast.left)
    else:
        raise RemyError(
            f"Left operand of arithmetic must be a date, timestamp, or timedelta literal, "
            f"got {type(ast.left).__name__}"
        )
    
    if isinstance(ast.right, DateLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, DateTimeLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, TimedeltaLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, BinaryOp):
        # Recursive evaluation for nested arithmetic
        right_value = _evaluate_binary_op(ast.right)
    else:
        raise RemyError(
            f"Right operand of arithmetic must be a date, timestamp, or timedelta literal, "
            f"got {type(ast.right).__name__}"
        )
    
    # Handle addition
    if ast.operator == '+':
        # date + timedelta or timestamp + timedelta
        if isinstance(left_value, date) and not isinstance(left_value, datetime) and isinstance(right_value, Timedelta):
            return add_timedelta_to_date(left_value, right_value)
        elif isinstance(left_value, datetime) and isinstance(right_value, Timedelta):
            return add_timedelta_to_datetime(left_value, right_value)
        # timedelta + date or timedelta + timestamp (commutative)
        elif isinstance(left_value, Timedelta) and isinstance(right_value, date) and not isinstance(right_value, datetime):
            return add_timedelta_to_date(right_value, left_value)
        elif isinstance(left_value, Timedelta) and isinstance(right_value, datetime):
            return add_timedelta_to_datetime(right_value, left_value)
        else:
            raise RemyError(
                f"Invalid operands for addition: {type(left_value).__name__} + {type(right_value).__name__}. "
                f"Only date/timestamp + timedelta is supported."
            )
    
    # Handle subtraction
    elif ast.operator == '-':
        # date - timedelta or timestamp - timedelta
        if isinstance(left_value, date) and not isinstance(left_value, datetime) and isinstance(right_value, Timedelta):
            return subtract_timedelta_from_date(left_value, right_value)
        elif isinstance(left_value, datetime) and isinstance(right_value, Timedelta):
            return subtract_timedelta_from_datetime(left_value, right_value)
        else:
            raise RemyError(
                f"Invalid operands for subtraction: {type(left_value).__name__} - {type(right_value).__name__}. "
                f"Only date/timestamp - timedelta is supported."
            )
    
    else:
        raise RemyError(f"Unsupported binary operator: {ast.operator}")


def _evaluate_compare(ast: Compare, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate a comparison operation.

    Args:
        ast: Compare AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels matching the comparison

    Raises:
        RemyError: If operator is not supported or operands have wrong types
    """
    # Validate supported operators
    if ast.operator not in ('=', '<', '<=', '>', '>='):
        raise RemyError(
            f"Comparison operator '{ast.operator}' is not yet supported. "
            f"Currently supported: =, <, <=, >, >="
        )

    # Left side must be an Identifier (field name)
    if not isinstance(ast.left, Identifier):
        raise RemyError(
            f"Left operand of comparison must be an Identifier (field name), "
            f"got {type(ast.left).__name__}"
        )

    # Right side must be a Literal, temporal literal, or BinaryOp
    # If it's a BinaryOp, evaluate it first to get a value
    if isinstance(ast.right, BinaryOp):
        value = _evaluate_binary_op(ast.right)
    elif isinstance(ast.right, TimedeltaLiteral):
        # Timedelta literals can't be compared directly
        value = ast.right.value
    elif isinstance(ast.right, (Literal, DateTimeLiteral, DateLiteral)):
        value = ast.right.value
    else:
        raise RemyError(
            f"Right operand of comparison must be a Literal, temporal literal, or arithmetic expression, "
            f"got {type(ast.right).__name__}"
        )

    field_name = ast.left.name.upper()

    # Check if the value is a Timedelta - we don't support timedelta comparisons
    if isinstance(value, Timedelta):
        raise InvalidComparison(
            "Comparing timedeltas is not supported. "
            "Timedelta values can only be used in arithmetic with dates/timestamps."
        )

    # If the field doesn't exist in indices, return empty set
    # (fields are dynamic and optional)
    if field_name not in field_indices:
        return set()

    index = field_indices[field_name]

    # Use NotecardIndex.find() to get matching labels
    # The approach differs based on the operator:
    # - '=': find(low=value, high=value) - exact match
    # - '<': find(low=null, high=value) excluding value itself
    # - '<=': find(low=null, high=value) including value
    # - '>': find(low=value, high=null) excluding value itself
    # - '>=': find(low=value, high=null) including value
    
    if ast.operator == '=':
        # Exact match: low=value, high=value
        return {label for _, label in index.find(low=value, high=value)}
    
    elif ast.operator == '<':
        # Strictly less than: all values up to (but not including) value
        # Note: NotecardIndex.find() doesn't support exclusive boundaries,
        # so we retrieve values <= value and filter out the boundary value.
        # This is efficient because we only filter the boundary value(s).
        result = set()
        for field_value, label in index.find(low=null, high=value):
            if field_value < value:
                result.add(label)
        return result
    
    elif ast.operator == '<=':
        # Less than or equal: all values up to and including value
        return {label for _, label in index.find(low=null, high=value)}
    
    elif ast.operator == '>':
        # Strictly greater than: all values from value onwards, excluding value
        # Note: NotecardIndex.find() doesn't support exclusive boundaries,
        # so we retrieve values >= value and filter out the boundary value.
        # This is efficient because we only filter the boundary value(s).
        result = set()
        for field_value, label in index.find(low=value, high=null):
            if field_value > value:
                result.add(label)
        return result
    
    elif ast.operator == '>=':
        # Greater than or equal: all values from value onwards
        return {label for _, label in index.find(low=value, high=null)}
    
    # This should never be reached due to the operator validation above
    raise RemyError(f"Unexpected operator: {ast.operator}")


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
