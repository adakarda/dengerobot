#!/usr/bin/env bash
# Durum gozleyicisi (LQG) karsilastirmasi. Proje kokunden: bash tools/run_gozleyici.sh
# KALMAN=1: egim filtresi Kalman. LQG=1/2: robotun kendi LQR'i da gozleyiciyle kosar. NOMINAL=1: model hatasiz robotlar.
# Gozleyici izgarasi icin once: python tools/lqr_design.py --gozleyici-izgara
set -e
cd "$(dirname "$0")/.."
mkdir -p sim/results build
g++ -std=gnu++14 -O2 -Wall -Wno-unused-variable -DCDTP_TILT_KALMAN="${KALMAN:-0}" -DCDTP_LQG="${LQG:-0}" \
  -Icommon/cdtp_core/src -Isim \
  sim/gozleyici_karsilastir.cpp common/cdtp_core/src/robot_logic.cpp \
  -o build/gozleyici.exe
./build/gozleyici.exe sim/results/
