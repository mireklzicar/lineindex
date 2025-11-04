# NA18507 chr1 (small subset) – Tabix vs samtools (strace)

This report summarizes an apples-to-apples style measurement on a small NA18507 chr1 dataset prepared in this folder (two SRRs, ~100k read pairs each, hg18 chr1).

Methodology adjustments to mirror Table 3 of the Tabix paper:
- Single process per tool with preloaded index:
  - Tabix: `tabix -R regions.bed chr1_align.tsv.gz`
  - samtools (SAM text): `samtools view na18507.hg18.chr1.40x.bam -L regions.bed`
- Intervals: 1,000 random intervals with width uniformly sampled from 1..1000 bp on chr1.
- Metrics captured:
  - CPU time (user+sys) for queries via `/usr/bin/time`.
  - Bytes read from disk by summing return values of `read()/pread64()` from strace logs.
  - Bytes of data emitted (plain text) via `wc -c` on tool output.
  - `lseek()` calls per query (from strace logs).
- Indexing: Tabix TSV built from the chr1 BAM with `bgzip + tabix` (indexing times omitted here due to the very small dataset; focus is query I/O behavior).

Raw artifacts live under `benchmarks/na18507_tabix_chr1_40x/work/strace/`.

## Overall (1000 intervals, widths 1..1000 bp)

| tool      | cpu_s | mb_read | mb_output | lseek_per_query | queries |
|---|---:|---:|---:|---:|---:|
| tabix     | 0.010 | 0.623   | 0.005     | 1.580           | 1000    |
| samtools  | 0.020 | 4.357   | 0.029     | 0.019           | 1000    |
| lineindex | 1.000 | 2.513   | 0.005     | 0.570           | 1000    |

Notes:
- Absolute times are tiny due to the demo-scale dataset; ratios and I/O behavior are the main signal.
- `mb_output` differs: Tabix prints TSV text derived from BAM; `samtools view` prints SAM text.

## By interval width

Buckets: `1–10 bp`, `11–100 bp`, `101–1000 bp`.

| bucket     | queries | tabix_cpu_s | tabix_mb_read | tabix_mb_output | tabix_lseek_per_q | samtools_cpu_s | samtools_mb_read | samtools_mb_output | samtools_lseek_per_q | lineindex_cpu_s | lineindex_mb_read | lineindex_mb_output | lineindex_lseek_per_q |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| w1_10      | 13      | 0.000       | 0.242         | 0.000           | 2.000             | 0.020          | 4.335            | 0.000              | 1.462               | 0.900           | 2.220             | 0.000               | 38.538                 |
| w11_100    | 94      | 0.000       | 0.479         | 0.000           | 1.138             | 0.020          | 4.336            | 0.000              | 0.202               | 0.920           | 2.226             | 0.000               | 5.340                  |
| w101_1000  | 893     | 0.010       | 0.621         | 0.005           | 1.577             | 0.020          | 4.355            | 0.028              | 0.021               | 0.960           | 2.498             | 0.005               | 0.635                  |

Observations on this small dataset:
- Tabix shows low MB read and ~1.1–2.0 lseek/query across widths, reflecting random BGZF seeks with the linear index; CPU time rises with width.
- `samtools view -L` reads more from disk and shows very low lseek/query with `pread64()` usage; CPU time largely dominated by BAM decode and SAM formatting, weakly dependent on width at this scale.

## Relation to the original Table 3
- Same query shape (1..1000 bp), single process per tool, index loaded once, syscall-based I/O accounting.
- Different dataset scale (ours is ~1× coverage after subsetting vs ~40×), so absolute numbers are not directly comparable.
- Modern htslib prefers `pread64()` over `lseek()+read`; we therefore count total `read/pread64` bytes and report `lseek()` separately.

## LineIndex comparison
- Region queries are outside LineIndex’s current scope (LineIndex is line-number addressing). For apples-to-apples region benchmarks, LineIndex would need a region adapter (secondary index from `chr:start-end` or fixed-width bins to line numbers).
- We ran a separate synthetic benchmark that compares LineIndex uncompressed/compressed and multiple memory-map modes against Tabix/indxr for random line lookups (see `benchmarks/general/results.json` and plots). For region-like workloads on structured text, adding a region adapter is recommended.

## Reproducing this run
```bash
# Build Tabix TSV and run the strace harness
./micromamba run -n na18507 -r work/.micromamba bash scripts/build_tabix_from_bam.sh
./micromamba run -n na18507 -r work/.micromamba bash scripts/run_strace_bench.sh
# Tables are generated from TSVs in work/strace/
```
