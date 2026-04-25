"""Tests for type mismatch detection in query comparisons."""

import pytest
from datetime import date, datetime, timezone

from remy.exceptions import InvalidComparison
from remy.notecard_index import null, NotecardIndex
from remy.query.eval import evaluate_query
from remy.query.ast_nodes import (
    Compare, Identifier, DateLiteral, DateTimeLiteral, Literal
)


# ---------------------------------------------------------------------------
# Mock index helpers
# ---------------------------------------------------------------------------

class MockTypedIndex:
    """
    Mock index that stores typed values and properly exposes indexed_types.

    The find() method uses the real (id(type), value) key ordering so that
    range queries behave the same as NotecardIndex.find().
    """

    def __init__(self, field_name, value_to_labels):
        """
        Args:
            field_name: Field name string (will be uppercased).
            value_to_labels: Dict mapping field values to sets of labels.
        """
        self.field_name = field_name.upper()
        self.value_to_labels = value_to_labels

    @property
    def indexed_types(self):
        return frozenset(type(v) for v in self.value_to_labels.keys())

    def find(self, low=null, high=null, snap=None):
        """Yield (value, label) pairs within the key-ordered range."""
        if low is not null:
            low_key = (id(type(low)), low)
        else:
            low_key = None

        if high is not null:
            high_key = (id(type(high)), high)
        else:
            high_key = None

        for value, labels in self.value_to_labels.items():
            val_key = (id(type(value)), value)

            if low_key is not None:
                try:
                    if val_key < low_key:
                        continue
                except TypeError:
                    continue

            if high_key is not None:
                try:
                    if val_key > high_key:
                        continue
                except TypeError:
                    continue

            for label in labels:
                yield (value, label)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TODAY = date(2024, 6, 1)
TODAY_DT = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

DATETIME_ONLY_INDEX = MockTypedIndex('CREATED', {
    datetime(2024, 5, 25, 0, 0, 0, tzinfo=timezone.utc): {'card1'},
    datetime(2024, 5, 30, 0, 0, 0, tzinfo=timezone.utc): {'card2'},
    datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc): {'card3'},
})

DATE_ONLY_INDEX = MockTypedIndex('CREATED', {
    date(2024, 5, 25): {'card1'},
    date(2024, 5, 30): {'card2'},
    date(2024, 6, 1): {'card3'},
})

MIXED_INDEX = MockTypedIndex('CREATED', {
    date(2024, 5, 20): {'card_date1'},
    datetime(2024, 5, 25, 0, 0, 0, tzinfo=timezone.utc): {'card_dt1'},
    date(2024, 5, 28): {'card_date2'},
    datetime(2024, 6, 1, 0, 0, 0, tzinfo=timezone.utc): {'card_dt2'},
})

EMPTY_INDEX = MockTypedIndex('CREATED', {})


# ---------------------------------------------------------------------------
# Helper to build a Compare AST node against a DateLiteral or DateTimeLiteral
# ---------------------------------------------------------------------------

def date_compare(op, field, value):
    """Return a Compare(op, Identifier(field), DateLiteral(value)) node."""
    return Compare(op, Identifier(field), DateLiteral(value))


def datetime_compare(op, field, value):
    """Return a Compare(op, Identifier(field), DateTimeLiteral(value)) node."""
    return Compare(op, Identifier(field), DateTimeLiteral(value))


# ---------------------------------------------------------------------------
# Tests: ordering operators against datetime-only index with a date value
# ---------------------------------------------------------------------------

def test_gte_date_against_datetime_index_raises():
    """created >= <date> against datetime-only index raises InvalidComparison."""
    ast = date_compare('>=', 'created', TODAY)
    with pytest.raises(InvalidComparison, match="date"):
        evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})


def test_gt_date_against_datetime_index_raises():
    """created > <date> against datetime-only index raises InvalidComparison."""
    ast = date_compare('>', 'created', TODAY)
    with pytest.raises(InvalidComparison, match="date"):
        evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})


def test_lte_date_against_datetime_index_raises():
    """created <= <date> against datetime-only index raises InvalidComparison."""
    ast = date_compare('<=', 'created', TODAY)
    with pytest.raises(InvalidComparison, match="date"):
        evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})


def test_lt_date_against_datetime_index_raises():
    """created < <date> against datetime-only index raises InvalidComparison."""
    ast = date_compare('<', 'created', TODAY)
    with pytest.raises(InvalidComparison, match="date"):
        evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})


# ---------------------------------------------------------------------------
# Test: equality operator against datetime-only index with a date value -> empty
# ---------------------------------------------------------------------------

def test_eq_date_against_datetime_index_returns_empty():
    """created = <date> against datetime-only index returns empty (no error)."""
    ast = date_compare('=', 'created', TODAY)
    result = evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})
    assert result == set()


# ---------------------------------------------------------------------------
# Tests: ordering operators against mixed (date + datetime) index
# ---------------------------------------------------------------------------

def test_gte_date_against_mixed_index_no_error():
    """created >= <date> against mixed index does not raise InvalidComparison."""
    ast = date_compare('>=', 'created', TODAY)
    # Should not raise; result content is implementation-defined
    evaluate_query(ast, {'CREATED': MIXED_INDEX})


def test_gte_datetime_against_mixed_index_no_error():
    """created >= <datetime> against mixed index does not raise InvalidComparison."""
    ast = datetime_compare('>=', 'created', TODAY_DT)
    evaluate_query(ast, {'CREATED': MIXED_INDEX})


def test_gt_date_against_mixed_index_no_error():
    """created > <date> against mixed index does not raise InvalidComparison."""
    ast = date_compare('>', 'created', TODAY)
    evaluate_query(ast, {'CREATED': MIXED_INDEX})


def test_lte_datetime_against_mixed_index_no_error():
    """created <= <datetime> against mixed index does not raise InvalidComparison."""
    ast = datetime_compare('<=', 'created', TODAY_DT)
    evaluate_query(ast, {'CREATED': MIXED_INDEX})


# ---------------------------------------------------------------------------
# Tests: ordering operators work correctly when value type matches sole type
# ---------------------------------------------------------------------------

def test_gte_datetime_against_datetime_index_correct():
    """created >= <datetime> against datetime-only index returns correct results."""
    threshold = datetime(2024, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    ast = datetime_compare('>=', 'created', threshold)
    result = evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})
    assert result == {'card2', 'card3'}


def test_gt_datetime_against_datetime_index_correct():
    """created > <datetime> against datetime-only index returns correct results."""
    threshold = datetime(2024, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    ast = datetime_compare('>', 'created', threshold)
    result = evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})
    assert result == {'card3'}


def test_lte_datetime_against_datetime_index_correct():
    """created <= <datetime> against datetime-only index returns correct results."""
    threshold = datetime(2024, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    ast = datetime_compare('<=', 'created', threshold)
    result = evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})
    assert result == {'card1', 'card2'}


def test_lt_datetime_against_datetime_index_correct():
    """created < <datetime> against datetime-only index returns correct results."""
    threshold = datetime(2024, 5, 30, 0, 0, 0, tzinfo=timezone.utc)
    ast = datetime_compare('<', 'created', threshold)
    result = evaluate_query(ast, {'CREATED': DATETIME_ONLY_INDEX})
    assert result == {'card1'}


def test_gte_date_against_date_index_correct():
    """created >= <date> against date-only index returns correct results."""
    threshold = date(2024, 5, 30)
    ast = date_compare('>=', 'created', threshold)
    result = evaluate_query(ast, {'CREATED': DATE_ONLY_INDEX})
    assert result == {'card2', 'card3'}


# ---------------------------------------------------------------------------
# Tests: ordering comparison against empty index returns empty (no error)
# ---------------------------------------------------------------------------

def test_gte_against_empty_index_returns_empty():
    """created >= <date> against empty index returns empty result (no error)."""
    ast = date_compare('>=', 'created', TODAY)
    result = evaluate_query(ast, {'CREATED': EMPTY_INDEX})
    assert result == set()


def test_gt_against_empty_index_returns_empty():
    """created > <datetime> against empty index returns empty result (no error)."""
    ast = datetime_compare('>', 'created', TODAY_DT)
    result = evaluate_query(ast, {'CREATED': EMPTY_INDEX})
    assert result == set()


def test_lte_against_empty_index_returns_empty():
    """created <= <date> against empty index returns empty result (no error)."""
    ast = date_compare('<=', 'created', TODAY)
    result = evaluate_query(ast, {'CREATED': EMPTY_INDEX})
    assert result == set()


def test_lt_against_empty_index_returns_empty():
    """created < <datetime> against empty index returns empty result (no error)."""
    ast = datetime_compare('<', 'created', TODAY_DT)
    result = evaluate_query(ast, {'CREATED': EMPTY_INDEX})
    assert result == set()


# ---------------------------------------------------------------------------
# Test: NotecardIndex.indexed_types is populated correctly after index build
# ---------------------------------------------------------------------------

class MockCard:
    def __init__(self, primary_label, content, source_url='mock://test'):
        self.primary_label = primary_label
        self.content = content
        self.source_url = source_url


class MockNotecardCache:
    def __init__(self, cards):
        # cards: list of MockCard
        self.cards_by_label = {card.primary_label: card for card in cards}
        self.primary_labels = [card.primary_label for card in cards]


def _datetime_parser(value):
    """Parse a datetime string like '2024-06-01T12:00:00' into a datetime."""
    dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return [dt]


def test_notecard_index_indexed_types_datetime():
    """NotecardIndex.indexed_types returns frozenset({datetime}) for datetime values."""
    cards = [
        MockCard('card1', ':CREATED: 2024-05-25T00:00:00\nContent 1'),
        MockCard('card2', ':CREATED: 2024-05-30T00:00:00\nContent 2'),
    ]
    cache = MockNotecardCache(cards)
    idx = NotecardIndex(cache, 'CREATED', _datetime_parser)

    # Before access, should not yet be built
    # After access, should reflect datetime
    result = idx.indexed_types
    assert result == frozenset({datetime})


def test_notecard_index_indexed_types_empty():
    """NotecardIndex.indexed_types is an empty frozenset when no cards have the field."""
    cards = [
        MockCard('card1', 'No field here\nJust content'),
    ]
    cache = MockNotecardCache(cards)
    idx = NotecardIndex(cache, 'CREATED', _datetime_parser)

    result = idx.indexed_types
    assert result == frozenset()


def test_notecard_index_indexed_types_cached():
    """NotecardIndex.indexed_types returns the same frozenset on repeated access."""
    cards = [
        MockCard('card1', ':CREATED: 2024-05-25T00:00:00\nContent'),
    ]
    cache = MockNotecardCache(cards)
    idx = NotecardIndex(cache, 'CREATED', _datetime_parser)

    first = idx.indexed_types
    second = idx.indexed_types
    assert first is second  # Same object (cached)
