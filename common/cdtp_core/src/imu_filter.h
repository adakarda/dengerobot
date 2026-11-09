// MPU6050 eksen eslemesi + tumleyen filtre.
#pragma once
#include "cdtp_config.h"
#include "core_math.h"

namespace cdtp {

// Ham IMU eksenlerini robot eksenlerine esleme. idx: 0=X 1=Y 2=Z, sign: +1/-1.
// Robot ekseni: ileri (on), yukari (govde boyunca), yunuslama hizi (one egilme +), sapma hizi (sola donus +).
// Varsayilan: MPU6050 X ileri, Z yukari (Y sola). Bu montajda one dusus jiroskop Y'de POZITIF okunur
// (sag el kurali; MuJoCo dijital ikiziyle dogrulandi).
struct AxisMap {
  int fwdIdx = 0;   int fwdSign = 1;
  int upIdx = 2;    int upSign = 1;
  int pitchIdx = 1; int pitchSign = 1;
  int yawIdx = 2;   int yawSign = 1;
};

struct ImuSample {
  float acc[3];   // m/s^2 (ham eksen)
  float gyro[3];  // rad/s (ham eksen, bias cikarilmis)
};

class TiltFilter {
 public:
  TiltFilter() = default;
  explicit TiltFilter(float alpha) : alpha_(alpha) {}
  void setOffset(float offsetRad) { offset_ = offsetRad; }
  float offset() const { return offset_; }

  void reset(const ImuSample& s, const AxisMap& m) {
    theta_ = accAngle(s, m);
    initialized_ = true;
  }

  // Donus: govde egimi (rad), one egik +.
  void update(const ImuSample& s, const AxisMap& m, float dt) {
    pitchRate_ = m.pitchSign * s.gyro[m.pitchIdx];
    yawRate_ = m.yawSign * s.gyro[m.yawIdx];
    float thAcc = accAngle(s, m);
    if (!initialized_) {
      theta_ = thAcc;
      initialized_ = true;
    }
    // ivme olcer, hizlanma sirasinda yanilir; buyuklugu 1 g'den cok sapinca ona daha az guven
    float an = sqrtf(s.acc[0] * s.acc[0] + s.acc[1] * s.acc[1] + s.acc[2] * s.acc[2]);
    float trust = fabsf(an - 9.81f) < 2.0f ? (1.0f - alpha_) : 0.002f;
    theta_ = (1.0f - trust) * (theta_ + pitchRate_ * dt) + trust * thAcc;
  }

  float theta() const { return theta_ - offset_; }
  float thetaRaw() const { return theta_; }
  float pitchRate() const { return pitchRate_; }
  float yawRate() const { return yawRate_; }

 private:
  static float accAngle(const ImuSample& s, const AxisMap& m) {
    float fwd = m.fwdSign * s.acc[m.fwdIdx];
    float up = m.upSign * s.acc[m.upIdx];
    // one egilince yercekiminin govde-ileri bileseni negatif okunur
    return atan2f(-fwd, up);
  }
  float alpha_ = cfg::COMP_ALPHA;
  float theta_ = 0, pitchRate_ = 0, yawRate_ = 0, offset_ = 0;
  bool initialized_ = false;
};

// Ayni arayuz, Kalman: durum [theta, b] (b: kalan jiroskop bias'i, rad/s). Lauszus 2012 (TKJ) yapisi.
// Tahmin: theta += (omega - b) dt. Olcum: ivmeden aci. Ivme 1 g'den sapinca R buyur (tumleyen filtredeki guven
// azaltmanin ayni fikri). pitchRate() bias cikarilmis hizi verir; LQR'in omega girdisi de duzelir.
struct KalmanTuning {
  float qTheta = cfg::KF_Q_THETA;  // rad^2/s, aci sureci gurultusu
  float qBias = cfg::KF_Q_BIAS;    // (rad/s)^2/s, bias rastgele yuruyusu
  float rAcc = cfg::KF_R_ACC;      // rad^2, ivme acisi olcum gurultusu
  float rAccBad = cfg::KF_R_ACC_BAD;  // ivme 1 g'den 2 m/s^2'den fazla saparken
  float p0Bias = cfg::KF_P0_BIAS;  // (rad/s)^2, baslangic bias belirsizligi
};

class TiltKalman {
 public:
  TiltKalman() = default;
  explicit TiltKalman(const KalmanTuning& t) : k_(t) {}
  void setOffset(float offsetRad) { offset_ = offsetRad; }
  float offset() const { return offset_; }

  void reset(const ImuSample& s, const AxisMap& m) {
    theta_ = accAngle(s, m);
    b_ = 0;
    p00_ = k_.rAcc;
    p01_ = 0;
    p11_ = k_.p0Bias;
    initialized_ = true;
  }

  void update(const ImuSample& s, const AxisMap& m, float dt) {
    const float rate = m.pitchSign * s.gyro[m.pitchIdx];
    yawRate_ = m.yawSign * s.gyro[m.yawIdx];
    if (!initialized_) reset(s, m);
    // tahmin: F = [[1, -dt], [0, 1]]
    theta_ += (rate - b_) * dt;
    p00_ += dt * (dt * p11_ - 2 * p01_) + k_.qTheta * dt;
    p01_ -= dt * p11_;
    p11_ += k_.qBias * dt;
    // duzeltme: H = [1, 0]
    float an = sqrtf(s.acc[0] * s.acc[0] + s.acc[1] * s.acc[1] + s.acc[2] * s.acc[2]);
    float r = fabsf(an - 9.81f) < 2.0f ? k_.rAcc : k_.rAccBad;
    float y = accAngle(s, m) - theta_;
    float S = p00_ + r;
    float k0 = p00_ / S, k1 = p01_ / S;
    theta_ += k0 * y;
    b_ += k1 * y;
    float p00 = p00_, p01 = p01_;
    p00_ -= k0 * p00;
    p01_ -= k0 * p01;
    p11_ -= k1 * p01;
    pitchRate_ = rate - b_;
  }

  float theta() const { return theta_ - offset_; }
  float thetaRaw() const { return theta_; }
  float pitchRate() const { return pitchRate_; }
  float yawRate() const { return yawRate_; }
  float bias() const { return b_; }
  float sigmaTheta() const { return sqrtf(p00_ > 0 ? p00_ : 0); }

 private:
  static float accAngle(const ImuSample& s, const AxisMap& m) {
    return atan2f(-m.fwdSign * s.acc[m.fwdIdx], m.upSign * s.acc[m.upIdx]);
  }
  KalmanTuning k_;
  float theta_ = 0, b_ = 0, pitchRate_ = 0, yawRate_ = 0, offset_ = 0;
  float p00_ = 0, p01_ = 0, p11_ = 0;
  bool initialized_ = false;
};

#if CDTP_TILT_KALMAN
using TiltEstimator = TiltKalman;
#else
using TiltEstimator = TiltFilter;
#endif

}  // namespace cdtp
