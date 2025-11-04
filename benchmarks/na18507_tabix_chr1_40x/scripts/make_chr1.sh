#!/usr/bin/env bash
set -euo pipefail

THREADS="${THREADS:-8}"
REF="work/ref/hg18.fa"
IN="work/out/na18507.hg18.markdup.bam"
OUTDIR="work/out"
mkdir -p "$OUTDIR"

if [[ ! -s "$IN" ]]; then
  echo "ERROR: $IN missing. Run merge_markdup.sh" >&2
  exit 1
fi
if [[ ! -s "${REF}.fai" ]]; then
  echo "ERROR: $REF.fai missing. Run get_hg18.sh" >&2
  exit 1
fi

CHR1_LEN=$(awk '$1=="chr1"{print $2}' "${REF}.fai")
echo "[INFO] chr1 length: ${CHR1_LEN}"

# Subset to chr1
CHR1="$OUTDIR/na18507.hg18.chr1.bam"
if [[ ! -s "$CHR1" ]]; then
  echo "[CHR1] Subsetting to chr1"
  samtools view -@ "$THREADS" -b "$IN" chr1 | samtools sort -@ "$THREADS" -o "$CHR1" -
  samtools index "$CHR1"
fi

# Coverage estimate (mean depth) via samtools depth
echo "[COV] Estimating mean depth on chr1 (downsample will refine)"
samtools depth -@ "$THREADS" -r chr1 "$CHR1" | awk '{sum+=$3} END{ if (NR>0) print sum/NR; else print 0}' > "$OUTDIR/chr1.mean_depth.txt"
echo "[OK] Mean depth (approx): $(cat $OUTDIR/chr1.mean_depth.txt)x"
