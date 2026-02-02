"""Tests for remy macro CLI commands."""
from pathlib import Path
from click.testing import CliRunner

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'


def test_macro_help():
    """Test that macro --help shows subcommands."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_macros'), 'macro', '--help'])

    assert result.exit_code == 0
    assert 'list' in result.output
    assert 'Manage and inspect query macros' in result.output


def test_main_help_shows_macro():
    """Test that main --help shows the macro command group."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'macro' in result.output


# Tests for 'remy macro list' command


def test_macro_list_default_format():
    """Test macro list with default format (names only)."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_macros'), 'macro', 'list'])

    assert result.exit_code == 0
    # Should list macro names with @ prefix, one per line, sorted alphabetically
    lines = result.output.strip().split('\n')
    assert '@archived' in lines
    assert '@high' in lines
    assert '@work' in lines
    # Verify alphabetical order
    assert lines == sorted(lines)


def test_macro_list_full_format():
    """Test macro list with --full flag."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_macros'), 'macro', 'list', '--full'])

    assert result.exit_code == 0
    output = result.output.strip()
    
    # Should contain full definitions
    assert '@archived := status="archived"' in output
    assert '@high := priority>5' in output
    assert '@work := tags="work"' in output
    
    # Should be sorted alphabetically
    lines = result.output.strip().split('\n')
    macro_names = [line.split()[0] for line in lines if line]
    assert macro_names == sorted(macro_names)


def test_macro_list_expand_format():
    """Test macro list with --expand flag."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_macros'), 'macro', 'list', '--expand'])

    assert result.exit_code == 0
    output = result.output.strip()
    
    # Should contain expanded definitions
    assert '@archived :=' in output
    assert '@high :=' in output
    assert '@work :=' in output
    
    # Should be sorted alphabetically
    lines = result.output.strip().split('\n')
    macro_names = [line.split()[0] for line in lines if line]
    assert macro_names == sorted(macro_names)


def test_macro_list_no_macros():
    """Test macro list when config has no MACROS defined."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'macro', 'list'])

    # Should exit cleanly with no output (MACROS not defined triggers AttributeError)
    assert result.exit_code == 0
    assert result.output == ''


def test_macro_list_no_cache():
    """Test macro list without --cache option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['macro', 'list'])

    # Should fail with error message
    assert result.exit_code == 1
    assert 'Error: The --cache option is required' in result.output


def test_macro_list_empty_macros_dict():
    """Test macro list when MACROS dict exists but is empty."""
    from remy.cli.__main__ import main
    import tempfile
    
    # Create a temporary directory with empty MACROS
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        remy_dir = tmppath / '.remy'
        remy_dir.mkdir()
        
        config_file = remy_dir / 'config.py'
        config_file.write_text("""
PARSER_BY_FIELD_NAME = {}
MACROS = {}
""")
        
        # Create at least one notecard file so cache loads properly
        (tmppath / 'test.ntc').touch()
        
        runner = CliRunner()
        result = runner.invoke(main, ['--cache', str(tmppath), 'macro', 'list'])
        
        # Should exit cleanly with no output
        assert result.exit_code == 0
        assert result.output == ''


def test_macro_list_invalid_macro_definition():
    """Test macro list when MACROS contains invalid definition."""
    from remy.cli.__main__ import main
    import tempfile
    
    # Create a temporary directory with invalid MACROS
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        remy_dir = tmppath / '.remy'
        remy_dir.mkdir()
        
        config_file = remy_dir / 'config.py'
        config_file.write_text("""
PARSER_BY_FIELD_NAME = {}
MACROS = {
    'INVALID': 'not a valid macro',
}
""")
        
        # Create at least one notecard file so cache loads properly
        (tmppath / 'test.ntc').touch()
        
        runner = CliRunner()
        result = runner.invoke(main, ['--cache', str(tmppath), 'macro', 'list'])
        
        # Should fail with parsing error
        assert result.exit_code == 1
        assert 'Error parsing config macros' in result.output
