"""Tests for datetime and date literal parsing and evaluation in query language."""

import pytest
from datetime import datetime, date, timezone, timedelta

from remy.exceptions import RemyError
from remy.query.parser import parse_query
from remy.query.eval import evaluate_query
from remy.query.ast_nodes import (
    Compare, Identifier, DateTimeLiteral, DateLiteral
)


# Sentinel value to distinguish "no value" from "None value"
_null = object()


class MockNotecardIndex:
    """
    Mock NotecardIndex for testing temporal queries.
    
    This class simulates the NotecardIndex interface for testing purposes,
    storing a simple mapping of values to sets of labels.
    """

    def __init__(self, field_name, value_to_labels):
        """
        Initialize mock index.

        Args:
            field_name: Name of the field (will be uppercased)
            value_to_labels: Dict mapping values to sets of labels
        """
        self.field_name = field_name.upper()
        self.value_to_labels = value_to_labels

    def find(self, low=_null, high=_null, snap=None):
        """
        Mock implementation of NotecardIndex.find().

        For equality matching (low == high), yields (value, label) tuples
        for all labels associated with that value.
        
        For range queries, yields all (value, label) tuples where low <= value <= high.

        Args:
            low: Lower bound value (defaults to sentinel _null)
            high: Upper bound value (defaults to sentinel _null)
            snap: Snapping mode (ignored in mock)

        Yields:
            Tuples of (value, label) for matching entries
        """
        # Get all values sorted (handle None specially)
        all_values = list(self.value_to_labels.keys())
        # Sort with None first (if present), then sort the rest
        none_values = [v for v in all_values if v is None]
        other_values = sorted([v for v in all_values if v is not None])
        all_values = none_values + other_values
        
        # Determine the range
        if low is _null:
            start_idx = 0
        else:
            # Find first value >= low
            start_idx = 0
            for i, v in enumerate(all_values):
                if v is None:
                    # None compares less than everything, so if low is not None, skip it
                    if low is not None:
                        continue
                if v is not None and low is not None and v >= low:
                    start_idx = i
                    break
                if v == low:  # Exact match (including None == None)
                    start_idx = i
                    break
            else:
                # No value >= low, return empty
                return
        
        if high is _null:
            end_idx = len(all_values)
        else:
            # Find last value <= high
            end_idx = len(all_values)
            for i in range(len(all_values) - 1, -1, -1):
                v = all_values[i]
                if v is None:
                    # None compares less than everything
                    if high is None:
                        end_idx = i + 1
                        break
                    else:
                        # Skip None if high is not None
                        continue
                if v is not None and high is not None and v <= high:
                    end_idx = i + 1
                    break
            else:
                # No value <= high, return empty
                return
        
        # Yield all matching (value, label) tuples
        for value in all_values[start_idx:end_idx]:
            if value in self.value_to_labels:
                for label in sorted(self.value_to_labels[value]):
                    yield (value, label)


# ============================================================================
# Parsing Tests
# ============================================================================

def test_parse_datetime_literal_basic():
    """Test parsing basic datetime literal without timezone."""
    ast = parse_query("created_date >= '2024-01-31 15:30:00'::timestamp")
    
    assert isinstance(ast, Compare)
    assert ast.operator == '>='
    assert isinstance(ast.left, Identifier)
    assert ast.left.name == 'created_date'
    assert isinstance(ast.right, DateTimeLiteral)
    assert ast.right.value == datetime(2024, 1, 31, 15, 30, 0)
    assert ast.right.value.tzinfo is None  # Should be naive


def test_parse_datetime_literal_with_timezone_positive():
    """Test parsing datetime literal with positive timezone offset."""
    ast = parse_query("modified_time >= '2024-06-15 10:00:00+05:00'::timestamp")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, DateTimeLiteral)
    # 10:00:00+05:00 should be converted to 05:00:00 UTC
    assert ast.right.value == datetime(2024, 6, 15, 5, 0, 0)
    assert ast.right.value.tzinfo is None  # Should be naive after UTC conversion


def test_parse_datetime_literal_with_timezone_negative():
    """Test parsing datetime literal with negative timezone offset."""
    ast = parse_query("event_time < '2024-12-01 18:30:00-08:00'::timestamp")
    
    assert isinstance(ast, Compare)
    assert isinstance(ast.right, DateTimeLiteral)
    # 18:30:00-08:00 should be converted to 02:30:00 (next day) UTC
    assert ast.right.value == datetime(2024, 12, 2, 2, 30, 0)
    assert ast.right.value.tzinfo is None


def test_parse_datetime_literal_various_operators():
    """Test datetime literals with various comparison operators."""
    operators = ['<', '<=', '>', '>=', '=']
    
    for op in operators:
        query = f"timestamp {op} '2024-01-01 00:00:00'::timestamp"
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert ast.operator == op
        assert isinstance(ast.right, DateTimeLiteral)


def test_parse_date_literal_basic():
    """Test parsing basic date literal."""
    ast = parse_query("due_date < '2024-12-31'::date")
    
    assert isinstance(ast, Compare)
    assert ast.operator == '<'
    assert isinstance(ast.left, Identifier)
    assert ast.left.name == 'due_date'
    assert isinstance(ast.right, DateLiteral)
    assert ast.right.value == date(2024, 12, 31)


def test_parse_date_literal_various_operators():
    """Test date literals with various comparison operators."""
    operators = ['<', '<=', '>', '>=', '=']
    
    for op in operators:
        query = f"birth_date {op} '1990-05-15'::date"
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert ast.operator == op
        assert isinstance(ast.right, DateLiteral)
        assert ast.right.value == date(1990, 5, 15)


def test_parse_datetime_and_date_in_complex_query():
    """Test datetime and date literals in complex queries with AND/OR."""
    query = ("created_date >= '2024-01-01'::date AND "
             "modified_time < '2024-12-31 23:59:59'::timestamp")
    ast = parse_query(query)
    
    # Should parse as AND with two comparisons
    from remy.query.ast_nodes import And
    assert isinstance(ast, And)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.right, Compare)
    assert isinstance(ast.left.right, DateLiteral)
    assert isinstance(ast.right.right, DateTimeLiteral)


def test_parse_datetime_with_parentheses():
    """Test datetime literals with parentheses for grouping."""
    query = ("(start_date >= '2024-01-01'::date OR "
             "end_date <= '2024-12-31'::date) AND "
             "status = 'active'")
    ast = parse_query(query)
    
    from remy.query.ast_nodes import And, Or
    assert isinstance(ast, And)
    assert isinstance(ast.left, Or)


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_parse_datetime_invalid_format():
    """Test that invalid datetime format raises RemyError."""
    with pytest.raises(RemyError, match="Invalid datetime format"):
        parse_query("timestamp = 'not-a-datetime'::timestamp")


def test_parse_datetime_date_only_string():
    """Test that date-only string in timestamp is accepted and treated as midnight."""
    ast = parse_query("timestamp = '2024-01-31'::timestamp")
    
    # Should be accepted and parsed as midnight
    assert isinstance(ast.right, DateTimeLiteral)
    assert ast.right.value == datetime(2024, 1, 31, 0, 0, 0)


def test_parse_date_invalid_format():
    """Test that invalid date format raises RemyError."""
    with pytest.raises(RemyError, match="Invalid date format"):
        parse_query("date_field = 'not-a-date'::date")


def test_parse_date_with_time_component():
    """Test that date with time component raises RemyError."""
    with pytest.raises(RemyError, match="Invalid date format"):
        parse_query("date_field = '2024-01-31 10:00:00'::date")


# ============================================================================
# Evaluation Tests
# ============================================================================

def test_evaluate_datetime_equality():
    """Test evaluating datetime equality comparison."""
    # Create mock index with datetime values
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date = '2024-02-20 14:30:00'::timestamp
    ast = parse_query("created_date = '2024-02-20 14:30:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card2'}


def test_evaluate_datetime_less_than():
    """Test evaluating datetime < comparison."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date < '2024-02-20 14:30:00'::timestamp
    ast = parse_query("created_date < '2024-02-20 14:30:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    # Should match only card1 (2024-01-15)
    assert result == {'card1'}


def test_evaluate_datetime_less_than_or_equal():
    """Test evaluating datetime <= comparison."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date <= '2024-02-20 14:30:00'::timestamp
    ast = parse_query("created_date <= '2024-02-20 14:30:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    # Should match card1 and card2
    assert result == {'card1', 'card2'}


def test_evaluate_datetime_greater_than():
    """Test evaluating datetime > comparison."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date > '2024-02-20 14:30:00'::timestamp
    ast = parse_query("created_date > '2024-02-20 14:30:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    # Should match only card3
    assert result == {'card3'}


def test_evaluate_datetime_greater_than_or_equal():
    """Test evaluating datetime >= comparison."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date >= '2024-02-20 14:30:00'::timestamp
    ast = parse_query("created_date >= '2024-02-20 14:30:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    # Should match card2 and card3
    assert result == {'card2', 'card3'}


def test_evaluate_date_equality():
    """Test evaluating date equality comparison."""
    due_index = MockNotecardIndex('DUE_DATE', {
        date(2024, 1, 15): {'card1'},
        date(2024, 2, 20): {'card2'},
        date(2024, 3, 10): {'card3'}
    })
    
    field_indices = {'DUE_DATE': due_index}
    
    # Query: due_date = '2024-02-20'::date
    ast = parse_query("due_date = '2024-02-20'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card2'}


def test_evaluate_date_less_than():
    """Test evaluating date < comparison."""
    due_index = MockNotecardIndex('DUE_DATE', {
        date(2024, 1, 15): {'card1'},
        date(2024, 2, 20): {'card2'},
        date(2024, 3, 10): {'card3'}
    })
    
    field_indices = {'DUE_DATE': due_index}
    
    # Query: due_date < '2024-02-20'::date
    ast = parse_query("due_date < '2024-02-20'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card1'}


def test_evaluate_date_greater_than_or_equal():
    """Test evaluating date >= comparison."""
    due_index = MockNotecardIndex('DUE_DATE', {
        date(2024, 1, 15): {'card1'},
        date(2024, 2, 20): {'card2'},
        date(2024, 3, 10): {'card3'}
    })
    
    field_indices = {'DUE_DATE': due_index}
    
    # Query: due_date >= '2024-02-20'::date
    ast = parse_query("due_date >= '2024-02-20'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == {'card2', 'card3'}


def test_evaluate_datetime_with_timezone_conversion():
    """Test that timezone-aware queries are properly converted to UTC for comparison."""
    # Index contains UTC datetime values
    event_index = MockNotecardIndex('EVENT_TIME', {
        datetime(2024, 6, 15, 5, 0, 0): {'card1'},  # 05:00 UTC
        datetime(2024, 6, 15, 10, 0, 0): {'card2'}, # 10:00 UTC
        datetime(2024, 6, 15, 15, 0, 0): {'card3'}  # 15:00 UTC
    })
    
    field_indices = {'EVENT_TIME': event_index}
    
    # Query with +05:00 timezone: 10:00:00+05:00 = 05:00:00 UTC
    ast = parse_query("event_time = '2024-06-15 10:00:00+05:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    # Should match card1 (which has 05:00 UTC)
    assert result == {'card1'}


def test_evaluate_datetime_range_query():
    """Test evaluating datetime range query with AND."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'},
        datetime(2024, 3, 10, 8, 15, 0): {'card3'},
        datetime(2024, 4, 5, 16, 45, 0): {'card4'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query: created_date >= '2024-02-01 00:00:00'::timestamp 
    #        AND created_date <= '2024-03-31 23:59:59'::timestamp
    query = ("created_date >= '2024-02-01 00:00:00'::timestamp AND "
             "created_date <= '2024-03-31 23:59:59'::timestamp")
    ast = parse_query(query)
    result = evaluate_query(ast, field_indices)
    
    # Should match card2 and card3 (February and March)
    assert result == {'card2', 'card3'}


def test_evaluate_date_range_query():
    """Test evaluating date range query with AND."""
    start_index = MockNotecardIndex('START_DATE', {
        date(2024, 1, 15): {'card1'},
        date(2024, 2, 20): {'card2'},
        date(2024, 3, 10): {'card3'},
        date(2024, 4, 5): {'card4'}
    })
    
    field_indices = {'START_DATE': start_index}
    
    # Query: start_date >= '2024-02-01'::date AND start_date <= '2024-03-31'::date
    query = "start_date >= '2024-02-01'::date AND start_date <= '2024-03-31'::date"
    ast = parse_query(query)
    result = evaluate_query(ast, field_indices)
    
    # Should match card2 and card3
    assert result == {'card2', 'card3'}


def test_evaluate_mixed_datetime_and_string():
    """Test query with both datetime and string comparisons."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1', 'card2'},
        datetime(2024, 2, 20, 14, 30, 0): {'card3'}
    })
    
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card3'},
        'inactive': {'card2'}
    })
    
    field_indices = {
        'CREATED_DATE': created_index,
        'STATUS': status_index
    }
    
    # Query: created_date >= '2024-01-01 00:00:00'::timestamp AND status = 'active'
    query = "created_date >= '2024-01-01 00:00:00'::timestamp AND status = 'active'"
    ast = parse_query(query)
    result = evaluate_query(ast, field_indices)
    
    # Should match card1 and card3 (active cards after 2024-01-01)
    assert result == {'card1', 'card3'}


def test_evaluate_no_matches():
    """Test temporal query with no matches."""
    created_index = MockNotecardIndex('CREATED_DATE', {
        datetime(2024, 1, 15, 10, 0, 0): {'card1'},
        datetime(2024, 2, 20, 14, 30, 0): {'card2'}
    })
    
    field_indices = {'CREATED_DATE': created_index}
    
    # Query for dates in the future
    ast = parse_query("created_date > '2025-01-01 00:00:00'::timestamp")
    result = evaluate_query(ast, field_indices)
    
    assert result == set()


def test_evaluate_unknown_temporal_field():
    """Test that querying unknown temporal field returns empty set."""
    field_indices = {}
    
    ast = parse_query("unknown_date >= '2024-01-01'::date")
    result = evaluate_query(ast, field_indices)
    
    assert result == set()


# ============================================================================
# Edge Cases and Special Tests
# ============================================================================

def test_datetime_literal_milliseconds():
    """Test datetime parsing with fractional seconds (if supported by ISO format)."""
    # Python's fromisoformat supports microseconds
    ast = parse_query("timestamp = '2024-01-31 15:30:00.123456'::timestamp")
    
    assert isinstance(ast.right, DateTimeLiteral)
    assert ast.right.value == datetime(2024, 1, 31, 15, 30, 0, 123456)


def test_datetime_literal_midnight():
    """Test datetime literal at midnight."""
    ast = parse_query("timestamp = '2024-01-01 00:00:00'::timestamp")
    
    assert isinstance(ast.right, DateTimeLiteral)
    assert ast.right.value == datetime(2024, 1, 1, 0, 0, 0)


def test_date_literal_leap_year():
    """Test date literal on leap day."""
    ast = parse_query("date_field = '2024-02-29'::date")
    
    assert isinstance(ast.right, DateLiteral)
    assert ast.right.value == date(2024, 2, 29)


def test_datetime_whitespace_in_query():
    """Test that whitespace around datetime literals is handled correctly."""
    queries = [
        "date='2024-01-01'::date",
        "date = '2024-01-01'::date",
        "date  =  '2024-01-01'::date",
        " date = '2024-01-01'::date ",
    ]
    
    for query in queries:
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert isinstance(ast.right, DateLiteral)
        assert ast.right.value == date(2024, 1, 1)


def test_ast_node_equality_datetime():
    """Test that datetime AST nodes can be compared for equality."""
    ast1 = parse_query("timestamp = '2024-01-31 15:30:00'::timestamp")
    ast2 = parse_query("timestamp = '2024-01-31 15:30:00'::timestamp")
    
    assert ast1 == ast2
    
    ast3 = parse_query("timestamp = '2024-01-31 15:30:01'::timestamp")
    assert ast1 != ast3


def test_ast_node_equality_date():
    """Test that date AST nodes can be compared for equality."""
    ast1 = parse_query("date_field = '2024-01-31'::date")
    ast2 = parse_query("date_field = '2024-01-31'::date")
    
    assert ast1 == ast2
    
    ast3 = parse_query("date_field = '2024-02-01'::date")
    assert ast1 != ast3


# ============================================================================
# Special Keyword Tests for 'now' and 'today'
# ============================================================================

def test_parse_now_keyword():
    """Test parsing 'now'::timestamp keyword."""
    ast = parse_query("timestamp >= now::timestamp")
    
    assert isinstance(ast, Compare)
    assert ast.operator == '>='
    assert isinstance(ast.right, DateTimeLiteral)
    assert isinstance(ast.right.value, datetime)
    # Verify it's close to current time (within 1 second)
    time_diff = (datetime.now(timezone.utc).replace(tzinfo=None) - ast.right.value).total_seconds()
    assert abs(time_diff) < 1


def test_parse_today_keyword():
    """Test parsing 'today'::date keyword."""
    ast = parse_query("date_field = today::date")
    
    assert isinstance(ast, Compare)
    assert ast.operator == '='
    assert isinstance(ast.right, DateLiteral)
    assert isinstance(ast.right.value, date)
    # Verify it's today's date
    assert ast.right.value == date.today()


def test_now_and_today_with_various_operators():
    """Test that now and today work with all comparison operators."""
    operators = ['<', '<=', '>', '>=', '=']
    
    for op in operators:
        # Test now::timestamp
        query = f"timestamp {op} now::timestamp"
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert ast.operator == op
        assert isinstance(ast.right, DateTimeLiteral)
        
        # Test today::date
        query = f"date_field {op} today::date"
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert ast.operator == op
        assert isinstance(ast.right, DateLiteral)


def test_now_in_complex_query():
    """Test 'now' keyword in complex queries with AND/OR."""
    query = "created >= now::timestamp AND status = 'active'"
    ast = parse_query(query)
    
    from remy.query.ast_nodes import And
    assert isinstance(ast, And)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.left.right, DateTimeLiteral)


def test_today_in_complex_query():
    """Test 'today' keyword in complex queries with AND/OR."""
    query = "start_date <= today::date OR end_date >= today::date"
    ast = parse_query(query)
    
    from remy.query.ast_nodes import Or
    assert isinstance(ast, Or)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.left.right, DateLiteral)
    assert isinstance(ast.right, Compare)
    assert isinstance(ast.right.right, DateLiteral)


def test_now_returns_utc_time():
    """Test that 'now'::timestamp returns UTC time (naive datetime)."""
    ast = parse_query("timestamp = now::timestamp")
    
    # Should be a naive datetime (no timezone info)
    assert ast.right.value.tzinfo is None
    
    # Should be close to current UTC time
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_diff = (utc_now - ast.right.value).total_seconds()
    assert abs(time_diff) < 1


def test_now_and_today_case_insensitive():
    """Test that now and today keywords are case insensitive."""
    # Test NOW
    for variant in ['now', 'NOW', 'NoW', 'nOw']:
        query = f"timestamp = {variant}::timestamp"
        ast = parse_query(query)
        assert isinstance(ast.right, DateTimeLiteral)
    
    # Test TODAY
    for variant in ['today', 'TODAY', 'ToDay', 'tOdAy']:
        query = f"date_field = {variant}::date"
        ast = parse_query(query)
        assert isinstance(ast.right, DateLiteral)


def test_evaluate_query_with_now():
    """Test evaluating queries with 'now' keyword."""
    # Create a mock index with past and future datetimes
    past_dt = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
    future_dt = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    
    dt_index = MockNotecardIndex('TIMESTAMP', {
        past_dt: {'card_past'},
        future_dt: {'card_future'}
    })
    
    field_indices = {'TIMESTAMP': dt_index}
    
    # Query: timestamp < now::timestamp (should match past)
    ast = parse_query("timestamp < now::timestamp")
    result = evaluate_query(ast, field_indices)
    assert result == {'card_past'}
    
    # Query: timestamp > now::timestamp (should match future)
    ast = parse_query("timestamp > now::timestamp")
    result = evaluate_query(ast, field_indices)
    assert result == {'card_future'}


def test_evaluate_query_with_today():
    """Test evaluating queries with 'today' keyword."""
    # Create a mock index with dates
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)
    
    date_index = MockNotecardIndex('DATE_FIELD', {
        yesterday: {'card_yesterday'},
        date.today(): {'card_today'},
        tomorrow: {'card_tomorrow'}
    })
    
    field_indices = {'DATE_FIELD': date_index}
    
    # Query: date_field < today::date (should match yesterday)
    ast = parse_query("date_field < today::date")
    result = evaluate_query(ast, field_indices)
    assert result == {'card_yesterday'}
    
    # Query: date_field = today::date (should match today)
    ast = parse_query("date_field = today::date")
    result = evaluate_query(ast, field_indices)
    assert result == {'card_today'}
    
    # Query: date_field > today::date (should match tomorrow)
    ast = parse_query("date_field > today::date")
    result = evaluate_query(ast, field_indices)
    assert result == {'card_tomorrow'}
