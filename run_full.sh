#!/bin/bash

# ======================
# KONFIGURASI AWAL
# ======================
MODE="full"           # Pilih: full, station, waveform_only, resume
CLIENT="LOCAL"
NETWORK="AM"
STATIONS="R7D14, R34E2, R799F, RC355, R5F0D, R02C2"
CHANNELS="EHZ,EHN, EHE"
START_DATE="2023-12-01"
END_DATE="2025-06-22"
OUTPUT_DIR="/home/geo3hakim/QF/fdsn_am"
FORCE_NEW=false       # true jika ingin paksa folder baru

MAX_THREADS=$(python3 -c 'import os; print(os.cpu_count())')
if [ -z "$MAX_THREADS" ]; then
  MAX_THREADS=8
fi

# ======================
# EKSEKUSI PROGRAM
# ======================

echo "[INFO] Menjalankan FDSN Downloader dengan mode: $MODE dan thread : $MAX_THREADS Threads"

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

# Tambah argumen berdasarkan MODE
if [ "$FORCE_NEW" = true ]; then
  ARGS+=(--force_new)
fi

case "$MODE" in
  station)
    ARGS+=(--only_station_list)
    ;;
  waveform_only)
    ARGS+=(--only_download)
    ;;
  resume)
    ARGS+=(--resume_failed)
    ;;
  full)
    # tidak perlu tambahan
    ;;
  *)
    echo "[ERROR] MODE tidak dikenal: $MODE"
    exit 1
    ;;
esac

# Jalankan
python3 main.py "${ARGS[@]}"

echo "[INFO] Proses selesai."
