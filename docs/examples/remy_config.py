__all__ = [
    'PARSER_BY_FIELD_NAME'
]

def tags_parser(field):
    return tuple(f.strip().lower() for f in field.split(','))


def timestamp_parser(field):
    from dateutil.parser import parse
    from pytz import utc

    timestamp = parse(field.split(',')[0].strip())
    timestamp = timestamp.astimezone(utc)

    return (timestamp,)


PARSER_BY_FIELD_NAME = {
    'TAGS'      : tags_parser,
    'SPOTTED'   : timestamp_parser,
    'COMPLETED' : timestamp_parser,
}
