from pathlib import Path
from click.testing import CliRunner


def test_complete_help():
    """Test that complete --help shows the command description."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['complete', '--help'])

    assert result.exit_code == 0
    assert 'Generate bash completion script' in result.output
    assert '-o' in result.output
    assert '--output' in result.output


def test_main_help_shows_complete():
    """Test that main --help shows the complete subcommand."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'complete' in result.output
    assert 'Generate bash completion script' in result.output


def test_complete_stdout():
    """Test that complete without arguments outputs to stdout."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['complete'])

    assert result.exit_code == 0
    # Check for bash completion function
    assert '_remy_completion' in result.output
    # Check for installation instructions header
    assert 'Installation Instructions' in result.output
    assert 'bash-completion' in result.output
    # Check for bash completion logic
    assert 'COMP_WORDS' in result.output
    assert '_REMY_COMPLETE' in result.output


def test_complete_with_output_option():
    """Test that complete -o writes to specified file."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_path = 'completion.sh'
        result = runner.invoke(main, ['complete', '-o', output_path])

        assert result.exit_code == 0
        assert 'Bash completion script written to' in result.output
        assert output_path in result.output

        # Verify file was created with correct content
        assert Path(output_path).exists()
        content = Path(output_path).read_text()
        assert '_remy_completion' in content
        assert 'Installation Instructions' in content


def test_complete_with_positional_argument():
    """Test that complete with positional argument writes to specified file."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_path = 'completion.sh'
        result = runner.invoke(main, ['complete', output_path])

        assert result.exit_code == 0
        assert 'Bash completion script written to' in result.output
        assert output_path in result.output

        # Verify file was created with correct content
        assert Path(output_path).exists()
        content = Path(output_path).read_text()
        assert '_remy_completion' in content


def test_complete_both_options_error():
    """Test that specifying both -o and positional argument raises error."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['complete', '-o', 'file1.sh', 'file2.sh'])

    assert result.exit_code != 0
    assert 'Cannot specify both' in result.output
    assert '-o/--output' in result.output
    assert 'positional argument' in result.output


def test_complete_creates_parent_directories():
    """Test that complete creates parent directories if they don't exist."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_path = 'nested/dir/completion.sh'
        result = runner.invoke(main, ['complete', '-o', output_path])

        assert result.exit_code == 0
        assert Path(output_path).exists()
        assert Path('nested/dir').is_dir()


def test_complete_script_has_installation_header():
    """Test that the generated script includes installation instructions."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['complete'])

    assert result.exit_code == 0
    output_lines = result.output.split('\n')
    
    # Check for header elements
    assert any('Installation Instructions' in line for line in output_lines)
    assert any('bash-completion' in line for line in output_lines)
    assert any('.bashrc' in line for line in output_lines)
    assert any('source' in line for line in output_lines)
    # Check for examples
    assert any('sudo cp' in line or 'sudo apt-get install' in line for line in output_lines)


def test_complete_script_valid_bash_syntax():
    """Test that the generated script is valid bash."""
    from remy.cli.__main__ import main
    import subprocess

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_path = 'completion.sh'
        result = runner.invoke(main, ['complete', '-o', output_path])

        assert result.exit_code == 0

        # Try to source the script with bash -n (syntax check)
        bash_result = subprocess.run(
            ['bash', '-n', output_path],
            capture_output=True,
            text=True
        )
        
        assert bash_result.returncode == 0, f"Bash syntax error: {bash_result.stderr}"


def test_complete_no_cache_required():
    """Test that complete command works without --cache option."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    # Don't provide --cache option
    result = runner.invoke(main, ['complete'], env={'REMY_CACHE': ''})

    # Should succeed without cache
    assert result.exit_code == 0
    assert '_remy_completion' in result.output


def test_complete_script_contains_completion_function():
    """Test that the script defines the completion function correctly."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    result = runner.invoke(main, ['complete'])

    assert result.exit_code == 0
    
    # Check for essential bash completion elements
    assert '_remy_completion()' in result.output
    assert 'COMP_WORDS' in result.output
    assert 'COMP_CWORD' in result.output
    assert '_REMY_COMPLETE=bash_complete' in result.output
    # Check that the complete command is registered (may be in a setup function)
    assert 'complete' in result.output and '_remy_completion' in result.output and 'remy' in result.output


def test_complete_long_output_option():
    """Test that --output long form works."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_path = 'completion.sh'
        result = runner.invoke(main, ['complete', '--output', output_path])

        assert result.exit_code == 0
        assert Path(output_path).exists()


def test_complete_file_write_error():
    """Test that file write errors are handled gracefully."""
    from remy.cli.__main__ import main

    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create a directory where we'll try to write a file
        Path('readonly_dir').mkdir()
        Path('readonly_dir').chmod(0o444)  # Make read-only
        
        output_path = 'readonly_dir/completion.sh'
        result = runner.invoke(main, ['complete', '-o', output_path])

        # Should fail with a clear error message
        assert result.exit_code != 0
        assert 'Failed to write' in result.output or 'Error' in result.output
