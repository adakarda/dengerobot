// Duragan Kalman gozleyicisi: durum s = [x, v, theta, omega, d], LQG'nin kestirim yarisi.
// d: girise eklenen yavas bozucu gerilim (V); nominal modelde olmayan kutu, surtunme ve kutle hatasini toplar.
// Model ve kazanc tools/lqr_design.py'den (gains.h: AD, BD, OBS_L). Ayrilma ilkesi: LQR K degismez.
//   tahmin:   s- = AD s + BD u        (u: bir onceki adimda motorlara verilen ortak gerilim, V)
//   duzeltme: s  = s- + L (z - C s-)  z = [x enkoder, theta egim filtresi, omega jiro], C ilgili satirlari secer
// L sabit oldugu icin her adim yalniz 5x5 + 5x3 carpim; kovaryans tasinmaz.
#pragma once
#include "gains.h"

namespace cdtp {

class StateObserver {
 public:
  static constexpr int N = 5;
  using Gain = float[N][3];

  StateObserver() : L_(gains::OBS_L) {}
  explicit StateObserver(const Gain& L) : L_(L) {}

  void reset(float x, float v, float th, float om) {
    s_[0] = x;
    s_[1] = v;
    s_[2] = th;
    s_[3] = om;
    s_[4] = 0;
  }

  void update(float u, float xMeas, float thMeas, float omMeas) {
    float p[N];
    for (int i = 0; i < N; ++i) {
      p[i] = gains::BD[0][i] * u;
      for (int j = 0; j < N; ++j) p[i] += gains::AD[i][j] * s_[j];
    }
    const float e[3] = {xMeas - p[0], thMeas - p[2], omMeas - p[3]};
    for (int i = 0; i < N; ++i) s_[i] = p[i] + L_[i][0] * e[0] + L_[i][1] * e[1] + L_[i][2] * e[2];
  }

  float x() const { return s_[0]; }
  float v() const { return s_[1]; }
  float theta() const { return s_[2]; }
  float omega() const { return s_[3]; }
  float disturbance() const { return s_[4]; }

 private:
  const Gain& L_;
  float s_[N] = {0, 0, 0, 0, 0};
};

}  // namespace cdtp
