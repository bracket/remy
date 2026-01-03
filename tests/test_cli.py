from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from datetime import datetime, UTC

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
    """Test that --cache option is required when REMY_CACHE is not set."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Explicitly unset REMY_CACHE environment variable (in case it's set in user's shell)
    result = runner.invoke(main, ['query', '--all'], env={'REMY_CACHE': ''})

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


def test_query_deterministic_default_order():
    """Test that default ordering is deterministic across runs."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Run the same query multiple times
    result1 = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])
    result2 = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])
    result3 = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])
    
    # All should succeed
    assert result1.exit_code == 0
    assert result2.exit_code == 0
    assert result3.exit_code == 0
    
    # All should produce identical output
    assert result1.output == result2.output
    assert result2.output == result3.output
    
    # Extract notecard order from output
    import re
    notecards1 = re.findall(r'^NOTECARD (\S+)', result1.output, re.MULTILINE)
    notecards2 = re.findall(r'^NOTECARD (\S+)', result2.output, re.MULTILINE)
    
    # Order should be identical
    assert notecards1 == notecards2
    
    # Default order should be lexicographic by primary label
    assert notecards1 == sorted(notecards1)


def test_query_order_by_id():
    """Test explicit --order-by id sorting."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'id'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should be sorted lexicographically
    assert notecards == sorted(notecards)
    
    # Verify some expected cards are present
    assert '1' in notecards
    assert '2' in notecards
    assert 'task1' in notecards


def test_query_order_by_field():
    """Test ordering by a metadata field (priority)."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Tasks with priority should come first, in order of priority value
    # task2 and task5 have priority 1
    # task3 has priority 2
    # task1 and task4 have priority 3
    # Cards without priority should come last
    
    # Find indices of cards
    task2_idx = notecards.index('task2')
    task5_idx = notecards.index('task5')
    task3_idx = notecards.index('task3')
    task1_idx = notecards.index('task1')
    task4_idx = notecards.index('task4')
    
    # Priority 1 tasks should come before priority 2
    assert task2_idx < task3_idx
    assert task5_idx < task3_idx
    
    # Priority 2 task should come before priority 3
    assert task3_idx < task1_idx
    assert task3_idx < task4_idx
    
    # Cards without priority should come last (after all priority cards)
    weasel_idx = notecards.index('1')
    assert task1_idx < weasel_idx
    assert task4_idx < weasel_idx


def test_query_order_by_field_with_ties():
    """Test that ties in field values are broken by primary label."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # task2 and task5 both have priority 1
    task2_idx = notecards.index('task2')
    task5_idx = notecards.index('task5')
    
    # They should be in lexicographic order by label (task2 < task5)
    assert task2_idx < task5_idx
    
    # task1 and task4 both have priority 3
    task1_idx = notecards.index('task1')
    task4_idx = notecards.index('task4')
    
    # They should be in lexicographic order by label (task1 < task4)
    assert task1_idx < task4_idx


def test_query_order_by_field_missing_values():
    """Test that cards without a field value are sorted last."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Cards with priority field
    priority_cards = ['task1', 'task2', 'task3', 'task4', 'task5']
    
    # Cards without priority field
    no_priority_cards = ['1', '2']
    
    # Find the last priority card
    last_priority_idx = max(notecards.index(card) for card in priority_cards)
    
    # Find the first no-priority card
    first_no_priority_idx = min(notecards.index(card) for card in no_priority_cards if card in notecards)
    
    # All priority cards should come before all no-priority cards
    assert last_priority_idx < first_no_priority_idx


def test_query_reverse_order():
    """Test --reverse flag with default ordering."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Get normal order
    result_normal = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all'])
    
    # Get reversed order
    result_reversed = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--reverse'])
    
    assert result_normal.exit_code == 0
    assert result_reversed.exit_code == 0
    
    # Extract notecard primary labels from both outputs
    import re
    notecards_normal = re.findall(r'^NOTECARD (\S+)', result_normal.output, re.MULTILINE)
    notecards_reversed = re.findall(r'^NOTECARD (\S+)', result_reversed.output, re.MULTILINE)
    
    # Reversed should be the reverse of normal
    assert notecards_reversed == list(reversed(notecards_normal))


def test_query_reverse_with_order_by_field():
    """Test --reverse flag with field ordering."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    
    # Get normal priority order
    result_normal = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority'])
    
    # Get reversed priority order
    result_reversed = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority', '--reverse'])
    
    assert result_normal.exit_code == 0
    assert result_reversed.exit_code == 0
    
    # Extract notecard primary labels from both outputs
    import re
    notecards_normal = re.findall(r'^NOTECARD (\S+)', result_normal.output, re.MULTILINE)
    notecards_reversed = re.findall(r'^NOTECARD (\S+)', result_reversed.output, re.MULTILINE)
    
    # Reversed should be the reverse of normal
    assert notecards_reversed == list(reversed(notecards_normal))


def test_query_order_by_nonexistent_field():
    """Test ordering by a field that doesn't exist."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'nonexistent'])
    
    # Should succeed - cards without the field are sorted last
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Since no cards have this field, they should all be sorted by primary label as tie-breaker
    assert notecards == sorted(notecards)


def test_query_order_by_with_filtered_results():
    """Test that ordering works correctly with filtered query results."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox'", '--order-by', 'priority'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should only include inbox tasks
    assert set(notecards) == {'task1', 'task2'}
    
    # task2 has priority 1, task1 has priority 3
    # So task2 should come before task1
    task2_idx = notecards.index('task2')
    task1_idx = notecards.index('task1')
    assert task2_idx < task1_idx


def test_edit_help():
    """Test that edit --help shows the command description."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'edit', '--help'])

    assert result.exit_code == 0
    assert 'Edit a notecard by label' in result.output
    assert 'LABEL' in result.output


def test_main_help_shows_edit():
    """Test that main --help shows the edit subcommand."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'edit' in result.output
    assert 'Edit a notecard by label' in result.output


@patch('os.execvp')
def test_edit_existing_label(mock_execvp):
    """Test editing an existing notecard by label."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'edit', 'task1'])

    # Should not exit with error before execvp
    assert result.exit_code == 0 or mock_execvp.called
    
    # Verify execvp was called with correct arguments
    assert mock_execvp.called
    call_args = mock_execvp.call_args[0]
    
    # First argument should be 'vim'
    assert call_args[0] == 'vim'
    
    # Second argument is the command list
    command = call_args[1]
    assert command[0] == 'vim'
    
    # Should contain the path to the file
    assert 'notes_with_fields' in command[1]
    
    # Should have line number argument (task1 is on line 0 in fragment, so +1)
    assert '+1' in command
    
    # Should have positioning command
    assert '+normal ztzo' in command


@patch('os.execvp')
def test_edit_label_not_found(mock_execvp):
    """Test editing a nonexistent label shows error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'edit', 'nonexistent'])

    # Should exit with error
    assert result.exit_code != 0
    
    # Should show error message
    assert 'Error:' in result.output
    assert 'Unable to find card' in result.output
    assert 'nonexistent' in result.output
    
    # execvp should not be called
    assert not mock_execvp.called


@patch('os.execvp')
def test_edit_create_new_notecard(mock_execvp):
    """Test creating a new notecard without label."""
    from remy.cli.__main__ import main
    
    # Mock datetime to have deterministic output
    fixed_datetime = datetime(2026, 1, 3, 15, 30, 45, tzinfo=UTC)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_datetime
        mock_datetime.UTC = UTC
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            cache_path = Path.cwd() / 'test_cache'
            cache_path.mkdir()
            
            result = runner.invoke(main, ['--cache', str(cache_path), 'edit'])
            
            # Should not exit with error before execvp
            assert result.exit_code == 0 or mock_execvp.called
            
            # Verify execvp was called
            assert mock_execvp.called
            call_args = mock_execvp.call_args[0]
            
            # First argument should be 'vim'
            assert call_args[0] == 'vim'
            
            # Second argument is the command list
            command = call_args[1]
            assert command[0] == 'vim'
            
            # Should contain the dated path
            assert '2026/01/03.ntc' in command[1]
            
            # For new file, should have +normal G if file exists, or no positioning
            # Since file doesn't exist initially, should not have +normal G
            if len(command) > 2:
                # If there are extra args, it should be +normal G (file exists case)
                assert '+normal G' in command


@patch('os.execvp')
def test_edit_new_notecard_existing_file(mock_execvp):
    """Test creating new notecard when file already exists."""
    from remy.cli.__main__ import main
    
    # Mock datetime to have deterministic output
    fixed_datetime = datetime(2026, 1, 3, 15, 30, 45, tzinfo=UTC)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_datetime
        mock_datetime.UTC = UTC
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            cache_path = Path.cwd() / 'test_cache'
            cache_path.mkdir()
            
            # Create the dated file in advance
            dated_path = cache_path / '2026' / '01'
            dated_path.mkdir(parents=True)
            dated_file = dated_path / '03.ntc'
            dated_file.write_text('NOTECARD existing\nexisting content\n')
            
            result = runner.invoke(main, ['--cache', str(cache_path), 'edit'])
            
            # Should not exit with error before execvp
            assert result.exit_code == 0 or mock_execvp.called
            
            # Verify execvp was called
            assert mock_execvp.called
            call_args = mock_execvp.call_args[0]
            
            # Second argument is the command list
            command = call_args[1]
            
            # Should have +normal G for existing file
            assert '+normal G' in command


@patch('os.execvp')
def test_edit_creates_parent_directories(mock_execvp):
    """Test that edit creates parent directories for new notecards."""
    from remy.cli.__main__ import main
    
    # Mock datetime to have deterministic output
    fixed_datetime = datetime(2026, 1, 3, 15, 30, 45, tzinfo=UTC)
    
    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_datetime
        mock_datetime.UTC = UTC
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            cache_path = Path.cwd() / 'test_cache'
            cache_path.mkdir()
            
            result = runner.invoke(main, ['--cache', str(cache_path), 'edit'])
            
            # Verify parent directories were created
            expected_dir = cache_path / '2026' / '01'
            assert expected_dir.exists()
            assert expected_dir.is_dir()


@patch('os.execvp')
def test_edit_with_cache_from_environment(mock_execvp):
    """Test that edit command works with REMY_CACHE environment variable."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(
        main, 
        ['edit', 'task1'],
        env={'REMY_CACHE': str(DATA / 'test_notes')}
    )

    # Should not exit with error before execvp
    assert result.exit_code == 0 or mock_execvp.called
    
    # Verify execvp was called
    assert mock_execvp.called

