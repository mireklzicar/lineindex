#!/usr/bin/env python3
"""
Benchmark LineIndex against alternative indexing tools.

The benchmark covers three operations for a range of file sizes:
    1. Preparing the dataset (plain text file).
    2. Building the tool-specific index (LineIndex variants, indxr/indexr, tabix).
    3. Fetching a batch of random single-line lookups.

Results are printed in a tabular form and stored as JSON for later analysis.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import random
import resource
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lineindex.example import create_example_file
from lineindex.lineindex import LineIndex

# The pip package named `indexr` is not a line-oriented indexer.
# We instead rely on the `indxr` project, which offers comparable functionality.
try:
    from indxr import Indxr
except ImportError as exc:  # pragma: no cover - optional dependency
    raise SystemExit(
        "The benchmark requires the `indxr` package. Install it with `pip install indxr`."
    ) from exc


DATA_DIR = Path(__file__).resolve().parent / "data"
TABIX_DIR = DATA_DIR / "tabix"
RESULTS_PATH = Path(__file__).resolve().parent / "results.json"
LINEINDEX_VARIANTS: Sequence[tuple[str, Dict[str, object]]] = (
    # Uncompressed variants
    ("lineindex_auto", {"memory_map": "auto", "compress": False}),
    ("lineindex_none", {"memory_map": "none", "compress": False}),
    ("lineindex_offsets", {"memory_map": "offsets", "compress": False}),
    ("lineindex_data", {"memory_map": "data", "compress": False}),
    ("lineindex_all", {"memory_map": "all", "compress": False}),
    # Compressed (idzip/BGZF) variants
    ("lineindex_compressed", {"memory_map": "auto", "compress": True}),
    ("lineindex_compressed_offsets", {"memory_map": "offsets", "compress": True}),
    ("lineindex_compressed_none", {"memory_map": "none", "compress": True}),
)

LINE_COUNTS: Sequence[int] = (
    1_000,
    10_000,
    100_000,
    1_000_000,
    5_000_000,
    10_000_000,
)

NUM_RANDOM_LOOKUPS = 200
RANDOM_SEED = 12345


@dataclass
class BenchmarkTimings:
    build_seconds: float
    lookup_total_seconds: float
    lookup_avg_milliseconds: float
    lookup_std_milliseconds: float
    disk_bytes: int
    peak_rss_bytes: int

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


def _current_rss_bytes() -> int:
    """Return the current peak RSS in bytes for this process."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux reports kilobytes
    if sys.platform == "darwin":
        return int(usage)
    return int(usage * 1024)


CTX = mp.get_context("spawn")


def _run_worker(target, *args):
    queue: mp.Queue = CTX.Queue()
    process = CTX.Process(target=target, args=(*args, queue))
    process.start()
    result = queue.get()
    process.join()
    if process.exitcode != 0:
        raise RuntimeError(f"Worker {target.__name__} failed with code {process.exitcode}")
    return result


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TABIX_DIR.mkdir(parents=True, exist_ok=True)


def ensure_plain_text_file(line_count: int) -> Path:
    """
    Create (or reuse) an example file with the requested number of lines.
    """
    filename = DATA_DIR / f"example_{line_count:,}.txt".replace(",", "_")
    if not filename.exists():
        print(f"[dataset] creating {filename.name} with {line_count:,} lines")
        create_example_file(str(filename), num_lines=line_count)
    return filename


def _lineindex_worker(
    txt_path_str: str,
    random_indices: Sequence[int],
    memory_map_mode: str,
    compress: bool,
    queue: mp.Queue,
) -> None:
    from pathlib import Path

    txt_path = Path(txt_path_str)
    idx_path = txt_path.with_suffix(".txt.idx")
    numlines_path = txt_path.with_suffix(".txt.numlines")
    data_path = Path(str(txt_path) + ".dz") if compress else txt_path

    for path in (idx_path, numlines_path, Path(str(txt_path) + ".dz") if compress else None):
        if path and path.exists():
            path.unlink()

    baseline = _current_rss_bytes()

    start = time.perf_counter()
    index = LineIndex(str(txt_path), memory_map=memory_map_mode, compress=compress)
    build_seconds = time.perf_counter() - start
    index.close()

    index = LineIndex(str(txt_path), memory_map=memory_map_mode, compress=compress)
    lookup_durations = []
    for position in random_indices:
        loop_start = time.perf_counter()
        index[position]
        lookup_durations.append(time.perf_counter() - loop_start)
    index.close()

    peak = _current_rss_bytes()
    avg_ms = statistics.mean(lookup_durations) * 1_000
    std_ms = statistics.pstdev(lookup_durations) * 1_000 if len(lookup_durations) > 1 else 0.0

    disk_bytes = 0
    for path in (data_path, idx_path, numlines_path):
        if path.exists():
            disk_bytes += path.stat().st_size

    queue.put(
        {
            "build_seconds": build_seconds,
            "lookup_total_seconds": sum(lookup_durations),
            "lookup_avg_milliseconds": avg_ms,
            "lookup_std_milliseconds": std_ms,
            "disk_bytes": disk_bytes,
            "peak_rss_bytes": max(0, peak - baseline),
        }
    )


def _indxr_worker(
    txt_path_str: str,
    random_indices: Sequence[int],
    queue: mp.Queue,
) -> None:
    from pathlib import Path

    baseline = _current_rss_bytes()

    start = time.perf_counter()
    index = Indxr(path=txt_path_str, kind="txt")
    build_seconds = time.perf_counter() - start

    lookup_durations = []
    for position in random_indices:
        loop_start = time.perf_counter()
        index[position]
        lookup_durations.append(time.perf_counter() - loop_start)

    peak = _current_rss_bytes()
    avg_ms = statistics.mean(lookup_durations) * 1_000
    std_ms = statistics.pstdev(lookup_durations) * 1_000 if len(lookup_durations) > 1 else 0.0

    disk_bytes = Path(txt_path_str).stat().st_size

    queue.put(
        {
            "build_seconds": build_seconds,
            "lookup_total_seconds": sum(lookup_durations),
            "lookup_avg_milliseconds": avg_ms,
            "lookup_std_milliseconds": std_ms,
            "disk_bytes": disk_bytes,
            "peak_rss_bytes": max(0, peak - baseline),
        }
    )


def _tabix_worker(
    txt_path_str: str,
    random_indices: Sequence[int],
    queue: mp.Queue,
) -> None:
    from pathlib import Path

    txt_path = Path(txt_path_str)
    base_name = txt_path.stem
    tsv_path = TABIX_DIR / f"{base_name}.tsv"
    gz_path = TABIX_DIR / f"{base_name}.tsv.gz"
    tbi_path = TABIX_DIR / f"{base_name}.tsv.gz.tbi"

    for path in (gz_path, tbi_path):
        if path.exists():
            path.unlink()

    baseline = _current_rss_bytes()

    start = time.perf_counter()
    with open(txt_path, "r", encoding="utf-8") as src, open(tsv_path, "w", encoding="utf-8") as dst:
        for offset, line in enumerate(src, start=1):
            dst.write(f"chr1\t{offset}\t{offset}\t{line.rstrip()}\n")
    subprocess.run(["bgzip", "-f", str(tsv_path)], check=True, capture_output=False)
    subprocess.run(["tabix", "-s", "1", "-b", "2", "-e", "3", str(gz_path)], check=True, capture_output=False)
    build_seconds = time.perf_counter() - start

    lookup_durations = []
    for position in random_indices:
        region = f"chr1:{position + 1}-{position + 1}"
        loop_start = time.perf_counter()
        subprocess.run(
            ["tabix", str(gz_path), region],
            check=True,
            capture_output=True,
            text=True,
        )
        lookup_durations.append(time.perf_counter() - loop_start)

    peak = _current_rss_bytes()
    avg_ms = statistics.mean(lookup_durations) * 1_000
    std_ms = statistics.pstdev(lookup_durations) * 1_000 if len(lookup_durations) > 1 else 0.0

    disk_bytes = 0
    for path in (gz_path, tbi_path):
        if path.exists():
            disk_bytes += path.stat().st_size

    queue.put(
        {
            "build_seconds": build_seconds,
            "lookup_total_seconds": sum(lookup_durations),
            "lookup_avg_milliseconds": avg_ms,
            "lookup_std_milliseconds": std_ms,
            "disk_bytes": disk_bytes,
            "peak_rss_bytes": max(0, peak - baseline),
        }
    )


def benchmark_lineindex(
    txt_path: Path, random_indices: Sequence[int], *, memory_map_mode: str, compress: bool
) -> BenchmarkTimings:
    metrics = _run_worker(
        _lineindex_worker,
        str(txt_path),
        list(random_indices),
        memory_map_mode,
        compress,
    )
    return BenchmarkTimings(**metrics)


def benchmark_indxr(txt_path: Path, random_indices: Sequence[int]) -> BenchmarkTimings:
    metrics = _run_worker(
        _indxr_worker,
        str(txt_path),
        list(random_indices),
    )
    return BenchmarkTimings(**metrics)


def benchmark_tabix(txt_path: Path, random_indices: Sequence[int]) -> BenchmarkTimings:
    metrics = _run_worker(
        _tabix_worker,
        str(txt_path),
        list(random_indices),
    )
    return BenchmarkTimings(**metrics)


def pretty_seconds(value: float) -> str:
    if value >= 1:
        return f"{value:6.2f}s"
    return f"{value * 1_000:6.1f}ms"


def run_benchmarks() -> Dict[int, Dict[str, Dict[str, float]]]:
    ensure_directories()
    rng = random.Random(RANDOM_SEED)
    results: Dict[int, Dict[str, Dict[str, float]]] = {}

    for line_count in LINE_COUNTS:
        txt_path = ensure_plain_text_file(line_count)
        sample_size = min(NUM_RANDOM_LOOKUPS, line_count)
        random_indices = rng.sample(range(line_count), sample_size)

        results[line_count] = {}
        print(f"\n=== {line_count:,} lines ===")

        for label, cfg in LINEINDEX_VARIANTS:
            timings = benchmark_lineindex(
                txt_path,
                random_indices,
                memory_map_mode=cfg["memory_map"],  # type: ignore[index]
                compress=cfg["compress"],  # type: ignore[index]
            )
            results[line_count][label] = timings.as_dict()
            print(
                f"{label:<20}",
                pretty_seconds(timings.build_seconds),
                pretty_seconds(timings.lookup_total_seconds),
                f"{timings.lookup_avg_milliseconds:7.3f} ms/lookup",
            )

        timings = benchmark_indxr(txt_path, random_indices)
        results[line_count]["indxr"] = timings.as_dict()
        print(
            f"{'indxr':<20}",
            pretty_seconds(timings.build_seconds),
            pretty_seconds(timings.lookup_total_seconds),
            f"{timings.lookup_avg_milliseconds:7.3f} ms/lookup",
        )

        timings = benchmark_tabix(txt_path, random_indices)
        results[line_count]["tabix"] = timings.as_dict()
        print(
            f"{'tabix':<20}",
            pretty_seconds(timings.build_seconds),
            pretty_seconds(timings.lookup_total_seconds),
            f"{timings.lookup_avg_milliseconds:7.3f} ms/lookup",
        )

    return results


def generate_plots(results: Dict[int, Dict[str, Dict[str, float]]]) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:  # pragma: no cover - plotting optional
        print(f"matplotlib unavailable ({exc}); skipping plot generation.")
        return

    normalized = {int(key): value for key, value in results.items()}
    line_counts = np.array(sorted(normalized.keys()))
    labels = list(next(iter(normalized.values())).keys())
    plots_dir = Path(__file__).resolve().parent / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    def label_display(label: str) -> str:
        return label.replace("lineindex_", "li-")

    # Build time plot
    plt.figure(figsize=(8, 5))
    for label in labels:
        build_times = [normalized[n][label]["build_seconds"] for n in line_counts]
        plt.plot(line_counts, build_times, marker="o", label=label_display(label))
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Lines in file")
    plt.ylabel("Build time (s)")
    plt.title("Index build time vs file size")
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    plt.savefig(plots_dir / "build_times.png", dpi=200)
    plt.close()

    # Lookup latency plot
    plt.figure(figsize=(8, 5))
    for label in labels:
        lookup_us = [normalized[n][label]["lookup_avg_milliseconds"] * 1_000 for n in line_counts]
        plt.plot(line_counts, lookup_us, marker="o", label=label_display(label))
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Lines in file")
    plt.ylabel("Lookup latency (µs)")
    plt.title("Single-line lookup latency vs file size")
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    plt.savefig(plots_dir / "lookup_times.png", dpi=200)
    plt.close()

    # Disk size vs lookup latency
    plt.figure(figsize=(8, 5))
    for label in labels:
        disk_mb = [max(normalized[n][label]["disk_bytes"], 1) / (1024 * 1024) for n in line_counts]
        lookup_us = [normalized[n][label]["lookup_avg_milliseconds"] * 1_000 for n in line_counts]
        plt.plot(disk_mb, lookup_us, marker="o", label=label_display(label))
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Disk footprint (MB)")
    plt.ylabel("Lookup latency (µs)")
    plt.title("Disk footprint vs lookup latency")
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    plt.savefig(plots_dir / "disk_vs_lookup.png", dpi=200)
    plt.close()

    # RAM vs lookup latency
    plt.figure(figsize=(8, 5))
    for label in labels:
        ram_mb = [
            max(normalized[n][label]["peak_rss_bytes"], 1) / (1024 * 1024) for n in line_counts
        ]
        lookup_us = [normalized[n][label]["lookup_avg_milliseconds"] * 1_000 for n in line_counts]
        plt.plot(ram_mb, lookup_us, marker="o", label=label_display(label))
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Peak RSS (MB)")
    plt.ylabel("Lookup latency (µs)")
    plt.title("Peak RSS vs lookup latency")
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    plt.savefig(plots_dir / "ram_vs_lookup.png", dpi=200)
    plt.close()


def main() -> int:
    try:
        results = run_benchmarks()
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user.", file=sys.stderr)
        return 1

    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nSaved detailed results to {RESULTS_PATH.relative_to(Path.cwd())}")
    generate_plots(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
