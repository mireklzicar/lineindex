"""
Region adapter for LineIndex.

Provides a lightweight secondary index over a tab-delimited file with
columns: chrom, start, end, <payload...> (at least 3 columns).

The adapter maps genomic intervals to line numbers and can fetch the
corresponding TSV lines via LineIndex.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .lineindex import LineIndex


@dataclass
class ChromIndex:
    starts: np.ndarray  # uint64, sorted ascending
    ends: np.ndarray  # uint64, reordered to match starts sort
    lines: np.ndarray  # uint64, original 1-based line numbers in the TSV


class RegionIndex:
    """
    Build and query a simple per-chromosome interval index for a TSV file.

    The index layout on disk is a directory with per-chromosome .npy files
    holding `starts`, `ends`, `lines`, and a meta.json.
    """

    def __init__(self, tsv_path: str, index_dir: str | None = None, *, memory_map: bool = True):
        self.tsv_path = str(tsv_path)
        self.index_dir = index_dir or (self.tsv_path + ".li_region")
        self.memory_map = memory_map
        self._chrom_cache: Dict[str, ChromIndex] = {}

    # ------------------------------- build/load
    def build(self) -> None:
        """Build the region index from TSV and write it to disk."""
        Path(self.index_dir).mkdir(parents=True, exist_ok=True)
        per_chrom: Dict[str, List[Tuple[int, int, int]]] = {}
        num_lines = 0
        with open(self.tsv_path, "r", encoding="utf-8") as fh:
            for i, line in enumerate(fh, start=1):
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                chrom = parts[0]
                try:
                    start = int(parts[1])
                    end = int(parts[2])
                except ValueError:
                    # skip header or malformed lines
                    continue
                per_chrom.setdefault(chrom, []).append((start, end, i))
                num_lines = i

        meta = {"tsv": self.tsv_path, "chroms": {}, "num_lines": num_lines}
        for chrom, recs in per_chrom.items():
            # sort by start ascending; stable sort keeps input order for ties
            recs.sort(key=lambda t: t[0])
            starts = np.fromiter((r[0] for r in recs), dtype=np.uint64, count=len(recs))
            ends = np.fromiter((r[1] for r in recs), dtype=np.uint64, count=len(recs))
            lines = np.fromiter((r[2] for r in recs), dtype=np.uint64, count=len(recs))
            np.save(self._path(chrom, "starts"), starts)
            np.save(self._path(chrom, "ends"), ends)
            np.save(self._path(chrom, "lines"), lines)
            meta["chroms"][chrom] = int(len(recs))

        with open(self._meta_path(), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)

    def exists(self) -> bool:
        return os.path.exists(self._meta_path())

    def _path(self, chrom: str, kind: str) -> str:
        return os.path.join(self.index_dir, f"{chrom}.{kind}.npy")

    def _meta_path(self) -> str:
        return os.path.join(self.index_dir, "meta.json")

    def _load_chrom(self, chrom: str) -> ChromIndex | None:
        if chrom in self._chrom_cache:
            return self._chrom_cache[chrom]
        starts_path = self._path(chrom, "starts")
        ends_path = self._path(chrom, "ends")
        lines_path = self._path(chrom, "lines")
        if not (os.path.exists(starts_path) and os.path.exists(ends_path) and os.path.exists(lines_path)):
            return None
        if self.memory_map:
            starts = np.load(starts_path, mmap_mode="r")
            ends = np.load(ends_path, mmap_mode="r")
            lines = np.load(lines_path, mmap_mode="r")
        else:
            starts = np.load(starts_path)
            ends = np.load(ends_path)
            lines = np.load(lines_path)
        ci = ChromIndex(starts=starts, ends=ends, lines=lines)
        self._chrom_cache[chrom] = ci
        return ci

    # --------------------------------- query
    def query_lines(self, chrom: str, start: int, end: int) -> List[int]:
        """Return 1-based line numbers overlapping chrom:start-end inclusive."""
        ci = self._load_chrom(chrom)
        if ci is None or len(ci.starts) == 0:
            return []
        # All starts <= end are potential candidates
        # np.searchsorted gives index of first element > end
        upto = int(np.searchsorted(ci.starts, end, side="right"))
        if upto <= 0:
            return []
        # Vectorized filter for ends >= start
        mask = ci.ends[:upto] >= start
        if not np.any(mask):
            return []
        return [int(x) for x in ci.lines[:upto][mask].tolist()]

    def query_lines_bed(self, bed_path: str) -> List[int]:
        """Return unique line numbers overlapping all regions in a BED-like file."""
        hits: List[int] = []
        with open(bed_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                chrom, s, e, *_ = line.rstrip("\n").split("\t")
                start = int(s)
                end = int(e)
                hits.extend(self.query_lines(chrom, start, end))
        # keep original order (stable) but uniquify
        seen = set()
        unique = []
        for h in hits:
            if h not in seen:
                unique.append(h)
                seen.add(h)
        return unique

    # ------------------------------- fetch
    def fetch_tsv_lines(self, line_numbers: Iterable[int], *, memory_map: str = "offsets", compress: bool = False) -> List[str]:
        li = LineIndex(self.tsv_path, compress=compress, memory_map=memory_map)
        try:
            return li.fetch_many(list(line_numbers))
        finally:
            li.close()
