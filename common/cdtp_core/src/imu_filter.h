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
    float trust = fabsf(an - 9.81f) < 2.0f ? (1.0f - cfg::COMP_ALPHA) : 0.002f;
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
  float theta_ = 0, pitchRate_ = 0, yawRate_ = 0, offset_ = 0;
  bool initialized_ = false;
};

}  // namespace cdtp
