"""Tests for timedelta literal parsing and arithmetic in query language."""

import pytest
from datetime import datetime, date, timezone

from remy.exceptions import RemyError, InvalidComparison
from remy.query.parser import parse_query
from remy.query.ast_nodes import (
    Compare, Identifier, DateTimeLiteral, DateLiteral, 
    TimedeltaLiteral, Timedelta, BinaryOp
)
from remy.query.eval import evaluate_query
from tests.test_query_temporal import MockNotecardIndex


# ============================================================================
# Parsing Tests - Timedelta Literals
# ============================================================================

def test_parse_timedelta_days():
    """Test parsing timedelta with days unit."""
    ast = parse_query("field = '2 days'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 2
    assert ast.right.value.unit == 'days'


def test_parse_timedelta_day_singular():
    """Test parsing timedelta with singular day unit."""
    ast = parse_query("field = '1 day'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 1
    assert ast.right.value.unit == 'days'  # Normalized to plural


def test_parse_timedelta_hours():
    """Test parsing timedelta with hours unit."""
    ast = parse_query("field = '3 hours'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 3
    assert ast.right.value.unit == 'hours'


def test_parse_timedelta_hour_singular():
    """Test parsing timedelta with singular hour unit."""
    ast = parse_query("field = '1 hour'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 1
    assert ast.right.value.unit == 'hours'  # Normalized to plural


def test_parse_timedelta_months():
    """Test parsing timedelta with months unit."""
    ast = parse_query("field = '2 months'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 2
    assert ast.right.value.unit == 'months'


def test_parse_timedelta_month_singular():
    """Test parsing timedelta with singular month unit."""
    ast = parse_query("field = '1 month'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 1
    assert ast.right.value.unit == 'months'  # Normalized to plural


def test_parse_timedelta_years():
    """Test parsing timedelta with years unit."""
    ast = parse_query("field = '5 years'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 5
    assert ast.right.value.unit == 'years'


def test_parse_timedelta_year_singular():
    """Test parsing timedelta with singular year unit."""
    ast = parse_query("field = '1 year'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, TimedeltaLiteral)
    assert ast.right.value.value == 1
    assert ast.right.value.unit == 'years'  # Normalized to plural


def test_parse_timedelta_invalid_format():
    """Test that invalid timedelta format raises RemyError."""
    with pytest.raises(RemyError, match="Invalid timedelta format"):
        parse_query("field = 'invalid'::timedelta")


def test_parse_timedelta_invalid_unit():
    """Test that invalid timedelta unit raises RemyError."""
    with pytest.raises(RemyError, match="Invalid timedelta format"):
        parse_query("field = '2 weeks'::timedelta")


def test_parse_timedelta_missing_number():
    """Test that timedelta without number raises RemyError."""
    with pytest.raises(RemyError, match="Invalid timedelta format"):
        parse_query("field = 'days'::timedelta")


# ============================================================================
# Parsing Tests - Arithmetic with Dates and Timestamps
# ============================================================================

def test_parse_date_plus_timedelta():
    """Test parsing date + timedelta arithmetic."""
    ast = parse_query("field = '2024-01-01'::date + '2 days'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '+'
    assert isinstance(ast.right.left, DateLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)


def test_parse_date_minus_timedelta():
    """Test parsing date - timedelta arithmetic."""
    ast = parse_query("field = '2024-12-31'::date - '1 month'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '-'
    assert isinstance(ast.right.left, DateLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)


def test_parse_timestamp_plus_timedelta():
    """Test parsing timestamp + timedelta arithmetic."""
    ast = parse_query("field = '2024-01-01 10:00:00'::timestamp + '3 hours'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '+'
    assert isinstance(ast.right.left, DateTimeLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)


def test_parse_timestamp_minus_timedelta():
    """Test parsing timestamp - timedelta arithmetic."""
    ast = parse_query("field = '2024-01-01 10:00:00'::timestamp - '2 hours'::timedelta")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '-'
    assert isinstance(ast.right.left, DateTimeLiteral)
    assert isinstance(ast.right.right, TimedeltaLiteral)


def test_parse_timedelta_plus_date():
    """Test parsing timedelta + date (commutative addition)."""
    ast = parse_query("field = '2 days'::timedelta + '2024-01-01'::date")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, BinaryOp)
    assert ast.right.operator == '+'
    assert isinstance(ast.right.left, TimedeltaLiteral)
    assert isinstance(ast.right.right, DateLiteral)


def test_parse_complex_date_arithmetic():
    """Test parsing complex expressions with multiple operations."""
    # This tests that the grammar supports chained operations
    ast = parse_query("field >= '2024-01-01'::date + '1 month'::timedelta")
    
    assert isinstance(ast, Compare)
    assert ast.operator == '>='
    assert isinstance(ast.right, BinaryOp)


# ============================================================================
# Evaluation Tests - Date Arithmetic
# ============================================================================

def test_evaluate_date_plus_days():
    """Test evaluating date + days arithmetic."""
    from datetime import date
    
    # Create mock index with dates
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 1, 3): {'card1'},  # 2024-01-01 + 2 days
        date(2024, 1, 5): {'card2'},
        date(2024, 1, 10): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Query: date_field = '2024-01-01'::date + '2 days'::timedelta
    ast = parse_query("date_field = '2024-01-01'::date + '2 days'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_minus_days():
    """Test evaluating date - days arithmetic."""
    from datetime import date
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 1, 29): {'card1'},  # 2024-01-31 - 2 days
        date(2024, 1, 25): {'card2'},
        date(2024, 1, 20): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Query: date_field = '2024-01-31'::date - '2 days'::timedelta
    ast = parse_query("date_field = '2024-01-31'::date - '2 days'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_plus_months():
    """Test evaluating date + months arithmetic (calendar-aware)."""
    from datetime import date
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 3, 1): {'card1'},  # 2024-01-01 + 2 months
        date(2024, 2, 1): {'card2'},
        date(2024, 4, 1): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    ast = parse_query("date_field = '2024-01-01'::date + '2 months'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_plus_years():
    """Test evaluating date + years arithmetic."""
    from datetime import date
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2026, 1, 15): {'card1'},  # 2024-01-15 + 2 years
        date(2025, 1, 15): {'card2'},
        date(2027, 1, 15): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    ast = parse_query("date_field = '2024-01-15'::date + '2 years'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_month_end_capping():
    """Test that month arithmetic caps to end-of-month correctly."""
    from datetime import date
    
    # January 31 + 1 month = February 29 (2024 is a leap year)
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 2, 29): {'card1'},  # Capped to Feb 29 (leap year)
        date(2024, 2, 28): {'card2'},
        date(2024, 3, 31): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    ast = parse_query("date_field = '2024-01-31'::date + '1 month'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_leap_year():
    """Test arithmetic with leap year dates."""
    from datetime import date
    
    # Feb 29, 2024 + 1 year = Feb 28, 2025 (not a leap year)
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2025, 2, 28): {'card1'},  # Feb 29 -> Feb 28 (non-leap year)
        date(2025, 3, 1): {'card2'},
        date(2025, 2, 27): {'card3'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    ast = parse_query("date_field = '2024-02-29'::date + '1 year'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


# ============================================================================
# Evaluation Tests - Timestamp Arithmetic
# ============================================================================

def test_evaluate_timestamp_plus_hours():
    """Test evaluating timestamp + hours arithmetic."""
    dt1 = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)  # 10:00 + 3 hours
    dt2 = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP_FIELD', {
        dt1: {'card1'},
        dt2: {'card2'}
    })
    
    field_indices = {'TIMESTAMP_FIELD': timestamp_index}
    
    ast = parse_query("timestamp_field = '2024-01-01 10:00:00'::timestamp + '3 hours'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_timestamp_minus_hours():
    """Test evaluating timestamp - hours arithmetic."""
    dt1 = datetime(2024, 1, 1, 7, 0, 0, tzinfo=timezone.utc)  # 10:00 - 3 hours
    dt2 = datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone.utc)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP_FIELD', {
        dt1: {'card1'},
        dt2: {'card2'}
    })
    
    field_indices = {'TIMESTAMP_FIELD': timestamp_index}
    
    ast = parse_query("timestamp_field = '2024-01-01 10:00:00'::timestamp - '3 hours'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_timestamp_plus_days():
    """Test evaluating timestamp + days arithmetic."""
    dt1 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=timezone.utc)  # Jan 1 + 2 days
    dt2 = datetime(2024, 1, 5, 10, 0, 0, tzinfo=timezone.utc)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP_FIELD', {
        dt1: {'card1'},
        dt2: {'card2'}
    })
    
    field_indices = {'TIMESTAMP_FIELD': timestamp_index}
    
    ast = parse_query("timestamp_field = '2024-01-01 10:00:00'::timestamp + '2 days'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_timestamp_plus_months():
    """Test evaluating timestamp + months arithmetic."""
    dt1 = datetime(2024, 3, 15, 10, 0, 0, tzinfo=timezone.utc)  # Jan 15 + 2 months
    dt2 = datetime(2024, 2, 15, 10, 0, 0, tzinfo=timezone.utc)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP_FIELD', {
        dt1: {'card1'},
        dt2: {'card2'}
    })
    
    field_indices = {'TIMESTAMP_FIELD': timestamp_index}
    
    ast = parse_query("timestamp_field = '2024-01-15 10:00:00'::timestamp + '2 months'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


# ============================================================================
# Evaluation Tests - Date + Sub-day Timedelta (converts to timestamp)
# ============================================================================

def test_evaluate_date_plus_hours_returns_timestamp():
    """Test that date + hours returns a timestamp (not a date)."""
    # Date + hours should convert to timestamp at 00:00:00 UTC
    dt1 = datetime(2024, 1, 1, 3, 0, 0, tzinfo=timezone.utc)  # 2024-01-01 00:00:00 + 3 hours
    
    timestamp_index = MockNotecardIndex('FIELD', {
        dt1: {'card1'},
        datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone.utc): {'card2'}
    })
    
    field_indices = {'FIELD': timestamp_index}
    
    ast = parse_query("field = '2024-01-01'::date + '3 hours'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_minus_hours_returns_timestamp():
    """Test that date - hours returns a timestamp (not a date)."""
    # Date - hours should convert to timestamp at 00:00:00 UTC
    dt1 = datetime(2023, 12, 31, 21, 0, 0, tzinfo=timezone.utc)  # 2024-01-01 00:00:00 - 3 hours
    
    timestamp_index = MockNotecardIndex('FIELD', {
        dt1: {'card1'},
        datetime(2023, 12, 31, 20, 0, 0, tzinfo=timezone.utc): {'card2'}
    })
    
    field_indices = {'FIELD': timestamp_index}
    
    ast = parse_query("field = '2024-01-01'::date - '3 hours'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


# ============================================================================
# Evaluation Tests - Commutative Addition
# ============================================================================

def test_evaluate_timedelta_plus_date():
    """Test that timedelta + date works (commutative)."""
    from datetime import date
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 1, 3): {'card1'},  # 2 days + 2024-01-01
        date(2024, 1, 5): {'card2'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    ast = parse_query("date_field = '2 days'::timedelta + '2024-01-01'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_timedelta_plus_timestamp():
    """Test that timedelta + timestamp works (commutative)."""
    dt1 = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP_FIELD', {
        dt1: {'card1'},
        datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc): {'card2'}
    })
    
    field_indices = {'TIMESTAMP_FIELD': timestamp_index}
    
    ast = parse_query("timestamp_field = '3 hours'::timedelta + '2024-01-01 10:00:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_evaluate_timedelta_comparison_raises_error():
    """Test that comparing timedeltas raises InvalidComparison."""
    field_indices = {}
    
    ast = parse_query("field = '2 days'::timedelta")
    
    with pytest.raises(InvalidComparison, match="Comparing timedeltas is not supported"):
        evaluate_query(ast, field_indices)


def test_evaluate_invalid_arithmetic_operands():
    """Test that invalid arithmetic operands raise RemyError."""
    # Can't subtract date from timedelta
    field_indices = {}
    
    # This should parse but fail during evaluation
    # We need to manually construct the AST since the parser might not allow this
    from remy.query.eval import _evaluate_binary_op
    
    td = TimedeltaLiteral(Timedelta(2, 'days'))
    dt = DateLiteral(date(2024, 1, 1))
    
    # timedelta - date is not valid
    ast = BinaryOp('-', td, dt)
    
    with pytest.raises(RemyError, match="Invalid operands for subtraction"):
        _evaluate_binary_op(ast)


# ============================================================================
# Complex Query Tests
# ============================================================================

def test_evaluate_range_query_with_arithmetic():
    """Test range queries with arithmetic on both sides."""
    from datetime import date
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        date(2024, 1, 15): {'card1'},
        date(2024, 2, 5): {'card2'},
        date(2024, 2, 20): {'card3'},
        date(2024, 3, 5): {'card4'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Range: >= 2024-01-01 + 1 month AND <= 2024-01-01 + 2 months
    # = >= 2024-02-01 AND <= 2024-03-01
    query = ("date_field >= '2024-01-01'::date + '1 month'::timedelta AND "
             "date_field <= '2024-01-01'::date + '2 months'::timedelta")
    ast = parse_query(query)
    result = evaluate_query(ast, field_indices)
    
    # Should match card2 (Feb 5) and card3 (Feb 20)
    assert result == {'card2', 'card3'}


def test_evaluate_now_plus_timedelta():
    """Test that 'now' + timedelta works."""
    from datetime import timedelta as dt_timedelta
    
    # Create a timestamp slightly in the future
    future_dt = datetime.now(timezone.utc) + dt_timedelta(hours=1, seconds=1)
    past_dt = datetime.now(timezone.utc) - dt_timedelta(hours=1)
    
    timestamp_index = MockNotecardIndex('TIMESTAMP', {
        future_dt: {'card_future'},
        past_dt: {'card_past'}
    })
    
    field_indices = {'TIMESTAMP': timestamp_index}
    
    # Query: timestamp > 'now'::timestamp + '1 hour'::timedelta
    # Should match only future card
    ast = parse_query("timestamp > 'now'::timestamp + '1 hour'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card_future'}


def test_evaluate_today_plus_timedelta():
    """Test that 'today' + timedelta works."""
    from datetime import date, timedelta as dt_timedelta
    
    tomorrow = date.today() + dt_timedelta(days=1)
    yesterday = date.today() - dt_timedelta(days=1)
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        tomorrow: {'card_tomorrow'},
        date.today(): {'card_today'},
        yesterday: {'card_yesterday'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Query: date_field = 'today'::date + '1 day'::timedelta
    ast = parse_query("date_field = 'today'::date + '1 day'::timedelta")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card_tomorrow'}
