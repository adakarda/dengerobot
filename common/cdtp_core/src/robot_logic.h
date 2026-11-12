// Robotun tum karar mantigi: mod makinesi, denge (LQR), hareket, yanasma.
// Donanimdan bagimsizdir: firmware her 5 ms'de bir step() cagirir, simulasyon da ayni sinifi kullanir.
#pragma once
#include <stdint.h>
#include "battery.h"
#include "cdtp_config.h"
#include "core_math.h"
#include "dock_fsm.h"
#include "imu_filter.h"
#include "ir_frame.h"
#include "protocol.h"
#include "state_observer.h"

namespace cdtp {

enum class Mode : uint8_t { STANDBY, BALANCE, DOCK, CHARGING, FALLEN };
enum class Task : uint8_t { STATIC = 0, GUIDANCE = 1, CHARGING = 2, INTEGRATED = 3 };
enum class GloveMode : uint8_t { STEP = 0, CONTINUOUS = 1 };
enum class MotionState : uint8_t { STATIC, MOVING, TURNING, RECOVERY };

const char* modeName(Mode m);
const char* taskName(Task t);
const char* motionName(MotionState m);

struct RobotInputs {
  float t = 0;               // s
  ImuSample imu{};           // ham eksen, gyro bias cikarilmis
  int32_t encL = 0, encR = 0;  // kumulatif sayim (ham)
  float vbat = 11.1f;        // V
  float vcharge = 0;         // plaka gerilimi, V
  int32_t irL = 0, irR = 0;  // IR dusen kenar sayaclari (kumulatif)
  bool motorPower = true;    // acil stop sonrasi 12 V var mi (olculmuyorsa hep true)
  bool gloveNew = false;     // bu adimda yeni paket geldi mi
  GlovePacket glove{};
};

struct RobotOutputs {
  bool motorEnable = false;
  float dutyL = 0, dutyR = 0;  // -1..1, + = ileri (yon cevirme dahil edilmis)
};

class RobotLogic {
 public:
  RobotLogic();
  void setAxisMap(const AxisMap& m) { axes_ = m; }
  void setPitchOffset(float rad) { tilt_.setOffset(rad); }
  void setTask(Task t) { task_ = t; }
  void setGloveMode(GloveMode m) { gloveMode_ = m; }

  RobotOutputs step(const RobotInputs& in);

  // Telemetri / izleme
  Mode mode() const { return mode_; }
  Task task() const { return task_; }
  MotionState motion() const { return motion_; }
  const char* direction() const { return dir_; }
  DockState dockState() const { return dock_.state(); }
  float thetaDeg() const { return tilt_.theta() / DEG; }
  float trimDeg() const { return thTrim_ / DEG; }
  float x() const { return x_; }
  float v() const { return v_; }
  float vDiff() const { return vDiff_; }
  float thetaRawRad() const { return tilt_.thetaRaw(); }
  float thetaRad() const { return tilt_.theta(); }
  float pitchRateRad() const { return tilt_.pitchRate(); }
  float uLast() const { return uLast_; }
  float psiDeg() const { return psi_ / DEG; }
  bool charging() const { return charging_; }
  int batteryPct() const { return bat_.percent(); }
  float batteryV() const { return bat_.volts(); }
  int irNL() const { return irL_.n(); }
  int irNR() const { return irR_.n(); }
  Cmd lastGloveCmd() const { return gloveCmd_; }
  bool gloveAlive() const { return gloveAlive_; }
  int telemetryJson(char* buf, int len, uint32_t seq) const;
  // Takim protokolu (shared/protocol/messages.md): WebSocket telemetri cercevesi
  int telemetryJsonWs(char* buf, int len, uint32_t seq) const;

 private:
  void enterBalance();
  void handleGlove(const RobotInputs& in);
  void startStep(Cmd c);
  bool dockAllowed() const;
  RobotOutputs balanceControl(float vbat, float leanRad);
  void updateMotionState();

  AxisMap axes_;
  TiltEstimator tilt_;
  BatteryMonitor bat_;
  IrFrameCounter irL_, irR_;
  DockFsm dock_;

  Mode mode_ = Mode::STANDBY;
  Task task_ = Task::INTEGRATED;
  GloveMode gloveMode_ = GloveMode::STEP;
  MotionState motion_ = MotionState::STATIC;
  const char* dir_ = "-";

  float t_ = 0, modeT_ = 0, armT_ = 0, fallT_ = 0;
  // olcumler
  int32_t encL0_ = 0, encR0_ = 0;
  bool encInit_ = false;
  float x_ = 0, v_ = 0, psi_ = 0;
  float xHist_[4] = {0, 0, 0, 0};
  int histIdx_ = 0;
  // durum gozleyicisi (CDTP_LQG=1): v, theta, omega LQR'a buradan gider
  StateObserver obs_;
  float vDiff_ = 0;            // enkoder farkindan hiz (gozleyicisiz yol)
  float uLast_ = 0;            // son adimda motorlara verilen ortak gerilim (V)
  float thCtl_ = 0, omCtl_ = 0;  // LQR'in kullandigi egim ve egim hizi
  // referanslar
  float xRaw_ = 0, vRaw_ = 0;  // bicimlendirme oncesi referans
  float thTrim_ = 0;           // ogrenilen denge acisi (rad); acilista sifir, cal komutu kalici ofseti verir
  float xRef_ = 0, vRef_ = 0, aRef_ = 0, psiRef_ = 0, rRef_ = 0;
  float xStart_ = 0, psiStart_ = 0;
  Trapezoid lin_, rot_;
  bool linActive_ = false, rotActive_ = false;
  float vCmd_ = 0, rCmd_ = 0;  // hiz modu hedefleri (surekli mod / yanasma)
  // eldiven
  Cmd gloveCmd_ = Cmd::STOP, prevGloveCmd_ = Cmd::STOP;
  float gloveLastT_ = -10, gloveIdleT_ = 0;
  bool gloveAlive_ = false;
  bool pendingBack_ = false;
  // yanasma tetik
  float beaconT_ = 0;
  float undockHoldT_ = 0;  // eldivenle ayrildiktan sonra otomatik yanasma beklemesi
  bool charging_ = false;
  float chargeLostT_ = 0;
};

}  // namespace cdtp
