"""
Provides example data and functionality for Linex.

This module creates an example text file when imported and provides
utility functions for generating example files.
"""
import os
from pathlib import Path


DEFAULT_EXAMPLE_PATH = "example.txt"
DEFAULT_NUM_LINES = 1000


def create_example_file(filename=DEFAULT_EXAMPLE_PATH, num_lines=DEFAULT_NUM_LINES):
    """
    Create an example text file with numbered lines.
    
    Args:
        filename (str): Path where the example file will be created
        num_lines (int): Number of lines to generate
        
    Returns:
        str: The absolute path to the created file
    """
    filepath = Path(filename).absolute()
    
    with open(filepath, 'w') as f:
        for i in range(num_lines):
            f.write(f"Line {i}\n")
            
    return str(filepath)


def get_example_path():
    """
    Get path to the example file, creating it if it doesn't exist.
    
    Returns:
        str: Path to the example file
    """
    if not os.path.exists(DEFAULT_EXAMPLE_PATH):
        create_example_file()
    return os.path.abspath(DEFAULT_EXAMPLE_PATH)


# Create example file when the module is imported
example_path = get_example_path()