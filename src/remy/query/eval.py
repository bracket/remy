"""
Query evaluator for set-based operations.

This module evaluates parsed query ASTs against NotecardIndex objects using
set-based operations. It supports three types of sets:
- PairSet: sorted sets of (value, label) pairs
- LabelSet: sets of labels (strings)
- ValueSet: type-aware sets of values

The evaluator returns PairSets, LabelSets, or ValueSets depending on the query.
For backward compatibility, the evaluate_query() function projects results to
LabelSets for final output.
"""

from remy.exceptions import RemyError, InvalidComparison
from remy.notecard_index import null
from remy.query.ast_nodes import (
    ASTNode, Literal, Identifier, Compare, In, And, Or, Not,
    DateTimeLiteral, DateLiteral, TimedeltaLiteral, BinaryOp, Timedelta, FunctionCall
)
from remy.query.set_types import (
    PairSet, LabelSet, ValueSet, create_pairset, 
    pairset_to_labelset, pairset_to_valueset
)
from sortedcontainers import SortedSet
from typing import TYPE_CHECKING, Dict, Set, Union

if TYPE_CHECKING:
    from remy.notecard_index import NotecardIndex


# Type alias for the result of evaluation
EvalResult = Union[PairSet, LabelSet, ValueSet]


def evaluate_query(ast: ASTNode, field_indices: Dict[str, 'NotecardIndex']) -> Set[str]:
    """
    Evaluate a query AST against field indices and return matching primary labels.

    This is the main entry point for query evaluation. It evaluates the query
    and projects the result to a LabelSet for backward compatibility.

    Args:
        ast: The parsed query AST node to evaluate
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        Set of primary labels (strings) that match the query criteria

    Raises:
        RemyError: If the query uses unsupported operators or constructs
    """
    result = _evaluate(ast, field_indices)
    
    # Project to LabelSet for output
    if isinstance(result, set):
        # Already a LabelSet
        return result
    elif isinstance(result, SortedSet):
        # PairSet - project to labels
        return pairset_to_labelset(result)
    elif isinstance(result, ValueSet):
        raise RemyError(
            "Query expression evaluates to a ValueSet, which cannot be used to select notecards. "
            "Use the labels() function to project to labels."
        )
    else:
        raise RemyError(f"Unexpected evaluation result type: {type(result)}")


def _evaluate(ast: ASTNode, field_indices: Dict[str, 'NotecardIndex']) -> EvalResult:
    """
    Internal evaluation function that returns PairSets, LabelSets, or ValueSets.

    This function evaluates query expressions using set-based operations.
    
    Args:
        ast: The parsed query AST node to evaluate
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        PairSet, LabelSet, or ValueSet depending on the expression

    Raises:
        RemyError: If the query uses unsupported operators or constructs
    """
    if isinstance(ast, Compare):
        return _evaluate_compare(ast, field_indices)
    elif isinstance(ast, And):
        return _evaluate_and(ast, field_indices)
    elif isinstance(ast, Or):
        return _evaluate_or(ast, field_indices)
    elif isinstance(ast, FunctionCall):
        return _evaluate_function_call(ast, field_indices)
    elif isinstance(ast, Identifier):
        return _evaluate_identifier(ast, field_indices)
    elif isinstance(ast, Not):
        raise RemyError("NOT operator is not yet supported in query evaluation")
    elif isinstance(ast, In):
        raise RemyError("IN operator is not yet supported in query evaluation")
    else:
        raise RemyError(f"Unsupported AST node type: {type(ast).__name__}")


def _evaluate_binary_op(ast: BinaryOp):
    """
    Evaluate a binary arithmetic operation (+ or -) between date/timestamp and timedelta.
    
    Args:
        ast: BinaryOp AST node
        
    Returns:
        Evaluated date or datetime value
        
    Raises:
        RemyError: If operands are invalid or operation is not supported
        InvalidComparison: If attempting to compare timedeltas
    """
    from datetime import datetime, date
    
    # Extract values from left and right operands
    if isinstance(ast.left, DateLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, DateTimeLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, TimedeltaLiteral):
        left_value = ast.left.value
    elif isinstance(ast.left, BinaryOp):
        # Recursive evaluation for nested arithmetic
        left_value = _evaluate_binary_op(ast.left)
    else:
        raise RemyError(
            f"Left operand of arithmetic must be a date, timestamp, or timedelta literal, "
            f"got {type(ast.left).__name__}"
        )
    
    if isinstance(ast.right, DateLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, DateTimeLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, TimedeltaLiteral):
        right_value = ast.right.value
    elif isinstance(ast.right, BinaryOp):
        # Recursive evaluation for nested arithmetic
        right_value = _evaluate_binary_op(ast.right)
    else:
        raise RemyError(
            f"Right operand of arithmetic must be a date, timestamp, or timedelta literal, "
            f"got {type(ast.right).__name__}"
        )
    
    # Handle addition
    if ast.operator == '+':
        # date + timedelta or timestamp + timedelta
        if isinstance(left_value, date) and isinstance(right_value, Timedelta):
            return left_value + right_value
        # timedelta + date or timedelta + timestamp (commutative)
        elif isinstance(left_value, Timedelta) and isinstance(right_value, date):
            return right_value + left_value
        else:
            raise RemyError(
                f"Invalid operands for addition: {type(left_value).__name__} + {type(right_value).__name__}. "
                f"Only date/timestamp + timedelta is supported."
            )
    
    # Handle subtraction
    elif ast.operator == '-':
        # date - timedelta or timestamp - timedelta
        if isinstance(left_value, date) and isinstance(right_value, Timedelta):
            return left_value - right_value
        else:
            raise RemyError(
                f"Invalid operands for subtraction: {type(left_value).__name__} - {type(right_value).__name__}. "
                f"Only date/timestamp - timedelta is supported."
            )
    
    else:
        raise RemyError(f"Unsupported binary operator: {ast.operator}")


def _evaluate_compare(ast: Compare, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """
    Evaluate a comparison operation and return a PairSet.

    Args:
        ast: Compare AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        PairSet of (value, label) pairs matching the comparison

    Raises:
        RemyError: If operator is not supported or operands have wrong types
    """
    # Validate supported operators
    if ast.operator not in ('=', '<', '<=', '>', '>='):
        raise RemyError(
            f"Comparison operator '{ast.operator}' is not yet supported. "
            f"Currently supported: =, <, <=, >, >="
        )

    # Left side must be an Identifier (field name)
    if not isinstance(ast.left, Identifier):
        raise RemyError(
            f"Left operand of comparison must be an Identifier (field name), "
            f"got {type(ast.left).__name__}"
        )

    # Right side must be a Literal, temporal literal, or BinaryOp
    # If it's a BinaryOp, evaluate it first to get a value
    if isinstance(ast.right, BinaryOp):
        value = _evaluate_binary_op(ast.right)
    elif isinstance(ast.right, TimedeltaLiteral):
        # Timedelta literals can't be compared directly
        value = ast.right.value
    elif isinstance(ast.right, (Literal, DateTimeLiteral, DateLiteral)):
        value = ast.right.value
    else:
        raise RemyError(
            f"Right operand of comparison must be a Literal, temporal literal, or arithmetic expression, "
            f"got {type(ast.right).__name__}"
        )

    field_name = ast.left.name.upper()

    # Check if the value is a Timedelta - we don't support timedelta comparisons
    if isinstance(value, Timedelta):
        raise InvalidComparison(
            "Comparing timedeltas is not supported. "
            "Timedelta values can only be used in arithmetic with dates/timestamps."
        )

    # If the field doesn't exist in indices, return empty PairSet
    # (fields are dynamic and optional)
    if field_name not in field_indices:
        return create_pairset()

    index = field_indices[field_name]

    # Use NotecardIndex.find() to get matching pairs
    # The NotecardIndex already returns (value, label) pairs
    # We need to convert them to PairSets with type prefixes
    
    if ast.operator == '=':
        # Exact match: low=value, high=value
        return create_pairset(index.find(low=value, high=value))
    
    elif ast.operator == '<':
        # Strictly less than: all values up to (but not including) value
        result = create_pairset()
        for field_value, label in index.find(low=null, high=value):
            if field_value < value:
                result.add(((id(type(field_value)), field_value), label))
        return result
    
    elif ast.operator == '<=':
        # Less than or equal: all values up to and including value
        return create_pairset(index.find(low=null, high=value))
    
    elif ast.operator == '>':
        # Strictly greater than: all values from value onwards, excluding value
        result = create_pairset()
        for field_value, label in index.find(low=value, high=null):
            if field_value > value:
                result.add(((id(type(field_value)), field_value), label))
        return result
    
    elif ast.operator == '>=':
        # Greater than or equal: all values from value onwards
        return create_pairset(index.find(low=value, high=null))
    
    # This should never be reached due to the operator validation above
    raise RemyError(f"Unexpected operator: {ast.operator}")


def _evaluate_identifier(ast: Identifier, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """
    Evaluate a bare identifier to return all pairs from that index.
    
    This allows queries like: join_by_value_to_label(previous, tags="remy")
    where 'previous' references the entire PREVIOUS index.
    
    Special handling for @id pseudo-index which contains (label, label) pairs
    for all notecard primary labels.
    
    Args:
        ast: Identifier AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects
    
    Returns:
        PairSet containing all pairs from the referenced index
    
    Raises:
        RemyError: If the identifier doesn't reference a known index
    """
    field_name = ast.name.upper()
    
    # Handle @id pseudo-index
    if field_name == '@ID':
        # Create a PairSet with (primary_label, primary_label) for all cards
        result = create_pairset()
        # Get all primary labels from any index (they all have access to the cache)
        if field_indices:
            # Get the first index to access the notecard cache
            any_index = next(iter(field_indices.values()))
            for label in any_index.notecard_cache.primary_labels:
                # Add (label, label) pair with type prefix
                typed_value = (id(type(label)), label)
                result.add((typed_value, label))
        return result
    
    # Regular field index
    if field_name not in field_indices:
        raise RemyError(
            f"Identifier '{ast.name}' does not reference a known field index. "
            f"Available indices: {', '.join(sorted(field_indices.keys()))}"
        )
    
    index = field_indices[field_name]
    
    # Return all pairs from the index (no filtering)
    return create_pairset(index.find(low=null, high=null))


def _evaluate_and(ast: And, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """
    Evaluate an AND operation using intersect_by_label semantics.

    Args:
        ast: And AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        PairSet of pairs matching both sub-queries (using intersect_by_label)
    """
    left_result = _evaluate(ast.left, field_indices)
    right_result = _evaluate(ast.right, field_indices)

    # AND uses intersect_by_label: keep pairs from left whose label appears in right
    return _intersect_by_label(left_result, right_result)


def _evaluate_or(ast: Or, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """
    Evaluate an OR operation using union semantics.

    Args:
        ast: Or AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        PairSet of pairs matching either sub-query (using union)
    """
    left_result = _evaluate(ast.left, field_indices)
    right_result = _evaluate(ast.right, field_indices)

    # OR uses union: combine all pairs from both sides
    return _union(left_result, right_result)


def _evaluate_function_call(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> EvalResult:
    """
    Evaluate a function call (set operator).

    Args:
        ast: FunctionCall AST node
        field_indices: Dictionary mapping uppercase field names to NotecardIndex objects

    Returns:
        PairSet, LabelSet, or ValueSet depending on the function

    Raises:
        RemyError: If the function is unknown or arguments are invalid
    """
    func_name = ast.function_name.lower()
    
    # Map function names to implementations
    if func_name == 'intersect_by_label':
        return _call_intersect_by_label(ast, field_indices)
    elif func_name == 'intersect_by_value':
        return _call_intersect_by_value(ast, field_indices)
    elif func_name == 'difference_by_label':
        return _call_difference_by_label(ast, field_indices)
    elif func_name == 'difference_by_value':
        return _call_difference_by_value(ast, field_indices)
    elif func_name == 'join_by_value_to_label':
        return _call_join_by_value_to_label(ast, field_indices)
    elif func_name == 'union':
        return _call_union(ast, field_indices)
    elif func_name == 'intersect':
        return _call_intersect(ast, field_indices)
    elif func_name == 'difference':
        return _call_difference(ast, field_indices)
    elif func_name == 'flip':
        return _call_flip(ast, field_indices)
    elif func_name == 'labels':
        return _call_labels(ast, field_indices)
    elif func_name == 'values':
        return _call_values(ast, field_indices)
    else:
        raise RemyError(f"Unknown function: {ast.function_name}")


def _call_intersect_by_label(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate intersect_by_label(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"intersect_by_label expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _intersect_by_label(a, b)


def _call_intersect_by_value(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate intersect_by_value(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"intersect_by_value expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _intersect_by_value(a, b)


def _call_difference_by_label(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate difference_by_label(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"difference_by_label expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _difference_by_label(a, b)


def _call_difference_by_value(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate difference_by_value(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"difference_by_value expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _difference_by_value(a, b)


def _call_join_by_value_to_label(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate join_by_value_to_label(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"join_by_value_to_label expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _join_by_value_to_label(a, b)


def _call_union(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> EvalResult:
    """Evaluate union(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"union expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _union(a, b)


def _call_intersect(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> EvalResult:
    """Evaluate intersect(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"intersect expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _intersect(a, b)


def _call_labels(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> LabelSet:
    """Evaluate labels(PairSet) function."""
    if len(ast.arguments) != 1:
        raise RemyError(f"labels expects 1 argument, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    
    return _labels(a)


def _call_values(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> ValueSet:
    """Evaluate values(PairSet) function."""
    if len(ast.arguments) != 1:
        raise RemyError(f"values expects 1 argument, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    
    return _values(a)


def _call_difference(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> EvalResult:
    """Evaluate difference(A, B) function."""
    if len(ast.arguments) != 2:
        raise RemyError(f"difference expects 2 arguments, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    b = _evaluate(ast.arguments[1], field_indices)
    
    return _difference(a, b)


def _call_flip(ast: FunctionCall, field_indices: Dict[str, 'NotecardIndex']) -> PairSet:
    """Evaluate flip(PairSet) function."""
    if len(ast.arguments) != 1:
        raise RemyError(f"flip expects 1 argument, got {len(ast.arguments)}")
    
    a = _evaluate(ast.arguments[0], field_indices)
    
    return _flip(a)


# ============================================================================
# Set Operator Implementations
# ============================================================================

def _intersect_by_label(a: EvalResult, b: EvalResult) -> PairSet:
    """
    Keep pairs in A whose label appears in B.
    
    Args:
        a: PairSet, LabelSet, or ValueSet
        b: PairSet, LabelSet, or ValueSet
        
    Returns:
        PairSet with filtered pairs
    """
    # Convert both to have labels
    if isinstance(a, SortedSet):
        # A is a PairSet
        pairset_a = a
    else:
        raise RemyError(f"intersect_by_label: first argument must be a PairSet, got {type(a).__name__}")
    
    # Get labels from B
    if isinstance(b, set):
        # B is a LabelSet
        labels_b = b
    elif isinstance(b, SortedSet):
        # B is a PairSet - project to labels
        labels_b = pairset_to_labelset(b)
    elif isinstance(b, ValueSet):
        raise RemyError("intersect_by_label: second argument cannot be a ValueSet")
    else:
        raise RemyError(f"intersect_by_label: unexpected type {type(b).__name__}")
    
    # Keep pairs from A whose label is in labels_b
    result = create_pairset()
    for typed_value, label in pairset_a:
        if label in labels_b:
            result.add((typed_value, label))
    
    return result


def _intersect_by_value(a: EvalResult, b: EvalResult) -> PairSet:
    """
    Keep pairs in A whose value appears in B.
    
    Args:
        a: PairSet
        b: PairSet or ValueSet
        
    Returns:
        PairSet with filtered pairs
    """
    # A must be a PairSet
    if not isinstance(a, SortedSet):
        raise RemyError(f"intersect_by_value: first argument must be a PairSet, got {type(a).__name__}")
    
    # Get values from B
    if isinstance(b, ValueSet):
        # B is a ValueSet
        values_b = b._set  # Access the internal typed values
    elif isinstance(b, SortedSet):
        # B is a PairSet - project to values
        values_b = pairset_to_valueset(b)._set
    elif isinstance(b, set):
        raise RemyError("intersect_by_value: second argument cannot be a LabelSet")
    else:
        raise RemyError(f"intersect_by_value: unexpected type {type(b).__name__}")
    
    # Keep pairs from A whose value is in values_b
    result = create_pairset()
    for typed_value, label in a:
        if typed_value in values_b:
            result.add((typed_value, label))
    
    return result


def _difference_by_label(a: EvalResult, b: EvalResult) -> PairSet:
    """
    Remove pairs from A whose label appears in B.
    
    Args:
        a: PairSet
        b: PairSet or LabelSet
        
    Returns:
        PairSet with filtered pairs
    """
    # A must be a PairSet
    if not isinstance(a, SortedSet):
        raise RemyError(f"difference_by_label: first argument must be a PairSet, got {type(a).__name__}")
    
    # Get labels from B
    if isinstance(b, set):
        # B is a LabelSet
        labels_b = b
    elif isinstance(b, SortedSet):
        # B is a PairSet - project to labels
        labels_b = pairset_to_labelset(b)
    elif isinstance(b, ValueSet):
        raise RemyError("difference_by_label: second argument cannot be a ValueSet")
    else:
        raise RemyError(f"difference_by_label: unexpected type {type(b).__name__}")
    
    # Keep pairs from A whose label is NOT in labels_b
    result = create_pairset()
    for typed_value, label in a:
        if label not in labels_b:
            result.add((typed_value, label))
    
    return result


def _difference_by_value(a: EvalResult, b: EvalResult) -> PairSet:
    """
    Remove pairs from A whose value appears in B.
    
    Args:
        a: PairSet
        b: PairSet or ValueSet
        
    Returns:
        PairSet with filtered pairs
    """
    # A must be a PairSet
    if not isinstance(a, SortedSet):
        raise RemyError(f"difference_by_value: first argument must be a PairSet, got {type(a).__name__}")
    
    # Get values from B
    if isinstance(b, ValueSet):
        # B is a ValueSet
        values_b = b._set
    elif isinstance(b, SortedSet):
        # B is a PairSet - project to values
        values_b = pairset_to_valueset(b)._set
    elif isinstance(b, set):
        raise RemyError("difference_by_value: second argument cannot be a LabelSet")
    else:
        raise RemyError(f"difference_by_value: unexpected type {type(b).__name__}")
    
    # Keep pairs from A whose value is NOT in values_b
    result = create_pairset()
    for typed_value, label in a:
        if typed_value not in values_b:
            result.add((typed_value, label))
    
    return result


def _join_by_value_to_label(a: EvalResult, b: EvalResult) -> PairSet:
    """
    Relational join where value of A matches label of B.
    
    For each pair (l1, v) in A and (v, x) in B (where v matches as string),
    produce (l1, x).
    
    Args:
        a: PairSet
        b: PairSet
        
    Returns:
        PairSet with joined pairs
    """
    # Both must be PairSets
    if not isinstance(a, SortedSet):
        raise RemyError(f"join_by_value_to_label: first argument must be a PairSet, got {type(a).__name__}")
    if not isinstance(b, SortedSet):
        raise RemyError(f"join_by_value_to_label: second argument must be a PairSet, got {type(b).__name__}")
    
    # Build a map from labels in B to all their values
    # This allows efficient lookup: for each value v in A, find all (v, x) in B
    b_by_label = {}
    for typed_value, label in b:
        _, value = typed_value
        if label not in b_by_label:
            b_by_label[label] = []
        b_by_label[label].append(typed_value)
    
    # For each (l1, v) in A, find all (v, x) in B and create (l1, x)
    result = create_pairset()
    for typed_value_a, label_a in a:
        _, value_a = typed_value_a
        # Coerce value_a to string to match label
        value_a_str = str(value_a)
        if value_a_str in b_by_label:
            # Found matching label in B
            for typed_value_b in b_by_label[value_a_str]:
                result.add((typed_value_b, label_a))
    
    return result


def _union(a: EvalResult, b: EvalResult) -> EvalResult:
    """
    Set union of A and B.
    
    Works on PairSets, LabelSets, or ValueSets (both must be same type).
    
    Args:
        a: PairSet, LabelSet, or ValueSet
        b: PairSet, LabelSet, or ValueSet (same type as a)
        
    Returns:
        PairSet, LabelSet, or ValueSet
    """
    # Check that both are the same type
    if type(a) != type(b):
        raise RemyError(
            f"union: both arguments must be the same type, got {type(a).__name__} and {type(b).__name__}"
        )
    
    if isinstance(a, set):
        # Both are LabelSets
        return a | b
    elif isinstance(a, SortedSet):
        # Both are PairSets
        return a | b
    elif isinstance(a, ValueSet):
        # Both are ValueSets
        return a.union(b)
    else:
        raise RemyError(f"union: unexpected type {type(a).__name__}")


def _intersect(a: EvalResult, b: EvalResult) -> EvalResult:
    """
    Set intersection of A and B.
    
    Works on PairSets, LabelSets, or ValueSets (both must be same type).
    
    Args:
        a: PairSet, LabelSet, or ValueSet
        b: PairSet, LabelSet, or ValueSet (same type as a)
        
    Returns:
        PairSet, LabelSet, or ValueSet
    """
    # Check that both are the same type
    if type(a) != type(b):
        raise RemyError(
            f"intersect: both arguments must be the same type, got {type(a).__name__} and {type(b).__name__}"
        )
    
    if isinstance(a, set):
        # Both are LabelSets
        return a & b
    elif isinstance(a, SortedSet):
        # Both are PairSets
        return a & b
    elif isinstance(a, ValueSet):
        # Both are ValueSets
        return a.intersection(b)
    else:
        raise RemyError(f"intersect: unexpected type {type(a).__name__}")


def _labels(a: EvalResult) -> LabelSet:
    """
    Project to LabelSet.
    
    Args:
        a: PairSet or LabelSet
        
    Returns:
        LabelSet
    """
    if isinstance(a, set):
        # Already a LabelSet - no-op
        return a
    elif isinstance(a, SortedSet):
        # PairSet - project to labels
        return pairset_to_labelset(a)
    elif isinstance(a, ValueSet):
        raise RemyError("labels() cannot be called on a ValueSet")
    else:
        raise RemyError(f"labels: unexpected type {type(a).__name__}")


def _values(a: EvalResult) -> ValueSet:
    """
    Project to ValueSet.
    
    Args:
        a: PairSet or ValueSet
        
    Returns:
        ValueSet
    """
    if isinstance(a, ValueSet):
        # Already a ValueSet - no-op
        return a
    elif isinstance(a, SortedSet):
        # PairSet - project to values
        return pairset_to_valueset(a)
    elif isinstance(a, set):
        raise RemyError("values() cannot be called on a LabelSet")
    else:
        raise RemyError(f"values: unexpected type {type(a).__name__}")


def _difference(a: EvalResult, b: EvalResult) -> EvalResult:
    """
    Set difference of A and B (pair-unaware).
    
    Works on PairSets, LabelSets, or ValueSets (both must be same type).
    
    Args:
        a: PairSet, LabelSet, or ValueSet
        b: PairSet, LabelSet, or ValueSet (same type as a)
        
    Returns:
        PairSet, LabelSet, or ValueSet
    """
    # Check that both are the same type
    if type(a) != type(b):
        raise RemyError(
            f"difference: both arguments must be the same type, got {type(a).__name__} and {type(b).__name__}"
        )
    
    if isinstance(a, set):
        # Both are LabelSets
        return a - b
    elif isinstance(a, SortedSet):
        # Both are PairSets
        return a - b
    elif isinstance(a, ValueSet):
        # Both are ValueSets
        return a.difference(b)
    else:
        raise RemyError(f"difference: unexpected type {type(a).__name__}")


def _flip(a: EvalResult) -> PairSet:
    """
    Flip a PairSet, swapping labels and values.
    
    Each pair (value, label) in the input becomes (label, value) in the output,
    where the original label becomes the new value and the original value becomes the new label.
    Values must be strings (labels) for this operation to succeed.
    
    Args:
        a: PairSet
        
    Returns:
        PairSet with flipped pairs
        
    Raises:
        RemyError: If argument is not a PairSet or if any value is not a string
    """
    # A must be a PairSet
    if not isinstance(a, SortedSet):
        raise RemyError(f"flip: argument must be a PairSet, got {type(a).__name__}")
    
    # Create result PairSet with flipped pairs
    result = create_pairset()
    for typed_value, label in a:
        # Extract the actual value
        _, value = typed_value
        
        # Validate that value is a string (label)
        if not isinstance(value, str):
            raise RemyError(
                f"flip: cannot flip pair ({value}, {label}) because value is not a string. "
                f"All values must be strings (labels) to use flip(). Got type: {type(value).__name__}"
            )
        
        # Create flipped pair: original (value, label) becomes (label, value)
        # The original label becomes the new value (first position)
        # The original value becomes the new label (second position)
        typed_new_value = (id(type(label)), label)
        result.add((typed_new_value, value))
    
    return result
