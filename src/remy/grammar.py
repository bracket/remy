import functools

memoize = functools.lru_cache()

@memoize
def notecard_grammar(compile = True):
    import re

    g = { }

    g['prefix']          = r'NOTECARD'
    g['label_character'] = r'[-_0-9a-zA-Z]'
    g['label']           = r'{label_character}+'
    g['labels_tail']     = r'(?:\s+{label})'
    g['labels']          = r'{label}{labels_tail}?'
    g['endline']         = r'\r\n|\n'

    g['field_content'] = r'.*'
    g['field'] = r':{label}:{field_content}{endline}'

    g['notecard_start_line']      = r'{prefix}\s+{labels}\s*{endline}'

    g['lbracket'] = r'\['
    g['rbracket'] = r'\]'
    g['url']       = r'[^\]]+'
    g['reference'] = r'{lbracket}\s*{url}\s*{rbracket}'

    g['element'] = r'{field}|{reference}'


    if not compile:
        return g

    expanded = expand_grammar(g)
    named = { k : '(?P<{}>{})'.format(k, r) for k, r in expanded.items() }

    g = { k : r.format(**named) for k, r in g.items() }
    g = { k : re.compile(r) for k, r in g.items() }

    return g


def expand_grammar(g):
    grouped = { k : '(?:{})'.format(v) for k, v in g.items() }

    def expand(r):
        x = None

        while x != r:
            x, r = r, r.format(**grouped)

        return x

    return { k : expand(r) for k, r in g.items() }
