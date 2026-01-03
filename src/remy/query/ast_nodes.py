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
    
    Supports operator overloading for addition and subtraction with date/datetime objects.
    """
    value: int
    unit: TypeLiteral['days', 'hours', 'minutes', 'seconds', 'weeks', 'months', 'years']
    
    def __add__(self, other):
        """Add this timedelta to a date or datetime."""
        from datetime import datetime, date, timezone, timedelta as dt_timedelta
        from dateutil.relativedelta import relativedelta
        
        if isinstance(other, datetime):
            # Add to datetime
            if self.unit == 'seconds':
                return other + dt_timedelta(seconds=self.value)
            elif self.unit == 'minutes':
                return other + dt_timedelta(minutes=self.value)
            elif self.unit == 'hours':
                return other + dt_timedelta(hours=self.value)
            elif self.unit == 'days':
                return other + dt_timedelta(days=self.value)
            elif self.unit == 'weeks':
                return other + dt_timedelta(weeks=self.value)
            elif self.unit == 'months':
                return other + relativedelta(months=self.value)
            elif self.unit == 'years':
                return other + relativedelta(years=self.value)
            else:
                raise ValueError(f"Unknown timedelta unit: {self.unit}")
        elif isinstance(other, date):
            # Add to date
            # Sub-day units (seconds, minutes, hours) convert date to timestamp
            if self.unit in ('seconds', 'minutes', 'hours'):
                # Convert date to timestamp at midnight UTC, then add
                dt_timestamp = datetime.combine(other, datetime.min.time(), tzinfo=timezone.utc)
                if self.unit == 'seconds':
                    return dt_timestamp + dt_timedelta(seconds=self.value)
                elif self.unit == 'minutes':
                    return dt_timestamp + dt_timedelta(minutes=self.value)
                else:  # hours
                    return dt_timestamp + dt_timedelta(hours=self.value)
            elif self.unit == 'days':
                return other + dt_timedelta(days=self.value)
            elif self.unit == 'weeks':
                return other + dt_timedelta(weeks=self.value)
            elif self.unit == 'months':
                return other + relativedelta(months=self.value)
            elif self.unit == 'years':
                return other + relativedelta(years=self.value)
            else:
                raise ValueError(f"Unknown timedelta unit: {self.unit}")
        else:
            return NotImplemented
    
    def __radd__(self, other):
        """Support commutative addition: date + timedelta."""
        return self.__add__(other)
    
    def __rsub__(self, other):
        """Support subtraction: date - timedelta (negate and add)."""
        from datetime import datetime, date, timezone, timedelta as dt_timedelta
        from dateutil.relativedelta import relativedelta
        
        if isinstance(other, datetime):
            # Subtract from datetime
            if self.unit == 'seconds':
                return other - dt_timedelta(seconds=self.value)
            elif self.unit == 'minutes':
                return other - dt_timedelta(minutes=self.value)
            elif self.unit == 'hours':
                return other - dt_timedelta(hours=self.value)
            elif self.unit == 'days':
                return other - dt_timedelta(days=self.value)
            elif self.unit == 'weeks':
                return other - dt_timedelta(weeks=self.value)
            elif self.unit == 'months':
                return other - relativedelta(months=self.value)
            elif self.unit == 'years':
                return other - relativedelta(years=self.value)
            else:
                raise ValueError(f"Unknown timedelta unit: {self.unit}")
        elif isinstance(other, date):
            # Subtract from date
            # Sub-day units (seconds, minutes, hours) convert date to timestamp
            if self.unit in ('seconds', 'minutes', 'hours'):
                # Convert date to timestamp at midnight UTC, then subtract
                dt_timestamp = datetime.combine(other, datetime.min.time(), tzinfo=timezone.utc)
                if self.unit == 'seconds':
                    return dt_timestamp - dt_timedelta(seconds=self.value)
                elif self.unit == 'minutes':
                    return dt_timestamp - dt_timedelta(minutes=self.value)
                else:  # hours
                    return dt_timestamp - dt_timedelta(hours=self.value)
            elif self.unit == 'days':
                return other - dt_timedelta(days=self.value)
            elif self.unit == 'weeks':
                return other - dt_timedelta(weeks=self.value)
            elif self.unit == 'months':
                return other - relativedelta(months=self.value)
            elif self.unit == 'years':
                return other - relativedelta(years=self.value)
            else:
                raise ValueError(f"Unknown timedelta unit: {self.unit}")
        else:
            return NotImplemented


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
