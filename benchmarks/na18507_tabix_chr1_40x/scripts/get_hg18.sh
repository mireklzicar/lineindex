#!/usr/bin/env bash
set -euo pipefail
# Download UCSC hg18 per-chromosome FASTA and build a single FASTA + indexes.

REFDIR="work/ref"
mkdir -p "$REFDIR"
pushd "$REFDIR" >/dev/null

BASE="https://hgdownload.soe.ucsc.edu/goldenPath/hg18/chromosomes"
# Grab per-chromosome fasta.gz. Default: chr1..22, X, Y, M.
# Override with CHR_LIST (e.g. CHR_LIST="1" downloads chr1 only).
DEFAULT_CHRS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y M"
CHR_LIST=( ${CHR_LIST:-$DEFAULT_CHRS} )
for chr in "${CHR_LIST[@]}"; do
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
