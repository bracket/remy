"""
Lark grammar specification for WHERE clause query language.

This module defines the grammar for parsing SQL-like WHERE clauses
used to filter notecards based on metadata.
"""

from lark import Lark

# Lark grammar for WHERE clause queries
# Uses LALR parser for performance
QUERY_GRAMMAR = r"""
    ?start: or_expr

    ?or_expr: and_expr
            | or_expr _OR and_expr   -> or_op

    ?and_expr: not_expr
             | and_expr _AND not_expr -> and_op

    ?not_expr: _NOT not_expr          -> not_op
             | comparison

    ?comparison: in_expr
               | additive COMP_OP additive -> compare
    
    ?in_expr: additive _IN list_literal -> in_op
            | additive
    
    ?additive: primary
             | additive "+" primary  -> add_op
             | additive "-" primary  -> sub_op

    ?primary: identifier
            | datetime_literal
            | date_literal
            | timedelta_literal
            | literal
            | "(" or_expr ")"

    identifier: DOTTED_NAME
    literal: STRING | NUMBER | TRUE | FALSE | NULL
    datetime_literal: STRING DATETIME_CAST
    date_literal: STRING DATE_CAST
    timedelta_literal: STRING TIMEDELTA_CAST
    list_literal: "[" [literal ("," literal)*] "]"

    _AND.2: /\band\b/i
    _OR.2: /\bor\b/i
    _NOT.2: /\bnot\b/i
    _IN.2: /\bin\b/i

    COMP_OP: "=" | "!=" | "<=" | ">=" | "<" | ">"

    TRUE.2: /\btrue\b/i
    FALSE.2: /\bfalse\b/i
    NULL.2: /\bnull\b/i

    DOTTED_NAME: /[_a-zA-Z][_a-zA-Z0-9]*(\.[_a-zA-Z][_a-zA-Z0-9]*)*/

    STRING: /'(?:[^'\\]|\\.)*'/ | /"(?:[^"\\]|\\.)*"/

    DATETIME_CAST: "::timestamp"
    DATE_CAST: "::date"
    TIMEDELTA_CAST: "::timedelta"

    NUMBER: SIGNED_NUMBER

    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


def get_parser():
    """Get or create the Lark parser instance."""
    return Lark(QUERY_GRAMMAR, parser='lalr')
