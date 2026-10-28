#pragma once
#include <math.h>

namespace cdtp {

constexpr float PI_F = 3.14159265358979f;
constexpr float DEG = PI_F / 180.0f;

inline float clampf(float x, float lo, float hi) { return x < lo ? lo : (x > hi ? hi : x); }
inline float signf(float x) { return x > 0 ? 1.0f : (x < 0 ? -1.0f : 0.0f); }
inline float wrapPi(float a) {
  while (a > PI_F) a -= 2 * PI_F;
  while (a < -PI_F) a += 2 * PI_F;
  return a;
}

// Tek eksenli trapez hiz profili: 0'dan hedef mesafeye, dur.
class Trapezoid {
 public:
  void start(float dist, float vmax, float amax) {
    dist_ = fabsf(dist);
    dir_ = dist >= 0 ? 1.0f : -1.0f;
    vmax_ = vmax;
    amax_ = amax;
    t_ = 0;
    pos_ = 0;
    vel_ = 0;
    active_ = dist_ > 1e-6f;
    stopping_ = false;
  }
  // Yumusak durdurma: kalan yolu fren mesafesine indir.
  void stopSoft() {
    if (!active_) return;
    float brake = vel_ * vel_ / (2 * amax_);
    dist_ = pos_ + brake;
    stopping_ = true;
  }
  void step(float dt) {
    if (!active_) return;
    float remaining = dist_ - pos_;
    float vBrake = sqrtf(fmaxf(0.0f, 2 * amax_ * remaining));
    float vTarget = fminf(vmax_, vBrake);
    float v0 = vel_;
    if (vel_ < vTarget) vel_ = fminf(vTarget, vel_ + amax_ * dt);
    else vel_ = fmaxf(vTarget, vel_ - amax_ * dt);
    acc_ = (vel_ - v0) / dt;
    pos_ += vel_ * dt;
    if (remaining <= 1e-4f || (vel_ <= 1e-4f && remaining < 2e-3f)) {
      pos_ = dist_;
      vel_ = 0;
      active_ = false;
    }
  }
  bool active() const { return active_; }
  float pos() const { return dir_ * pos_; }
  float vel() const { return dir_ * vel_; }
  float acc() const { return dir_ * acc_; }

 private:
  float dist_ = 0, dir_ = 1, vmax_ = 0, amax_ = 1, t_ = 0, pos_ = 0, vel_ = 0, acc_ = 0;
  bool active_ = false, stopping_ = false;
};

}  // namespace cdtp
