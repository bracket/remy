"""
Utility functions for query processing.
"""


def extract_field_names(ast):
    """
    Extract all field names (identifiers) from a query AST.
    
    Args:
        ast: The query AST node
    
    Returns:
        Set of uppercase field names referenced in the query
    """
    from remy.query.ast_nodes import Identifier, Compare, And, Or, Not, In
    
    field_names = set()
    
    def visit(node):
        if isinstance(node, Identifier):
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
    
    visit(ast)
    return field_names
