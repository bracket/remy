from pathlib import Path

from .url import URL
from .exceptions import RemyError
from .grammar import notecard_grammar


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
