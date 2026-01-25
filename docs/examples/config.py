__all__ = [
    'PARSER_BY_FIELD_NAME',
    'MACROS'
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

# Optional: Define global query macros that are available in all queries
# Macro names are derived from the definition (after @), not from the dictionary keys
MACROS = {
    # Example: Simple macros for common filters
    'WORK_BLOCKS': '@work_blocks := union(tags="focus_block", tags="activation_block")',
    
    # Example: Parametric macro that takes a project set and filters for work blocks
    'PROJECT_BLOCKS': '@project_blocks(ProjectSet) := ProjectSet and @work_blocks',
    
    # Example: Macro for closed or previous blocks
    'CLOSED_BLOCKS': '@closed_blocks := union(status="closed", flip(previous))',
    
    # Example: Complex macro using other config macros
    'CHAIN_HEADS': '@chain_heads(ProjectSet) := difference_by_label(@project_blocks(ProjectSet), @closed_blocks)',
}
