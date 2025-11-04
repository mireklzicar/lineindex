#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a local micromamba environment with bwa/samtools/htslib etc.
# - No sudo required; installs under ./work/.micromamba
# - Creates the env defined in ../environment.yml as "na18507"

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/.." && pwd)
ENV_YML="$ROOT/environment.yml"
MAMBA_ROOT_PREFIX="$ROOT/work/.micromamba"
MICROMAMBA="$ROOT/micromamba"
ENV_NAME="na18507"

mkdir -p "$MAMBA_ROOT_PREFIX"

if [[ ! -x "$MICROMAMBA" ]]; then
  echo "[BOOT] Downloading micromamba (linux-64)"
  curl -sS -L "https://micromamba.snakepit.net/api/micromamba/linux-64/latest" -o "$ROOT/micromamba.tar.bz2"
  tar -xjf "$ROOT/micromamba.tar.bz2" -C "$ROOT" bin/micromamba
  mv "$ROOT/bin/micromamba" "$MICROMAMBA"
  rm -rf "$ROOT/bin" "$ROOT/micromamba.tar.bz2"
  chmod +x "$MICROMAMBA"
fi

echo "[ENV] Creating/updating env $ENV_NAME under $MAMBA_ROOT_PREFIX"
"$MICROMAMBA" create -y -n "$ENV_NAME" -r "$MAMBA_ROOT_PREFIX" -f "$ENV_YML"

echo "[CHK] Tools in env:"
"$MICROMAMBA" run -n "$ENV_NAME" -r "$MAMBA_ROOT_PREFIX" bash -lc 'command -v bwa; bwa 2>&1 | head -n1 || true; command -v samtools; samtools --version | head -n1; command -v bgzip; command -v tabix; python3 -V'

cat <<EOT

[OK] Env ready.

Use one of the following to run steps:

1) Run the NA18507 pipeline steps (example):
   THREADS=8 \
   "$MICROMAMBA" run -n "$ENV_NAME" -r "$MAMBA_ROOT_PREFIX" make -C "$ROOT" all

2) Run a single script (e.g., build ENA runlist):
   "$MICROMAMBA" run -n "$ENV_NAME" -r "$MAMBA_ROOT_PREFIX" bash "$ROOT/scripts/ena_make_runlist.sh"

3) Run the general Tabix vs LineIndex benchmark:
   "$MICROMAMBA" run -n "$ENV_NAME" -r "$MAMBA_ROOT_PREFIX" bash -lc 'python3 -m pip install -e .; python3 benchmarks/general/run_benchmarks.py'

Environment location: $MAMBA_ROOT_PREFIX
EOT

