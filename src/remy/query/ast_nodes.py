"""
AST node classes for query language.

These simple data classes represent the parsed structure of WHERE clause queries.
They are separated from evaluation logic to maintain clean separation of concerns.
"""

from dataclasses import dataclass
from typing import Any, List
from datetime import datetime, date


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


@dataclass
class Literal(ASTNode):
    """Represents a literal value (string, number, boolean, null)."""
    value: Any


@dataclass
class Identifier(ASTNode):
    """Represents an identifier (field name or label), optionally with dotted path."""
    name: str


@dataclass
class Compare(ASTNode):
    """Represents a comparison operation (=, !=, <, <=, >, >=)."""
    operator: str
    left: ASTNode
    right: ASTNode


@dataclass
class In(ASTNode):
    """Represents an IN operation for membership testing."""
    left: ASTNode
    values: List[ASTNode]


@dataclass
class And(ASTNode):
    """Represents a logical AND operation."""
    left: ASTNode
    right: ASTNode


@dataclass
class Or(ASTNode):
    """Represents a logical OR operation."""
    left: ASTNode
    right: ASTNode


@dataclass
class Not(ASTNode):
    """Represents a logical NOT operation."""
    operand: ASTNode


@dataclass
class DateTimeLiteral(ASTNode):
    """Represents a datetime literal value (e.g., '2024-01-31 15:30:00'::timestamp)."""
    value: datetime


@dataclass
class DateLiteral(ASTNode):
    """Represents a date literal value (e.g., '2024-01-31'::date)."""
    value: date
