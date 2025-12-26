"""Tests for embedded arithmetic in date/timestamp literals and extended timedelta formats."""

import pytest
from datetime import datetime, date, timezone, timedelta

from remy.exceptions import RemyError
from remy.notecard_index import null
from remy.query.parser import parse_query
from remy.query.ast_nodes import (
    Compare, Identifier, DateTimeLiteral, DateLiteral, 
    TimedeltaLiteral, Timedelta, BinaryOp
)
from remy.query.eval import evaluate_query, _evaluate_binary_op


# Sentinel value to distinguish "no value" from "None value"
_null = null


class MockNotecardIndex:
    """Mock NotecardIndex for testing."""

    def __init__(self, field_name, value_to_labels):
        self.field_name = field_name.upper()
        self.value_to_labels = value_to_labels

    def find(self, low=_null, high=_null, snap=None):
        try:
            all_values = sorted(self.value_to_labels.keys())
        except TypeError:
            all_values = list(self.value_to_labels.keys())
        
        for value in all_values:
            if low is not _null and high is not _null and low == high:
                if value == low:
                    for label in sorted(self.value_to_labels[value]):
                        yield (value, label)
                continue
            
            try:
                if low is not _null and value < low:
                    continue
                if high is not _null and value > high:
                    continue
            except TypeError:
                continue
                
            if value in self.value_to_labels:
                for label in sorted(self.value_to_labels[value]):
                    yield (value, label)


# ============================================================================
# Parsing Tests - Embedded Arithmetic
# ============================================================================

def test_parse_now_minus_days():
    """Test parsing 'now - 2 days'::timestamp."""
    ast = parse_query("field = 'now - 2 days'::timestamp")
    
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '-'
    assert isinstance(ast.right.left, DateTimeLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)
    assert ast.right.right.value.value == 2
    assert ast.right.right.value.unit == 'days'


def test_parse_today_minus_hours():
    """Test parsing 'today - 72 hours'::date."""
    ast = parse_query("field = 'today - 72 hours'::date")
    
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '-'
    assert isinstance(ast.right.left, DateLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)
    assert ast.right.right.value.value == 72
    assert ast.right.right.value.unit == 'hours'


def test_parse_today_plus_days():
    """Test parsing 'today + 2 days'::timestamp."""
    ast = parse_query("field = 'today + 2 days'::timestamp")
    
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '+'


def test_parse_date_plus_months():
    """Test parsing '2024-01-31 + 1 month'::date."""
    ast = parse_query("field = '2024-01-31 + 1 month'::date")
    
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '+'
    assert isinstance(ast.right.left, DateLiteral)
    assert ast.right.left.value == date(2024, 1, 31)


# ============================================================================
# Parsing Tests - Time Format Timedeltas
# ============================================================================

def test_parse_timedelta_hhmm():
    """Test parsing HH:MM format."""
    ast = parse_query("field = '01:30'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    # 1 hour 30 minutes = 5400 seconds
    assert ast.right.value.value == 5400
    assert ast.right.value.unit == 'seconds'


def test_parse_timedelta_hhmmss():
    """Test parsing HH:MM:SS format."""
    ast = parse_query("field = '02:15:45'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    # 2 hours 15 minutes 45 seconds = 8145 seconds
    assert ast.right.value.value == 8145
    assert ast.right.value.unit == 'seconds'


def test_parse_timedelta_mm_only():
    """Test parsing :MM format (minutes only)."""
    ast = parse_query("field = ':45'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    # 45 minutes = 2700 seconds
    assert ast.right.value.value == 2700
    assert ast.right.value.unit == 'seconds'


def test_parse_timedelta_mmss():
    """Test parsing :MM:SS format."""
    ast = parse_query("field = ':30:15'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    # 30 minutes 15 seconds = 1815 seconds
    assert ast.right.value.value == 1815
    assert ast.right.value.unit == 'seconds'


def test_parse_timedelta_ss_only():
    """Test parsing ::SS format (seconds only)."""
    ast = parse_query("field = '::30'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 30
    assert ast.right.value.unit == 'seconds'


# ============================================================================
# Parsing Tests - Optional Whitespace
# ============================================================================

def test_parse_timedelta_no_space():
    """Test parsing timedelta with no space between number and unit."""
    ast = parse_query("field = '2days'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 2
    assert ast.right.value.unit == 'days'


def test_parse_timedelta_no_space_hours():
    """Test parsing '48hours'."""
    ast = parse_query("field = '48hours'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 48
    assert ast.right.value.unit == 'hours'


def test_parse_timedelta_no_space_weeks():
    """Test parsing '3weeks'."""
    ast = parse_query("field = '3weeks'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 3
    assert ast.right.value.unit == 'weeks'


# ============================================================================
# Parsing Tests - New Units
# ============================================================================

def test_parse_timedelta_minutes():
    """Test parsing minutes unit."""
    ast = parse_query("field = '30 minutes'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 30
    assert ast.right.value.unit == 'minutes'


def test_parse_timedelta_seconds():
    """Test parsing seconds unit."""
    ast = parse_query("field = '90 seconds'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 90
    assert ast.right.value.unit == 'seconds'


def test_parse_timedelta_weeks():
    """Test parsing weeks unit."""
    ast = parse_query("field = '2 weeks'::timedelta")
    
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 2
    assert ast.right.value.unit == 'weeks'


# ============================================================================
# Evaluation Tests - Equivalence
# ============================================================================

def test_equivalence_now_minus_days():
    """Test that 'now - 2 days'::timestamp equals 'now'::timestamp - '2 days'::timedelta."""
    # Parse both expressions
    ast1 = parse_query("field = 'now - 2 days'::timestamp")
    ast2 = parse_query("field = 'now'::timestamp - '2 days'::timedelta")
    
    # Get the right-hand sides (both should be BinaryOp)
    rhs1 = ast1.right
    rhs2 = ast2.right
    
    assert isinstance(rhs1, BinaryOp)
    assert isinstance(rhs2, BinaryOp)
    
    # Evaluate both - they should be very close in time (within a few microseconds)
    result1 = _evaluate_binary_op(rhs1)
    result2 = _evaluate_binary_op(rhs2)
    
    # Check that results are within 1 second of each other (accounting for parsing time)
    time_diff = abs((result1 - result2).total_seconds())
    assert time_diff < 1.0


def test_equivalence_today_minus_days():
    """Test that 'today - 2 days'::date equals 'today'::date - '2 days'::timedelta."""
    ast1 = parse_query("field = 'today - 2 days'::date")
    ast2 = parse_query("field = 'today'::date - '2 days'::timedelta")
    
    result1 = _evaluate_binary_op(ast1.right)
    result2 = _evaluate_binary_op(ast2.right)
    
    # Both should be dates and equal
    assert isinstance(result1, date)
    assert isinstance(result2, date)
    assert result1 == result2


def test_equivalence_today_minus_hours():
    """Test that 'today - 48 hours'::timestamp equals 'today'::date - '48 hours'::timedelta."""
    ast1 = parse_query("field = 'today - 48 hours'::timestamp")
    ast2 = parse_query("field = 'today'::date - '48 hours'::timedelta")
    
    result1 = _evaluate_binary_op(ast1.right)
    result2 = _evaluate_binary_op(ast2.right)
    
    # Both should be timestamps and equal
    assert isinstance(result1, datetime)
    assert isinstance(result2, datetime)
    assert result1 == result2


# ============================================================================
# Evaluation Tests - Type Preservation
# ============================================================================

def test_date_minus_days_returns_date():
    """Test that date - days returns a date."""
    ast = parse_query("field = 'today - 2 days'::date")
    result = _evaluate_binary_op(ast.right)
    
    assert isinstance(result, date)
    assert not isinstance(result, datetime)


def test_date_minus_hours_returns_datetime():
    """Test that date - hours returns a datetime (date converted to midnight UTC)."""
    ast = parse_query("field = 'today - 3 hours'::date")
    result = _evaluate_binary_op(ast.right)
    
    assert isinstance(result, datetime)


def test_timestamp_minus_days_returns_datetime():
    """Test that timestamp - days returns a datetime."""
    ast = parse_query("field = 'now - 2 days'::timestamp")
    result = _evaluate_binary_op(ast.right)
    
    assert isinstance(result, datetime)


# ============================================================================
# Evaluation Tests - Time Format
# ============================================================================

def test_eval_time_format_addition():
    """Test adding time format timedelta."""
    # Create a known datetime
    base_dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    # Parse and evaluate '01:30' (1 hour 30 minutes)
    ast = parse_query("field = '01:30'::timedelta")
    td = ast.right.value
    
    result = base_dt + td
    expected = datetime(2024, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
    
    assert result == expected


def test_eval_minutes_format():
    """Test adding minutes-only format."""
    base_dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    ast = parse_query("field = ':45'::timedelta")
    td = ast.right.value
    
    result = base_dt + td
    expected = datetime(2024, 1, 1, 10, 45, 0, tzinfo=timezone.utc)
    
    assert result == expected


# ============================================================================
# Evaluation Tests - New Units
# ============================================================================

def test_eval_weeks():
    """Test weeks arithmetic."""
    base_date = date(2024, 1, 1)
    
    ast = parse_query("field = '2 weeks'::timedelta")
    td = ast.right.value
    
    result = base_date + td
    expected = date(2024, 1, 15)  # 14 days later
    
    assert result == expected


def test_eval_minutes():
    """Test minutes arithmetic."""
    base_dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    ast = parse_query("field = '30 minutes'::timedelta")
    td = ast.right.value
    
    result = base_dt + td
    expected = datetime(2024, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
    
    assert result == expected


def test_eval_seconds():
    """Test seconds arithmetic."""
    base_dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    
    ast = parse_query("field = '90 seconds'::timedelta")
    td = ast.right.value
    
    result = base_dt + td
    expected = datetime(2024, 1, 1, 10, 1, 30, tzinfo=timezone.utc)
    
    assert result == expected


# ============================================================================
# Integration Tests - Full Query Evaluation
# ============================================================================

def test_query_with_embedded_arithmetic():
    """Test full query evaluation with embedded arithmetic."""
    # Create test data with a date 3 days ago
    three_days_ago = date.today() - timedelta(days=3)
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        three_days_ago: {'card1'},
        date.today(): {'card2'},
        date.today() + timedelta(days=1): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Query: date_field = 'today - 3 days'::date
    ast = parse_query("date_field = 'today - 3 days'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_query_with_time_format():
    """Test query with time format timedelta."""
    # Create test data
    base_time = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    time_plus_90min = base_time + timedelta(minutes=90)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP', {
        base_time: {'card1'},
        time_plus_90min: {'card2'}
    })
    
    field_indices = {'TIMESTAMP': timestamp_index}
    
    # Query using time format
    # We can't use embedded arithmetic with specific times, but we can use the timedelta
    ast = parse_query("timestamp = '2024-01-01 10:00:00'::timestamp + '01:30'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card2'}


# ============================================================================
# Error Cases
# ============================================================================

def test_invalid_time_format_with_unit():
    """Test that mixing time format and unit raises an error."""
    # The time format shouldn't have a unit
    with pytest.raises(RemyError):
        parse_query("field = '01:30 hours'::timedelta")
