#!/usr/bin/env bash
set -euo pipefail
# Fetch ENA filereport for NA18507 study and filter to Bentley-era runs.
# Produces: work/ena_all.tsv and work/ena_bentley.tsv

mkdir -p work
URL="https://www.ebi.ac.uk/ena/portal/api/filereport"
# SRP000239 is the SRA study for SRA000271 (NA18507 Bentley 2008)
FIELDS="run_accession,first_public,library_layout,fastq_ftp,fastq_md5,fastq_bytes,sample_alias"
curl -sS "${URL}?accession=SRP000239&result=read_run&fields=${FIELDS}&download=true" > work/ena_all.tsv

# Keep header + SRR00[2-6]… (exclude SRR029…, SRR0349… etc.)
awk -F'\t' 'NR==1 || $1 ~ /^SRR00[2-6]/ {print $0}' work/ena_all.tsv > work/ena_bentley.tsv

echo "[OK] Wrote work/ena_bentley.tsv"
