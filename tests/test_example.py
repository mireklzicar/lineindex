"""Tests for the example module."""

import os
import tempfile
from lineindex.example import create_example_file, DEFAULT_NUM_LINES
from lineindex import LineIndex


def test_create_example_file():
    """Test creating example files."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp:
        temp_path = temp.name

    try:
        # Test with default parameters
        filepath = create_example_file(temp_path)
        assert os.path.exists(filepath)

        # Check line count
        with open(filepath, "r") as f:
            line_count = sum(1 for _ in f)
        assert line_count == DEFAULT_NUM_LINES

        # Check content
        with open(filepath, "r") as f:
            for i, line in enumerate(f):
                assert line.strip() == f"Line {i}"
                if i >= 10:  # Just check the first few lines
                    break

        # Test with custom line count
        custom_lines = 50
        filepath = create_example_file(temp_path, num_lines=custom_lines)

        with open(filepath, "r") as f:
            line_count = sum(1 for _ in f)
        assert line_count == custom_lines

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_example_import():
    """Test that importing the example module creates the example file."""
    example_path = "example.txt"

    try:
        # The file should already exist from importing the module
        assert os.path.exists(example_path)

        # Should be able to use it with LineIndex
        db = LineIndex(example_path)
        assert len(db) == DEFAULT_NUM_LINES
        assert db[0] == "Line 0"
        assert db[10] == "Line 10"

    finally:
        # Clean up
        if os.path.exists(example_path):
            os.unlink(example_path)

        idx_file = example_path + ".idx"
        if os.path.exists(idx_file):
            os.unlink(idx_file)

        numlines_file = os.path.join(
            os.path.dirname(example_path), os.path.basename(example_path) + ".numlines"
        )
        if os.path.exists(numlines_file):
            os.unlink(numlines_file)
