"""
AST node classes for query language.

These simple data classes represent the parsed structure of WHERE clause queries.
They are separated from evaluation logic to maintain clean separation of concerns.
"""

from dataclasses import dataclass
from typing import Any, List, Literal as TypeLiteral
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


@dataclass
class Timedelta(ASTNode):
    """
    Represents a timedelta value with calendar-aware units.
    
    Unlike Python's datetime.timedelta which is limited to days/seconds/microseconds,
    this class can represent months and years for calendar-aware arithmetic.
    """
    value: int
    unit: TypeLiteral['days', 'hours', 'months', 'years']


@dataclass
class TimedeltaLiteral(ASTNode):
    """Represents a timedelta literal value (e.g., '2 days'::timedelta, '1 month'::timedelta)."""
    value: Timedelta


@dataclass
class BinaryOp(ASTNode):
    """Represents a binary operation (e.g., date + timedelta)."""
    operator: TypeLiteral['+', '-']
    left: ASTNode
    right: ASTNode
