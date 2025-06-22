#!/bin/bash

# ======================
# KONFIGURASI
# ======================

CLIENT="LOCAL"
NETWORK="AM"
STATIONS="R7D14, R34E2, R799F, RC355, R5F0D, R02C2"
CHANNELS="EHZ,EHN, EHE"
START_DATE="2025-06-01"
END_DATE="2025-06-05"
OUTPUT_DIR="FDSN_TMP"

# Dapatkan jumlah core secara otomatis via Python (paling aman)
MAX_THREADS=$(python3 -c 'import os; print(os.cpu_count())')
if [ -z "$MAX_THREADS" ]; then
  MAX_THREADS=8
fi

USE_RESUME=true
FORCE_NEW=true

# ======================
# EKSEKUSI
# ======================

echo "[INFO] Menjalankan FDSN Downloader dengan $MAX_THREADS threads..."

ARGS=(
  --client "$CLIENT"
  --network "$NETWORK"
  --station "$STATIONS"
  --channel "$CHANNELS"
  --start "$START_DATE"
  --end "$END_DATE"
  --output_dir "$OUTPUT_DIR"
  --threads "$MAX_THREADS"
)

if [ "$USE_RESUME" = true ]; then
  ARGS+=(--resume_failed)
fi

if [ "$FORCE_NEW" = true ]; then
  ARGS+=(--force_new)
fi

python3 main.py "${ARGS[@]}"

echo "[INFO] File disimpan di: $OUTPUT_DIR"
echo "[INFO] Log tersedia di : $OUTPUT_DIR/log.txt"
echo "[INFO] Daftar file     : $OUTPUT_DIR/fname.csv"
