"""
Configuration file for test notecard cache.
Defines parsers for notecard fields used in testing.
"""

__all__ = [
    'PARSER_BY_FIELD_NAME'
]


def simple_field_parser(field):
    """Parser for simple single-value fields."""
    return (field.strip(),)


def tags_parser(field):
    """Parser for comma-separated tags."""
    return tuple(f.strip().lower() for f in field.split(','))


def number_parser(field):
    """Parser for numeric fields."""
    value = field.strip()
    if '.' in value:
        return (float(value),)
    else:
        return (int(value),)


PARSER_BY_FIELD_NAME = {
    'TAG': simple_field_parser,
    'TAGS': tags_parser,
    'STATUS': simple_field_parser,
    'PRIORITY': number_parser,
    'CATEGORY': simple_field_parser,
}
