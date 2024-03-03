from pathlib import Path

from .url import URL
from .exceptions import RemyError
from .grammar import notecard_grammar

null = object()

class Notecard(object):
    def __init__(self, labels, content, source_url = None):
        self.primary_label = labels[0]
        self.labels = labels
        self.content = content

        self.source_url = source_url

        self.__first_block = null


    def __repr__(self):
        return "Notecard('{}')".format(self.primary_label)


    @property
    def first_block(self):
        from remy.ast.parse import parse_content
        from remy.ast import Text

        if self.__first_block is not null:
            return self.__first_block

        first_node_content = next((
            n.content.strip()
            for n in parse_content(self.content)
            if isinstance(n, Text) and n.content.strip()
        ), None)

        if first_node_content is None:
            self.__first_block = None
            return None

        block_re = notecard_grammar(True)['endblock']

        m = block_re.search(first_node_content)

        if m:
            first_block = first_node_content[:m.start()]
        else:
            first_block = first_node_content

        self.__first_block = first_block

        return first_block


def from_file(path):
    path = Path(path)
    url = URL(path)

    start_line_re = notecard_grammar(True)['notecard_start_line']

    last_line_no = 0
    last_labels = None
    current_content = [ ]

    with path.open() as fd:
        for line_no, line in enumerate(fd):
            m = start_line_re.match(line)

            if m:
                if last_labels is not None:
                    yield Notecard(last_labels, ''.join(current_content), url._replace(fragment=str(last_line_no)))

                last_line_no = line_no
                last_labels = m.group('labels').split()
                current_content = [ ]
            else:
                current_content.append(line)

    if last_labels is not None:
        yield Notecard(last_labels, ''.join(current_content), url._replace(fragment=str(last_line_no)))


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
