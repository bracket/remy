import re
from pathlib import Path
import functools

from .url import URL
from .exceptions import RemyError

memoize = functools.lru_cache()


class Notecard(object):
    def __init__(self, labels, content, source_url = None):
        self.primary_label = labels[0]
        self.labels = labels
        self.content = content
        self.source_url = source_url


    def __repr__(self):
        return "Notecard('{}')".format(self.primary_label)


def from_file(path):
    path = Path(path)
    url = URL(path)

    start_line_re = notecard_grammar(True)['start_line']

    last_labels = None
    current_content = [ ]

    with path.open() as fd:
        for line_no, line in enumerate(fd):
            m = start_line_re.match(line)

            if m:
                if last_labels is not None:
                    yield Notecard(last_labels, ''.join(current_content), url)

                last_labels = m.group('labels').split()
                current_content = [ ]
            else:
                current_content.append(line)

    if last_labels is not None:
        yield Notecard(last_labels, ''.join(current_content), url)


def from_path(path):
    path = Path(path)

    if path.name.startswith('.'):
        return

    if not path.is_dir():
        yield from from_file(path)
        return

    for p in path.iterdir():
        yield from from_path(p)


def from_url(url):
    url = URL(url)

    if url.scheme != 'file':
        raise RemyError("only 'file' scheme is currently supported for URLs. url: '{}'".format(url))

    yield from from_path(url.path)


@memoize
def notecard_grammar(compile = True):
    g = { }

    g['prefix']          = r'NOTECARD'
    g['label_character'] = r'[-_0-9a-zA-Z]'
    g['label']           = r'{label_character}+'
    g['labels_tail']     = r'(?:\s+{label})'
    g['labels']          = r'{label}{labels_tail}?'
    g['endline']         = r'\r\n|\n'

    g['lbracket'] = r'\['
    g['rbracket'] = r'\]'
    g['reference'] = r'{lbracket}\s*[^\]]*\s*{rbracket}'

    g['start_line']      = r'{prefix}\s+{labels}\s*{endline}'

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
