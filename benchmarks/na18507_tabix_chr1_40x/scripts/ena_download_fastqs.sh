#!/usr/bin/env bash
set -euo pipefail

THREADS="${THREADS:-4}"
TSV="work/ena_bentley.tsv"
OUTDIR="work/fastq"
mkdir -p "$OUTDIR"

if [[ ! -s "$TSV" ]]; then
  echo "ERROR: $TSV missing. Run scripts/ena_make_runlist.sh first." >&2
  exit 1
fi

# Build a download list (https URLs) and an md5 list side-by-side
awk -F'\t' 'NR>1 {n=split($4,a,";"); m=split($5,b,";"); for(i=1;i<=n;i++){print "https://" a[i] "\t" b[i] }}' "$TSV" > work/fastq_urls_md5.tsv

# Download in parallel
cut -f1 work/fastq_urls_md5.tsv | xargs -P "$THREADS" -n 1 -I {} bash -c '
  url="{}"
  base=$(basename "$url")
  if [[ -s "work/fastq/$base" ]]; then
     echo "[SKIP] $base exists"
  else
     echo "[DL] $base"
     curl -sS -L "$url" -o "work/fastq/$base"
  fi
'

# Verify MD5
echo "[CHK] MD5 verification"
paste <(cut -f2 work/fastq_urls_md5.tsv) <(cut -f1 work/fastq_urls_md5.tsv | awk -F/ "{print \"work/fastq/\"$NF}") | \
  awk '{print $1"  "$2}' > work/fastq.md5
md5sum -c work/fastq.md5
echo "[OK] Downloads verified"
