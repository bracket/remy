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
