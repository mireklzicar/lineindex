#!/usr/bin/env bash
set -euo pipefail
# Download UCSC hg18 per-chromosome FASTA and build a single FASTA + indexes.

REFDIR="work/ref"
mkdir -p "$REFDIR"
pushd "$REFDIR" >/dev/null

BASE="https://hgdownload.soe.ucsc.edu/goldenPath/hg18/chromosomes"
# Grab all chrom fasta.gz (chr1..chr22, X, Y, M, *_random if desired)
# For our purposes we at least need chr1, but we align genome-wide then subset.
for chr in {1..22} X Y M; do
  f="chr${chr}.fa.gz"
  url="${BASE}/${f}"
  if [[ ! -s "$f" ]]; then
    echo "[DL] $f"
    curl -sS -L "$url" -o "$f"
  fi
done

# Concatenate to one FASTA
if [[ ! -s hg18.fa ]]; then
  echo "[CAT] Building hg18.fa"
  zcat chr*.fa.gz > hg18.fa
fi

# Build indexes
if [[ ! -s hg18.fa.bwt ]]; then
  echo "[IDX] bwa index (backtrack)"
  bwa index -a bwtsw hg18.fa
fi

if [[ ! -s hg18.fa.fai ]]; then
  echo "[IDX] samtools faidx"
  samtools faidx hg18.fa
fi

popd >/dev/null
echo "[OK] Reference ready at work/ref/hg18.fa"
