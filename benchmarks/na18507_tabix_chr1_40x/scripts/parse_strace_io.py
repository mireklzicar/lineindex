#!/usr/bin/env python3
"""
Parse strace logs and summarize I/O metrics.

We sum bytes returned by read()/pread64() (actual bytes read), count lseek() calls,
and report total calls per syscall. The parser expects strace default textual output.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass


READ_RE = re.compile(r"\b(?:read|pread64)\([^)]*\)\s*=\s*(-?\d+)")
LSEEK_RE = re.compile(r"\blseek\(")


@dataclass
class Summary:
    bytes_read: int = 0
    read_calls: int = 0
    lseek_calls: int = 0


def parse_file(path: str) -> Summary:
    s = Summary()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = READ_RE.search(line)
            if m:
                ret = int(m.group(1))
                if ret > 0:
                    s.bytes_read += ret
                    s.read_calls += 1
            if "lseek(" in line:
                s.lseek_calls += 1
    return s


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: parse_strace_io.py <strace_log>", file=sys.stderr)
        return 2
    s = parse_file(argv[1])
    print(f"bytes_read\t{s.bytes_read}")
    print(f"read_calls\t{s.read_calls}")
    print(f"lseek_calls\t{s.lseek_calls}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

