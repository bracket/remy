"""
Configuration file for test notecard cache with malformed data.
"""

__all__ = [
    'PARSER_BY_FIELD_NAME'
]


def number_parser(field):
    """Parser for numeric fields."""
    value = field.strip()
    if '.' in value:
        return (float(value),)
    else:
        return (int(value),)


PARSER_BY_FIELD_NAME = {
    'PRIORITY': number_parser,
}
