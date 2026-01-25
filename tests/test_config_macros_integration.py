"""Integration tests for config-based macros with real notecard cache."""

import pytest
import tempfile
import shutil
from pathlib import Path

from remy import NotecardCache
from remy.url import URL
from remy.cli.__main__ import execute_query_filter


@pytest.fixture
def test_cache_dir():
    """Create a temporary test cache directory with notecards and config."""
    # Create temporary directory
    tmpdir = Path(tempfile.mkdtemp())
    
    try:
        # Create .remy directory
        config_dir = tmpdir / '.remy'
        config_dir.mkdir()
        
        # Create config.py with PARSER_BY_FIELD_NAME and MACROS
        config_content = '''
def tags_parser(field):
    return tuple(f.strip().lower() for f in field.split(','))

def status_parser(field):
    return (field.strip().lower(),)

PARSER_BY_FIELD_NAME = {
    'TAGS': tags_parser,
    'STATUS': status_parser,
}

MACROS = {
    'WORK': '@work := tags="work"',
    'URGENT': '@urgent := tags="urgent"',
    'ACTIVE': '@active := status="active"',
    'CLOSED': '@closed := status="closed"',
    'ACTIVE_WORK': '@active_work := @work AND @active',
    'FILTER': '@filter(Field, Value) := Field=Value',
}
'''
        (config_dir / 'config.py').write_text(config_content)
        
        # Create some notecard files
        notecard1 = '''NOTECARD task1
:TAGS: work, urgent
:STATUS: active

This is a work task that is urgent.
'''
        
        notecard2 = '''NOTECARD task2
:TAGS: work
:STATUS: closed

This is a closed work task.
'''
        
        notecard3 = '''NOTECARD task3
:TAGS: personal
:STATUS: active

This is a personal task.
'''
        
        notecard4 = '''NOTECARD task4
:TAGS: work, urgent
:STATUS: closed

Another closed urgent work task.
'''
        
        # Write notecard files
        (tmpdir / 'notes.ntc').write_text(notecard1 + '\n' + notecard2 + '\n' + notecard3 + '\n' + notecard4)
        
        yield tmpdir
    finally:
        # Cleanup
        shutil.rmtree(tmpdir)


def test_config_macro_basic_usage(test_cache_dir):
    """Test using a simple config macro in a query."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @work macro from config
    cards = execute_query_filter(cache, "@work")
    
    # Should match task1, task2, and task4 (all have tags="work")
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1', 'task2', 'task4'}


def test_config_macro_combined_with_and(test_cache_dir):
    """Test combining config macros with AND operator."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @work AND @urgent from config
    cards = execute_query_filter(cache, "@work AND @urgent")
    
    # Should match task1 and task4 (both have tags="work" and tags="urgent")
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1', 'task4'}


def test_config_macro_with_query_macro(test_cache_dir):
    """Test using config macro with query-defined macro."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Define @inactive in query and use with @work from config
    cards = execute_query_filter(cache, "@inactive := status='closed'; @work AND @inactive")
    
    # Should match task2 and task4 (work tasks that are closed)
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task2', 'task4'}


def test_config_macro_referencing_another_config_macro(test_cache_dir):
    """Test config macro that references another config macro."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @active_work which is defined as @work AND @active in config
    cards = execute_query_filter(cache, "@active_work")
    
    # Should match task1 only (has tags="work" and status="active")
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1'}


def test_config_macro_parametric(test_cache_dir):
    """Test using a parametric config macro."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @filter parametric macro from config
    cards = execute_query_filter(cache, "@filter(tags, 'work')")
    
    # Should match task1, task2, and task4 (all have tags="work")
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1', 'task2', 'task4'}


def test_config_macro_or_combination(test_cache_dir):
    """Test combining config macros with OR operator."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @urgent OR @closed from config
    cards = execute_query_filter(cache, "@urgent OR @closed")
    
    # Should match task1, task2, and task4 
    # (task1 and task4 are urgent, task2 and task4 are closed)
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1', 'task2', 'task4'}


def test_config_macro_with_regular_query(test_cache_dir):
    """Test mixing config macros with regular query expressions."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Use @work from config with a regular filter
    cards = execute_query_filter(cache, "@work AND status='active'")
    
    # Should match task1 only
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1'}


def test_query_without_config_macros_still_works(test_cache_dir):
    """Test that regular queries still work when config has macros."""
    cache = NotecardCache(URL(test_cache_dir))
    
    # Regular query without using any macros
    cards = execute_query_filter(cache, "tags='personal'")
    
    # Should match task3
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task3'}


def test_config_macro_duplicate_error(test_cache_dir):
    """Test that duplicate macro names between config and query are rejected."""
    from remy.exceptions import RemyError
    
    cache = NotecardCache(URL(test_cache_dir))
    
    # Try to redefine @work which is already in config
    with pytest.raises(RemyError, match="already defined in config"):
        execute_query_filter(cache, "@work := tags='different'; @work")


def test_cache_without_macros_in_config(test_cache_dir):
    """Test that cache works when config doesn't have MACROS."""
    # Create a new config without MACROS
    config_dir = test_cache_dir / '.remy'
    config_content = '''
def tags_parser(field):
    return tuple(f.strip().lower() for f in field.split(','))

PARSER_BY_FIELD_NAME = {
    'TAGS': tags_parser,
}
'''
    (config_dir / 'config.py').write_text(config_content)
    
    cache = NotecardCache(URL(test_cache_dir))
    
    # Query with its own macros should still work
    cards = execute_query_filter(cache, "@work := tags='work'; @work")
    
    # Should match task1, task2, and task4
    labels = [card.primary_label for card in cards]
    assert set(labels) == {'task1', 'task2', 'task4'}
