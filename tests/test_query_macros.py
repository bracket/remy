"""Tests for query macro support."""

import pytest

from remy.exceptions import RemyError
from remy.query.parser import parse_query
from remy.query.eval import resolve_macros
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, And, Or,
    MacroDefinition, MacroReference, StatementList
)


def test_parse_zero_arity_macro():
    """Test parsing zero-arity macro definitions."""
    ast = parse_query("@work := tags='work';")
    assert isinstance(ast, StatementList)
    assert len(ast.statements) == 1
    assert isinstance(ast.statements[0], MacroDefinition)
    
    macro_def = ast.statements[0]
    assert macro_def.name == 'work'
    assert macro_def.parameters == []
    assert isinstance(macro_def.body, Compare)


def test_parse_parametric_macro():
    """Test parsing parametric macro definitions."""
    # Single parameter
    ast = parse_query("@filter(Field) := Field='value';")
    assert isinstance(ast, StatementList)
    macro_def = ast.statements[0]
    assert macro_def.name == 'filter'
    assert macro_def.parameters == ['Field']
    
    # Multiple parameters
    ast = parse_query("@filter(Field, Value) := Field=Value;")
    macro_def = ast.statements[0]
    assert macro_def.name == 'filter'
    assert macro_def.parameters == ['Field', 'Value']


def test_parse_macro_reference():
    """Test parsing macro references."""
    # Zero-arity reference
    ast = parse_query("@work")
    assert isinstance(ast, MacroReference)
    assert ast.name == 'work'
    assert ast.arguments == []
    
    # With arguments
    ast = parse_query("@filter(tags)")
    assert isinstance(ast, MacroReference)
    assert ast.name == 'filter'
    assert len(ast.arguments) == 1


def test_parse_multi_statement():
    """Test parsing queries with multiple statements."""
    ast = parse_query("@work := tags='work'; @work")
    assert isinstance(ast, StatementList)
    assert len(ast.statements) == 2
    assert isinstance(ast.statements[0], MacroDefinition)
    assert isinstance(ast.statements[1], MacroReference)


def test_backward_compatibility():
    """Test that single-statement queries still work (no macros)."""
    # Simple query without semicolon
    ast = parse_query("tags='work'")
    assert isinstance(ast, Compare)
    
    # Simple query with semicolon should also work
    ast = parse_query("tags='work';")
    assert isinstance(ast, Compare)
    
    # Complex expression
    ast = parse_query("tags='work' AND status='active'")
    assert isinstance(ast, And)


def test_resolve_zero_arity_macro():
    """Test resolving zero-arity macros."""
    ast = parse_query("@work := tags='work'; @work")
    resolved = resolve_macros(ast)
    
    # Should resolve to the macro body
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_resolve_parametric_macro():
    """Test resolving parametric macros with parameter substitution."""
    # Single parameter
    ast = parse_query("@filter(Field) := Field='value'; @filter(tags)")
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'value'
    
    # Multiple parameters
    ast = parse_query("@filter(Field, Value) := Field=Value; @filter(tags, 'work')")
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_forward_reference():
    """Test that macros can be used before they're defined."""
    # @main uses @work, which is defined after @main
    ast = parse_query("@main := @work; @work := tags='work';")
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_macro_in_complex_expression():
    """Test using macros in complex expressions."""
    ast = parse_query("""
        @work := tags='work';
        @active := status='active';
        @work AND @active
    """)
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, And)
    assert isinstance(resolved.left, Compare)
    assert isinstance(resolved.right, Compare)


def test_nested_macro_references():
    """Test macros that reference other macros."""
    ast = parse_query("""
        @work := tags='work';
        @active_work := @work AND status='active';
        @active_work
    """)
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, And)


def test_circular_dependency_detection():
    """Test that circular macro dependencies are detected."""
    # Direct circular reference
    ast = parse_query("@a := @b; @b := @a; @a")
    with pytest.raises(RemyError, match="Circular macro dependency"):
        resolve_macros(ast)
    
    # Self-reference
    ast = parse_query("@work := @work; @work")
    with pytest.raises(RemyError, match="Circular macro dependency"):
        resolve_macros(ast)
    
    # Three-way circular reference
    ast = parse_query("@a := @b; @b := @c; @c := @a; @a")
    with pytest.raises(RemyError, match="Circular macro dependency"):
        resolve_macros(ast)


def test_undefined_macro_error():
    """Test that undefined macros are left as MacroReference nodes for field resolution."""
    # A bare macro reference is treated as a potential pseudo-index
    # It won't raise an error during macro resolution - it's left as MacroReference
    ast = parse_query("@undefined")
    resolved = resolve_macros(ast)
    # It should remain as a MacroReference that will be treated as identifier during evaluation
    assert isinstance(resolved, MacroReference)
    assert resolved.name == 'undefined'
    
    # Undefined macro in a more complex expression is also left as-is
    ast = parse_query("@work := tags='work'; @work AND @undefined")
    resolved = resolve_macros(ast)
    # @work should be expanded, but @undefined should remain as MacroReference
    assert isinstance(resolved, And)
    # The right side should be a MacroReference
    assert isinstance(resolved.right, MacroReference)
    assert resolved.right.name == 'undefined'


def test_duplicate_macro_definition():
    """Test that duplicate macro definitions are rejected."""
    ast = parse_query("@work := tags='work'; @work := status='active'; @work")
    with pytest.raises(RemyError, match="Duplicate macro definition"):
        resolve_macros(ast)


def test_wrong_argument_count():
    """Test that calling macros with wrong number of arguments raises an error."""
    # Too few arguments
    ast = parse_query("@filter(Field, Value) := Field=Value; @filter(tags)")
    with pytest.raises(RemyError, match="expects 2 arguments"):
        resolve_macros(ast)
    
    # Too many arguments
    ast = parse_query("@filter(Field) := Field='value'; @filter(tags, 'extra')")
    with pytest.raises(RemyError, match="expects 1 argument"):
        resolve_macros(ast)


def test_macro_with_function_call():
    """Test macros that use function calls."""
    ast = parse_query("""
        @work_blocks := union(tags='focus_block', tags='activation_block');
        @work_blocks
    """)
    resolved = resolve_macros(ast)
    
    # Should resolve to FunctionCall node
    from remy.query.ast_nodes import FunctionCall
    assert isinstance(resolved, FunctionCall)
    assert resolved.function_name == 'union'


def test_parametric_macro_with_function():
    """Test parametric macros with function calls."""
    ast = parse_query("""
        @project_work(ProjectName) := intersect_by_label(ProjectName, tags='work');
        @project_work(tags='alpha')
    """)
    resolved = resolve_macros(ast)
    
    from remy.query.ast_nodes import FunctionCall
    assert isinstance(resolved, FunctionCall)
    assert resolved.function_name == 'intersect_by_label'
    assert len(resolved.arguments) == 2


def test_macro_argument_is_expression():
    """Test that macro arguments can be complex expressions."""
    ast = parse_query("""
        @filter(Condition) := Condition;
        @filter(tags='work' AND status='active')
    """)
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, And)


def test_no_main_expression_error():
    """Test that queries with only macro definitions raise an error."""
    ast = parse_query("@work := tags='work';")
    with pytest.raises(RemyError, match="must have a @main macro"):
        resolve_macros(ast)


def test_explicit_main_macro():
    """Test that @main can be explicitly defined."""
    ast = parse_query("@main := tags='work';")
    resolved = resolve_macros(ast)
    assert isinstance(resolved, Compare)
    assert resolved.left.name == 'tags'
    assert resolved.right.value == 'work'


def test_explicit_main_with_other_macros():
    """Test @main can reference other macros."""
    ast = parse_query("""
        @work := tags='work';
        @main := @work AND status='active';
    """)
    resolved = resolve_macros(ast)
    assert isinstance(resolved, And)


def test_unnamed_statement_not_at_end_error():
    """Test that unnamed statements not at the end cause an error."""
    ast = parse_query("tags='work'; @other := status='active';")
    with pytest.raises(RemyError, match="Only the last statement can be unnamed"):
        resolve_macros(ast)


def test_both_explicit_main_and_unnamed_final_error():
    """Test that having both explicit @main and unnamed final statement is an error."""
    ast = parse_query("@main := tags='work'; status='active'")
    with pytest.raises(RemyError, match="Cannot have both an explicit @main definition"):
        resolve_macros(ast)


def test_parameter_names_case_sensitive():
    """Test that parameter names are case-sensitive (PascalCase)."""
    # PascalCase parameter names should work
    ast = parse_query("@filter(FieldName, FieldValue) := FieldName=FieldValue; @filter(tags, 'work')")
    resolved = resolve_macros(ast)
    assert isinstance(resolved, Compare)


def test_multiple_macro_uses():
    """Test using the same macro multiple times."""
    ast = parse_query("""
        @work := tags='work';
        @work OR @work
    """)
    resolved = resolve_macros(ast)
    
    assert isinstance(resolved, Or)
    assert isinstance(resolved.left, Compare)
    assert isinstance(resolved.right, Compare)


def test_optional_final_semicolon():
    """Test that the final semicolon is optional."""
    # With final semicolon
    ast1 = parse_query("@work := tags='work'; @work;")
    resolved1 = resolve_macros(ast1)
    
    # Without final semicolon
    ast2 = parse_query("@work := tags='work'; @work")
    resolved2 = resolve_macros(ast2)
    
    # Both should resolve to the same thing
    assert type(resolved1) == type(resolved2)
    assert isinstance(resolved1, Compare)


def test_macro_names_lowercase():
    """Test that macro names must start with lowercase after @."""
    # Valid macro names
    parse_query("@work := tags='work';")
    parse_query("@my_macro := tags='work';")
    parse_query("@macro123 := tags='work';")
    
    # Invalid macro names (should fail to parse) - Capital letters not allowed after @
    # These should actually parse as identifiers, not macros
    # The grammar enforces this, so let's verify
    try:
        ast = parse_query("@Work := tags='work';")
        # If it parses, it shouldn't be a macro definition
        # It should fail because @Work doesn't match MACRO_NAME pattern
        assert False, "Should not parse @Work as macro"
    except RemyError:
        pass  # Expected


def test_complex_nested_macros():
    """Test complex nested macro scenarios."""
    ast = parse_query("""
        @base := tags='work';
        @filtered := @base AND status='active';
        @final := @filtered OR tags='urgent';
        @final
    """)
    resolved = resolve_macros(ast)
    
    # Should be fully expanded
    assert isinstance(resolved, Or)
