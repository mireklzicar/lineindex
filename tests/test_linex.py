"""Tests for the Linex class."""
import os
import tempfile
import pytest
import numpy as np
from linex import Linex


@pytest.fixture
def sample_file():
    """Create a temporary sample file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        for i in range(1000):
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


def test_init(sample_file):
    """Test Linex initialization."""
    db = Linex(sample_file)
    assert len(db) == 1000
    assert os.path.exists(sample_file + ".idx")


def test_single_line_access(sample_file):
    """Test accessing single lines."""
    db = Linex(sample_file)
    
    # First line
    assert db[0] == "Line 0"
    
    # Middle line
    assert db[500] == "Line 500"
    
    # Last line
    assert db[999] == "Line 999"
    
    # Negative index
    assert db[-1] == "Line 999"
    assert db[-2] == "Line 998"


def test_slice_access(sample_file):
    """Test accessing slices of lines."""
    db = Linex(sample_file)
    
    # Simple slice
    lines = db[10:15]
    assert len(lines) == 5
    assert lines[0] == "Line 10"
    assert lines[4] == "Line 14"
    
    # Slice with step
    lines = db[10:20:2]
    assert len(lines) == 5
    assert lines[0] == "Line 10"
    assert lines[1] == "Line 12"
    assert lines[4] == "Line 18"
    
    # Negative indices in slice
    lines = db[-5:]
    assert len(lines) == 5
    assert lines[0] == "Line 995"
    assert lines[4] == "Line 999"


def test_parallel_access(sample_file):
    """Test parallel line retrieval."""
    db = Linex(sample_file)
    
    # Sequential access
    lines_seq = db[100:200]
    
    # Parallel access
    lines_par = db.get(slice(100, 200), workers=2)
    
    # Results should be the same
    assert lines_seq == lines_par


def test_header_option(sample_file):
    """Test the header option."""
    db = Linex(sample_file, header=True)
    
    # First line should now be the second line in the file
    assert db[0] == "Line 1"
    
    # Second line should be the third line in the file
    assert db[1] == "Line 2"


def test_fetch_many(sample_file):
    """Test fetching multiple lines in optimized order."""
    db = Linex(sample_file)
    
    # Fetch lines in random order
    indices = [5, 100, 50, 999, 0]
    lines = db.fetch_many(indices)
    
    assert len(lines) == 5
    assert lines[0] == "Line 5"
    assert lines[1] == "Line 100"
    assert lines[2] == "Line 50"
    assert lines[3] == "Line 999"
    assert lines[4] == "Line 0"


def test_out_of_bounds(sample_file):
    """Test behavior with out-of-bounds indices."""
    db = Linex(sample_file)
    
    # Index too large
    with pytest.raises(IndexError):
        _ = db[1000]
    
    # Index too negative
    with pytest.raises(IndexError):
        _ = db[-1001]


def test_clear(sample_file):
    """Test clearing index files."""
    db = Linex(sample_file)
    assert os.path.exists(sample_file + ".idx")
    
    db.clear()
    assert not os.path.exists(sample_file + ".idx")


# Optional test for compression support
@pytest.mark.optional
def test_compression(sample_file):
    """Test file compression (requires idzip package)."""
    try:
        import idzip
        db = Linex(sample_file, compress=True)
        
        # Check compressed file was created
        assert os.path.exists(sample_file + ".dz")
        
        # Test line access still works
        assert db[0] == "Line 0"
        assert db[999] == "Line 999"
        
        # Clean up compressed file
        db.clear()
        assert not os.path.exists(sample_file + ".dz")
        
    except ImportError:
        pytest.skip("idzip package not installed, skipping compression test")