// 3S Li-ion: gerilimden yaklasik doluluk yuzdesi.
#pragma once
#include "core_math.h"

namespace cdtp {

inline float socFromCellV(float v) {
  // dinlenme egrisi (18650, yaklasik)
  static const float V[] = {3.30f, 3.50f, 3.60f, 3.70f, 3.75f, 3.80f, 3.90f, 4.00f, 4.10f, 4.20f};
  static const float S[] = {0, 5, 10, 25, 40, 50, 65, 78, 90, 100};
  if (v <= V[0]) return 0;
  for (int i = 1; i < 10; ++i)
    if (v <= V[i]) return S[i - 1] + (S[i] - S[i - 1]) * (v - V[i - 1]) / (V[i] - V[i - 1]);
  return 100;
}

class BatteryMonitor {
 public:
  void update(float vbat, float dt) {
    if (v_ <= 0) v_ = vbat;
    float a = dt / (TAU + dt);
    v_ += a * (vbat - v_);
  }
  float volts() const { return v_; }
  int percent() const { return (int)(socFromCellV(v_ / 3.0f) + 0.5f); }

 private:
  static constexpr float TAU = 3.0f;  // motor akimindaki dalgalanmayi suzer
  float v_ = 0;
};

}  // namespace cdtp
