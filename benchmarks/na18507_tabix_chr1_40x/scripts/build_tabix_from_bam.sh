#!/usr/bin/env bash
set -euo pipefail

# Convert a chr1 BAM to a Tabix-indexable TSV and index it.
# Columns: chrom  start  end  qname

THREADS="${THREADS:-8}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="$ROOT_DIR/work"

REF_FA="$ROOT_DIR/work/ref/hg18.fa"
BAM_IN="${BAM_IN:-$ROOT_DIR/work/out/na18507.hg18.chr1.40x.bam}"
if [[ ! -s "$BAM_IN" ]]; then
  # Fallback if 40x downsample not created yet
  BAM_IN="$ROOT_DIR/work/out/na18507.hg18.chr1.bam"
fi

if [[ ! -s "$BAM_IN" ]]; then
  echo "ERROR: BAM not found: $BAM_IN" >&2
  exit 1
fi

TABIX_DIR="$OUTDIR/tabix"
mkdir -p "$TABIX_DIR"
TSV="$TABIX_DIR/chr1_align.tsv"
GZ="$TSV.gz"

echo "[TSV] Emitting alignment intervals -> $TSV"
# NOTE: This uses SEQ length to approximate end coordinate. For perfect end positions, parse the CIGAR.
samtools view "$BAM_IN" \
  | awk 'BEGIN{OFS="\t"} $3!~/^\*/ {len=length($10); if (len<1) len=1; start=$4; end=$4+len-1; print $3, start, end, $1}' > "$TSV"

echo "[BGZIP] Compressing"
bgzip -@ "$THREADS" -f "$TSV"

echo "[TBI] Indexing"
tabix -f -s 1 -b 2 -e 3 "$GZ"

echo "[OK] Tabix files at $GZ and ${GZ}.tbi"

