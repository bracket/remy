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
            | or_expr "OR" and_expr   -> or_op

    ?and_expr: not_expr
             | and_expr "AND" not_expr -> and_op

    ?not_expr: "NOT" not_expr          -> not_op
             | comparison

    ?comparison: in_expr
               | primary COMP_OP primary -> compare

    ?in_expr: primary "IN" list_literal -> in_op
            | primary

    ?primary: identifier
            | literal
            | "(" or_expr ")"

    identifier: DOTTED_NAME
    literal: STRING | NUMBER | TRUE | FALSE | NULL
    list_literal: "[" [literal ("," literal)*] "]"

    COMP_OP: "=" | "!=" | "<=" | ">=" | "<" | ">"
    DOTTED_NAME: /[_a-zA-Z][_a-zA-Z0-9]*(\.[_a-zA-Z][_a-zA-Z0-9]*)*/
    
    TRUE: "TRUE"
    FALSE: "FALSE"
    NULL: "NULL"
    
    STRING: /'(?:[^'\\]|\\.)*'/ | /"(?:[^"\\]|\\.)*"/
    
    NUMBER: SIGNED_NUMBER
    
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
"""


def get_parser():
    """Get or create the Lark parser instance."""
    return Lark(QUERY_GRAMMAR, parser='lalr', start='start')
