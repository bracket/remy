from pathlib import Path
from click.testing import CliRunner

FILE = Path(__file__).absolute()
HERE = FILE.parent
DATA = HERE / 'data'


def test_main_help():
    """Test that main --help shows the query subcommand."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'query' in result.output
    assert 'Query and filter notecards' in result.output


def test_query_help():
    """Test that query --help shows all expected options."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--help'])

    assert result.exit_code == 0
    assert '--where' in result.output
    assert '--all' in result.output
    assert '--format' in result.output
    assert 'raw' in result.output
    assert 'json' in result.output


def test_query_all():
    """Test query --all returns all notecards."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])

    assert result.exit_code == 0
    # Check for notecard identifiers
    assert 'NOTECARD 1 weasel' in result.output
    assert 'NOTECARD 2 beaver' in result.output
    assert 'NOTECARD 1fe9b4c66472604a3363a11bceb3350dd24d67a4dee4878f304ccbe6542b3ba5' in result.output


def test_query_with_expression():
    """Test query with a positional expression argument."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox'"])

    # Should succeed and filter to only inbox notecards
    assert result.exit_code == 0
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task2 review-task' in result.output
    # Should not include non-inbox cards
    assert 'NOTECARD 1 weasel' not in result.output


def test_query_with_where_flag():
    """Test query with --where flag."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--where', "tag = 'inbox'"])

    # Should succeed and filter to only inbox notecards
    assert result.exit_code == 0
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task2 review-task' in result.output
    # Should not include non-inbox cards
    assert 'NOTECARD 1 weasel' not in result.output


def test_query_no_arguments_error():
    """Test that query without arguments shows an error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query'])

    assert result.exit_code != 0
    assert 'Must provide a query expression' in result.output


def test_query_format_raw():
    """Test query with --format=raw (default)."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=raw'])

    assert result.exit_code == 0
    # Output should be in raw notecard format
    assert 'NOTECARD 1 weasel' in result.output
    assert 'weasel\n' in result.output


def test_query_format_json_not_implemented():
    """Test that --format=json raises NotImplementedError."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json'])

    assert result.exit_code != 0
    assert isinstance(result.exception, NotImplementedError)
    assert 'JSON output format is not yet implemented' in str(result.exception)


def test_query_output_reparseable():
    """Test that query output can be reparsed by Remy."""
    from remy.cli.__main__ import main
    from remy.notecard import from_file

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])

    assert result.exit_code == 0

    # Write output to a temporary file and try to reparse it
    with runner.isolated_filesystem():
        output_file = Path('output.ntc')
        output_file.write_text(result.output)

        # Try to parse the output file
        cards = list(from_file(output_file))

        # Should have parsed some notecards
        assert len(cards) > 0

        # Check that we got expected notecards
        primary_labels = [card.primary_label for card in cards]
        assert '1' in primary_labels
        assert '2' in primary_labels


def test_cache_option_required():
    """Test that --cache option is required."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['query', '--all'])

    assert result.exit_code != 0
    assert 'Missing option' in result.output or '--cache' in result.output


def test_cache_from_environment_variable():
    """Test that REMY_CACHE environment variable works."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Set REMY_CACHE environment variable
    result = runner.invoke(main, ['query', '--all'], 
                          env={'REMY_CACHE': str(DATA / 'test_notes')})

    assert result.exit_code == 0
    assert 'NOTECARD 1 weasel' in result.output
    assert 'NOTECARD 2 beaver' in result.output


def test_cache_option_overrides_environment_variable():
    """Test that --cache option overrides REMY_CACHE environment variable."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Set REMY_CACHE to a different path, but override with --cache
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'],
                          env={'REMY_CACHE': '/nonexistent/path'})

    assert result.exit_code == 0
    assert 'NOTECARD 1 weasel' in result.output


def test_query_simple_equality():
    """Test simple equality query filtering."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox'"])

    assert result.exit_code == 0
    # Should include inbox tasks
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task2 review-task' in result.output
    # Should not include other tasks
    assert 'NOTECARD task3 done-task' not in result.output
    assert 'NOTECARD task4 urgent' not in result.output
    assert 'NOTECARD task5 archive' not in result.output


def test_query_and_operation():
    """Test AND operation in queries."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox' AND priority = 3"])

    assert result.exit_code == 0
    # Should include only inbox task with priority 3
    assert 'NOTECARD task1 inbox-task' in result.output
    # Should not include other inbox tasks with different priority
    assert 'NOTECARD task2 review-task' not in result.output
    # Should not include other tasks
    assert 'NOTECARD task4 urgent' not in result.output


def test_query_or_operation():
    """Test OR operation in queries."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox' OR tag = 'urgent'"])

    assert result.exit_code == 0
    # Should include inbox tasks
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task2 review-task' in result.output
    # Should include urgent task
    assert 'NOTECARD task4 urgent' in result.output
    # Should not include other tasks
    assert 'NOTECARD task3 done-task' not in result.output
    assert 'NOTECARD task5 archive' not in result.output


def test_query_parse_error():
    """Test that parse errors are handled gracefully."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox' AND"])

    # Should fail with non-zero exit code
    assert result.exit_code != 0
    # Should display error message
    assert 'Error:' in result.output or 'error' in result.output.lower()


def test_query_unknown_field():
    """Test that unknown fields return empty results."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "unknown_field = 'value'"])

    # Should succeed but return no results
    assert result.exit_code == 0
    # Output should be empty (no notecards)
    assert 'NOTECARD' not in result.output


def test_query_all_flag_still_works():
    """Test that --all flag returns all notecards without filtering."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])

    assert result.exit_code == 0
    # Should include all notecards
    assert 'NOTECARD 1 weasel' in result.output
    assert 'NOTECARD 2 beaver' in result.output
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task2 review-task' in result.output
    assert 'NOTECARD task3 done-task' in result.output


def test_query_complex_expression():
    """Test complex expression with multiple fields."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query',
                                   "status = 'active' AND priority = 3"])

    assert result.exit_code == 0
    # Should include active tasks with priority 3
    assert 'NOTECARD task1 inbox-task' in result.output
    assert 'NOTECARD task4 urgent' in result.output
    # Should not include tasks with different status or priority
    assert 'NOTECARD task2 review-task' not in result.output
    assert 'NOTECARD task3 done-task' not in result.output
    assert 'NOTECARD task5 archive' not in result.output
