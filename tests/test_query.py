"""Tests for the query parser."""

import pytest

from remy.exceptions import RemyError
from remy.query.parser import parse_query
from remy.query.ast_nodes import (
    Literal, Identifier, Compare, In, And, Or, Not
)


def test_parse_simple_comparison():
    """Test parsing simple comparison expressions."""
    # Test equality
    ast = parse_query("name = 'Alice'")
    assert isinstance(ast, Compare)
    assert ast.operator == '='
    assert isinstance(ast.left, Identifier)
    assert ast.left.name == 'name'
    assert isinstance(ast.right, Literal)
    assert ast.right.value == 'Alice'

    # Test inequality
    ast = parse_query("status != 'inactive'")
    assert isinstance(ast, Compare)
    assert ast.operator == '!='

    # Test numeric comparisons
    ast = parse_query("age > 18")
    assert isinstance(ast, Compare)
    assert ast.operator == '>'
    assert ast.right.value == 18

    ast = parse_query("score >= 90")
    assert isinstance(ast, Compare)
    assert ast.operator == '>='

    ast = parse_query("count < 100")
    assert isinstance(ast, Compare)
    assert ast.operator == '<'

    ast = parse_query("level <= 5")
    assert isinstance(ast, Compare)
    assert ast.operator == '<='


def test_parse_identifiers():
    """Test parsing identifiers including dotted paths."""
    ast = parse_query("name = 'test'")
    assert ast.left.name == 'name'

    # Test dotted identifiers
    ast = parse_query("tags.name = 'important'")
    assert ast.left.name == 'tags.name'

    ast = parse_query("user.profile.email = 'test@example.com'")
    assert ast.left.name == 'user.profile.email'


def test_parse_literals():
    """Test parsing different literal types."""
    # String literals with single quotes
    ast = parse_query("name = 'Alice'")
    assert ast.right.value == 'Alice'

    # String literals with double quotes
    ast = parse_query('name = "Bob"')
    assert ast.right.value == 'Bob'

    # Integers
    ast = parse_query("count = 42")
    assert ast.right.value == 42

    # Floats
    ast = parse_query("price = 19.99")
    assert ast.right.value == 19.99

    # Scientific notation
    ast = parse_query("large = 1.5e10")
    assert ast.right.value == 1.5e10

    # Negative numbers
    ast = parse_query("temp = -10")
    assert ast.right.value == -10

    # Boolean literals
    ast = parse_query("active = TRUE")
    assert ast.right.value is True

    ast = parse_query("disabled = FALSE")
    assert ast.right.value is False

    # NULL literal
    ast = parse_query("data = NULL")
    assert ast.right.value is None


def test_parse_and_expression():
    """Test parsing AND expressions."""
    ast = parse_query("age > 18 AND status = 'active'")

    assert isinstance(ast, And)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.right, Compare)

    assert ast.left.operator == '>'
    assert ast.left.left.name == 'age'
    assert ast.left.right.value == 18

    assert ast.right.operator == '='
    assert ast.right.left.name == 'status'
    assert ast.right.right.value == 'active'


def test_parse_or_expression():
    """Test parsing OR expressions."""
    ast = parse_query("status = 'active' OR status = 'pending'")

    assert isinstance(ast, Or)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.right, Compare)


def test_parse_not_expression():
    """Test parsing NOT expressions."""
    ast = parse_query("NOT active = TRUE")

    assert isinstance(ast, Not)
    assert isinstance(ast.operand, Compare)
    assert ast.operand.left.name == 'active'


def test_parse_in_expression():
    """Test parsing IN expressions."""
    ast = parse_query("status IN ['active', 'pending', 'review']")

    assert isinstance(ast, In)
    assert isinstance(ast.left, Identifier)
    assert ast.left.name == 'status'
    assert len(ast.values) == 3
    assert all(isinstance(v, Literal) for v in ast.values)
    assert ast.values[0].value == 'active'
    assert ast.values[1].value == 'pending'
    assert ast.values[2].value == 'review'

    # Test with numbers
    ast = parse_query("id IN [1, 2, 3]")
    assert len(ast.values) == 3
    assert ast.values[0].value == 1

    # Test empty list
    ast = parse_query("id IN []")
    assert len(ast.values) == 0


def test_parse_parentheses():
    """Test parsing expressions with parentheses for grouping."""
    ast = parse_query("(age > 18 AND status = 'active') OR priority = 'high'")

    assert isinstance(ast, Or)
    assert isinstance(ast.left, And)
    assert isinstance(ast.right, Compare)


def test_operator_precedence():
    """Test that operator precedence is correct: NOT > AND > OR."""
    # NOT has highest precedence
    ast = parse_query("NOT a = 1 AND b = 2")
    assert isinstance(ast, And)
    assert isinstance(ast.left, Not)
    assert isinstance(ast.right, Compare)

    # AND has higher precedence than OR
    ast = parse_query("a = 1 OR b = 2 AND c = 3")
    assert isinstance(ast, Or)
    assert isinstance(ast.left, Compare)
    assert isinstance(ast.right, And)


def test_complex_expressions():
    """Test parsing complex nested expressions."""
    query = "(status = 'active' OR status = 'pending') AND (age > 18 OR verified = TRUE)"
    ast = parse_query(query)

    assert isinstance(ast, And)
    assert isinstance(ast.left, Or)
    assert isinstance(ast.right, Or)

    # More complex with NOT
    query = "NOT (status = 'inactive' OR banned = TRUE) AND score >= 50"
    ast = parse_query(query)

    assert isinstance(ast, And)
    assert isinstance(ast.left, Not)
    assert isinstance(ast.left.operand, Or)
    assert isinstance(ast.right, Compare)


def test_parse_errors():
    """Test that malformed queries raise RemyError."""
    # Empty query
    with pytest.raises(RemyError, match="empty"):
        parse_query("")

    with pytest.raises(RemyError, match="empty"):
        parse_query("   ")

    # Invalid syntax
    with pytest.raises(RemyError, match="Failed to parse"):
        parse_query("name =")

    with pytest.raises(RemyError, match="Failed to parse"):
        parse_query("= 'value'")

    with pytest.raises(RemyError, match="Failed to parse"):
        parse_query("AND OR")

    # Unmatched parentheses
    with pytest.raises(RemyError, match="Failed to parse"):
        parse_query("(age > 18")

    with pytest.raises(RemyError, match="Failed to parse"):
        parse_query("age > 18)")


def test_escaped_strings():
    """Test parsing strings with escape sequences."""
    # Test escaped quotes in single-quoted string
    ast = parse_query(r"text = 'it\'s working'")
    assert ast.right.value == "it's working"

    # Test escaped quotes in double-quoted string
    ast = parse_query(r'text = "say \"hello\""')
    assert ast.right.value == 'say "hello"'

    # Test escaped backslash
    ast = parse_query(r"path = 'c:\\users\\test'")
    assert ast.right.value == r'c:\users\test'


def test_whitespace_handling():
    """Test that whitespace is properly ignored."""
    queries = [
        "age=18",
        "age = 18",
        "age  =  18",
        " age = 18 ",
        "age\n=\n18",
    ]

    for query in queries:
        ast = parse_query(query)
        assert isinstance(ast, Compare)
        assert ast.left.name == 'age'
        assert ast.right.value == 18


def test_ast_node_equality():
    """Test that AST nodes can be compared for equality."""
    ast1 = parse_query("name = 'Alice'")
    ast2 = parse_query("name = 'Alice'")

    assert ast1 == ast2

    ast3 = parse_query("name = 'Bob'")
    assert ast1 != ast3


def test_ast_node_repr():
    """Test that AST nodes have useful string representations."""
    ast = parse_query("age > 18")

    repr_str = repr(ast)
    assert 'Compare' in repr_str
    assert '>' in repr_str
    assert 'Identifier' in repr_str
    assert 'age' in repr_str
    assert 'Literal' in repr_str
    assert '18' in repr_str


def test_case_insensitive_keywords():
    """Test that all keywords are case insensitive."""
    # Test AND keyword
    ast_lower = parse_query("age > 18 and status = 'active'")
    ast_upper = parse_query("age > 18 AND status = 'active'")
    ast_mixed = parse_query("age > 18 AnD status = 'active'")
    assert isinstance(ast_lower, And)
    assert isinstance(ast_upper, And)
    assert isinstance(ast_mixed, And)

    # Test OR keyword
    ast_lower = parse_query("a = 1 or b = 2")
    ast_upper = parse_query("a = 1 OR b = 2")
    assert isinstance(ast_lower, Or)
    assert isinstance(ast_upper, Or)

    # Test NOT keyword
    ast_lower = parse_query("not a = 1")
    ast_upper = parse_query("NOT a = 1")
    assert isinstance(ast_lower, Not)
    assert isinstance(ast_upper, Not)

    # Test IN keyword
    ast_lower = parse_query("status in [1, 2]")
    ast_upper = parse_query("status IN [1, 2]")
    assert isinstance(ast_lower, In)
    assert isinstance(ast_upper, In)

    # Test TRUE, FALSE, NULL
    ast = parse_query("active = true")
    assert ast.right.value is True
    ast = parse_query("active = TRUE")
    assert ast.right.value is True
    ast = parse_query("active = TrUe")
    assert ast.right.value is True

    ast = parse_query("disabled = false")
    assert ast.right.value is False
    ast = parse_query("disabled = FALSE")
    assert ast.right.value is False

    ast = parse_query("data = null")
    assert ast.right.value is None
    ast = parse_query("data = NULL")
    assert ast.right.value is None
    ast = parse_query("data = NuLl")
    assert ast.right.value is None

    # Verify keywords don't interfere with identifiers containing them
    ast = parse_query("notifier = 'test'")
    assert ast.left.name == 'notifier'

    ast = parse_query("android = 'phone'")
    assert ast.left.name == 'android'
