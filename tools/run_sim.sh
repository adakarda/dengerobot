#!/usr/bin/env bash
# Simulasyonu derler ve tum testleri kosar. Proje kokunden calistirin: bash tools/run_sim.sh
# KALMAN=1 bash tools/run_sim.sh: egim filtresi olarak Kalman (imu_filter.h TiltKalman)
set -e
cd "$(dirname "$0")/.."
mkdir -p sim/results build
g++ -std=gnu++14 -O2 -Wall -Wno-unused-variable -DCDTP_TILT_KALMAN="${KALMAN:-0}" \
  -Icommon/cdtp_core/src -Isim \
  sim/sim_main.cpp common/cdtp_core/src/robot_logic.cpp \
  -o build/sim.exe
./build/sim.exe sim/results/
