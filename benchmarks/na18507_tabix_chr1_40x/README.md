# NA18507 (Bentley 2008) → chr1 BAM (hg18) + Tabix vs LineIndex benchmarking

This folder prepares:
- ENA downloads for the Bentley-era NA18507 runs (Illumina GA/GAII; 2008–2009).
- A chr1 BAM on hg18 (NCBI36) emulating the dataset referenced in the Tabix paper (NA18507 chr1 short-read alignment, Bentley 2008).
- A Tabix-indexable TSV derived from the BAM, and a strace-based benchmarking harness similar in spirit to the paper’s Table 3 footnote (measured by strace).

It uses ENA HTTPS links (no SRA Toolkit required), `bwa aln` (backtrack) for alignment, and `samtools` for BAM processing.

## Reproducible environment
Use a local micromamba-based env (no sudo) with bwa/samtools/htslib and Python deps.

```bash
# Create env under ./work/.micromamba and validate tools
bash scripts/bootstrap_env.sh
```

This provides `bwa`, `samtools`, `bgzip`/`tabix` (from htslib) and Python packages including `numpy`, `matplotlib`, `indxr`. For LineIndex’s compressed mode, we install the optional extra `python-idzip` when running the general benchmarks.

## Quick start (feasible demo)
The full dataset is large. The sequence below limits to two runs and subsets reads to keep it fast to reproduce while preserving the workflow.

```bash
# 1) Get Bentley-era run list
./micromamba run -n na18507 -r work/.micromamba bash scripts/ena_make_runlist.sh

# 2) (Optional) Limit to two SRRs for a quick demo
head -n 1 work/ena_bentley.tsv > work/ena_bentley.tsv.tmp
rg -n '^SRR002271|^SRR002277' -N work/ena_bentley.tsv | cut -d: -f1 | xargs -I{} sed -n '{}p' work/ena_bentley.tsv >> work/ena_bentley.tsv.tmp
mv work/ena_bentley.tsv.tmp work/ena_bentley.tsv

# 3) Download FASTQs and verify md5
THREADS=4 ./micromamba run -n na18507 -r work/.micromamba bash scripts/ena_download_fastqs.sh

# (Optional) subset each FASTQ to ~100k reads to speed up alignment
zcat work/fastq/SRR002271_1.fastq.gz | head -n 400000 | pigz > work/fastq/SRR002271_1.fastq.gz.tmp && mv -f work/fastq/SRR002271_1.fastq.gz.tmp work/fastq/SRR002271_1.fastq.gz
zcat work/fastq/SRR002271_2.fastq.gz | head -n 400000 | pigz > work/fastq/SRR002271_2.fastq.gz.tmp && mv -f work/fastq/SRR002271_2.fastq.gz.tmp work/fastq/SRR002271_2.fastq.gz
zcat work/fastq/SRR002277_1.fastq.gz | head -n 400000 | pigz > work/fastq/SRR002277_1.fastq.gz.tmp && mv -f work/fastq/SRR002277_1.fastq.gz.tmp work/fastq/SRR002277_1.fastq.gz
zcat work/fastq/SRR002277_2.fastq.gz | head -n 400000 | pigz > work/fastq/SRR002277_2.fastq.gz.tmp && mv -f work/fastq/SRR002277_2.fastq.gz.tmp work/fastq/SRR002277_2.fastq.gz

# 4) Fetch hg18 reference (chr1-only for speed) and build indexes
CHR_LIST=1 ./micromamba run -n na18507 -r work/.micromamba bash scripts/get_hg18.sh

# 5) Align, merge, mark duplicates, make chr1 BAM, compute coverage and downsample (depth will be low when subsetting reads)
./micromamba run -n na18507 -r work/.micromamba bash scripts/align_bwa_hg18.sh
./micromamba run -n na18507 -r work/.micromamba bash scripts/merge_markdup.sh
./micromamba run -n na18507 -r work/.micromamba bash scripts/make_chr1.sh
TARGET=40 ./micromamba run -n na18507 -r work/.micromamba bash scripts/downsample_chr1_40x.sh

# 6) Build a Tabix indexable TSV from chr1 BAM (chrom, start, end, qname)
./micromamba run -n na18507 -r work/.micromamba bash scripts/build_tabix_from_bam.sh

# 7) Run strace-based benchmark: Tabix vs samtools
./micromamba run -n na18507 -r work/.micromamba bash scripts/run_strace_bench.sh
```

Outputs:
- `work/out/na18507.hg18.chr1.bam` (+ `.bai`) and optionally `na18507.hg18.chr1.40x.bam`
- `work/tabix/chr1_align.tsv.gz` (+ `.tbi`)
- Strace results under `work/strace/`: `tabix_summary.txt`, `samtools_summary.txt`, detailed syscall logs and a quick `seeks.txt` counter

Notes:
- With subsetting, the mean chr1 depth is ~1×, so the “40×” downsample step will cap at 1.0.
- The strace harness measures syscalls and counts seeks across a random set of intervals; depending on data density and `pread64` usage, seek counts may not be strictly “one per interval”.

## General benchmark: LineIndex vs Tabix on synthetic text
To compare LineIndex (uncompressed and idzip-compressed) with different memory mapping modes versus Tabix and `indxr`, run the general benchmark. It creates plain text files of varying sizes, builds the appropriate indexes, and performs random single-line lookups.

```bash
# Ensure lineindex is installed with compression extra inside the env
./micromamba run -n na18507 -r work/.micromamba bash -lc 'python3 -m pip install -e ".[compression]"'

# Run the benchmark (saves JSON + plots under benchmarks/general)
./micromamba run -n na18507 -r work/.micromamba bash -lc 'python3 benchmarks/general/run_benchmarks.py'
```

What’s compared:
- LineIndex uncompressed: memory_map = auto, none, offsets, data, all
- LineIndex compressed (idzip/BGZF): memory_map = auto, offsets, none
- `indxr` (line-oriented indexer)
- Tabix (via a generated TSV with columns chr1, start, end, payload)

## Implementation notes
- Compression: Tabix uses BGZF; LineIndex uses `python-idzip` (BGZF) for compressed mode. Compressed mode supports mapping the offsets array, while the data itself is accessed via idzip streams (memory-mapping the compressed data file is not supported).
- Reference fetch supports `CHR_LIST` to limit chromosomes (e.g. `CHR_LIST=1`).
- `.gitignore` excludes this folder’s working directories and env artifacts.

## Possible LineIndex enhancements
- Region adapters: optional utilities to build secondary indexes mapping domain keys (e.g. `chr:start-end`, or fixed-width bins) to line numbers, to emulate Tabix-like region queries on structured text.
- Compressed-mode tuning: larger BGZF block size and smarter read-ahead/caching of neighboring blocks for contiguous lookups.
- Optional C-extension for high-speed offset scanning to reduce build time on very large files.
