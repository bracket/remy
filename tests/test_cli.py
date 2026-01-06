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


def test_query_format_json_basic():
    """Test basic JSON output format."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json'])

    assert result.exit_code == 0
    
    # Parse JSON output
    data = json.loads(result.output)
    
    # Should be a list
    assert isinstance(data, list)
    
    # Should have multiple notecards
    assert len(data) > 0
    
    # Each element should be a string containing notecard text
    for item in data:
        assert isinstance(item, str)
        assert item.startswith('NOTECARD ')


def test_query_format_json_multiple_notecards():
    """Test JSON output with multiple notecards."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json'])

    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Should have multiple notecards
    assert len(data) >= 2
    
    # Verify some expected notecards are present
    notecard_texts = ''.join(data)
    assert 'NOTECARD 1 weasel' in notecard_texts
    assert 'NOTECARD 2 beaver' in notecard_texts


def test_query_format_json_single_notecard():
    """Test JSON output with single notecard."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'done'", '--format=json'])

    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Should have exactly one notecard
    assert len(data) == 1
    
    # Verify it's the expected notecard
    assert 'NOTECARD task3 done-task' in data[0]
    assert 'Completed task' in data[0]


def test_query_format_json_empty_results():
    """Test JSON output with no results (empty array)."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'nonexistent'", '--format=json'])

    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Should be an empty array
    assert data == []


def test_query_format_json_case_insensitive():
    """Test that format option is case-insensitive."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    
    # Test various case combinations
    for format_str in ['json', 'JSON', 'Json', 'JsOn']:
        result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', f'--format={format_str}'])
        
        assert result.exit_code == 0
        
        # Should parse as valid JSON
        data = json.loads(result.output)
        assert isinstance(data, list)


def test_query_format_json_pretty_print():
    """Test pretty-print flag produces indented output."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    
    # Get compact output (default)
    result_compact = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json'])
    
    # Get pretty-printed output
    result_pretty = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json', '--pretty-print'])
    
    assert result_compact.exit_code == 0
    assert result_pretty.exit_code == 0
    
    # Both should parse as valid JSON
    data_compact = json.loads(result_compact.output)
    data_pretty = json.loads(result_pretty.output)
    
    # Should contain same data
    assert data_compact == data_pretty
    
    # Pretty output should have more lines (due to indentation)
    compact_lines = result_compact.output.count('\n')
    pretty_lines = result_pretty.output.count('\n')
    assert pretty_lines > compact_lines
    
    # Pretty output should contain indentation
    assert '  ' in result_pretty.output  # 2-space indent


def test_query_format_json_special_characters():
    """Test JSON output with special characters in notecard text."""
    from remy.cli.__main__ import main
    from click.testing import CliRunner
    import json
    from pathlib import Path
    
    runner = CliRunner()
    
    # Create a temporary notecard file with special characters
    with runner.isolated_filesystem():
        test_file = Path('special.ntc')
        test_file.write_text('''NOTECARD special-chars
:TAG: test
Text with "quotes" and 'apostrophes'
Text with backslash \\ character
Text with newline in content
Text with tab\tcharacter
''')
        
        result = runner.invoke(main, ['--cache', str(test_file.parent), 'query', '--all', '--format=json'])
        
        assert result.exit_code == 0
        
        # Should parse as valid JSON
        data = json.loads(result.output)
        
        assert len(data) == 1
        notecard_text = data[0]
        
        # Verify special characters are preserved
        assert '"quotes"' in notecard_text
        assert "'apostrophes'" in notecard_text
        assert '\\' in notecard_text
        assert '\t' in notecard_text


def test_query_format_json_unicode_characters():
    """Test JSON output with Unicode characters."""
    from remy.cli.__main__ import main
    from click.testing import CliRunner
    import json
    from pathlib import Path
    
    runner = CliRunner()
    
    # Create a temporary notecard file with Unicode characters
    with runner.isolated_filesystem():
        test_file = Path('unicode.ntc')
        test_file.write_text('''NOTECARD unicode-test
:TAG: test
Text with emoji 🎉 and symbols ✓
Text with accents: café, naïve, résumé
Text with Japanese: こんにちは
Text with Chinese: 你好
Text with Arabic: مرحبا
''', encoding='utf-8')
        
        result = runner.invoke(main, ['--cache', str(test_file.parent), 'query', '--all', '--format=json'])
        
        assert result.exit_code == 0
        
        # Should parse as valid JSON
        data = json.loads(result.output)
        
        assert len(data) == 1
        notecard_text = data[0]
        
        # Verify Unicode characters are preserved
        assert '🎉' in notecard_text
        assert '✓' in notecard_text
        assert 'café' in notecard_text
        assert 'naïve' in notecard_text
        assert 'こんにちは' in notecard_text
        assert '你好' in notecard_text
        assert 'مرحبا' in notecard_text


def test_query_format_json_with_order_by():
    """Test JSON output respects --order-by flag."""
    from remy.cli.__main__ import main
    import json
    import re

    runner = CliRunner()
    
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json', '--order-by', 'priority'])
    
    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Extract primary labels from JSON output
    labels = []
    for notecard_text in data:
        match = re.search(r'NOTECARD (\S+)', notecard_text)
        if match:
            labels.append(match.group(1))
    
    # Verify ordering (priority 1 before priority 2 before priority 3, then no-priority cards)
    task2_idx = labels.index('task2') if 'task2' in labels else -1
    task3_idx = labels.index('task3') if 'task3' in labels else -1
    task1_idx = labels.index('task1') if 'task1' in labels else -1
    
    if task2_idx >= 0 and task3_idx >= 0:
        assert task2_idx < task3_idx  # priority 1 before priority 2
    if task3_idx >= 0 and task1_idx >= 0:
        assert task3_idx < task1_idx  # priority 2 before priority 3


def test_query_format_json_with_limit():
    """Test JSON output respects --limit flag."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--format=json', '--limit', '3'])
    
    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Should have exactly 3 notecards
    assert len(data) == 3


def test_query_format_json_full_notecard_text():
    """Test that JSON output contains complete notecard text with fields and content."""
    from remy.cli.__main__ import main
    import json

    runner = CliRunner()
    
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox'", '--format=json'])
    
    assert result.exit_code == 0
    
    data = json.loads(result.output)
    
    # Find the task1 notecard
    task1_text = None
    for notecard_text in data:
        if 'NOTECARD task1 inbox-task' in notecard_text:
            task1_text = notecard_text
            break
    
    assert task1_text is not None
    
    # Verify it contains the NOTECARD line
    assert 'NOTECARD task1 inbox-task' in task1_text
    
    # Verify it contains field data
    assert ':TAG: inbox' in task1_text
    assert ':PRIORITY: 3' in task1_text
    assert ':STATUS: active' in task1_text
    
    # Verify it contains content
    assert 'Task in inbox with priority 3' in task1_text


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


def test_query_limit_basic():
    """Test that --limit returns exactly N results when N < total results."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--limit', '3'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 3 notecards
    assert len(notecards) == 3


def test_query_limit_short_form():
    """Test that -l short form works for limit."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '-l', '2'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 2 notecards
    assert len(notecards) == 2


def test_query_limit_greater_than_results():
    """Test that --limit returns all results when N >= total results."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Filter to inbox tasks (only 2)
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "tag = 'inbox'", '--limit', '100'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return all inbox tasks (2 total)
    assert len(notecards) == 2
    assert set(notecards) == {'task1', 'task2'}


def test_query_limit_one():
    """Test that --limit=1 returns exactly one result."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--limit', '1'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 1 notecard
    assert len(notecards) == 1


def test_query_limit_with_order_by():
    """Test that --limit works with --order-by."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority', '--limit', '2'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 2 notecards
    assert len(notecards) == 2
    
    # Should return the first 2 according to priority sort order
    # task2 and task5 both have priority 1, and should come first
    # Within the same priority, they're sorted by primary label
    assert notecards == ['task2', 'task5']


def test_query_limit_with_reverse():
    """Test that --limit works with --reverse."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Get the full reversed list first
    result_full = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--reverse'])
    import re
    notecards_full = re.findall(r'^NOTECARD (\S+)', result_full.output, re.MULTILINE)
    
    # Now get limited reversed list
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--reverse', '--limit', '3'])
    
    assert result.exit_code == 0
    
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 3 notecards
    assert len(notecards) == 3
    
    # Should be the first 3 from the reversed list
    assert notecards == notecards_full[:3]


def test_query_limit_with_order_by_and_reverse():
    """Test that --limit works with both --order-by and --reverse."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--order-by', 'priority', '--reverse', '--limit', '2'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 2 notecards
    assert len(notecards) == 2
    
    # With priority sorting reversed, we get the last 2 from the reversed priority order
    # The important thing is that limit works correctly with both order-by and reverse


def test_query_order_by_earliest_with_limit_one():
    """Test that --order-by priority --limit=1 returns the first (lowest priority) result."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Filter to tasks with priority field and get the one with lowest priority
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "priority > 0", '--order-by', 'priority', '--limit', '1'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 1 notecard
    assert len(notecards) == 1
    
    # Should be one of the lowest priority tasks (priority 1)
    # task2 or task5 both have priority 1, but task2 comes first alphabetically
    assert notecards[0] == 'task2'


def test_query_order_by_latest_with_limit_one():
    """Test that --order-by priority --reverse --limit=1 returns the last (highest priority) result."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Filter to tasks with priority field and get the one with highest priority
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', "priority > 0", '--order-by', 'priority', '--reverse', '--limit', '1'])
    
    assert result.exit_code == 0
    
    # Extract notecard primary labels from output
    import re
    notecards = re.findall(r'^NOTECARD (\S+)', result.output, re.MULTILINE)
    
    # Should return exactly 1 notecard
    assert len(notecards) == 1
    
    # Should be one of the highest priority tasks (priority 3)
    # task1 or task4 both have priority 3, but task4 comes last alphabetically  
    # When reversed, the highest priority comes first, and among ties, reverse alphabetical
    assert notecards[0] == 'task4'


def test_query_limit_zero_error():
    """Test that --limit=0 produces an error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--limit', '0'])
    
    # Should fail with non-zero exit code
    assert result.exit_code != 0
    
    # Should display error message about invalid value
    assert 'Invalid value' in result.output or 'out of range' in result.output.lower()


def test_query_limit_negative_error():
    """Test that negative limit produces an error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--limit', '-5'])
    
    # Should fail with non-zero exit code
    assert result.exit_code != 0
    
    # Should display error message about invalid value
    assert 'Invalid value' in result.output or 'out of range' in result.output.lower()


def test_query_limit_non_numeric_error():
    """Test that non-numeric limit produces an error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--all', '--limit', 'abc'])
    
    # Should fail with non-zero exit code
    assert result.exit_code != 0
    
    # Should display error message about invalid value
    assert 'Invalid value' in result.output or 'not a valid integer' in result.output.lower()


def test_query_help_includes_limit():
    """Test that query --help shows the --limit option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--cache', str(DATA / 'test_notes'), 'query', '--help'])

    assert result.exit_code == 0
    assert '--limit' in result.output
    assert '-l' in result.output
    assert 'Limit the number of results' in result.output or 'limit' in result.output.lower()
