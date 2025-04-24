#!/usr/bin/env python
"""
Command-line interface for the Linex package.

Provides commands for:
- Compressing text files
- Indexing text files
- Retrieving lines by index or range
"""
import sys
import argparse
from typing import Optional, List, Tuple, Union
from .linex import Linex
from .example import create_example_file, DEFAULT_NUM_LINES


def parse_range(range_str: str) -> Union[int, slice]:
    """
    Parse a range string like "5" or "5:10" or "5:100:2" into a slice or integer.
    
    Args:
        range_str: String in format "start:stop:step" or a single number
        
    Returns:
        A slice object or integer
    """
    if ":" in range_str:
        parts = [int(p) if p else None for p in range_str.split(":")]
        if len(parts) == 2:
            return slice(parts[0], parts[1])
        elif len(parts) == 3:
            return slice(parts[0], parts[1], parts[2])
        else:
            raise ValueError(f"Invalid range format: {range_str}")
    else:
        try:
            return int(range_str)
        except ValueError:
            raise ValueError(f"Invalid line number: {range_str}")


def display_lines(lines: Union[str, List[str]], line_numbers: bool = False, 
                 start_index: Optional[int] = None):
    """
    Display lines with optional line numbers.
    
    Args:
        lines: A single line or list of lines to display
        line_numbers: Whether to prefix lines with line numbers
        start_index: Starting index for line numbers (if enabled)
    """
    if isinstance(lines, str):
        lines = [lines]
        
    if line_numbers and start_index is None:
        start_index = 0
        
    for i, line in enumerate(lines):
        if line_numbers:
            print(f"{start_index + i}:\t{line}")
        else:
            print(line)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the linex command line tool.
    
    Args:
        argv: Command line arguments (uses sys.argv if None)
        
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    # Initialize argparse
    parser = argparse.ArgumentParser(
        description="Fast line-based random access to large text files"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Example command
    example_parser = subparsers.add_parser("example", help="Create an example file")
    example_parser.add_argument(
        "--lines", "-l", type=int, default=DEFAULT_NUM_LINES,
        help=f"Number of lines to generate (default: {DEFAULT_NUM_LINES})"
    )
    example_parser.add_argument(
        "--output", "-o", default="example.txt",
        help="Output file path (default: example.txt)"
    )
    
    # Main file access command (default)
    file_parser = subparsers.add_parser("file", help="Access lines from a file")
    file_parser.add_argument("file", help="Text file to process")
    file_parser.add_argument(
        "range", nargs="?", 
        help="Line number (e.g. '5') or range (e.g. '5:10' or '5:100:2')"
    )
    file_parser.add_argument(
        "--compress", "-c", action="store_true", 
        help="Compress the file using BGZF format (.dz)"
    )
    file_parser.add_argument(
        "--header", action="store_true", 
        help="Skip header line (line 0)"
    )
    file_parser.add_argument(
        "--threads", "-t", type=int, default=1,
        help="Number of threads for parallel processing (-1 for all CPUs)"
    )
    file_parser.add_argument(
        "--line-numbers", "-n", action="store_true",
        help="Display line numbers"
    )
    file_parser.add_argument(
        "--force-rebuild", "-f", action="store_true",
        help="Force rebuild of index files"
    )

    # Backwards-compat: if argv is None, get it from sys.argv
    if argv is None:
        argv = sys.argv[1:]
    
    # Here's the key change: handle backwards compatibility BEFORE parsing
    # If the first argument looks like a file path and not a command, insert 'file'
    if argv and argv[0] not in ("example", "file", "-h", "--help"):
        argv.insert(0, "file")
        
    args = parser.parse_args(argv)
    
    try:
        # Handle example command
        if args.command == "example":
            filepath = create_example_file(args.output, args.lines)
            print(f"Created example file with {args.lines} lines: {filepath}")
            return 0
            
        # Handle file command
        if args.command == "file":
            return handle_file_command(args)
            
        # If no command specified, show help
        parser.print_help()
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
        
def handle_file_command(args):
    """Handle the file access command logic."""
    try:
        # Initialize the Linex object
        db = Linex(args.file, compress=args.compress, header=args.header)
        
        # If force_rebuild, clear and recreate
        if args.force_rebuild:
            db.clear()
            db = Linex(args.file, compress=args.compress, header=args.header)
        
        # If range is provided, display the specified lines
        if args.range:
            try:
                line_range = parse_range(args.range)
                if isinstance(line_range, int):
                    result = db.get(line_range)
                    start_idx = line_range if args.line_numbers else None
                    display_lines(result, args.line_numbers, start_idx)
                else:  # slice
                    results = db.get(line_range, workers=args.threads)
                    start_idx = line_range.start if args.line_numbers else None
                    display_lines(results, args.line_numbers, start_idx)
            except (ValueError, IndexError) as e:
                print(f"Error: {e}", file=sys.stderr)
                return 1
        elif args.compress:
            # If only compression was requested and no range, just finish
            print(f"File compressed: {args.file} -> {args.file}.dz")
        else:
            # If no range or action was specified, show stats
            print(f"File: {args.file}")
            print(f"Lines: {len(db)}")
            print(f"Compressed: {'Yes' if args.compress else 'No'}")
            print(f"Has header: {'Yes' if args.header else 'No'}")
            print("")
            print("Usage examples:")
            print(f"  linex file {args.file} 0          # Get first line")
            print(f"  linex file {args.file} 0:10       # Get first 10 lines")
            print(f"  linex file {args.file} 5:15:2     # Get every other line from 5-14")
            print(f"  linex example                     # Create an example file")
            
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())