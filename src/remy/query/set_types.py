"""
Set types for query evaluation: PairSet, LabelSet, and ValueSet.

These classes provide type-aware set operations for the query language,
ensuring proper handling of non-homogeneous values.
"""

from sortedcontainers import SortedSet
from typing import Any, Iterable, Tuple


class ValueSet:
    """
    A type-aware set of values that maintains separation between incomparable types.
    
    Values are stored using the same type-prefixing scheme as NotecardIndex:
    each value is stored as (id(type(value)), value) to prevent comparing
    incomparable types like strings and integers.
    
    This class semantically behaves like a SortedSet but with built-in type handling.
    """
    
    def __init__(self, values: Iterable[Any] = None):
        """
        Initialize a ValueSet.
        
        Args:
            values: Optional iterable of values to initialize the set with
        """
        self._set = SortedSet()
        if values:
            for value in values:
                self.add(value)
    
    def add(self, value: Any):
        """Add a value to the set."""
        typed_value = (id(type(value)), value)
        self._set.add(typed_value)
    
    def __contains__(self, value: Any) -> bool:
        """Check if a value is in the set."""
        typed_value = (id(type(value)), value)
        return typed_value in self._set
    
    def __iter__(self):
        """Iterate over values (without type prefixes)."""
        for typed_value in self._set:
            yield typed_value[1]
    
    def __len__(self) -> int:
        """Return the number of values in the set."""
        return len(self._set)
    
    def __repr__(self) -> str:
        """Return a string representation of the ValueSet."""
        return f"ValueSet({list(self)})"
    
    def __eq__(self, other) -> bool:
        """Check equality with another ValueSet."""
        if not isinstance(other, ValueSet):
            return False
        return self._set == other._set
    
    def union(self, other: 'ValueSet') -> 'ValueSet':
        """Return the union of this ValueSet with another."""
        if not isinstance(other, ValueSet):
            raise TypeError(f"Cannot union ValueSet with {type(other).__name__}")
        result = ValueSet()
        result._set = self._set | other._set
        return result
    
    def intersection(self, other: 'ValueSet') -> 'ValueSet':
        """Return the intersection of this ValueSet with another."""
        if not isinstance(other, ValueSet):
            raise TypeError(f"Cannot intersect ValueSet with {type(other).__name__}")
        result = ValueSet()
        result._set = self._set & other._set
        return result
    
    def to_sorted_set(self) -> SortedSet:
        """Convert to a plain SortedSet (with type prefixes)."""
        return self._set.copy()


# Type aliases for clarity
LabelSet = set  # LabelSets are just regular Python sets of strings
PairSet = SortedSet  # PairSets are SortedSets of ((type_id, value), label) tuples


def create_pairset(pairs: Iterable[Tuple[Any, str]] = None) -> PairSet:
    """
    Create a PairSet from an iterable of (value, label) tuples.
    
    Args:
        pairs: Iterable of (value, label) tuples
        
    Returns:
        A SortedSet of ((type_id, value), label) tuples
    """
    pairset = SortedSet()
    if pairs:
        for value, label in pairs:
            typed_value = (id(type(value)), value)
            pairset.add((typed_value, label))
    return pairset


def pairset_to_labelset(pairset: PairSet) -> LabelSet:
    """
    Project a PairSet to a LabelSet (extract labels).
    
    Args:
        pairset: A PairSet
        
    Returns:
        A set of labels (strings)
    """
    return {label for _, label in pairset}


def pairset_to_valueset(pairset: PairSet) -> ValueSet:
    """
    Project a PairSet to a ValueSet (extract values).
    
    Args:
        pairset: A PairSet
        
    Returns:
        A ValueSet containing all unique values
    """
    valueset = ValueSet()
    for typed_value, _ in pairset:
        # typed_value is already (type_id, value)
        valueset._set.add(typed_value)
    return valueset
