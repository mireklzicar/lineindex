#!/usr/bin/env bash
set -euo pipefail

THREADS="${THREADS:-8}"
OUTDIR="work/out"
CHR1="$OUTDIR/na18507.hg18.chr1.bam"

if [[ ! -s "$CHR1" ]]; then
  echo "ERROR: $CHR1 missing. Run make_chr1.sh" >&2
  exit 1
fi

CURR=$(cat "$OUTDIR/chr1.mean_depth.txt")
TARGET="${TARGET:-40}"

python3 scripts/compute_subsample_fraction.py "$CURR" "$TARGET" > "$OUTDIR/subsample_fraction.txt"
F=$(cat "$OUTDIR/subsample_fraction.txt")

if awk "BEGIN{exit !($F<=0)}"; then
  echo "ERROR: invalid subsample fraction $F (current depth <= 0?)" >&2
  exit 1
fi

echo "[DS] Downsampling to ~${TARGET}x on chr1 with samtools view -s ${F}"
samtools view -@ "$THREADS" -bs "$F" "$CHR1" | samtools sort -@ "$THREADS" -o "$OUTDIR/na18507.hg18.chr1.${TARGET}x.bam" -
samtools index "$OUTDIR/na18507.hg18.chr1.${TARGET}x.bam"

# Recompute depth
samtools depth -@ "$THREADS" -r chr1 "$OUTDIR/na18507.hg18.chr1.${TARGET}x.bam" | \
  awk '{sum+=$3} END{ if (NR>0) print sum/NR; else print 0}' > "$OUTDIR/chr1.${TARGET}x.mean_depth.txt"

echo "[OK] chr1 ~${TARGET}x at $OUTDIR/na18507.hg18.chr1.${TARGET}x.bam (mean=$(cat $OUTDIR/chr1.${TARGET}x.mean_depth.txt)x)"
