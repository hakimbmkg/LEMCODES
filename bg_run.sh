#!/bin/bash

# Nama file log (timestamp otomatis)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="download_$TIMESTAMP.log"

# Jalankan downloader di background
nohup ./run_full.sh > "$LOGFILE" 2>&1 &

# Simpan PID
echo "## Run in BG ##."
echo "PID: $!"
echo "Log: $LOGFILE"
