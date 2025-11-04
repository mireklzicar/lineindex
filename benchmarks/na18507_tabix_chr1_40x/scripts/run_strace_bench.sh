#!/usr/bin/env bash
set -euo pipefail

# Run strace-based benchmarks on NA18507 chr1 alignment:
#   - Tabix on TSV.bgz built from BAM, single process via -R BED (index loaded once)
#   - samtools view on BAM with -L BED (SAM text output)
#   - Collect CPU time (user+sys), bytes read from disk (sum of read/pread64 returns),
#     data output size, and lseek calls per query.

THREADS="${THREADS:-8}"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$ROOT_DIR/work"
OUTDIR="$WORK/strace"
mkdir -p "$OUTDIR"

BAM_IN="${BAM_IN:-$WORK/out/na18507.hg18.chr1.40x.bam}"
[[ -s "$BAM_IN" ]] || BAM_IN="$WORK/out/na18507.hg18.chr1.bam"
if [[ ! -s "$BAM_IN" ]]; then
  echo "ERROR: Cannot find chr1 BAM. Run make_chr1.sh (and downsample if desired)." >&2
  exit 1
fi

TSV_GZ="$WORK/tabix/chr1_align.tsv.gz"
if [[ ! -s "$TSV_GZ" ]]; then
  bash "$ROOT_DIR/scripts/build_tabix_from_bam.sh"
fi

# Prepare a plain TSV for LineIndex (decompress if needed)
TSV_LI="$WORK/tabix/chr1_align.li.tsv"
if [[ ! -s "$TSV_LI" ]]; then
  if [[ -s "$WORK/tabix/chr1_align.tsv" ]]; then
    cp "$WORK/tabix/chr1_align.tsv" "$TSV_LI"
  else
    bgzip -dc "$TSV_GZ" > "$TSV_LI"
  fi
fi
# Prebuild LineIndex (.idx) for the TSV to avoid counting build time later
python3 -m lineindex.cli file "$TSV_LI" >/dev/null 2>&1 || true

FAI="$WORK/ref/hg18.fa.fai"
if [[ ! -s "$FAI" ]]; then
  echo "ERROR: Reference index $FAI missing. Run get_hg18.sh" >&2
  exit 1
fi

# Generate 1000 intervals with widths uniformly from 1..1000 bp
N="${N:-1000}"
MAXW="${MAXW:-1000}"
CHR_LEN=$(awk '$1=="chr1"{print $2}' "$FAI")
BED_ALL="$OUTDIR/regions.bed"
python3 - "$N" "$MAXW" "$CHR_LEN" > "$BED_ALL" << 'PY'
import sys, random
N=int(sys.argv[1]); MAXW=int(sys.argv[2]); L=int(sys.argv[3])
r=random.Random(12345)
for _ in range(N):
    w = r.randint(1, MAXW)
    start = r.randint(1, max(1, L - w + 1))
    end = start + w - 1
    # BED-like 3-column with 1-based inclusive coords acceptable by tabix -R
    print(f"chr1\t{start}\t{end}")
PY
echo "[INFO] Regions: $N, widths=1..$MAXW (saved to $BED_ALL)"

# Create width buckets to study dependence on interval size
BED_SMALL="$OUTDIR/regions_1_10.bed"
BED_MED="$OUTDIR/regions_11_100.bed"
BED_LARGE="$OUTDIR/regions_101_1000.bed"
awk '{w=$3-$2+1; if(w<=10) print $0}' "$BED_ALL" > "$BED_SMALL"
awk '{w=$3-$2+1; if(w>=11 && w<=100) print $0}' "$BED_ALL" > "$BED_MED"
awk '{w=$3-$2+1; if(w>=101) print $0}' "$BED_ALL" > "$BED_LARGE"

# Strace aggregation: summary (-c) following children (-f), quiet (-qq)
TABIX_SUM="$OUTDIR/tabix_summary.txt"
SAMTOOLS_SUM="$OUTDIR/samtools_summary.txt"
TABIX_LOG="$OUTDIR/tabix_syscalls.log"
SAMTOOLS_LOG="$OUTDIR/samtools_syscalls.log"
TABIX_OUT="$OUTDIR/tabix_output.txt"
SAMTOOLS_OUT="$OUTDIR/samtools_output.txt"

time_cpu() {
  # Print user+sys seconds using /usr/bin/time -f "%U %S"
  local cmd="$1"
  local tmp
  tmp=$(mktemp)
  bash -lc "/usr/bin/time -f '%U %S' -o '$tmp' bash -lc \"$cmd\" >/dev/null"
  awk '{sum+=$1+$2} END{printf("%.3f", sum)}' "$tmp"
  rm -f "$tmp"
}

parse_io() {
  python3 "$ROOT_DIR/scripts/parse_strace_io.py" "$1" | awk -v NQ="$2" '
    BEGIN{bytes=0;lseek=0}
    $1=="bytes_read"{bytes=$2}
    $1=="lseek_calls"{lseek=$2}
    END{printf("%.6f\t%.6f\n", bytes/1048576.0, (NQ>0? lseek/NQ: 0))}
  '
}

echo "[STRACE] Tabix (-R, single process, full set)"
strace -f -qq -c -o "$TABIX_SUM" -e trace=read,write,open,openat,close,fstat,lseek,pread64,mmap,munmap \
  bash -lc 'tabix -R '"$BED_ALL"' '"$TSV_GZ"' > '"$TABIX_OUT"''
strace -f -qq -o "$TABIX_LOG" -e trace=lseek,pread64,read \
  bash -lc 'tabix -R '"$BED_ALL"' '"$TSV_GZ"' > /dev/null'

echo "[STRACE] samtools view (-L, SAM text, full set)"
strace -f -qq -c -o "$SAMTOOLS_SUM" -e trace=read,write,open,openat,close,fstat,lseek,pread64,mmap,munmap \
  bash -lc 'samtools view '"$BAM_IN"' -L '"$BED_ALL"' > '"$SAMTOOLS_OUT"''
strace -f -qq -o "$SAMTOOLS_LOG" -e trace=lseek,pread64,read \
  bash -lc 'samtools view '"$BAM_IN"' -L '"$BED_ALL"' > /dev/null'

echo "[STRACE] lineindex region (single process, full set)"
LI_SUM="$OUTDIR/lineindex_summary.txt"
LI_LOG="$OUTDIR/lineindex_syscalls.log"
LI_OUT="$OUTDIR/lineindex_output.txt"

# Prebuild region index to avoid counting build in CPU time
python3 -m lineindex.cli region build --tsv "$TSV_LI" --index-dir "$WORK/tabix/chr1_align.li_index" >/dev/null

strace -f -qq -c -o "$LI_SUM" -e trace=read,write,open,openat,close,fstat,lseek,pread64,mmap,munmap \
  bash -lc 'python3 -m lineindex.cli region query --tsv '"$TSV_LI"' --index-dir '"$WORK/tabix/chr1_align.li_index"' --bed '"$BED_ALL"' --memory-map offsets > '"$LI_OUT"''
strace -f -qq -o "$LI_LOG" -e trace=lseek,pread64,read \
  bash -lc 'python3 -m lineindex.cli region query --tsv '"$TSV_LI"' --index-dir '"$WORK/tabix/chr1_align.li_index"' --bed '"$BED_ALL"' --memory-map offsets > /dev/null'

echo "[OK] Summaries:"
echo " - $TABIX_SUM"
echo " - $SAMTOOLS_SUM"
echo "[OK] Detailed syscall logs:"
echo " - $TABIX_LOG"
echo " - $SAMTOOLS_LOG"

# Derived metrics and CPU time
NQ=$(wc -l < "$BED_ALL")
TABIX_CPU=$(time_cpu "tabix -R '$BED_ALL' '$TSV_GZ' > /dev/null")
SAMTOOLS_CPU=$(time_cpu "samtools view '$BAM_IN' -L '$BED_ALL' > /dev/null")
LI_CPU=$(time_cpu "python3 -m lineindex.cli region query --tsv '$TSV_LI' --index-dir '$WORK/tabix/chr1_align.li_index' --bed '$BED_ALL' --memory-map offsets > /dev/null")
read TABIX_MB TABIX_SEEKPQ < <(parse_io "$TABIX_LOG" "$NQ")
read SAMTOOLS_MB SAMTOOLS_SEEKPQ < <(parse_io "$SAMTOOLS_LOG" "$NQ")
read LI_MB LI_SEEKPQ < <(parse_io "$LI_LOG" "$NQ")
TABIX_TXT_MB=$(wc -c < "$TABIX_OUT" | awk '{printf("%.6f", $1/1048576)}')
SAM_TXT_MB=$(wc -c < "$SAMTOOLS_OUT" | awk '{printf("%.6f", $1/1048576)}')
LI_TXT_MB=$(wc -c < "$LI_OUT" | awk '{printf("%.6f", $1/1048576)}')

{
  echo -e "tool\tcpu_s\tmb_read\tmb_output\tlseek_per_query\tqueries"
  echo -e "tabix\t$TABIX_CPU\t$TABIX_MB\t$TABIX_TXT_MB\t$TABIX_SEEKPQ\t$NQ"
  echo -e "samtools\t$SAMTOOLS_CPU\t$SAMTOOLS_MB\t$SAM_TXT_MB\t$SAMTOOLS_SEEKPQ\t$NQ"
  echo -e "lineindex\t$LI_CPU\t$LI_MB\t$LI_TXT_MB\t$LI_SEEKPQ\t$NQ"
} > "$OUTDIR/metrics.tsv"

# Bucketed timings by interval width
bucket_run() {
  local bed=$1; local label=$2
  local nq=$(wc -l < "$bed")
  local tlog="$OUTDIR/${label}_tabix.log"
  local slog="$OUTDIR/${label}_samtools.log"
  local tout="$OUTDIR/${label}_tabix.out"
  local sout="$OUTDIR/${label}_samtools.out"
  local tcpu scpu tmb smb tseek sseek
  tcpu=$(time_cpu "tabix -R '$bed' '$TSV_GZ' > '$tout'")
  strace -f -qq -o "$tlog" -e trace=lseek,pread64,read bash -lc 'tabix -R '"$bed"' '"$TSV_GZ"' > /dev/null'
  scpu=$(time_cpu "samtools view '$BAM_IN' -L '$bed' > '$sout'")
  strace -f -qq -o "$slog" -e trace=lseek,pread64,read bash -lc 'samtools view '"$BAM_IN"' -L '"$bed"' > /dev/null'
  lcpu=$(time_cpu "python3 -m lineindex.cli region query --tsv '$TSV_LI' --index-dir '$WORK/tabix/chr1_align.li_index' --bed '$bed' --memory-map offsets > '$tout'.li")
  strace -f -qq -o "$tlog.li" -e trace=lseek,pread64,read bash -lc 'python3 -m lineindex.cli region query --tsv '"$TSV_LI"' --index-dir '"$WORK/tabix/chr1_align.li_index"' --bed '"$bed"' --memory-map offsets > /dev/null'
  read tmb tseek < <(parse_io "$tlog" "$nq")
  read smb sseek < <(parse_io "$slog" "$nq")
  read lmb lseekpq < <(parse_io "$tlog.li" "$nq")
  local tsize=$(wc -c < "$tout" | awk '{printf("%.6f", $1/1048576)}')
  local ssize=$(wc -c < "$sout" | awk '{printf("%.6f", $1/1048576)}')
  local lsize=$(wc -c < "$tout.li" | awk '{printf("%.6f", $1/1048576)}')
  echo -e "$label\t$nq\t$tcpu\t$tmb\t$tsize\t$tseek\t$scpu\t$smb\t$ssize\t$sseek\t$lcpu\t$lmb\t$lsize\t$lseekpq" >> "$OUTDIR/buckets.tsv"
}

echo -e "bucket\tqueries\ttabix_cpu_s\ttabix_mb_read\ttabix_mb_output\ttabix_lseek_per_q\tsamtools_cpu_s\tsamtools_mb_read\tsamtools_mb_output\tsamtools_lseek_per_q\tlineindex_cpu_s\tlineindex_mb_read\tlineindex_mb_output\tlineindex_lseek_per_q" > "$OUTDIR/buckets.tsv"
bucket_run "$BED_SMALL" "w1_10"
bucket_run "$BED_MED"   "w11_100"
bucket_run "$BED_LARGE" "w101_1000"

echo "[OK] Metrics: $OUTDIR/metrics.tsv and $OUTDIR/buckets.tsv"
