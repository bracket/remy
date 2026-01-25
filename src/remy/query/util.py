"""
Utility functions for query processing.
"""


def extract_field_names(ast):
    """
    Extract all field names (identifiers) from a query AST.
    
    This should be called AFTER macro expansion. Any MacroReference nodes
    remaining in the AST are treated as pseudo-indices (field names).
    
    Args:
        ast: The query AST node (with macros already resolved)
    
    Returns:
        Set of uppercase field names referenced in the query, including
        pseudo-indices (identifiers starting with @).
    """
    from remy.query.ast_nodes import (
        Identifier, MacroReference, Compare, And, Or, Not, In, 
        FunctionCall, BinaryOp, StatementList, MacroDefinition
    )
    
    field_names = set()
    
    def visit(node):
        if isinstance(node, Identifier):
            field_names.add(node.name.upper())
        elif isinstance(node, MacroReference):
            # After macro expansion, unresolved MacroReference nodes are pseudo-indices
            field_names.add(('@' + node.name).upper())
        elif isinstance(node, Compare):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, And) or isinstance(node, Or):
            visit(node.left)
            visit(node.right)
        elif isinstance(node, Not):
            visit(node.operand)
        elif isinstance(node, In):
            visit(node.left)
            for value in node.values:
                visit(value)
        elif isinstance(node, FunctionCall):
            # Visit all arguments of the function call
            for arg in node.arguments:
                visit(arg)
        elif isinstance(node, BinaryOp):
            # Visit both operands of binary operations
            visit(node.left)
            visit(node.right)
        elif isinstance(node, StatementList):
            # This shouldn't happen after macro resolution, but handle it
            for stmt in node.statements:
                visit(stmt)
        elif isinstance(node, MacroDefinition):
            # Visit the body of macro definitions
            visit(node.body)
    
    visit(ast)
    return field_names
