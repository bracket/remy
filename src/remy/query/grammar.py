"""
Lark grammar specification for WHERE clause query language.

This module defines the grammar for parsing SQL-like WHERE clauses
used to filter notecards based on metadata.
"""

from lark import Lark

# Lark grammar for WHERE clause queries with macro support
# Uses Earley parser for better handling of ambiguous grammar
QUERY_GRAMMAR = r"""
    ?start: statement_list

    statement_list: statement (";" statement)* ";"?

    statement: MACRO_NAME ":=" or_expr                                    -> macro_def_zero_arity
             | MACRO_NAME "(" PARAM_NAME ("," PARAM_NAME)* ")" ":=" or_expr  -> macro_def_parametric
             | or_expr                                                         -> statement_expr

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

    ?primary: macro_call
            | function_call
            | macro_ref
            | identifier
            | datetime_literal
            | date_literal
            | timedelta_literal
            | literal
            | "(" or_expr ")"

    macro_call: MACRO_NAME "(" [or_expr ("," or_expr)*] ")"
    macro_ref: MACRO_NAME
    function_call: FUNC_NAME "(" [or_expr ("," or_expr)*] ")"
    identifier: IDENTIFIER
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

    MACRO_NAME: /@[_a-z][_a-z0-9]*/
    PARAM_NAME: /[A-Z][a-zA-Z0-9]*/
    FUNC_NAME: /[_a-z][_a-z0-9]*/
    IDENTIFIER: /[_a-zA-Z][_a-zA-Z0-9]*(\.[_a-zA-Z][_a-zA-Z0-9]*)*/

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
    # Use Earley parser to handle ambiguity in macro definitions
    # The 'resolve' option automatically resolves ambiguities using priority rules
    return Lark(QUERY_GRAMMAR, parser='earley')
