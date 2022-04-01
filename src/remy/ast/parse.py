from .text import Text
from .reference import Reference
from .field import Field


def parse_content(content):
    from remy.url import URL
    from remy.notecard import notecard_grammar

    element_re = notecard_grammar()['element']

    field_re = notecard_grammar()['field']
    reference_re = notecard_grammar()['reference']

    offset = 0

    for m in element_re.finditer(content):
        start, end = m.span()

        if offset != start:
            yield Text(content[offset:start])

        offset = end

        if m.group('field'):
            f = field_re.match(m.group())
            yield Field(m.group())

            # yield (f.group('label'), f.group('field_content'))
        elif m.group('reference'):
            r = reference_re.match(m.group())
            url = URL(r.group('url'))

            yield Reference(m.group(), url)

    final = content[offset:]

    if final:
        yield Text(final)
