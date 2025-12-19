"""Tests for query evaluator."""

import pytest

from remy.exceptions import RemyError
from remy.notecard_index import null
from remy.query.eval import evaluate_query
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, In, And, Or, Not
)


class MockNotecardIndex:
    """
    Mock NotecardIndex for testing.

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

    def find(self, low=null, high=null, snap=None):
        """
        Mock implementation of NotecardIndex.find().

        Supports both equality matching (low == high) and range queries.
        For range queries, returns all values in [low, high] inclusive.

        Args:
            low: Lower bound value (defaults to sentinel null)
            high: Upper bound value (defaults to sentinel null)
            snap: Snapping mode (ignored in mock)

        Yields:
            Tuples of (value, label) for matching entries
        """
        # For range queries, sort values (filtering out incomparable types)
        try:
            all_values = sorted(self.value_to_labels.keys())
        except TypeError:
            # Can't sort mixed types, just iterate without ordering
            all_values = list(self.value_to_labels.keys())
        
        # Determine actual bounds
        # If both low and high are null, return everything
        # If low is null but high is set, return everything up to high
        # If high is null but low is set, return everything from low onwards
        # If both are set and equal, it's an exact match
        # If both are set and different, it's a range query
        
        for value in all_values:
            # First check for exact match (handles None and other non-comparable values)
            if low is not null and high is not null and low == high:
                # Exact match case
                if value == low:
                    for label in self.value_to_labels[value]:
                        yield (value, label)
                continue
            
            # Range query - check if value is in range
            try:
                # Check lower bound
                if low is not null and value < low:
                    continue
                    
                # Check upper bound
                if high is not null and value > high:
                    continue
            except TypeError:
                # Can't compare types, skip this value
                continue
                
            # Yield all labels for this value
            if value in self.value_to_labels:
                for label in self.value_to_labels[value]:
                    yield (value, label)


def test_evaluate_simple_equality():
    """Test evaluating a simple equality comparison."""
    # Create a mock index: status field with 'active' -> ['card1', 'card2']
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2'},
        'inactive': {'card3'}
    })

    field_indices = {'STATUS': status_index}

    # Query: status = 'active'
    ast = Compare('=', Identifier('status'), Literal('active'))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1', 'card2'}


def test_evaluate_equality_with_number():
    """Test evaluating equality with numeric literal."""
    # Create a mock index: priority field with numbers
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1', 'card3'},
        2: {'card2'},
        3: {'card4'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority = 1
    ast = Compare('=', Identifier('priority'), Literal(1))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1', 'card3'}


def test_evaluate_equality_no_matches():
    """Test equality comparison with no matching values."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1'},
        'inactive': {'card2'}
    })

    field_indices = {'STATUS': status_index}

    # Query: status = 'pending' (doesn't exist)
    ast = Compare('=', Identifier('status'), Literal('pending'))
    result = evaluate_query(ast, field_indices)

    assert result == set()


def test_evaluate_unknown_field():
    """Test that unknown field names return empty set."""
    field_indices = {}

    # Query: unknown_field = 'value'
    ast = Compare('=', Identifier('unknown_field'), Literal('value'))
    result = evaluate_query(ast, field_indices)

    assert result == set()


def test_evaluate_field_name_case_insensitive():
    """Test that field names are converted to uppercase."""
    # Index is stored with uppercase key
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1'}
    })

    field_indices = {'STATUS': status_index}

    # Query with lowercase field name
    ast = Compare('=', Identifier('status'), Literal('active'))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}

    # Query with mixed case
    ast = Compare('=', Identifier('StAtUs'), Literal('active'))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


def test_evaluate_and_operation():
    """Test AND operation (set intersection)."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2', 'card3'}
    })

    priority_index = MockNotecardIndex('PRIORITY', {
        'high': {'card1', 'card3'}
    })

    field_indices = {
        'STATUS': status_index,
        'PRIORITY': priority_index
    }

    # Query: status = 'active' AND priority = 'high'
    ast = And(
        Compare('=', Identifier('status'), Literal('active')),
        Compare('=', Identifier('priority'), Literal('high'))
    )
    result = evaluate_query(ast, field_indices)

    # Should only include cards that match both conditions
    assert result == {'card1', 'card3'}


def test_evaluate_or_operation():
    """Test OR operation (set union)."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2'},
        'pending': {'card3'}
    })

    field_indices = {'STATUS': status_index}

    # Query: status = 'active' OR status = 'pending'
    ast = Or(
        Compare('=', Identifier('status'), Literal('active')),
        Compare('=', Identifier('status'), Literal('pending'))
    )
    result = evaluate_query(ast, field_indices)

    # Should include cards that match either condition
    assert result == {'card1', 'card2', 'card3'}


def test_evaluate_complex_and_or():
    """Test complex expression with nested AND/OR."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2'},
        'pending': {'card3'}
    })

    priority_index = MockNotecardIndex('PRIORITY', {
        'high': {'card1', 'card3', 'card4'}
    })

    field_indices = {
        'STATUS': status_index,
        'PRIORITY': priority_index
    }

    # Query: (status = 'active' OR status = 'pending') AND priority = 'high'
    ast = And(
        Or(
            Compare('=', Identifier('status'), Literal('active')),
            Compare('=', Identifier('status'), Literal('pending'))
        ),
        Compare('=', Identifier('priority'), Literal('high'))
    )
    result = evaluate_query(ast, field_indices)

    # (card1, card2, card3) AND (card1, card3, card4) = {card1, card3}
    assert result == {'card1', 'card3'}


def test_evaluate_unsupported_operator_not_equal():
    """Test that != operator raises RemyError (not yet supported)."""
    field_indices = {}

    ast = Compare('!=', Identifier('status'), Literal('active'))

    with pytest.raises(RemyError, match="not yet supported"):
        evaluate_query(ast, field_indices)


def test_evaluate_operator_less_than():
    """Test < operator with numeric comparisons."""
    # Create a mock index with numeric values
    age_index = MockNotecardIndex('AGE', {
        15: {'card1'},
        18: {'card2'},
        25: {'card3'},
        30: {'card4'}
    })

    field_indices = {'AGE': age_index}

    # Query: age < 18 (should match age=15)
    ast = Compare('<', Identifier('age'), Literal(18))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


def test_evaluate_operator_greater_than():
    """Test > operator with numeric comparisons."""
    age_index = MockNotecardIndex('AGE', {
        15: {'card1'},
        18: {'card2'},
        25: {'card3'},
        30: {'card4'}
    })

    field_indices = {'AGE': age_index}

    # Query: age > 18 (should match age=25 and age=30)
    ast = Compare('>', Identifier('age'), Literal(18))
    result = evaluate_query(ast, field_indices)

    assert result == {'card3', 'card4'}


def test_evaluate_operator_less_equal():
    """Test <= operator with numeric comparisons."""
    count_index = MockNotecardIndex('COUNT', {
        5: {'card1'},
        10: {'card2'},
        15: {'card3'}
    })

    field_indices = {'COUNT': count_index}

    # Query: count <= 10 (should match count=5 and count=10)
    ast = Compare('<=', Identifier('count'), Literal(10))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1', 'card2'}


def test_evaluate_operator_greater_equal():
    """Test >= operator with numeric comparisons."""
    score_index = MockNotecardIndex('SCORE', {
        85: {'card1'},
        90: {'card2'},
        95: {'card3'}
    })

    field_indices = {'SCORE': score_index}

    # Query: score >= 90 (should match score=90 and score=95)
    ast = Compare('>=', Identifier('score'), Literal(90))
    result = evaluate_query(ast, field_indices)

    assert result == {'card2', 'card3'}


def test_evaluate_not_operator_not_supported():
    """Test that NOT operator raises not-yet-implemented error."""
    field_indices = {}

    ast = Not(Compare('=', Identifier('status'), Literal('active')))

    with pytest.raises(RemyError, match="NOT operator is not yet supported"):
        evaluate_query(ast, field_indices)


def test_evaluate_in_operator_not_supported():
    """Test that IN operator raises not-yet-implemented error."""
    field_indices = {}

    ast = In(Identifier('status'), [Literal('active'), Literal('pending')])

    with pytest.raises(RemyError, match="IN operator is not yet supported"):
        evaluate_query(ast, field_indices)


def test_evaluate_invalid_compare_left_operand():
    """Test that non-Identifier left operand raises RemyError."""
    field_indices = {}

    # Invalid: literal on left side
    ast = Compare('=', Literal('value'), Literal('other'))

    with pytest.raises(RemyError, match="must be an Identifier"):
        evaluate_query(ast, field_indices)


def test_evaluate_invalid_compare_right_operand():
    """Test that non-Literal right operand raises RemyError."""
    field_indices = {}

    # Invalid: identifier on right side
    ast = Compare('=', Identifier('field1'), Identifier('field2'))

    with pytest.raises(RemyError, match="must be a Literal"):
        evaluate_query(ast, field_indices)


def test_evaluate_with_boolean_literal():
    """Test evaluation with boolean literals."""
    active_index = MockNotecardIndex('ACTIVE', {
        True: {'card1', 'card2'},
        False: {'card3'}
    })

    field_indices = {'ACTIVE': active_index}

    # Query: active = TRUE
    ast = Compare('=', Identifier('active'), Literal(True))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1', 'card2'}


def test_evaluate_with_none_literal():
    """Test evaluation with None (NULL) literal."""
    data_index = MockNotecardIndex('DATA', {
        None: {'card1'},
        'value': {'card2'}
    })

    field_indices = {'DATA': data_index}

    # Query: data = NULL
    ast = Compare('=', Identifier('data'), Literal(None))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


def test_evaluate_empty_and():
    """Test AND with one side returning empty set."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2'}
    })

    priority_index = MockNotecardIndex('PRIORITY', {
        'low': {'card3'}
    })

    field_indices = {
        'STATUS': status_index,
        'PRIORITY': priority_index
    }

    # Query: status = 'active' AND priority = 'high' (high doesn't exist)
    ast = And(
        Compare('=', Identifier('status'), Literal('active')),
        Compare('=', Identifier('priority'), Literal('high'))
    )
    result = evaluate_query(ast, field_indices)

    # Empty intersection
    assert result == set()


def test_evaluate_empty_or():
    """Test OR with both sides returning empty sets."""
    field_indices = {}

    # Query: field1 = 'value1' OR field2 = 'value2' (both fields don't exist)
    ast = Or(
        Compare('=', Identifier('field1'), Literal('value1')),
        Compare('=', Identifier('field2'), Literal('value2'))
    )
    result = evaluate_query(ast, field_indices)

    # Empty union
    assert result == set()


def test_evaluate_string_types():
    """Test that string literal types work correctly."""
    tags_index = MockNotecardIndex('TAGS', {
        'important': {'card1'},
        'urgent': {'card2'},
        'review': {'card3'}
    })

    field_indices = {'TAGS': tags_index}

    ast = Compare('=', Identifier('tags'), Literal('important'))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


def test_evaluate_float_types():
    """Test that float literal types work correctly."""
    score_index = MockNotecardIndex('SCORE', {
        95.5: {'card1'},
        87.3: {'card2'},
        92.0: {'card3'}
    })

    field_indices = {'SCORE': score_index}

    ast = Compare('=', Identifier('score'), Literal(95.5))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


# ========== Tests for order-based comparison operators ==========


def test_evaluate_less_than_operator():
    """Test < operator with numeric values."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority < 3
    ast = Compare('<', Identifier('priority'), Literal(3))
    result = evaluate_query(ast, field_indices)

    # Should include only cards with priority 1 and 2
    assert result == {'card1', 'card2'}


def test_evaluate_less_than_with_strings():
    """Test < operator with string values."""
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1'},
        'completed': {'card2'},
        'pending': {'card3'},
        'rejected': {'card4'}
    })

    field_indices = {'STATUS': status_index}

    # Query: status < 'pending' (lexicographic comparison)
    ast = Compare('<', Identifier('status'), Literal('pending'))
    result = evaluate_query(ast, field_indices)

    # 'active' and 'completed' are both < 'pending' lexicographically
    assert result == {'card1', 'card2'}


def test_evaluate_less_than_no_matches():
    """Test < operator when no values are less than threshold."""
    priority_index = MockNotecardIndex('PRIORITY', {
        5: {'card1'},
        6: {'card2'},
        7: {'card3'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority < 5 (no values less than 5)
    ast = Compare('<', Identifier('priority'), Literal(5))
    result = evaluate_query(ast, field_indices)

    assert result == set()


def test_evaluate_less_than_boundary():
    """Test < operator at boundary - should exclude the boundary value."""
    score_index = MockNotecardIndex('SCORE', {
        85.0: {'card1'},
        90.0: {'card2', 'card3'},
        95.0: {'card4'}
    })

    field_indices = {'SCORE': score_index}

    # Query: score < 90.0 (should not include 90.0)
    ast = Compare('<', Identifier('score'), Literal(90.0))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1'}


def test_evaluate_less_equal_operator():
    """Test <= operator with numeric values."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority <= 3
    ast = Compare('<=', Identifier('priority'), Literal(3))
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority 1, 2, and 3
    assert result == {'card1', 'card2', 'card3'}


def test_evaluate_less_equal_boundary():
    """Test <= operator includes the boundary value."""
    score_index = MockNotecardIndex('SCORE', {
        85.0: {'card1'},
        90.0: {'card2', 'card3'},
        95.0: {'card4'}
    })

    field_indices = {'SCORE': score_index}

    # Query: score <= 90.0 (should include 90.0)
    ast = Compare('<=', Identifier('score'), Literal(90.0))
    result = evaluate_query(ast, field_indices)

    assert result == {'card1', 'card2', 'card3'}


def test_evaluate_greater_than_operator():
    """Test > operator with numeric values."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority > 3
    ast = Compare('>', Identifier('priority'), Literal(3))
    result = evaluate_query(ast, field_indices)

    # Should include only cards with priority 4 and 5
    assert result == {'card4', 'card5'}


def test_evaluate_greater_than_with_dates():
    """Test > operator with date strings (assuming ISO format for ordering)."""
    date_index = MockNotecardIndex('DATE', {
        '2025-01-01': {'card1'},
        '2025-01-15': {'card2'},
        '2025-02-01': {'card3'},
        '2025-03-01': {'card4'}
    })

    field_indices = {'DATE': date_index}

    # Query: date > '2025-01-15'
    ast = Compare('>', Identifier('date'), Literal('2025-01-15'))
    result = evaluate_query(ast, field_indices)

    # Should include cards after 2025-01-15
    assert result == {'card3', 'card4'}


def test_evaluate_greater_than_no_matches():
    """Test > operator when no values are greater than threshold."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority > 5 (no values greater than 5)
    ast = Compare('>', Identifier('priority'), Literal(5))
    result = evaluate_query(ast, field_indices)

    assert result == set()


def test_evaluate_greater_than_boundary():
    """Test > operator at boundary - should exclude the boundary value."""
    score_index = MockNotecardIndex('SCORE', {
        85.0: {'card1'},
        90.0: {'card2', 'card3'},
        95.0: {'card4'}
    })

    field_indices = {'SCORE': score_index}

    # Query: score > 90.0 (should not include 90.0)
    ast = Compare('>', Identifier('score'), Literal(90.0))
    result = evaluate_query(ast, field_indices)

    assert result == {'card4'}


def test_evaluate_greater_equal_operator():
    """Test >= operator with numeric values."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority >= 3
    ast = Compare('>=', Identifier('priority'), Literal(3))
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority 3, 4, and 5
    assert result == {'card3', 'card4', 'card5'}


def test_evaluate_greater_equal_boundary():
    """Test >= operator includes the boundary value."""
    score_index = MockNotecardIndex('SCORE', {
        85.0: {'card1'},
        90.0: {'card2', 'card3'},
        95.0: {'card4'}
    })

    field_indices = {'SCORE': score_index}

    # Query: score >= 90.0 (should include 90.0)
    ast = Compare('>=', Identifier('score'), Literal(90.0))
    result = evaluate_query(ast, field_indices)

    assert result == {'card2', 'card3', 'card4'}


def test_evaluate_range_with_and():
    """Test range query using AND to combine >= and <=."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority >= 2 AND priority <= 4
    ast = And(
        Compare('>=', Identifier('priority'), Literal(2)),
        Compare('<=', Identifier('priority'), Literal(4))
    )
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority 2, 3, and 4
    assert result == {'card2', 'card3', 'card4'}


def test_evaluate_date_range_query():
    """Test date range query combining > and < operators with AND."""
    date_index = MockNotecardIndex('DATE', {
        '2025-01-01': {'card1'},
        '2025-01-15': {'card2'},
        '2025-02-01': {'card3'},
        '2025-02-15': {'card4'},
        '2025-03-01': {'card5'}
    })

    field_indices = {'DATE': date_index}

    # Query: date > '2025-01-01' AND date < '2025-03-01'
    ast = And(
        Compare('>', Identifier('date'), Literal('2025-01-01')),
        Compare('<', Identifier('date'), Literal('2025-03-01'))
    )
    result = evaluate_query(ast, field_indices)

    # Should include cards between the dates (exclusive)
    assert result == {'card2', 'card3', 'card4'}


def test_evaluate_inequality_with_or():
    """Test inequality operators combined with OR."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        2: {'card2'},
        3: {'card3'},
        4: {'card4'},
        5: {'card5'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority < 2 OR priority > 4
    ast = Or(
        Compare('<', Identifier('priority'), Literal(2)),
        Compare('>', Identifier('priority'), Literal(4))
    )
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority 1 or 5
    assert result == {'card1', 'card5'}


def test_evaluate_complex_query_with_inequalities():
    """Test complex query with multiple fields and inequality operators."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1', 'card2'},
        2: {'card3'},
        3: {'card4', 'card5'}
    })

    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card3', 'card4'},
        'pending': {'card2', 'card5'}
    })

    field_indices = {
        'PRIORITY': priority_index,
        'STATUS': status_index
    }

    # Query: priority >= 2 AND status = 'active'
    ast = And(
        Compare('>=', Identifier('priority'), Literal(2)),
        Compare('=', Identifier('status'), Literal('active'))
    )
    result = evaluate_query(ast, field_indices)

    # card3: priority 2, status active
    # card4: priority 3, status active
    assert result == {'card3', 'card4'}


def test_evaluate_inequality_unknown_field():
    """Test that inequality on unknown field returns empty set."""
    field_indices = {}

    # Query: unknown_field > 5
    ast = Compare('>', Identifier('unknown_field'), Literal(5))
    result = evaluate_query(ast, field_indices)

    assert result == set()


def test_evaluate_inequality_value_not_in_index():
    """Test inequality when the literal value is not in the index."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        3: {'card2'},
        5: {'card3'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority > 2 (2 is not in the index, but should still work)
    ast = Compare('>', Identifier('priority'), Literal(2))
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority > 2 (i.e., 3 and 5)
    assert result == {'card2', 'card3'}


def test_evaluate_less_than_value_not_in_index():
    """Test < when the literal value is not in the index."""
    priority_index = MockNotecardIndex('PRIORITY', {
        1: {'card1'},
        3: {'card2'},
        5: {'card3'}
    })

    field_indices = {'PRIORITY': priority_index}

    # Query: priority < 4 (4 is not in the index)
    ast = Compare('<', Identifier('priority'), Literal(4))
    result = evaluate_query(ast, field_indices)

    # Should include cards with priority < 4 (i.e., 1 and 3)
    assert result == {'card1', 'card2'}


def test_evaluate_all_operators_together():
    """Test all comparison operators can be used together."""
    value_index = MockNotecardIndex('VALUE', {
        10: {'card1'},
        20: {'card2'},
        30: {'card3'},
        40: {'card4'},
        50: {'card5'}
    })

    field_indices = {'VALUE': value_index}

    # Test each operator individually
    assert evaluate_query(Compare('=', Identifier('value'), Literal(30)), field_indices) == {'card3'}
    assert evaluate_query(Compare('<', Identifier('value'), Literal(30)), field_indices) == {'card1', 'card2'}
    assert evaluate_query(Compare('<=', Identifier('value'), Literal(30)), field_indices) == {'card1', 'card2', 'card3'}
    assert evaluate_query(Compare('>', Identifier('value'), Literal(30)), field_indices) == {'card4', 'card5'}
    assert evaluate_query(Compare('>=', Identifier('value'), Literal(30)), field_indices) == {'card3', 'card4', 'card5'}
