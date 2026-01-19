"""
Parser utilities for notecard metadata field values.

This module provides parsers that can be used in .remy/config.py to parse
notecard metadata field values, such as datetime fields with arithmetic support.

Example usage in .remy/config.py:
    from remy.parsers import parse_datetime_with_arithmetic

    PARSERS = {
        'tickle': parse_datetime_with_arithmetic,
        'deadline': parse_datetime_with_arithmetic,
    }
"""

import re
from datetime import datetime, timezone

from remy.exceptions import RemyError
from remy.query.parser import QueryTransformer
from remy.query.ast_nodes import DateTimeLiteral, BinaryOp
from remy.query.eval import _evaluate_binary_op


def parse_datetime_with_arithmetic(value: str) -> datetime:
    """
    Parse a datetime string with optional arithmetic expressions.

    This function parses datetime strings in ISO format with support for
    arithmetic operations using + and - operators with timedelta expressions.
    All returned datetime objects are timezone-aware (UTC).

    This parser reuses the datetime arithmetic parsing logic from the query
    module, ensuring that any updates to the query parser automatically
    reflect in this function.

    Supported formats:
        - Plain datetime: '2024-01-31' or '2024-01-31 15:30:00'
        - With addition: '2024-01-31 + 7 days'
        - With subtraction: '2024-01-31 - 2 weeks'
        - Chained operations: '2024-01-31 - 1 week + 3 days'
        - With time arithmetic: '2024-01-31 15:30:00 + 2 hours'

    Supported timedelta units:
        - day, days
        - hour, hours
        - minute, minutes
        - second, seconds
        - week, weeks
        - month, months
        - year, years
        - Time format: HH:MM or HH:MM:SS

    Args:
        value: A string containing a datetime with optional arithmetic

    Returns:
        A timezone-aware datetime object in UTC

    Raises:
        RemyError: If the input format is invalid or contains unsupported keywords

    Examples:
        >>> parse_datetime_with_arithmetic('2024-01-31')
        datetime.datetime(2024, 1, 31, 0, 0, tzinfo=datetime.timezone.utc)

        >>> parse_datetime_with_arithmetic('2024-01-31 15:30:00')
        datetime.datetime(2024, 1, 31, 15, 30, tzinfo=datetime.timezone.utc)

        >>> parse_datetime_with_arithmetic('2024-01-31 - 7 days')
        datetime.datetime(2024, 1, 24, 0, 0, tzinfo=datetime.timezone.utc)

        >>> parse_datetime_with_arithmetic('2024-12-25 + 2 weeks')
        datetime.datetime(2025, 1, 8, 0, 0, tzinfo=datetime.timezone.utc)

        >>> parse_datetime_with_arithmetic('2024-01-31 15:30:00 + 2 hours')
        datetime.datetime(2024, 1, 31, 17, 30, tzinfo=datetime.timezone.utc)
    """
    if not isinstance(value, str):
        raise RemyError(f"Expected string value, got {type(value).__name__}")

    value = value.strip()

    if not value:
        raise RemyError("Datetime value cannot be empty")

    # Check for 'now' or 'today' keywords (case-insensitive) and reject them
    if re.search(r'\b(now|today)\b', value, re.IGNORECASE):
        raise RemyError(
            "The 'now' and 'today' keywords are not supported in notecard metadata. "
            "Please use concrete timestamp values instead."
        )

    # Use the QueryTransformer to parse the datetime expression
    # This ensures we reuse all the existing parsing logic
    transformer = QueryTransformer()
    
    # Check if the string contains arithmetic operators using the transformer's method
    if transformer._contains_arithmetic(value):
        # Parse as temporal arithmetic expression (supports chained operations)
        ast_node = transformer._parse_temporal_arithmetic(value, target_type='timestamp')
        
        # Evaluate the BinaryOp to get the final datetime
        result = _evaluate_binary_op(ast_node)
        
        # Ensure the result is a datetime (not a date) and is timezone-aware in UTC
        if isinstance(result, datetime):
            if result.tzinfo is None:
                result = result.replace(tzinfo=timezone.utc)
            elif result.tzinfo != timezone.utc:
                result = result.astimezone(timezone.utc)
            return result
        else:
            # If we got a date, convert to datetime at midnight UTC
            return datetime.combine(result, datetime.min.time(), tzinfo=timezone.utc)
    else:
        # Plain datetime string without arithmetic - parse directly
        try:
            dt = datetime.fromisoformat(value)
            # If timezone-aware, convert to UTC
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            else:
                # If no timezone specified, treat as UTC
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError as e:
            raise RemyError(
                f"Invalid datetime format: '{value}'. "
                f"Expected ISO format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' with optional timezone. "
                f"Error: {str(e)}"
            )
