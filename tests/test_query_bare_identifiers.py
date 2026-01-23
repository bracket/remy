"""Tests for bare identifier and @id pseudo-index functionality."""

import pytest

from remy.exceptions import RemyError
from remy.notecard_index import null
from remy.query.parser import parse_query
from remy.query.eval import evaluate_query, _evaluate
from remy.query.set_types import create_pairset, pairset_to_labelset
from sortedcontainers import SortedSet


class MockNotecardIndex:
    """Mock NotecardIndex for testing."""

    def __init__(self, field_name, value_to_labels, notecard_cache=None):
        """
        Initialize mock index.

        Args:
            field_name: Name of the field (will be uppercased)
            value_to_labels: Dict mapping values to sets of labels
            notecard_cache: Mock notecard cache (optional)
        """
        self.field_name = field_name.upper()
        self.value_to_labels = value_to_labels
        self.notecard_cache = notecard_cache

    def find(self, low=null, high=null, snap=None):
        """
        Mock implementation of NotecardIndex.find().

        Yields:
            Tuples of (value, label) for matching entries
        """
        for value in self.value_to_labels.keys():
            # Exact match case
            if low is not null and high is not null and low == high:
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
            for label in self.value_to_labels[value]:
                yield (value, label)


class MockNotecardCache:
    """Mock NotecardCache for testing."""
    
    def __init__(self, primary_labels):
        self.primary_labels = primary_labels


def test_bare_identifier_references_whole_index():
    """Test that bare identifier returns all pairs from an index."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card3'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # Query: labels(tags) should return all cards with tags
    ast = parse_query("labels(tags)")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_bare_identifier_in_join():
    """Test bare identifier in join operation (the main use case)."""
    cache = MockNotecardCache(['card1', 'card2', 'card3', 'card4'])
    
    previous_index = MockNotecardIndex('PREVIOUS', {
        'card2': {'card3'},  # card3 points to card2
        'card1': {'card2'}   # card2 points to card1
    }, notecard_cache=cache)
    
    tags_index = MockNotecardIndex('TAGS', {
        'remy': {'card2'}  # card2 is tagged with 'remy'
    }, notecard_cache=cache)
    
    field_indices = {'PREVIOUS': previous_index, 'TAGS': tags_index}
    
    # Query: join_by_value_to_label(previous, tags='remy')
    # Should find cards whose 'previous' value matches a card tagged with 'remy'
    # previous has: (card2, card3), (card1, card2)
    # tags='remy' has: (remy, card2)
    # Join where value 'card2' matches label 'card2' -> result (remy, card3)
    # But wait, we want cards that reference (via previous) a card tagged with 'remy'
    # So: previous contains (cardX, cardY) where cardY is tagged with 'remy'
    # previous: {(card2, card3), (card1, card2)}
    # We want pairs where value (card3 or card2) is in labels of tags='remy'
    # tags='remy' labels: {card2}
    # So we want: pairs from previous where value is card2 -> (card1, card2)
    # Result: card2 (the label)
    # Actually, let me re-read the use case...
    
    ast = parse_query("join_by_value_to_label(previous, tags='remy')")
    result = evaluate_query(ast, field_indices)
    # The join should give us cards whose previous field points to a card tagged with remy
    # previous: (card2, card3), (card1, card2)
    # tags='remy': (remy, card2)
    # Join: for (v, l) in previous and (v2, l2) in tags='remy', if v == l2, yield (v2, l)
    # So: (card2, card3) from previous, card2 matches label in tags='remy', yield (remy, card3)
    # And: (card1, card2) from previous, card1 does NOT match any label in tags='remy'
    # Result: {card3}
    assert result == {'card3'}


def test_at_id_pseudo_index():
    """Test @id pseudo-index containing (label, label) pairs."""
    cache = MockNotecardCache(['card1', 'card2', 'card3'])
    
    # Create a mock index just to provide access to the cache
    dummy_index = MockNotecardIndex('DUMMY', {}, notecard_cache=cache)
    
    field_indices = {'DUMMY': dummy_index}
    
    # Query: labels(@id) should return all primary labels
    ast = parse_query("labels(@id)")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_at_id_with_status_filter():
    """Test @id combined with status filter."""
    cache = MockNotecardCache(['card1', 'card2', 'card3', 'card4'])
    
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card3'}
    }, notecard_cache=cache)
    
    field_indices = {'STATUS': status_index}
    
    # Query: intersect_by_label(@id, status='active')
    # @id contains all cards: (card1, card1), (card2, card2), (card3, card3), (card4, card4)
    # status='active' contains: (active, card1), (active, card3)
    # intersect_by_label keeps pairs from @id whose label appears in status='active'
    # Result: (card1, card1), (card3, card3) -> labels {card1, card3}
    ast = parse_query("intersect_by_label(@id, status='active')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card3'}


def test_bare_identifier_unknown_field_error():
    """Test that unknown bare identifier raises error."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # Query: labels(unknown_field)
    ast = parse_query("labels(unknown_field)")
    with pytest.raises(RemyError, match="does not reference a known field index"):
        evaluate_query(ast, field_indices)


def test_union_with_bare_identifiers():
    """Test union of two bare identifiers."""
    cache = MockNotecardCache(['card1', 'card2', 'card3', 'card4'])
    
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'}
    }, notecard_cache=cache)
    
    categories_index = MockNotecardIndex('CATEGORIES', {
        'work': {'card2', 'card3'}
    }, notecard_cache=cache)
    
    field_indices = {'TAGS': tags_index, 'CATEGORIES': categories_index}
    
    # Query: union(tags, categories)
    # Should return all pairs from both indices
    ast = parse_query("labels(union(tags, categories))")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_existing_queries_still_work():
    """Test that existing comparison-based queries still work."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # Old-style query should still work
    ast = parse_query("tags='foo'")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2'}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
