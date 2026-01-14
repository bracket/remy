"""Tests for remy index CLI commands."""
from pathlib import Path
from click.testing import CliRunner
import json

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'


def test_index_help():
    """Test that index --help shows subcommands."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', '--help'])

    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'dump' in result.output
    assert 'Manage and inspect notecard field indices' in result.output


def test_main_help_shows_index():
    """Test that main --help shows the index command group."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'index' in result.output


# Tests for 'remy index list' command


def test_index_list_raw_format():
    """Test index list with raw format (default)."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list'])

    assert result.exit_code == 0
    # Should list field names one per line
    lines = result.output.strip().split('\n')
    assert 'TAG' in lines
    assert 'TAGS' in lines
    assert 'STATUS' in lines
    assert 'PRIORITY' in lines
    assert 'CATEGORY' in lines


def test_index_list_raw_format_explicit():
    """Test index list with explicit --format=raw."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--format', 'raw'])

    assert result.exit_code == 0
    lines = result.output.strip().split('\n')
    assert 'TAG' in lines


def test_index_list_json_format():
    """Test index list with JSON format."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--format', 'json'])

    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    
    # Should be a list
    assert isinstance(data, list)
    
    # Should contain expected field names
    assert 'TAG' in data
    assert 'TAGS' in data
    assert 'STATUS' in data
    assert 'PRIORITY' in data
    assert 'CATEGORY' in data


def test_index_list_json_pretty_print():
    """Test index list with JSON pretty-print."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Get compact output
    result_compact = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--format', 'json'])
    
    # Get pretty-printed output
    result_pretty = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--format', 'json', '--pretty-print'])
    
    assert result_compact.exit_code == 0
    assert result_pretty.exit_code == 0
    
    # Both should parse as valid JSON
    data_compact = json.loads(result_compact.output)
    data_pretty = json.loads(result_pretty.output)
    
    # Should contain same data
    assert data_compact == data_pretty
    
    # Pretty output should have more lines
    compact_lines = result_compact.output.count('\n')
    pretty_lines = result_pretty.output.count('\n')
    assert pretty_lines > compact_lines


def test_index_list_sorted():
    """Test that index list output is sorted."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list'])

    assert result.exit_code == 0
    lines = result.output.strip().split('\n')
    
    # Should be sorted alphabetically
    assert lines == sorted(lines)


def test_index_list_with_cache_env():
    """Test index list with REMY_CACHE environment variable."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['index', 'list'],
                          env={'REMY_CACHE': str(DATA / 'test_notes')})

    assert result.exit_code == 0
    assert 'TAG' in result.output


# Tests for 'remy index dump' command


def test_index_dump_default():
    """Test index dump with default options (full, comma delimiter)."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG'])

    assert result.exit_code == 0
    
    # Should output label,value pairs
    lines = result.output.strip().split('\n')
    assert len(lines) == 5  # 5 notecards with TAG field
    
    # Check format
    assert 'task5,archive' in lines
    assert 'task3,done' in lines
    assert 'task1,inbox' in lines
    assert 'task2,inbox' in lines
    assert 'task4,urgent' in lines


def test_index_dump_labels_only():
    """Test index dump with --labels option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--labels'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    assert len(lines) == 5
    
    # Should only contain labels
    assert 'task1' in lines
    assert 'task2' in lines
    assert 'task3' in lines
    assert 'task4' in lines
    assert 'task5' in lines
    
    # Should not contain values
    assert 'inbox' not in lines
    assert 'done' not in lines


def test_index_dump_values_only():
    """Test index dump with --values option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--values'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    assert len(lines) == 5
    
    # Should contain values
    assert 'inbox' in lines
    assert 'done' in lines
    assert 'archive' in lines
    assert 'urgent' in lines
    
    # Count 'inbox' occurrences (should be 2)
    assert lines.count('inbox') == 2


def test_index_dump_unique_flag():
    """Test index dump with --unique flag."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--values', '--unique'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    
    # Should have 4 unique values (archive, done, inbox, urgent)
    assert len(lines) == 4
    
    # Should contain each value only once
    assert lines.count('inbox') == 1
    assert 'archive' in lines
    assert 'done' in lines
    assert 'urgent' in lines


def test_index_dump_delimiter_tab():
    """Test index dump with tab delimiter."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', 'tab'])

    assert result.exit_code == 0
    
    # Should contain tab-separated values
    assert '\t' in result.output
    assert 'task1\tinbox' in result.output


def test_index_dump_delimiter_pipe():
    """Test index dump with pipe delimiter."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', 'pipe'])

    assert result.exit_code == 0
    
    # Should contain pipe-separated values
    assert '|' in result.output
    assert 'task1|inbox' in result.output


def test_index_dump_delimiter_literal():
    """Test index dump with literal delimiter characters."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Test with literal comma
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', ','])
    assert result.exit_code == 0
    assert 'task1,inbox' in result.output
    
    # Test with literal tab
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', '\t'])
    assert result.exit_code == 0
    assert '\t' in result.output
    
    # Test with literal pipe
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', '|'])
    assert result.exit_code == 0
    assert '|' in result.output


def test_index_dump_delimiter_escaping():
    """Test that values containing delimiters are properly escaped."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Create a test notecard cache with special characters
    with runner.isolated_filesystem():
        test_dir = Path('test_escape')
        test_dir.mkdir()
        config_dir = test_dir / '.remy'
        config_dir.mkdir()
        
        # Create config file
        config_file = config_dir / 'config.py'
        config_file.write_text('''
def simple_parser(field):
    return (field.strip(),)

PARSER_BY_FIELD_NAME = {
    'TAG': simple_parser,
}
''')
        
        # Create notecard file with values containing commas
        test_file = test_dir / 'test.ntc'
        test_file.write_text('''NOTECARD test1
:TAG: value,with,commas
Content

NOTECARD test2
:TAG: normal
Content
''')
        
        result = runner.invoke(main, ['--cache', str(test_dir), 'index', 'dump', 'TAG', '-d', 'comma'])
        assert result.exit_code == 0
        
        # Value with commas should be quoted
        assert '"value,with,commas"' in result.output
        # Normal value should not be quoted
        assert 'test2,normal' in result.output


def test_index_dump_json_format():
    """Test index dump with JSON format."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', 'json'])

    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    
    # Should be a list of lists (pairs)
    assert isinstance(data, list)
    assert len(data) == 5
    
    # Each item should be a list with 2 elements
    for item in data:
        assert isinstance(item, list)
        assert len(item) == 2


def test_index_dump_json_pretty_print():
    """Test index dump with JSON pretty-print."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Get compact output
    result_compact = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', 'json'])
    
    # Get pretty-printed output
    result_pretty = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', 'json', '--pretty-print'])
    
    assert result_compact.exit_code == 0
    assert result_pretty.exit_code == 0
    
    # Both should parse as valid JSON
    data_compact = json.loads(result_compact.output)
    data_pretty = json.loads(result_pretty.output)
    
    # Should contain same data
    assert data_compact == data_pretty
    
    # Pretty output should have more lines
    compact_lines = result_compact.output.count('\n')
    pretty_lines = result_pretty.output.count('\n')
    assert pretty_lines > compact_lines


def test_index_dump_json_labels_only():
    """Test index dump with JSON format and --labels option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', 'json', '--labels'])

    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    
    # Should be a list of strings
    assert isinstance(data, list)
    assert len(data) == 5
    
    # Each item should be a string
    for item in data:
        assert isinstance(item, str)
    
    # Should contain labels
    assert 'task1' in data
    assert 'task2' in data


def test_index_dump_json_values_only():
    """Test index dump with JSON format and --values option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', 'json', '--values'])

    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    
    # Should be a list
    assert isinstance(data, list)
    assert len(data) == 5
    
    # Should contain values
    assert 'inbox' in data
    assert 'done' in data


def test_index_dump_nonexistent_field():
    """Test index dump with non-existent field name."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'NONEXISTENT'])

    assert result.exit_code != 0
    assert 'Error:' in result.output
    assert 'not found in configuration' in result.output
    assert 'NONEXISTENT' in result.output


def test_index_dump_invalid_delimiter():
    """Test index dump with invalid delimiter."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '-d', 'invalid'])

    assert result.exit_code != 0
    assert 'Error:' in result.output
    assert 'Unknown delimiter' in result.output


def test_index_dump_sorted_output():
    """Test that index dump output is sorted."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--values'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    
    # Values should be sorted: archive, done, inbox, inbox, urgent
    assert lines[0] == 'archive'
    assert lines[1] == 'done'
    assert lines[2] == 'inbox'
    assert lines[3] == 'inbox'
    assert lines[4] == 'urgent'


def test_index_dump_priority_numeric_values():
    """Test index dump with numeric field values."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'PRIORITY', '--values'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    
    # Should have 5 values
    assert len(lines) == 5
    
    # Values should be sorted numerically (as strings)
    assert '1' in lines
    assert '2' in lines
    assert '3' in lines


def test_index_dump_with_cache_env():
    """Test index dump with REMY_CACHE environment variable."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['index', 'dump', 'TAG'],
                          env={'REMY_CACHE': str(DATA / 'test_notes')})

    assert result.exit_code == 0
    assert 'task1,inbox' in result.output


def test_index_dump_help():
    """Test that index dump --help shows all options."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', '--help'])

    assert result.exit_code == 0
    assert '--format' in result.output
    assert '--full' in result.output
    assert '--labels' in result.output
    assert '--values' in result.output
    assert '--delimiter' in result.output
    assert '--unique' in result.output
    assert '--pretty-print' in result.output


def test_index_list_help():
    """Test that index list --help shows all options."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--help'])

    assert result.exit_code == 0
    assert '--format' in result.output
    assert '--pretty-print' in result.output
    assert '--include-all-fields' in result.output


def test_index_list_include_all_fields():
    """Test index list with --include-all-fields option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Create a test notecard cache with fields that don't have parsers
    with runner.isolated_filesystem():
        test_dir = Path('test_unparsed')
        test_dir.mkdir()
        config_dir = test_dir / '.remy'
        config_dir.mkdir()
        
        # Create config file with only some parsers
        config_file = config_dir / 'config.py'
        config_file.write_text('''
def simple_parser(field):
    return (field.strip(),)

PARSER_BY_FIELD_NAME = {
    'TAG': simple_parser,
}
''')
        
        # Create notecard file with multiple fields
        test_file = test_dir / 'test.ntc'
        test_file.write_text('''NOTECARD test1
:TAG: value1
:AUTHOR: John Doe
:DATE: 2024-01-01
Content

NOTECARD test2
:TAG: value2
:PRIORITY: high
Content
''')
        
        # Test without --include-all-fields (should only show TAG)
        result = runner.invoke(main, ['--cache', str(test_dir), 'index', 'list'])
        assert result.exit_code == 0
        lines = result.output.strip().split('\n')
        assert lines == ['TAG']
        
        # Test with --include-all-fields (should show all fields)
        result = runner.invoke(main, ['--cache', str(test_dir), 'index', 'list', '--include-all-fields'])
        assert result.exit_code == 0
        lines = result.output.strip().split('\n')
        assert 'TAG' in lines
        assert 'AUTHOR' in lines
        assert 'DATE' in lines
        assert 'PRIORITY' in lines
        assert len(lines) == 4


def test_index_list_include_all_fields_json():
    """Test index list with --include-all-fields and JSON format."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Create a test notecard cache with fields that don't have parsers
    with runner.isolated_filesystem():
        test_dir = Path('test_unparsed')
        test_dir.mkdir()
        config_dir = test_dir / '.remy'
        config_dir.mkdir()
        
        # Create config file with only TAG parser
        config_file = config_dir / 'config.py'
        config_file.write_text('''
def simple_parser(field):
    return (field.strip(),)

PARSER_BY_FIELD_NAME = {
    'TAG': simple_parser,
}
''')
        
        # Create notecard file with multiple fields
        test_file = test_dir / 'test.ntc'
        test_file.write_text('''NOTECARD test1
:TAG: value1
:CUSTOM_FIELD: custom_value
Content
''')
        
        # Test with --include-all-fields and JSON format
        result = runner.invoke(main, ['--cache', str(test_dir), 'index', 'list', '--include-all-fields', '--format', 'json'])
        assert result.exit_code == 0
        
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert 'TAG' in data
        assert 'CUSTOM_FIELD' in data
        assert len(data) == 2


def test_index_list_include_all_fields_no_extra_fields():
    """Test that --include-all-fields doesn't add duplicates when all fields have parsers."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Test with the existing test_notes data where all used fields have parsers
    result_without = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list'])
    result_with = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--include-all-fields'])
    
    assert result_without.exit_code == 0
    assert result_with.exit_code == 0
    
    # Should produce the same output
    assert result_without.output == result_with.output


def test_index_list_help():
    """Test that index list --help shows all options."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'list', '--help'])

    assert result.exit_code == 0
    assert '--format' in result.output
    assert '--pretty-print' in result.output


def test_index_dump_unique_with_full_mode():
    """Test that --unique works with full mode."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--unique'])

    assert result.exit_code == 0
    
    lines = result.output.strip().split('\n')
    
    # Should still have 5 entries since all (label, value) pairs are unique
    assert len(lines) == 5


def test_index_dump_case_insensitive_format():
    """Test that format option is case-insensitive."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Test various case combinations
    for format_str in ['json', 'JSON', 'Json']:
        result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'index', 'dump', 'TAG', '--format', format_str])
        
        assert result.exit_code == 0
        
        # Should parse as valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)
