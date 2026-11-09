#!/usr/bin/env bash
# Egim filtresi karsilastirmasi (tumleyen vs Kalman). Proje kokunden: bash tools/run_filtre.sh
# KALMAN=1 verilirse robotun kendi kapali dongusu de Kalman ile kosar.
set -e
cd "$(dirname "$0")/.."
mkdir -p sim/results build
g++ -std=gnu++14 -O2 -Wall -Wno-unused-variable -DCDTP_TILT_KALMAN="${KALMAN:-0}" \
  -Icommon/cdtp_core/src -Isim \
  sim/filtre_karsilastir.cpp common/cdtp_core/src/robot_logic.cpp \
  -o build/filtre.exe
./build/filtre.exe sim/results/
