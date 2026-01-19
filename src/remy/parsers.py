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
from remy.query.ast_nodes import Timedelta


def parse_datetime_with_arithmetic(value: str) -> datetime:
    """
    Parse a datetime string with optional arithmetic expressions.

    This function parses datetime strings in ISO format with support for
    arithmetic operations using + and - operators with timedelta expressions.
    All returned datetime objects are timezone-aware (UTC).

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

    # Check if the string contains arithmetic operators
    if _contains_arithmetic(value):
        return _parse_temporal_arithmetic(value)
    else:
        # Plain datetime string without arithmetic
        return _parse_plain_datetime(value)


def _contains_arithmetic(expr_str: str) -> bool:
    """
    Check if a string expression contains arithmetic operators.

    Args:
        expr_str: The expression string to check

    Returns:
        True if the string contains arithmetic operators, False otherwise
    """
    # Check if there's a + (but not timezone like +05:00 or +HH:MM)
    if '+' in expr_str:
        # Exclude timezone offsets like +05:00
        if not re.search(r'[+\-]\d{2}:\d{2}\s*$', expr_str):
            return True
    
    # For -, check if it's arithmetic (not part of a date like YYYY-MM-DD or timezone)
    if '-' in expr_str:
        # Exclude timezone offsets like -08:00
        if re.search(r'[+\-]\d{2}:\d{2}\s*$', expr_str):
            return False
        # Match: complete ISO date/timestamp followed by - and then more content
        # This ensures we have a complete temporal value before the operator
        if re.search(r'\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?\s*-\s*\d', expr_str):
            return True
    
    return False


def _parse_plain_datetime(datetime_str: str) -> datetime:
    """
    Parse a plain datetime string without arithmetic.

    Args:
        datetime_str: ISO format datetime string

    Returns:
        A timezone-aware datetime object in UTC

    Raises:
        RemyError: If the datetime format is invalid
    """
    try:
        # Try to parse datetime - fromisoformat handles timezone automatically
        dt = datetime.fromisoformat(datetime_str)
        # If timezone-aware, convert to UTC
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        else:
            # If no timezone specified, treat as UTC
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError as e:
        raise RemyError(
            f"Invalid datetime format: '{datetime_str}'. "
            f"Expected ISO format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' with optional timezone. "
            f"Error: {str(e)}"
        )


def _parse_temporal_arithmetic(expr_str: str) -> datetime:
    """
    Parse a temporal arithmetic expression like '2024-01-31 - 2 days'.

    This function supports chained arithmetic operations like
    '2024-01-31 - 1 week + 3 days' by processing them left-to-right.

    Args:
        expr_str: The expression string (e.g., '2024-01-31 - 2 days')

    Returns:
        A timezone-aware datetime object in UTC

    Raises:
        RemyError: If the expression is invalid
    """
    # Find all arithmetic operators with their positions
    # We need to find + or - that's NOT part of the date (YYYY-MM-DD) or timezone
    
    # First, extract the base datetime (leftmost value before any arithmetic)
    base_match = re.match(r'^(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', expr_str)
    
    if not base_match:
        raise RemyError(f"Invalid temporal arithmetic expression: '{expr_str}'")
    
    base_datetime_str = base_match.group(1).strip()
    remaining = expr_str[base_match.end():].strip()
    
    # Parse the base datetime
    result = _parse_plain_datetime(base_datetime_str)
    
    # Now process all arithmetic operations in sequence
    # Pattern: operator followed by timedelta
    while remaining:
        # Match operator and timedelta
        op_match = re.match(r'^([+\-])\s*(.+?)(?=\s*[+\-]|$)', remaining)
        
        if not op_match:
            raise RemyError(
                f"Invalid arithmetic operation in expression: '{expr_str}'. "
                f"Failed to parse: '{remaining}'"
            )
        
        operator = op_match.group(1)
        timedelta_str = op_match.group(2).strip()
        
        # Parse the timedelta
        timedelta_obj = _parse_timedelta_from_string(timedelta_str)
        
        # Apply the operation
        if operator == '+':
            result = timedelta_obj + result
        elif operator == '-':
            result = result - timedelta_obj
        else:
            raise RemyError(f"Unknown operator: {operator}")
        
        # Move to the next part
        remaining = remaining[op_match.end():].strip()
    
    return result


def _parse_timedelta_from_string(td_str: str) -> Timedelta:
    """
    Parse a timedelta string without the ::timedelta cast.

    Args:
        td_str: String like '2 days', '01:30', or '3 hours'

    Returns:
        Timedelta object

    Raises:
        RemyError: If the timedelta format is invalid
    """
    td_str = td_str.strip()
    
    # Try to parse as time format if it contains ':'
    if ':' in td_str:
        parts = td_str.split(':')
        if len(parts) == 2:
            # HH:MM or :MM format
            hours_str, minutes_str = parts
            hours = int(hours_str) if hours_str else 0
            minutes = int(minutes_str)
            seconds = 0
        elif len(parts) == 3:
            # HH:MM:SS, :MM:SS, or ::SS format
            hours_str, minutes_str, seconds_str = parts
            hours = int(hours_str) if hours_str else 0
            minutes = int(minutes_str) if minutes_str else 0
            seconds = int(seconds_str)
        else:
            raise RemyError(f"Invalid time format: '{td_str}'")
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return Timedelta(total_seconds, 'seconds')
    
    # Parse as "<number><optional_space><unit>"
    pattern = r'^(\d+)\s*(day|days|hour|hours|minute|minutes|second|seconds|week|weeks|month|months|year|years)$'
    match = re.match(pattern, td_str, re.IGNORECASE)
    
    if not match:
        raise RemyError(
            f"Invalid timedelta in arithmetic expression: '{td_str}'. "
            f"Expected format: '<number> <unit>' or 'HH:MM[:SS]'"
        )
    
    value = int(match.group(1))
    unit_str = match.group(2).lower()
    
    # Normalize to plural form
    unit_map = {
        'day': 'days', 'days': 'days',
        'hour': 'hours', 'hours': 'hours',
        'minute': 'minutes', 'minutes': 'minutes',
        'second': 'seconds', 'seconds': 'seconds',
        'week': 'weeks', 'weeks': 'weeks',
        'month': 'months', 'months': 'months',
        'year': 'years', 'years': 'years'
    }
    
    unit = unit_map[unit_str]
    return Timedelta(value, unit)
