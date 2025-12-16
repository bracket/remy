"""
Groupby utilities for grouping iterables by key.
"""

from collections import defaultdict


def list_groupby(iterable):
    """
    Group items by key into lists.
    
    Args:
        iterable: An iterable of (key, value) tuples
    
    Returns:
        A dictionary mapping keys to lists of values
    """
    result = defaultdict(list)
    for key, value in iterable:
        result[key].append(value)
    return dict(result)


def set_groupby(iterable):
    """
    Group items by key into sets.
    
    Args:
        iterable: An iterable of (key, value) tuples
    
    Returns:
        A dictionary mapping keys to sets of values
    """
    result = defaultdict(set)
    for key, value in iterable:
        result[key].add(value)
    return dict(result)
