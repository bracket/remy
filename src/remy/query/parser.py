"""
Lark-based parser for WHERE clause query language.

This module provides the parse_query function that converts SQL-like WHERE clauses
into an abstract syntax tree (AST) for later evaluation.
"""

from lark import Transformer, exceptions as lark_exceptions
from datetime import datetime, date, timezone

from remy.exceptions import RemyError
from remy.query.grammar import get_parser
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, In, And, Or, Not,
    DateTimeLiteral, DateLiteral, Timedelta, TimedeltaLiteral, BinaryOp
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
    
    def add_op(self, args):
        """Transform addition expression."""
        left, right = args
        return BinaryOp('+', left, right)
    
    def sub_op(self, args):
        """Transform subtraction expression."""
        left, right = args
        return BinaryOp('-', left, right)
    
    def _contains_arithmetic(self, expr_str):
        """Check if a string expression contains arithmetic operators."""
        import re
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
            # Match: complete ISO date/timestamp/keyword followed by - and then more content
            # This ensures we have a complete temporal value before the operator
            if re.search(r'(?:\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?|now|today)\s*-\s*\d', expr_str, re.IGNORECASE):
                return True
        return False
    
    def _parse_temporal_arithmetic(self, expr_str, target_type):
        """
        Parse a temporal arithmetic expression like 'now - 2 days' or 'today + 1 hour'.
        
        Args:
            expr_str: The expression string (e.g., 'now - 2 days')
            target_type: Either 'date' or 'timestamp'
            
        Returns:
            A BinaryOp AST node representing the arithmetic
        """
        import re
        
        # Find the arithmetic operator position
        # We need to find + or - that's NOT part of the date (YYYY-MM-DD)
        # Look for the operator after a complete date/timestamp/keyword
        
        # Try to find the operator
        operator_match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?|now|today)\s*([+\-])\s*', expr_str, re.IGNORECASE)
        
        if not operator_match:
            raise RemyError(f"Invalid temporal arithmetic expression: '{expr_str}'")
        
        # Extract parts
        left_str = operator_match.group(1).strip()
        operator = operator_match.group(2)
        # Everything after the operator
        right_str = expr_str[operator_match.end():].strip()
        
        # Parse left operand - can be 'now', 'today', or a date/datetime string
        if left_str.lower() == 'now':
            left_node = DateTimeLiteral(datetime.now(timezone.utc))
        elif left_str.lower() == 'today':
            left_node = DateLiteral(date.today())
        elif target_type == 'timestamp':
            # Try to parse as datetime
            try:
                dt = datetime.fromisoformat(left_str)
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc)
                else:
                    dt = dt.replace(tzinfo=timezone.utc)
                left_node = DateTimeLiteral(dt)
            except ValueError:
                raise RemyError(f"Invalid datetime in expression: '{left_str}'")
        else:  # target_type == 'date'
            # Try to parse as date
            try:
                dt = date.fromisoformat(left_str)
                left_node = DateLiteral(dt)
            except ValueError:
                raise RemyError(f"Invalid date in expression: '{left_str}'")
        
        # Parse right operand - should be a timedelta
        right_node = self._parse_timedelta_from_string(right_str)
        
        # Create the BinaryOp node
        return BinaryOp(operator, left_node, right_node)
    
    def _parse_timedelta_from_string(self, td_str):
        """
        Parse a timedelta string without the ::timedelta cast.
        
        Args:
            td_str: String like '2 days' or '01:30'
            
        Returns:
            TimedeltaLiteral node
        """
        import re
        
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
            return TimedeltaLiteral(Timedelta(total_seconds, 'seconds'))
        
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
        return TimedeltaLiteral(Timedelta(value, unit))

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
        """Transform datetime literal (e.g., '2024-01-31 15:30:00'::timestamp or 'now'::timestamp)."""
        # Get the string token
        token = args[0]
        # Remove quotes from the string
        datetime_str = str(token)[1:-1].strip()
        
        # Check if the string contains arithmetic operators
        # We need to parse expressions like "now - 2 days" or "today + 1 hour"
        if self._contains_arithmetic(datetime_str):
            result = self._parse_temporal_arithmetic(datetime_str, target_type='timestamp')
            return result
        
        # Check if this is the special "now" keyword (case-insensitive)
        if datetime_str.lower() == 'now':
            # Return current UTC datetime (timezone-aware)
            dt = datetime.now(timezone.utc)
            return DateTimeLiteral(dt)
        
        try:
            # Try to parse datetime - fromisoformat handles timezone automatically
            dt = datetime.fromisoformat(datetime_str)
            # If timezone-aware, convert to UTC
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            else:
                # If no timezone specified, treat as UTC
                dt = dt.replace(tzinfo=timezone.utc)
            return DateTimeLiteral(dt)
        except ValueError as e:
            raise RemyError(
                f"Invalid datetime format: '{datetime_str}'. "
                f"Expected ISO format 'YYYY-MM-DD HH:MM:SS' with optional timezone. "
                f"Error: {str(e)}"
            )

    def date_literal(self, args):
        """Transform date literal (e.g., '2024-01-31'::date or 'today'::date)."""
        # Get the string token
        token = args[0]
        # Remove quotes from the string
        date_str = str(token)[1:-1].strip()
        
        # Check if the string contains arithmetic operators
        if self._contains_arithmetic(date_str):
            result = self._parse_temporal_arithmetic(date_str, target_type='date')
            return result
        
        # Check if this is the special "today" keyword (case-insensitive)
        if date_str.lower() == 'today':
            # Return current UTC date
            dt = date.today()
            return DateLiteral(dt)
        
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
    
    def timedelta_literal(self, args):
        """
        Transform timedelta literal (e.g., '2 days'::timedelta, '1 month'::timedelta, '01:30'::timedelta).
        
        Supports:
        - Units: day/days, hour/hours, minute/minutes, second/seconds, week/weeks, month/months, year/years
        - Time format: HH:MM or HH:MM:SS or :MM or :MM:SS or ::SS
        - Optional whitespace between number and unit
        """
        import re
        
        # Get the string token
        token = args[0]
        # Remove quotes from the string
        timedelta_str = str(token)[1:-1].strip()
        
        # Try to parse as time format if it contains ':'
        if ':' in timedelta_str:
            parts = timedelta_str.split(':')
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
                raise RemyError(f"Invalid time format: '{timedelta_str}'")
            
            # Convert to total seconds for storage
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # We'll store this as seconds unit
            return TimedeltaLiteral(Timedelta(total_seconds, 'seconds'))
        
        # Parse the timedelta string: "<number><optional_space><unit>"
        # Support both singular and plural forms, optional whitespace
        pattern = r'^(\d+)\s*(day|days|hour|hours|minute|minutes|second|seconds|week|weeks|month|months|year|years)$'
        match = re.match(pattern, timedelta_str, re.IGNORECASE)
        
        if not match:
            raise RemyError(
                f"Invalid timedelta format: '{timedelta_str}'. "
                f"Expected format: '<number> <unit>' or 'HH:MM[:SS]' "
                f"where unit is day(s), hour(s), minute(s), second(s), week(s), month(s), or year(s). "
                f"Examples: '2 days', '1 month', '3hours', '01:30', ':45'"
            )
        
        value = int(match.group(1))
        unit_str = match.group(2).lower()
        
        # Normalize to plural form for consistent storage
        unit_map = {
            'day': 'days',
            'days': 'days',
            'hour': 'hours',
            'hours': 'hours',
            'minute': 'minutes',
            'minutes': 'minutes',
            'second': 'seconds',
            'seconds': 'seconds',
            'week': 'weeks',
            'weeks': 'weeks',
            'month': 'months',
            'months': 'months',
            'year': 'years',
            'years': 'years'
        }
        
        unit = unit_map[unit_str]
        
        return TimedeltaLiteral(Timedelta(value, unit))


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
