"""
FASTA convenience wrappers for LineIndex's bio extra.

We delegate random access to pyfaidx and provide a tiny helper to fetch
sequences by region or from a BED.
"""
from __future__ import annotations

from typing import Iterable, List, Tuple

try:
    from pyfaidx import Fasta  # type: ignore
except Exception as exc:  # pragma: no cover - optional dependency
    raise ImportError("pyfaidx is required for lineindex[bio] FASTA helpers") from exc


def fetch_region(fasta_path: str, region: str) -> str:
    """Fetch sequence for region like 'chr1:100-200' (1-based inclusive)."""
    fa = Fasta(fasta_path, read_ahead=8192)
    try:
        chrom, rng = region.split(":", 1)
        start, end = rng.split("-", 1)
        seq = fa[chrom][int(start) - 1 : int(end)].seq
        return str(seq)
    finally:
        fa.close()


def fetch_bed(fasta_path: str, bed_path: str) -> List[Tuple[str, int, int, str]]:
    """Fetch sequences for each BED line, returning list of (chrom, start, end, seq)."""
    fa = Fasta(fasta_path, read_ahead=8192)
    out: List[Tuple[str, int, int, str]] = []
    try:
        with open(bed_path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip() or line.startswith("#"):
                    continue
                chrom, s, e, *_ = line.rstrip("\n").split("\t")
                start = int(s)
                end = int(e)
                seq = fa[chrom][start - 1 : end].seq
                out.append((chrom, start, end, str(seq)))
    finally:
        fa.close()
    return out

