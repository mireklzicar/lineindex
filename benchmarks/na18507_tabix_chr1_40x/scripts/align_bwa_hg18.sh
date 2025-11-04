#!/usr/bin/env bash
set -euo pipefail

THREADS="${THREADS:-8}"
FASTQDIR="work/fastq"
REF="work/ref/hg18.fa"
OUTDIR="work/aln"
mkdir -p "$OUTDIR"

if [[ ! -s "$REF" ]]; then
  echo "ERROR: Reference $REF missing. Run scripts/get_hg18.sh" >&2
  exit 1
fi

# Find pairs in FASTQDIR like SRRXXXXX_1.fastq.gz / _2.fastq.gz
ls "$FASTQDIR"/*_1.fastq.gz 2>/dev/null | sed 's/_1.fastq.gz//' | while read -r PREFIX; do
  r1="${PREFIX}_1.fastq.gz"
  r2="${PREFIX}_2.fastq.gz"
  base=$(basename "$PREFIX")
  sai1="$OUTDIR/${base}.1.sai"
  sai2="$OUTDIR/${base}.2.sai"
  bam="$OUTDIR/${base}.bam"

  if [[ -s "$bam" ]]; then
     echo "[SKIP] $base bam exists"
     continue
  fi

  echo "[ALN] $base"
  bwa aln -t "$THREADS" "$REF" "$r1" > "$sai1"
  bwa aln -t "$THREADS" "$REF" "$r2" > "$sai2"
  bwa sampe "$REF" "$sai1" "$sai2" "$r1" "$r2" | \
    samtools view -@ "$THREADS" -bS - | \
    samtools sort -@ "$THREADS" -o "$bam" -

  samtools index "$bam"
done

echo "[OK] Per-run BAMs in $OUTDIR"
