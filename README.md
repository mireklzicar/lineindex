# LineIndex: Fast Line-based Random Access for Text Files

[![PyPI version](https://badge.fury.io/py/lineindex.svg)](https://badge.fury.io/py/lineindex)
[![Python Version](https://img.shields.io/pypi/pyversions/lineindex.svg)](https://pypi.org/project/lineindex/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

LineIndex provides lightning-fast random access to lines in large text files through efficient indexing. It's designed to handle very large files where you need to frequently access specific lines without reading the entire file.

## Key Features

- **O(1) Random Access**: Get any line by its number in constant time
- **Memory Efficient**: Uses memory mapping and lazy loading
- **Optional Compression**: Transparently handles BGZF compressed files
- **Parallel Processing**: Multi-threaded line retrieval for batch operations
- **Simple API**: Clean Pythonic interface with slice notation support
- **Command Line Tool**: Easy access from shell scripts

## Installation

```bash
# Basic installation
pip install lineindex

# With compression support
pip install lineindex[compression]

# For developers
pip install lineindex[dev]
```

## Quick Start

### Python API

```python
from lineindex import LineIndex

# Create an index for a large file
db = LineIndex("bigfile.txt")

# Get a single line
line = db[1000]  # get the 1001st line (0-indexed)

# Get a range of lines
lines = db[1000:1010]  # get 10 lines

# Get every other line in a range
lines = db[1000:1100:2]  # get every other line

# Use parallel processing for better performance with large slices
lines = db.get(1000:2000, workers=-1)  # use all available CPU cores

# With header skipping (useful for CSV files)
db = LineIndex("data.csv", header=True)
first_data_row = db[0]  # skips the header row

# With compression
db = LineIndex("bigfile.txt", compress=True)  # Creates bigfile.txt.dz

# Using the example module (creates example.txt in current directory)
from lineindex import example
db = LineIndex("example.txt")  # Use the auto-created example file

# Or create a custom example
from lineindex.example import create_example_file
create_example_file("custom.txt", num_lines=5000)
db = LineIndex("custom.txt")
```

### Command Line Interface

```bash
# Index and compress a file
lineindex file bigfile.txt --compress

# Get a single line
lineindex file bigfile.txt 1000

# Get a range of lines
lineindex file bigfile.txt 1000:1010

# Get every other line with line numbers
lineindex file bigfile.txt 1000:1100:2 --line-numbers

# Use multiple threads for better performance
lineindex file bigfile.txt 1000:2000 --threads 4

# Skip header line (useful for CSV files)
lineindex file data.csv 0 --header

# Create an example file with 1000 lines
lineindex example

# Create an example file with custom number of lines
lineindex example --lines 5000 --output my_example.txt
```

> **Note:** For backward compatibility, you can omit the `file` command, e.g., `lineindex bigfile.txt 1000`.

## How It Works

LineIndex creates a binary index file (.idx) containing the byte offset of each line in the file. This allows for O(1) access to any line by seeking directly to its byte position. The index is created once and reused for subsequent accesses.

For compressed files, LineIndex uses the BGZF format (via the `idzip` package) which preserves random access capabilities despite compression.

## Performance

LineIndex is designed for high performance:

- Uses memory mapping for efficient file access
- Employs vectorized NumPy operations for batch retrieval
- Supports multi-threaded line fetching
- Optimizes disk access patterns

## Use Cases

- **Log Analysis**: Quickly access specific log entries by line number
- **Data Processing**: Extract samples from large datasets without loading everything
- **Text Mining**: Randomly access lines for batch processing
- **Machine Learning**: Efficiently retrieve training examples from large text corpora

## Requirements

- Python 3.8 or higher
- NumPy
- Tqdm (for progress bars)
- python-idzip (optional, for compression support)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.