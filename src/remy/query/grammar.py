from remy.exceptions import RemyError
from remy.grammar import memoize, expand_grammar

def tokenize_query(query):
    t_re = token_re()

    offset    =  0
    query_end = len(query)

    while offset < query_end:
        m = t_re.match(query, offset)

        if not m:
            raise RemyError('unable to find token in query at offset:{} {}'.format(offset, query[offset:]))

        last = m.lastgroup
        value = m.group(last)

        offset = m.end()

        yield (last, value)


@memoize
def token_grammar(expand=False):
    g = { }

    g['identifier'] = r'[_a-zA-Z][_a-zA-Z0-9]*'

    # Using unicode code points to avoid escaping and formatting issues

    g['hyphen']     = r'\u002d' # '-'
    g['lparen']     = r'\u0028' # '('
    g['rparen']     = r'\u0029' # ')'
    g['lbracket']   = r'\u005b' # '['
    g['backslash']  = r'\u005c' # '\\'
    g['rbracket']   = r'\u005d' # ']'
    g['lbrace']     = r'\u007b' # '{'
    g['rbrace']     = r'\u007d' # '}'
    g['langle']     = r'\u003c' # '<'
    g['rangle']     = r'\u003e' # '>'
    g['comma']      = r','
    g['colon']      = r':'
    g['semicolon']  = r';'
    g['newline']    = r'\r?\n'
    g['ws']         = r'[ \t\r\n]+'

    g['single_quote'] = r'\u0027'
    g['double_quote'] = r'\u0022'

    g['escape_single'] = r'{backslash}(?:{backslash}|{single_quote})'
    g['escape_double'] = r'{backslash}(?:{backslash}|{double_quote})'

    g['single_quoted_string'] = r'{single_quote}(?:{escape_single}|[^\u0027])*{single_quote}'
    g['double_quoted_string'] = r'{double_quote}(?:{escape_double}|[^\u0022])*{double_quote}'
    g['string']               = r'{single_quoted_string}|{double_quoted_string}'

    g['digit']    = r'[0-9]'
    g['digits']   = r'{digit}+'
    g['sign']     = r'[-+]'
    g['integer']  = r'{sign}?{digits}'

    g['point']       = r'\u002e'
    g['exponent']    = r'[eE]{integer}'
    g['right_float'] = r'{sign}?{point}{digits}{exponent}?'
    g['left_float']  = r'{integer}{point}{digits}?{exponent}?'
    g['exp_float']   = r'{integer}{exponent}'
    g['float']       = r'{left_float}|{right_float}|{exp_float}'

    g['number']      = r'{float}|{integer}'


    g['literal'] = r'{string}|{number}'

    tokens = [
        'identifier',
        'literal',
        'lparen',   'rparen',
        'lbracket', 'rbracket',
        'lbrace',   'rbrace',
        'langle',   'rangle',
        'colon',    'semicolon',
        'comma',    'hyphen',
        'ws',
        'point',
    ]

    g['token'] = '|'.join('{{{}}}'.format(t) for t in tokens)

    if not expand:
        return g

    expanded = expand_grammar(g)
    named = { k : '(?P<{}>{})'.format(k, r) for k, r in expanded.items() }

    return { k : r.format(**named) for k, r in g.items() }


@memoize
def token_re():
    import re
    from pprint import pprint

    g = token_grammar(True)
    return re.compile(g['token'])
