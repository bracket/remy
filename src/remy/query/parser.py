from remy.grammar import memoize
from remy.query.grammar import tokenize_query
from pprint import pprint

def parse_query(query):
    parser = query_grammar()['top']

    tokens = [ t for t in tokenize_query(query) if t[0] != 'ws' ]

    return next(parser.parse(tokens, 0))


@memoize
def query_grammar():
    from remy.query.payer import terminal, concat, union, optional, named

    g = { }

    g['variable']   = named('variable', terminal('identifier'))
    g['label']      = concat(terminal('colon'), named('label', terminal('identifier')))

    g['node'] = concat(
        terminal('lparen'),
        optional(g['variable']),
        optional(g['label']),
        terminal('rparen'),
    )

    g['top'] = g['node']

    return g
