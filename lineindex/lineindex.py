"""
LineIndex - Fast line-based random access for large text files

This module provides efficient indexed access to text files by line number,
with optional compression support using the BGZF format (through idzip).
"""

import os
import struct
import mmap
import numpy as np
from tqdm import tqdm
import concurrent.futures
from typing import List

try:
    import idzip

    IDZIP_AVAILABLE = True
except ImportError:
    IDZIP_AVAILABLE = False


class LineIndex:
    """
    Fast line-by-line access to text files through indexing.

    This class creates an index of byte offsets for each line in a text file,
    allowing O(1) access to any line by number. Optionally compresses the
    source file using BGZF format (via idzip) for storage efficiency while
    maintaining random access capability.

    Args:
        filepath (str): Path to the text file to index
        compress (bool, optional): Whether to compress the source file. Defaults to False.
        header (bool, optional): Whether the file has a header line to skip. Defaults to False.
    """

    ONE_MB = 1 << 20
    TEN_MB = 10 * ONE_MB
    HUNDRED_MB = 100 * ONE_MB
    OFFSET_DTYPE = np.uint64  # <Q little-endian, 8 bytes / entry

    # ------------------------------------------------------------------ init
    def __init__(self, filepath, *, compress=False, header=False):
        if compress and not IDZIP_AVAILABLE:
            raise ImportError(
                "To use compression, please install the idzip package: pip install python-idzip"
            )

        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.compress = compress
        self.output_filepath = filepath + (".dz" if compress else "")
        self.header = header
        self.output_directory = os.path.dirname(self.output_filepath) or "."
        self.byteoffset_file = os.path.join(self.output_directory, self.filename + ".idx")

        self._build_or_validate()

        # open (or create) the data file --------------------------------
        if not compress:
            self.output_filepath = filepath
            self.file_opener = open
        else:
            self.file_opener = idzip.open
            if not os.path.exists(self.output_filepath):
                self._compress_file()

        self._open_main_file()

        # build or load the binary index --------------------------------
        if not os.path.exists(self.byteoffset_file):
            self._write_byte_offsets_bin()

        # a single mem-mapped view of all offsets (cheap, lazy-loaded)
        self.offsets = np.memmap(self.byteoffset_file, dtype=self.OFFSET_DTYPE, mode="r")

    def _build_or_validate(self):
        """Ensure the file exists and count lines if needed."""
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"File not found: {self.filepath}")

        # Count lines if needed
        numlines_file = os.path.join(self.output_directory, self.filename + ".numlines")
        if not os.path.exists(numlines_file):
            self.numlines = self._count_lines()
            # Save line count for future use
            with open(numlines_file, "w") as f:
                f.write(str(self.numlines))
        else:
            # Load existing line count
            with open(numlines_file, "r") as f:
                self.numlines = int(f.read().strip())

    def _count_lines(self):
        """Count the number of lines in the file."""
        lines = 0
        with open(self.filepath, "rb") as f:
            chunk = f.read(self.HUNDRED_MB)
            while chunk:
                lines += chunk.count(b"\n")
                chunk = f.read(self.HUNDRED_MB)

        # Handle case where the last line doesn't end with newline
        with open(self.filepath, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - 1 if f.tell() > 0 else 0, os.SEEK_SET)
            last_char = f.read(1)
            if last_char and last_char != b"\n":
                lines += 1

        return lines

    # ---------------------------------------------------------------- utils
    def __del__(self):
        try:
            self.main_file.close()
        except Exception:
            pass  # happens if __init__ failed early

    def __len__(self):
        return self.numlines

    # ---------------------------------------------------------- data access
    def __getitem__(self, key):
        """
        Access lines by index or slice.

        Args:
            key: Integer line number or slice

        Examples:
            db[123]      -> single line
            db[10:20]    -> list of lines
            db[10:20:2]  -> list of lines with step

        Returns:
            A single line (str) or list of lines
        """
        return self.get(key)

    def get(self, key, workers=1):
        """
        Access lines by index with optional parallelization.

        Args:
            key: Integer line number or slice
            workers (int): Number of parallel workers for slices.
                          -1 uses all available CPU cores.

        Returns:
            A single line (str) or list of lines
        """
        if workers == -1:
            workers = os.cpu_count() or 1

        if isinstance(key, slice):
            # determine start/stop/step with defaults
            start = key.start if key.start is not None else 0
            stop = key.stop if key.stop is not None else self.numlines
            step = key.step if key.step is not None else 1

            # handle negative indices
            if start < 0:
                start += self.numlines
            if stop < 0:
                stop += self.numlines

            # clamp to [0, self.numlines]
            start = max(min(start, self.numlines), 0)
            stop = max(min(stop, self.numlines), 0)

            idxs = range(start, stop, step)
            if workers <= 1:
                return [self._get_line(i) for i in idxs]
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                    return list(ex.map(self._get_line, idxs))

        elif isinstance(key, int):
            if key < 0:
                key += self.numlines
            if not (0 <= key < self.numlines):
                raise IndexError("line number out of range")
            return self._get_line(key)

        else:
            raise TypeError("index must be int or slice")

    # -------------------------------------------------------------- internal
    def _open_main_file(self):
        """Open the main data file and create a memory map."""
        # always binary read. For compressed files this is a BGZF wrapper
        self.main_file = self.file_opener(self.output_filepath, "rb")
        if not self.compress:
            # uncompressed → mmap for speed
            self.mm = mmap.mmap(self.main_file.fileno(), 0, access=mmap.ACCESS_READ)
        else:
            # compressed → use file-handle only
            self.mm = None

    # ~~~~~~~~~~~~~~~~~~~~~ compression of the source file ~~~~~~~~~~~~~~~~~~
    def _compress_file(self):
        """Create a .dz (BGZF) version of the plain-text file once."""
        chunk_size = self.HUNDRED_MB
        file_size = os.path.getsize(self.filepath)
        iterations = -(-file_size // chunk_size)

        with open(self.filepath, "rb") as src, idzip.IdzipFile(
            self.output_filepath, "wb", sync_size=10 * self.HUNDRED_MB
        ) as dst:

            for _ in tqdm(range(iterations), desc="Compressing", unit_scale=True, unit="chunk"):
                data = src.read(chunk_size)
                if not data:
                    break
                dst.write(data)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ offset index ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _write_byte_offsets_bin(self):
        """Write every line's starting byte position as uint64 to .idx"""
        with open(self.byteoffset_file, "wb") as idx:
            # first line always starts at byte 0
            idx.write(struct.pack("<Q", 0))

            self.main_file.seek(0)
            for _ in tqdm(
                range(self.numlines), desc="Writing byte offsets", unit="lines", unit_scale=True
            ):
                self.main_file.readline()  # consume current line
                idx.write(struct.pack("<Q", self.main_file.tell()))

            # rewind so later reads start at BOF
            self.main_file.seek(0)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ line retrieval ~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _get_byte_offset(self, line_number: int) -> int:
        """Get byte offset for a line number."""
        if self.header and line_number >= 0:
            line_number += 1
        if not (0 <= line_number < len(self.offsets)):
            raise IndexError("line number out of range")
        return int(self.offsets[line_number])

    def _get_line(self, line_number: int) -> str:
        """Retrieve a single line by number."""
        off = self._get_byte_offset(line_number)
        if self.mm is not None:
            # mmap path
            end = self.mm.find(b"\n", off)
            if end == -1:
                end = len(self.mm)
            return self.mm[off:end].decode()
        # compressed path → idzip file
        self.main_file.seek(off)
        line = self.main_file.readline()
        # strip trailing newline
        if line.endswith(b"\n"):
            line = line[:-1]
        return line.decode()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~ batch retrieval ~~~~~~~~~~~~~~~~~~~~~~~~~~
    def fetch_many(self, ids: List[int]) -> List[str]:
        """
        Fetch multiple lines by their indices in optimized order.

        Args:
            ids: List of line indices to fetch

        Returns:
            List of lines in the same order as the requested ids
        """
        ids_np = np.asarray(ids, dtype=np.int64)
        order = np.argsort(ids_np)

        # Apply header offset if needed
        if self.header:
            ids_np = ids_np + 1

        # Get offsets for all requested lines (in sorted order)
        offs = self.offsets[ids_np[order]]  # vectorised RAM read
        lines = [None] * len(ids)

        # Read lines in sequential order for better IO performance
        for slot, off in zip(order, offs):
            end = self.mm.find(b"\n", off)
            if end == -1:
                end = len(self.mm)
            lines[slot] = self.mm[off:end].decode()

        return lines

    # ---------------------------------------------------------------- util
    def clear(self):
        """Delete generated .dz and/or .idx files (for tests/rebuilds)."""
        if self.compress and os.path.exists(self.output_filepath):
            os.remove(self.output_filepath)
        if os.path.exists(self.byteoffset_file):
            os.remove(self.byteoffset_file)
        numlines_file = os.path.join(self.output_directory, self.filename + ".numlines")
        if os.path.exists(numlines_file):
            os.remove(numlines_file)
