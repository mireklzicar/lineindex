"""Tests for the Linex command line interface."""

import os
import tempfile
import subprocess
import pytest
from linex.cli import main, parse_range


def test_parse_range():
    """Test the range parsing function."""
    # Single number
    assert parse_range("5") == 5

    # Simple range
    r = parse_range("5:10")
    assert isinstance(r, slice)
    assert r.start == 5
    assert r.stop == 10
    assert r.step is None

    # Range with step
    r = parse_range("5:10:2")
    assert isinstance(r, slice)
    assert r.start == 5
    assert r.stop == 10
    assert r.step == 2

    # Invalid formats
    with pytest.raises(ValueError):
        parse_range("a")

    with pytest.raises(ValueError):
        parse_range("1:2:3:4")


@pytest.fixture
def sample_file():
    """Create a temporary sample file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        for i in range(100):
            f.write(f"Line {i}\n")

    yield f.name

    # Cleanup
    os.unlink(f.name)
    idx_file = f.name + ".idx"
    if os.path.exists(idx_file):
        os.unlink(idx_file)
    numlines_file = os.path.join(os.path.dirname(f.name), os.path.basename(f.name) + ".numlines")
    if os.path.exists(numlines_file):
        os.unlink(numlines_file)


def test_cli_single_line(sample_file):
    """Test CLI single line retrieval."""
    # Call the main function directly
    result = main([sample_file, "5"])
    assert result == 0  # Success

    # Test actual command line execution
    result = subprocess.run(
        ["linex", sample_file, "5"], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "Line 5"


def test_cli_line_range(sample_file):
    """Test CLI line range retrieval."""
    # Call the main function directly
    result = main([sample_file, "5:10"])
    assert result == 0  # Success

    # Test actual command line execution
    result = subprocess.run(
        ["linex", sample_file, "5:10"], capture_output=True, text=True, check=True
    )
    output_lines = result.stdout.strip().split("\n")
    assert len(output_lines) == 5
    assert output_lines[0] == "Line 5"
    assert output_lines[4] == "Line 9"


def test_cli_line_numbers(sample_file):
    """Test CLI with line number display."""
    # Test the command with line numbers
    result = subprocess.run(
        ["linex", sample_file, "5:8", "--line-numbers"], capture_output=True, text=True, check=True
    )
    output_lines = result.stdout.strip().split("\n")
    assert len(output_lines) == 3
    assert output_lines[0].startswith("5:")
    assert "Line 5" in output_lines[0]
    assert output_lines[2].startswith("7:")
    assert "Line 7" in output_lines[2]


def test_cli_invalid_range(sample_file):
    """Test CLI with invalid range."""
    # This should fail with non-zero exit code
    result = subprocess.run(["linex", sample_file, "invalid"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_cli_out_of_bounds(sample_file):
    """Test CLI with out-of-bounds index."""
    # This should fail with non-zero exit code
    result = subprocess.run(["linex", sample_file, "1000"], capture_output=True, text=True)
    assert result.returncode != 0
    assert "Error" in result.stderr


def test_cli_no_args():
    """Test CLI with no arguments."""
    # This should show help and exit with 0
    result = subprocess.run(["linex"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "usage:" in result.stdout


def test_cli_example_command():
    """Test the example command."""
    example_file = "test_example_cmd.txt"

    try:
        # Run the example command
        result = subprocess.run(
            ["linex", "example", "--output", example_file, "--lines", "50"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Check command succeeded
        assert result.returncode == 0
        assert "Created example file" in result.stdout
        assert "50 lines" in result.stdout

        # Verify file exists and has correct content
        assert os.path.exists(example_file)

        with open(example_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 50
            assert lines[0].strip() == "Line 0"
            assert lines[49].strip() == "Line 49"

    finally:
        # Clean up
        if os.path.exists(example_file):
            os.remove(example_file)
        if os.path.exists(example_file + ".idx"):
            os.remove(example_file + ".idx")
        if os.path.exists(
            os.path.join(
                os.path.dirname(example_file), os.path.basename(example_file) + ".numlines"
            )
        ):
            os.remove(
                os.path.join(
                    os.path.dirname(example_file), os.path.basename(example_file) + ".numlines"
                )
            )
