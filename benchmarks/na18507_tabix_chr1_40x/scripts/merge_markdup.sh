#!/usr/bin/env bash
set -euo pipefail

THREADS="${THREADS:-8}"
INDIR="work/aln"
OUTDIR="work/out"
mkdir -p "$OUTDIR"

BAMS=( $(ls "$INDIR"/*.bam 2>/dev/null || true) )
if [[ ${#BAMS[@]} -eq 0 ]]; then
  echo "ERROR: no per-run BAMs in $INDIR. Run align step." >&2
  exit 1
fi

MERGED="$OUTDIR/na18507.hg18.merged.bam"
MARKED="$OUTDIR/na18507.hg18.markdup.bam"

if [[ ! -s "$MERGED" ]]; then
  echo "[MERGE] ${#BAMS[@]} BAMs"
  samtools merge -@ "$THREADS" -o "$MERGED" "${BAMS[@]}"
  samtools index "$MERGED"
fi

if [[ ! -s "$MARKED" ]]; then
  echo "[MARKDUP]"
  # Name-sort -> fixmate -> position-sort -> markdup
  samtools sort -n -@ "$THREADS" -o "$OUTDIR/tmp.namesort.bam" "$MERGED"
  samtools fixmate -@ "$THREADS" -m "$OUTDIR/tmp.namesort.bam" "$OUTDIR/tmp.fixmate.bam"
  samtools sort -@ "$THREADS" -o "$OUTDIR/tmp.possort.bam" "$OUTDIR/tmp.fixmate.bam"
  samtools markdup -@ "$THREADS" "$OUTDIR/tmp.possort.bam" "$MARKED"
  samtools index "$MARKED"
  rm -f "$OUTDIR"/tmp.*.bam
fi

echo "[OK] Marked-dup BAM at $MARKED"
