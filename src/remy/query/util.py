"""
Utility functions for query processing.
"""

from datetime import datetime, date, timezone, timedelta as dt_timedelta
from dateutil.relativedelta import relativedelta
from remy.query.ast_nodes import Timedelta


def add_timedelta_to_date(dt: date, td: Timedelta) -> date | datetime:
    """
    Add a Timedelta to a date value with calendar-aware arithmetic.
    
    - For sub-day units (hours), treat date as 00:00:00 UTC timestamp and return timestamp
      NOTE: The date is always treated as midnight UTC, regardless of the system's local timezone.
      This ensures consistent behavior across different environments.
    - For day/month/year units, return a date
    - Month/year arithmetic is calendar-aware (end-of-month capping)
    
    Args:
        dt: Date value to add to
        td: Timedelta to add
        
    Returns:
        date or datetime depending on timedelta unit
    """
    if td.unit == 'hours':
        # Convert date to timestamp at midnight UTC, then add hours
        dt_timestamp = datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
        result = dt_timestamp + dt_timedelta(hours=td.value)
        return result
    elif td.unit == 'days':
        # Simple day addition
        return dt + dt_timedelta(days=td.value)
    elif td.unit == 'months':
        # Calendar-aware month addition
        return dt + relativedelta(months=td.value)
    elif td.unit == 'years':
        # Calendar-aware year addition
        return dt + relativedelta(years=td.value)
    else:
        raise ValueError(f"Unknown timedelta unit: {td.unit}")


def add_timedelta_to_datetime(dt: datetime, td: Timedelta) -> datetime:
    """
    Add a Timedelta to a datetime value with calendar-aware arithmetic.
    
    Args:
        dt: Datetime value to add to
        td: Timedelta to add
        
    Returns:
        datetime with timedelta added
    """
    if td.unit == 'hours':
        return dt + dt_timedelta(hours=td.value)
    elif td.unit == 'days':
        return dt + dt_timedelta(days=td.value)
    elif td.unit == 'months':
        # Calendar-aware month addition
        return dt + relativedelta(months=td.value)
    elif td.unit == 'years':
        # Calendar-aware year addition
        return dt + relativedelta(years=td.value)
    else:
        raise ValueError(f"Unknown timedelta unit: {td.unit}")


def subtract_timedelta_from_date(dt: date, td: Timedelta) -> date | datetime:
    """
    Subtract a Timedelta from a date value with calendar-aware arithmetic.
    
    NOTE: For sub-day units (hours), the date is treated as midnight UTC when converting
    to a timestamp. This ensures consistent behavior across different environments.
    
    Args:
        dt: Date value to subtract from
        td: Timedelta to subtract
        
    Returns:
        date or datetime depending on timedelta unit
    """
    if td.unit == 'hours':
        # Convert date to timestamp at midnight UTC, then subtract hours
        dt_timestamp = datetime.combine(dt, datetime.min.time(), tzinfo=timezone.utc)
        result = dt_timestamp - dt_timedelta(hours=td.value)
        return result
    elif td.unit == 'days':
        return dt - dt_timedelta(days=td.value)
    elif td.unit == 'months':
        return dt - relativedelta(months=td.value)
    elif td.unit == 'years':
        return dt - relativedelta(years=td.value)
    else:
        raise ValueError(f"Unknown timedelta unit: {td.unit}")


def subtract_timedelta_from_datetime(dt: datetime, td: Timedelta) -> datetime:
    """
    Subtract a Timedelta from a datetime value with calendar-aware arithmetic.
    
    Args:
        dt: Datetime value to subtract from
        td: Timedelta to subtract
        
    Returns:
        datetime with timedelta subtracted
    """
    if td.unit == 'hours':
        return dt - dt_timedelta(hours=td.value)
    elif td.unit == 'days':
        return dt - dt_timedelta(days=td.value)
    elif td.unit == 'months':
        return dt - relativedelta(months=td.value)
    elif td.unit == 'years':
        return dt - relativedelta(years=td.value)
    else:
        raise ValueError(f"Unknown timedelta unit: {td.unit}")


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
