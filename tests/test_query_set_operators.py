"""Tests for query set operators."""

import pytest

from remy.exceptions import RemyError
from remy.notecard_index import null
from remy.query.parser import parse_query
from remy.query.eval import evaluate_query, _evaluate
from remy.query.set_types import ValueSet, create_pairset, pairset_to_labelset
from sortedcontainers import SortedSet


class MockNotecardIndex:
    """Mock NotecardIndex for testing."""

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


def test_function_call_parsing():
    """Test that function calls parse correctly."""
    # Simple function call
    ast = parse_query("union(tags='foo', tags='bar')")
    assert ast.function_name == 'union'
    assert len(ast.arguments) == 2
    
    # Nested function call
    ast = parse_query("intersect_by_label(union(tags='a', tags='b'), status='active')")
    assert ast.function_name == 'intersect_by_label'
    assert len(ast.arguments) == 2
    assert ast.arguments[0].function_name == 'union'


def test_intersect_by_label_basic():
    """Test intersect_by_label operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card3'},
        'inactive': {'card2'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index}
    
    # intersect_by_label(tags='foo', status='active')
    # Should keep pairs from tags='foo' whose label appears in status='active'
    # tags='foo': {(foo, card1), (foo, card2)}
    # status='active': labels {card1, card3}
    # Result: {card1} (only card1 is in both)
    ast = parse_query("intersect_by_label(tags='foo', status='active')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1'}


def test_intersect_by_value_basic():
    """Test intersect_by_value operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card3'}
    })
    categories_index = MockNotecardIndex('CATEGORIES', {
        'foo': {'card4'},  # Same value 'foo'
        'baz': {'card5'}
    })
    
    field_indices = {'TAGS': tags_index, 'CATEGORIES': categories_index}
    
    # intersect_by_value(tags='foo', categories='foo')
    # Should keep pairs from tags='foo' whose value appears in categories='foo'
    # Since 'foo' appears in both, should return all cards with tags='foo'
    ast = parse_query("intersect_by_value(tags='foo', categories='foo')")
    result = evaluate_query(ast, field_indices)
    # tags='foo' has {card1, card2}, and value 'foo' is in categories
    assert result == {'card1', 'card2'}


def test_difference_by_label_basic():
    """Test difference_by_label operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index}
    
    # difference_by_label(tags='foo', status='active')
    # Should remove pairs from tags='foo' whose label appears in status='active'
    # tags='foo': {(foo, card1), (foo, card2)}
    # status='active': labels {card1}
    # Result: {card2} (card1 is removed)
    ast = parse_query("difference_by_label(tags='foo', status='active')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card2'}


def test_difference_by_value_basic():
    """Test difference_by_value operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card3'}
    })
    excluded_tags_index = MockNotecardIndex('EXCLUDED', {
        'foo': {'card4'}  # Same value 'foo'
    })
    
    field_indices = {'TAGS': tags_index, 'EXCLUDED': excluded_tags_index}
    
    # difference_by_value(tags='bar', excluded='foo')
    # Should keep pairs from tags='bar' whose value is NOT 'foo'
    # tags='bar' has value 'bar', excluded has value 'foo'
    # Result: {card3} (bar != foo, so it's kept)
    ast = parse_query("difference_by_value(tags='bar', excluded='foo')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card3'}


def test_union_operator():
    """Test union operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card3'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # union(tags='foo', tags='bar')
    # Should return all cards with either tag
    ast = parse_query("union(tags='foo', tags='bar')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_intersect_operator():
    """Test intersect operator (pair-unaware)."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # intersect(tags='foo', tags='bar')
    # Should return only pairs that appear in both (exact pair match)
    # Since tags='foo' and tags='bar' have different values, no overlap
    ast = parse_query("intersect(tags='foo', tags='bar')")
    result = evaluate_query(ast, field_indices)
    # No pairs match exactly
    assert result == set()
    
    # But if we have the same value for both:
    tags_index2 = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2', 'card3'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'foo': {'card1', 'card4'}  # Same value 'foo', overlapping labels
    })
    
    field_indices2 = {'TAGS': tags_index2, 'STATUS': status_index}
    
    # intersect(tags='foo', status='foo')
    # Should return cards that have (foo, card) pairs in both
    ast2 = parse_query("intersect(tags='foo', status='foo')")
    result2 = evaluate_query(ast2, field_indices2)
    # card1 appears in both with value 'foo'
    assert result2 == {'card1'}


def test_labels_projection():
    """Test labels projection operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # labels(tags='foo')
    # Should project to label set (which it already is after evaluation)
    ast = parse_query("labels(tags='foo')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2'}
    
    # labels on a union
    ast2 = parse_query("labels(union(tags='foo', tags='bar'))")
    result2 = evaluate_query(ast2, field_indices)
    assert result2 == {'card1', 'card2', 'card3'}


def test_values_projection():
    """Test values projection operator."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card3'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # values(tags='foo')
    # Should project to value set
    ast = parse_query("values(tags='foo')")
    
    # This should raise an error because ValueSet cannot be used to select notecards
    with pytest.raises(RemyError, match="evaluates to a ValueSet"):
        evaluate_query(ast, field_indices)


def test_labels_on_labelset_noop():
    """Test that labels() on a LabelSet is a no-op."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # labels(labels(tags='foo')) should be same as labels(tags='foo')
    ast = parse_query("labels(labels(tags='foo'))")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2'}


def test_labels_on_valueset_error():
    """Test that labels() on a ValueSet raises an error."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # labels(values(tags='foo')) should raise an error
    ast = parse_query("labels(values(tags='foo'))")
    with pytest.raises(RemyError, match="cannot be called on a ValueSet"):
        evaluate_query(ast, field_indices)


def test_values_on_valueset_noop():
    """Test that values() on a ValueSet is a no-op (though we can't easily test this through evaluate_query)."""
    # This would require accessing _evaluate directly since evaluate_query errors on ValueSet results
    pass


def test_values_on_labelset_error():
    """Test that values() on a LabelSet raises an error."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # values(labels(tags='foo')) should raise an error
    ast = parse_query("values(labels(tags='foo'))")
    with pytest.raises(RemyError, match="cannot be called on a LabelSet"):
        evaluate_query(ast, field_indices)


def test_nested_function_calls():
    """Test nested function calls."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'},
        'baz': {'card3', 'card4'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2', 'card3'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index}
    
    # intersect_by_label(union(tags='foo', tags='bar'), status='active')
    # union gives {card1, card2, card3}
    # intersect_by_label filters to cards that are active
    # All three are active, so result is {card1, card2, card3}
    ast = parse_query("intersect_by_label(union(tags='foo', tags='bar'), status='active')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_backward_compatibility_and():
    """Test that AND still works with new semantics (uses intersect_by_label)."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card3'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index}
    
    # Old syntax: tags='foo' AND status='active'
    # Should use intersect_by_label semantics
    ast = parse_query("tags='foo' AND status='active'")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1'}  # Only card1 has both


def test_backward_compatibility_or():
    """Test that OR still works with new semantics (uses union)."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card3'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index}
    
    # Old syntax: tags='foo' OR status='active'
    # Should use union semantics
    ast = parse_query("tags='foo' OR status='active'")
    result = evaluate_query(ast, field_indices)
    assert result == {'card1', 'card2', 'card3'}


def test_join_by_value_to_label():
    """Test join_by_value_to_label operator."""
    # Create a chain using 'previous' field
    # card3's previous is card2, card2's previous is card1
    current_index = MockNotecardIndex('CURRENT', {
        'card1': {'card1'},  # Self-reference for simplicity
        'card2': {'card2'},
        'card3': {'card3'}
    })
    previous_index = MockNotecardIndex('PREVIOUS', {
        'card2': {'card3'},  # card3 points to card2
        'card1': {'card2'}   # card2 points to card1
    })
    
    field_indices = {'CURRENT': current_index, 'PREVIOUS': previous_index}
    
    # join_by_value_to_label(previous='card2', current='card2')
    # previous='card2': {(card2, card3)}
    # current='card2': {(card2, card2)}
    # Join where value 'card2' matches label 'card2'
    # Result: {(card2, card3)} -> labels {card3}
    ast = parse_query("join_by_value_to_label(previous='card2', current='card2')")
    result = evaluate_query(ast, field_indices)
    assert result == {'card3'}


def test_union_type_mismatch_error():
    """Test that union requires matching types."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # union(tags='foo', labels(tags='foo'))
    # First is PairSet, second is LabelSet - should error
    # Actually, both will be PairSets after evaluation, so this should work
    # Let me use values to create a type mismatch
    
    # union(tags='foo', values(tags='foo'))
    # First is PairSet, second is ValueSet - should error
    ast = parse_query("union(tags='foo', values(tags='foo'))")
    with pytest.raises(RemyError, match="both arguments must be the same type"):
        evaluate_query(ast, field_indices)


def test_intersect_type_mismatch_error():
    """Test that intersect requires matching types."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # intersect(tags='foo', values(tags='foo'))
    # First is PairSet, second is ValueSet - should error
    ast = parse_query("intersect(tags='foo', values(tags='foo'))")
    with pytest.raises(RemyError, match="both arguments must be the same type"):
        evaluate_query(ast, field_indices)


def test_unknown_function_error():
    """Test that unknown functions raise an error."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    ast = parse_query("unknown_func(tags='foo')")
    with pytest.raises(RemyError, match="Unknown function"):
        evaluate_query(ast, field_indices)


def test_wrong_argument_count_error():
    """Test that functions with wrong argument count raise an error."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1'}
    })
    
    field_indices = {'TAGS': tags_index}
    
    # union expects 2 arguments
    ast = parse_query("union(tags='foo')")
    with pytest.raises(RemyError, match="expects 2 arguments"):
        evaluate_query(ast, field_indices)
    
    # labels expects 1 argument
    ast2 = parse_query("labels(tags='foo', tags='bar')")
    with pytest.raises(RemyError, match="expects 1 argument"):
        evaluate_query(ast2, field_indices)


def test_valueset_type_separation():
    """Test that ValueSet properly separates values of different types."""
    # Create a ValueSet with mixed types
    vs = ValueSet()
    vs.add("string")
    vs.add(42)
    vs.add(3.14)
    vs.add("another")
    
    assert len(vs) == 4
    assert "string" in vs
    assert 42 in vs
    assert 3.14 in vs
    assert "another" in vs
    
    # Different type with same repr shouldn't match
    assert "42" not in vs  # String "42" is different from int 42
    
    # Test union
    vs2 = ValueSet()
    vs2.add("string")
    vs2.add(99)
    
    union_vs = vs.union(vs2)
    assert len(union_vs) == 5  # string, 42, 3.14, another, 99
    
    # Test intersection
    intersect_vs = vs.intersection(vs2)
    assert len(intersect_vs) == 1  # Only "string" overlaps
    assert "string" in intersect_vs


def test_complex_nested_query():
    """Test a complex nested query with multiple operators."""
    tags_index = MockNotecardIndex('TAGS', {
        'foo': {'card1', 'card2'},
        'bar': {'card2', 'card3'},
        'baz': {'card4'}
    })
    status_index = MockNotecardIndex('STATUS', {
        'active': {'card1', 'card2', 'card4'},
        'inactive': {'card3'}
    })
    priority_index = MockNotecardIndex('PRIORITY', {
        'high': {'card1', 'card4'}
    })
    
    field_indices = {'TAGS': tags_index, 'STATUS': status_index, 'PRIORITY': priority_index}
    
    # Complex query: labels(intersect_by_label(union(tags='foo', tags='bar'), 
    #                                          intersect_by_label(status='active', priority='high')))
    # Step 1: union(tags='foo', tags='bar') = {card1, card2, card2, card3} = {card1, card2, card3}
    # Step 2: intersect_by_label(status='active', priority='high') 
    #         = status pairs where label in priority='high' 
    #         = {(active, card1), (active, card4)} (only card1 and card4 are high priority)
    #         -> labels {card1, card4}
    # Step 3: intersect_by_label(union_result, intersect_result)
    #         = pairs from union where label in {card1, card4}
    #         = {card1} (only card1 is in both sets)
    # Step 4: labels() = {card1}
    
    ast = parse_query(
        "labels(intersect_by_label(union(tags='foo', tags='bar'), "
        "intersect_by_label(status='active', priority='high')))"
    )
    result = evaluate_query(ast, field_indices)
    assert result == {'card1'}
