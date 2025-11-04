# NA18507 (Bentley 2008) → Tabix-style chr1 ~40× BAM (hg18)

This mini-repo prepares two things:
1. **ENA downloads** for the Bentley-era NA18507 runs (Illumina GA/GAII; 2008–2009).
2. A **chr1 ~40× BAM on hg18 (NCBI36)** to emulate the dataset described in the Tabix paper
   (“NA18507 chr1 40× short-read alignment from Bentley et al., 2008”).

It uses ENA HTTPS links for the FASTQs (no SRA Toolkit required), and `bwa aln` (backtrack) for alignment.

## Requirements (Linux/macOS)
- bash, awk, coreutils, curl, pigz (optional but fast), wget (optional)
- bwa (>=0.7, includes `aln/sampe`), samtools (>=1.10), bc
- ~1–2 TB free space if you download *all* selected runs; far less if you only keep chr1 BAM

## Quick start
```bash
# 0) Install bwa & samtools (conda example)
# mamba create -n na18507 -y bwa samtools pigz
# conda activate na18507

# 1) Get the Bentley-era run list as a TSV from ENA
bash scripts/ena_make_runlist.sh

# 2) Download FASTQs (multi-threaded via xargs; edit -P for parallelism)
bash scripts/ena_download_fastqs.sh

# 3) Fetch hg18 reference and index for bwa & samtools
bash scripts/get_hg18.sh

# 4) Align all runs to hg18 using bwa-aln (backtrack) and sampe; produce per-run BAMs
bash scripts/align_bwa_hg18.sh

# 5) Merge per-run BAMs, mark duplicates
bash scripts/merge_markdup.sh

# 6) Make chr1 BAM + index; estimate coverage on chr1
bash scripts/make_chr1.sh

# 7) Compute downsample fraction for ~40× and create chr1_40x BAM
bash scripts/downsample_chr1_40x.sh

# Outputs end up under ./work/out/
```

## Notes
- **Filtering runs**: we keep `SRR00[2-6]…` runs (the 2008–2009 Bentley-era GA/GAII) and exclude later `SRR029…` and `SRR0349…` blocks.
- **Reference**: UCSC hg18 (Mar 2006). Scripts download per-chromosome fasta to `work/ref/hg18.fa` and create indexes.
- **Performance**: adjust `THREADS` and `-P` parallelism knobs in scripts to fit your machine/cluster.
- **Reproducibility**: MD5s from ENA are checked automatically after each download.

