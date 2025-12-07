"""
AST node classes for query language.

These simple data classes represent the parsed structure of WHERE clause queries.
They are separated from evaluation logic to maintain clean separation of concerns.
"""


class ASTNode:
    """Base class for all AST nodes."""
    pass


class Literal(ASTNode):
    """Represents a literal value (string, number, boolean, null)."""
    
    def __init__(self, value):
        self.value = value
    
    def __eq__(self, other):
        return isinstance(other, Literal) and self.value == other.value
    
    def __repr__(self):
        return f"Literal({self.value!r})"


class Identifier(ASTNode):
    """Represents an identifier (field name or label), optionally with dotted path."""
    
    def __init__(self, name):
        self.name = name
    
    def __eq__(self, other):
        return isinstance(other, Identifier) and self.name == other.name
    
    def __repr__(self):
        return f"Identifier({self.name!r})"


class Compare(ASTNode):
    """Represents a comparison operation (=, !=, <, <=, >, >=)."""
    
    def __init__(self, operator, left, right):
        self.operator = operator
        self.left = left
        self.right = right
    
    def __eq__(self, other):
        return (isinstance(other, Compare) and 
                self.operator == other.operator and
                self.left == other.left and
                self.right == other.right)
    
    def __repr__(self):
        return f"Compare({self.operator!r}, {self.left!r}, {self.right!r})"


class In(ASTNode):
    """Represents an IN operation for membership testing."""
    
    def __init__(self, left, values):
        self.left = left
        self.values = values  # List of values
    
    def __eq__(self, other):
        return (isinstance(other, In) and 
                self.left == other.left and
                self.values == other.values)
    
    def __repr__(self):
        return f"In({self.left!r}, {self.values!r})"


class And(ASTNode):
    """Represents a logical AND operation."""
    
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
    def __eq__(self, other):
        return (isinstance(other, And) and 
                self.left == other.left and
                self.right == other.right)
    
    def __repr__(self):
        return f"And({self.left!r}, {self.right!r})"


class Or(ASTNode):
    """Represents a logical OR operation."""
    
    def __init__(self, left, right):
        self.left = left
        self.right = right
    
    def __eq__(self, other):
        return (isinstance(other, Or) and 
                self.left == other.left and
                self.right == other.right)
    
    def __repr__(self):
        return f"Or({self.left!r}, {self.right!r})"


class Not(ASTNode):
    """Represents a logical NOT operation."""
    
    def __init__(self, operand):
        self.operand = operand
    
    def __eq__(self, other):
        return isinstance(other, Not) and self.operand == other.operand
    
    def __repr__(self):
        return f"Not({self.operand!r})"
