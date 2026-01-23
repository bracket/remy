"""
Utility functions for query processing.
"""


def extract_field_names(ast):
    """
    Extract all field names (identifiers) from a query AST.
    
    Args:
        ast: The query AST node
    
    Returns:
        Set of uppercase field names referenced in the query.
        Note: @id pseudo-index is excluded as it's synthesized dynamically.
    """
    from remy.query.ast_nodes import Identifier, Compare, And, Or, Not, In, FunctionCall, BinaryOp
    
    field_names = set()
    
    def visit(node):
        if isinstance(node, Identifier):
            # Skip @id pseudo-index as it's synthesized
            if node.name.upper() != '@ID':
                field_names.add(node.name.upper())
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
    
    visit(ast)
    return field_names
