"""Tests for config-based macro support."""

import pytest

from remy.exceptions import RemyError
from remy.query.parser import parse_query
from remy.query.eval import parse_config_macros, resolve_macros
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, And, Or,
    MacroDefinition, MacroReference, StatementList
)


def test_parse_config_macros_basic():
    """Test parsing basic config macro definitions."""
    config = {
        'WORK': '@work := tags="work"',
    }
    
    macros = parse_config_macros(config)
    
    assert 'work' in macros
    assert isinstance(macros['work'], MacroDefinition)
    assert macros['work'].name == 'work'
    assert macros['work'].parameters == []


def test_parse_config_macros_multiple():
    """Test parsing multiple config macros."""
    config = {
        'WORK': '@work := tags="work"',
        'ACTIVE': '@active := status="active"',
        'URGENT': '@urgent := priority="high"',
    }
    
    macros = parse_config_macros(config)
    
    assert len(macros) == 3
    assert 'work' in macros
    assert 'active' in macros
    assert 'urgent' in macros


def test_parse_config_macros_parametric():
    """Test parsing parametric config macros."""
    config = {
        'FILTER': '@filter(Field, Value) := Field=Value',
        'PROJECT_BLOCKS': '@project_blocks(ProjectSet) := ProjectSet and tags="work"',
    }
    
    macros = parse_config_macros(config)
    
    assert 'filter' in macros
    assert macros['filter'].parameters == ['Field', 'Value']
    assert 'project_blocks' in macros
    assert macros['project_blocks'].parameters == ['ProjectSet']


def test_parse_config_macros_with_function_calls():
    """Test parsing config macros with function calls."""
    config = {
        'WORK_BLOCKS': '@work_blocks := union(tags="focus_block", tags="activation_block")',
    }
    
    macros = parse_config_macros(config)
    
    assert 'work_blocks' in macros
    from remy.query.ast_nodes import FunctionCall
    assert isinstance(macros['work_blocks'].body, FunctionCall)


def test_parse_config_macros_forbids_main():
    """Test that @main is forbidden in config macros."""
    config = {
        'MAIN': '@main := tags="work"',
    }
    
    with pytest.raises(RemyError, match="cannot define @main"):
        parse_config_macros(config)


def test_parse_config_macros_empty_definition():
    """Test that empty macro definitions are rejected."""
    config = {
        'EMPTY': '',
    }
    
    with pytest.raises(RemyError, match="empty definition"):
        parse_config_macros(config)


def test_parse_config_macros_invalid_syntax():
    """Test that invalid macro syntax is rejected."""
    config = {
        'INVALID': 'not a macro definition',
    }
    
    with pytest.raises(RemyError, match="Failed to parse config macro"):
        parse_config_macros(config)


def test_parse_config_macros_duplicate_in_config():
    """Test that duplicate macro names within config are rejected."""
    # Both define @work
    config = {
        'WORK1': '@work := tags="work"',
        'WORK2': '@work := status="active"',
    }
    
    with pytest.raises(RemyError, match="Duplicate config macro"):
        parse_config_macros(config)


def test_parse_config_macros_multiple_statements():
    """Test that multi-statement macro strings are rejected."""
    config = {
        'MULTI': '@work := tags="work"; @active := status="active"',
    }
    
    with pytest.raises(RemyError, match="exactly one macro definition"):
        parse_config_macros(config)


def test_resolve_with_config_macros_basic():
    """Test resolving queries with config macros."""
    # Config defines @work
    config = {
        'WORK': '@work := tags="work"',
    }
    config_macros = parse_config_macros(config)
    
    # Query uses @work
    ast = parse_query("@work")
    resolved = resolve_macros(ast, config_macros)
    
    # Should resolve to the macro body
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_resolve_with_config_macros_and_query_macros():
    """Test resolving queries that use both config and query-defined macros."""
    # Config defines @work
    config = {
        'WORK': '@work := tags="work"',
    }
    config_macros = parse_config_macros(config)
    
    # Query defines @active and uses both
    ast = parse_query("@active := status='active'; @work AND @active")
    resolved = resolve_macros(ast, config_macros)
    
    # Should resolve to And expression
    assert isinstance(resolved, And)


def test_resolve_config_macro_referencing_another_config_macro():
    """Test that config macros can reference each other."""
    config = {
        'BASE': '@base := tags="work"',
        'FILTERED': '@filtered := @base AND status="active"',
    }
    config_macros = parse_config_macros(config)
    
    # Query uses @filtered
    ast = parse_query("@filtered")
    resolved = resolve_macros(ast, config_macros)
    
    # Should be fully resolved
    assert isinstance(resolved, And)


def test_resolve_duplicate_macro_config_and_query():
    """Test that duplicate macros between config and query are rejected."""
    # Config defines @work
    config = {
        'WORK': '@work := tags="work"',
    }
    config_macros = parse_config_macros(config)
    
    # Query also tries to define @work
    ast = parse_query("@work := status='active'; @work")
    
    with pytest.raises(RemyError, match="already defined in config"):
        resolve_macros(ast, config_macros)


def test_resolve_query_macro_can_reference_config_macro():
    """Test that query-defined macros can reference config macros."""
    config = {
        'WORK': '@work := tags="work"',
    }
    config_macros = parse_config_macros(config)
    
    # Query defines macro that uses config macro
    ast = parse_query("@active_work := @work AND status='active'; @active_work")
    resolved = resolve_macros(ast, config_macros)
    
    assert isinstance(resolved, And)


def test_resolve_config_macros_with_parameters():
    """Test resolving parametric config macros."""
    config = {
        'FILTER': '@filter(Field, Value) := Field=Value',
    }
    config_macros = parse_config_macros(config)
    
    # Query uses the parametric macro
    ast = parse_query("@filter(tags, 'work')")
    resolved = resolve_macros(ast, config_macros)
    
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_resolve_config_macros_forward_references():
    """Test that config macros support forward references."""
    config = {
        # @main_filter references @work which is defined after
        'MAIN_FILTER': '@main_filter := @work AND status="active"',
        'WORK': '@work := tags="work"',
    }
    config_macros = parse_config_macros(config)
    
    # Query uses @main_filter
    ast = parse_query("@main_filter")
    resolved = resolve_macros(ast, config_macros)
    
    assert isinstance(resolved, And)


def test_resolve_config_macros_circular_dependency():
    """Test that circular dependencies in config macros are detected."""
    config = {
        'A': '@a := @b',
        'B': '@b := @a',
    }
    config_macros = parse_config_macros(config)
    
    ast = parse_query("@a")
    
    with pytest.raises(RemyError, match="Circular macro dependency"):
        resolve_macros(ast, config_macros)


def test_resolve_backward_compatibility_without_config():
    """Test that queries work without config macros (backward compatibility)."""
    # Query with its own macros, no config
    ast = parse_query("@work := tags='work'; @work")
    resolved = resolve_macros(ast, None)
    
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_resolve_empty_config_macros():
    """Test that empty config macros dict is handled gracefully."""
    config_macros = parse_config_macros({})
    
    ast = parse_query("tags='work'")
    resolved = resolve_macros(ast, config_macros)
    
    assert isinstance(resolved, Compare)


def test_config_macros_complex_example():
    """Test a complex real-world example with config macros."""
    config = {
        'WORK_BLOCKS': '@work_blocks := union(tags="focus_block", tags="activation_block")',
        'PROJECT_BLOCKS': '@project_blocks(ProjectSet) := ProjectSet and @work_blocks',
        'CLOSED_BLOCKS': '@closed_blocks := union(status="closed", flip(previous))',
        'CHAIN_HEADS': '@chain_heads(ProjectSet) := difference_by_label(@project_blocks(ProjectSet), @closed_blocks)',
    }
    config_macros = parse_config_macros(config)
    
    # Query uses these config macros
    ast = parse_query("@chain_heads(tags='alpha')")
    resolved = resolve_macros(ast, config_macros)
    
    # Should be fully resolved to a function call
    from remy.query.ast_nodes import FunctionCall
    assert isinstance(resolved, FunctionCall)
    assert resolved.function_name == 'difference_by_label'
