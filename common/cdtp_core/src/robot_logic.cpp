#include "robot_logic.h"

#include <stdio.h>

#include "gains.h"

namespace cdtp {

const char* modeName(Mode m) {
  switch (m) {
    case Mode::STANDBY: return "BEKLE";
    case Mode::BALANCE: return "DENGE";
    case Mode::DOCK: return "YANASMA";
    case Mode::CHARGING: return "SARJ";
    case Mode::FALLEN: return "DUSTU";
  }
  return "?";
}
const char* taskName(Task t) {
  switch (t) {
    case Task::STATIC: return "statik";
    case Task::GUIDANCE: return "yonlendirme";
    case Task::CHARGING: return "sarj";
    case Task::INTEGRATED: return "butunlesik";
  }
  return "?";
}
const char* motionName(MotionState m) {
  switch (m) {
    case MotionState::STATIC: return "statik";
    case MotionState::MOVING: return "ilerliyor";
    case MotionState::TURNING: return "donuyor";
    case MotionState::RECOVERY: return "toparlaniyor";
  }
  return "?";
}

RobotLogic::RobotLogic() { tilt_.setOffset(cfg::PITCH_OFFSET_DEG_DEFAULT * DEG); }

void RobotLogic::enterBalance() {
  mode_ = Mode::BALANCE;
  modeT_ = 0;
  xRef_ = xRaw_ = x_;
  vRef_ = aRef_ = vRaw_ = 0;
  psiRef_ = psi_;
  rRef_ = 0;
  linActive_ = rotActive_ = false;
  vCmd_ = rCmd_ = 0;
  dock_.abort();
  armT_ = beaconT_ = 0;
}

bool RobotLogic::dockAllowed() const { return task_ == Task::CHARGING || task_ == Task::INTEGRATED; }

void RobotLogic::startStep(Cmd c) {
  if (c == Cmd::FWD || c == Cmd::BACK) {
    xStart_ = xRaw_;
    lin_.start(c == Cmd::FWD ? cfg::STEP_DIST_M : -cfg::STEP_DIST_M, cfg::STEP_VMAX, cfg::STEP_ACCEL);
    linActive_ = true;
  } else if (c == Cmd::LEFT || c == Cmd::RIGHT) {
    psiStart_ = psiRef_;
    float a = cfg::TURN_ANGLE_DEG * DEG;
    rot_.start(c == Cmd::LEFT ? a : -a, cfg::TURN_RATE_DEG * DEG, cfg::TURN_ACCEL_DEG * DEG);
    rotActive_ = true;
  }
}

void RobotLogic::handleGlove(const RobotInputs& in) {
  const float dt = cfg::DT;
  Cmd cmd = gloveCmd_;
  if (in.gloveNew) {
    gloveLastT_ = in.t;
    cmd = (Cmd)in.glove.cmd;
  }
  const bool wasAlive = gloveAlive_;
  gloveAlive_ = (in.t - gloveLastT_) < cfg::GLOVE_TIMEOUT_S;
  if (!gloveAlive_) cmd = Cmd::STOP;
  const bool edge = cmd != prevGloveCmd_;
  prevGloveCmd_ = cmd;
  gloveCmd_ = cmd;
  const bool motionCmd = cmd == Cmd::FWD || cmd == Cmd::BACK || cmd == Cmd::LEFT || cmd == Cmd::RIGHT;
  gloveIdleT_ = motionCmd ? 0 : gloveIdleT_ + dt;

  if (mode_ == Mode::CHARGING) {
    // istasyondan eldivenle ayrilma: "geri" komutu
    if (edge && cmd == Cmd::BACK) {
      enterBalance();
      pendingBack_ = true;
      undockHoldT_ = cfg::UNDOCK_HOLD_S;  // kullanici ayirdi: hemen geri yanasma
    }
    return;
  }
  if (mode_ != Mode::BALANCE || task_ == Task::STATIC) return;

  if (gloveMode_ == GloveMode::CONTINUOUS) {
    vCmd_ = cmd == Cmd::FWD ? cfg::CONT_V : (cmd == Cmd::BACK ? -cfg::CONT_V : 0.0f);
    rCmd_ = cmd == Cmd::LEFT ? cfg::CONT_YAW_DEG * DEG : (cmd == Cmd::RIGHT ? -cfg::CONT_YAW_DEG * DEG : 0.0f);
    return;
  }
  // Adim modu: her hareket jesti bir adim (0,5 m ya da 90 deg). Notr el ("dur") adimi kesmez, robot adimi bitirip durur.
  // Adim surerken farkli bir hareket jesti ya da baglanti kopmasi adimi yumusakca keser.
  if (wasAlive && !gloveAlive_ && (linActive_ || rotActive_)) {
    lin_.stopSoft();
    rot_.stopSoft();
  }
  if (edge && motionCmd) {
    if (linActive_ || rotActive_) {
      lin_.stopSoft();
      rot_.stopSoft();
    } else {
      startStep(cmd);
    }
  }
}

RobotOutputs RobotLogic::balanceControl(float vbat, float leanRad) {
  using namespace gains;
  const float r = cfg::WHEEL_RADIUS_M;
  const float thRef = cfg::TH_FF_GAIN * TH_PER_ACC * aRef_ + leanRad;
  const float ex = clampf(x_ - xRef_, -0.25f, 0.25f);
  // Denge noktasi ogrenme: kutle merkezi eksenin tam ustunde degilse robot egik dengede durur ve LQR bunu
  // kalici konum hatasiyla karsilar (dururken yavas kayma). Robot yerinde dururken egim hedefi yavasca
  // bu hatayi sifirlayacak yone kaydirilir. Hareket, donus ve yanasmada donmus kalir.
  const bool still = !linActive_ && !rotActive_ && fabsf(vRef_) < 0.01f && fabsf(rRef_) < 0.05f && mode_ == Mode::BALANCE;
  if (still) thTrim_ = clampf(thTrim_ - cfg::TRIM_RATE * ex * cfg::DT, -cfg::TRIM_MAX_DEG * DEG, cfg::TRIM_MAX_DEG * DEG);
  float u = -(K_X * ex + K_V * (v_ - vRef_) + K_TH * (thCtl_ - thRef - thTrim_) + K_OM * omCtl_);
  u += cfg::MOTOR_KE * vRef_ / r;  // zit-EMK on-beslemesi
  float ud = YAW_KP * wrapPi(psiRef_ - psi_) + YAW_KD * (rRef_ - tilt_.yawRate());
  ud += cfg::MOTOR_KE * (rRef_ * cfg::TRACK_WIDTH_M * 0.5f) / r;

  vbat = fmaxf(vbat, 9.0f);
  const float vmax = cfg::DUTY_MAX * vbat;
  u = clampf(u, -vmax, vmax);
  uLast_ = u;  // gozleyicinin bir sonraki adimdaki girdisi
  const float udMax = fmaxf(0.0f, vmax - fabsf(u));  // denge onceliklidir, donus payi kalandan
  ud = clampf(ud, -udMax, udMax);

  float vl = u - ud, vr = u + ud;
  // olu bolge telafisi (yumusak)
  vl += cfg::MOTOR_DEADBAND_V * clampf(vl / 0.3f, -1, 1);
  vr += cfg::MOTOR_DEADBAND_V * clampf(vr / 0.3f, -1, 1);

  RobotOutputs o;
  o.motorEnable = true;
  o.dutyL = clampf(vl / vbat, -cfg::DUTY_MAX, cfg::DUTY_MAX);
  o.dutyR = clampf(vr / vbat, -cfg::DUTY_MAX, cfg::DUTY_MAX);
  if (cfg::MOTOR_LEFT_INVERT) o.dutyL = -o.dutyL;
  if (cfg::MOTOR_RIGHT_INVERT) o.dutyR = -o.dutyR;
  return o;
}

void RobotLogic::updateMotionState() {
  const float th = fabsf(tilt_.theta()), om = fabsf(tilt_.pitchRate());
  if (mode_ != Mode::BALANCE && mode_ != Mode::DOCK) {
    motion_ = MotionState::STATIC;
    dir_ = "-";
    return;
  }
  if (th > 5 * DEG || om > 40 * DEG) motion_ = MotionState::RECOVERY;
  else if (rotActive_ || fabsf(rRef_) > 0.1f) motion_ = MotionState::TURNING;
  else if (linActive_ || fabsf(vRef_) > 0.02f) motion_ = MotionState::MOVING;
  else motion_ = MotionState::STATIC;
  if (motion_ == MotionState::TURNING) dir_ = rRef_ > 0 ? "sol" : "sag";
  else if (motion_ == MotionState::MOVING) dir_ = vRef_ > 0 ? "ileri" : "geri";
  else dir_ = "-";
}

RobotOutputs RobotLogic::step(const RobotInputs& in) {
  const float dt = cfg::DT;
  t_ = in.t;
  modeT_ += dt;

  tilt_.update(in.imu, axes_, dt);
  bat_.update(in.vbat, dt);
  irL_.sample(in.irL, in.t);
  irR_.sample(in.irR, in.t);
  charging_ = in.vcharge > cfg::CHARGE_DETECT_V;

  if (!encInit_) {
    encL0_ = in.encL;
    encR0_ = in.encR;
    encInit_ = true;
  }
  const float mPerCount = 2 * PI_F * cfg::WHEEL_RADIUS_M / cfg::ENC_COUNTS_PER_REV;
  const float xl = (cfg::ENC_LEFT_INVERT ? -1 : 1) * (float)(in.encL - encL0_) * mPerCount;
  const float xr = (cfg::ENC_RIGHT_INVERT ? -1 : 1) * (float)(in.encR - encR0_) * mPerCount;
  // Enkoder tekerin govdeye gore donusunu sayar; yere gore teker yolu icin govde egimi eklenir: x = r*(phi_bagil + theta)
  x_ = 0.5f * (xl + xr) + cfg::WHEEL_RADIUS_M * tilt_.theta();
  // hiz: 4 ornek (20 ms) uzerinden fark; tek sayim kuantalamasini 4 kat azaltir
  const float xOld = xHist_[histIdx_];
  xHist_[histIdx_] = x_;
  histIdx_ = (histIdx_ + 1) & 3;
  vDiff_ = (x_ - xOld) / (4 * dt);
  psi_ += tilt_.yawRate() * dt;
  // Gozleyici yalniz motorlar dengedeyken modelle uyumlu; digerinde olcumlere sifirlanir
  const float uPrev = uLast_;
  uLast_ = 0;
  if (CDTP_LQG && (mode_ == Mode::BALANCE || mode_ == Mode::DOCK)) {
    obs_.update(uPrev, x_, tilt_.theta(), tilt_.pitchRate());
    v_ = obs_.v();
    // CDTP_LQG=2: yalniz v gozleyiciden; theta ve omega dogrudan filtrelerden (modelin donguye girdigi yol kisalir)
    thCtl_ = CDTP_LQG == 2 ? tilt_.theta() : obs_.theta();
    omCtl_ = CDTP_LQG == 2 ? tilt_.pitchRate() : obs_.omega();
  } else {
    obs_.reset(x_, vDiff_, tilt_.theta(), tilt_.pitchRate());
    v_ = vDiff_;
    thCtl_ = tilt_.theta();
    omCtl_ = tilt_.pitchRate();
  }

  handleGlove(in);

  const float th = tilt_.theta();
  RobotOutputs out;  // varsayilan: motorlar kapali

  if (mode_ == Mode::BALANCE || mode_ == Mode::DOCK) {
    fallT_ = fabsf(th) > cfg::FALL_ANGLE_DEG * DEG ? fallT_ + dt : 0;
    if (fallT_ > cfg::FALL_HOLD_S) {
      mode_ = Mode::FALLEN;
      modeT_ = 0;
      dock_.abort();
      linActive_ = rotActive_ = false;
      pendingBack_ = false;
    }
  }

  // Acil stop basili: motorlara guc yok. Denge birakilir; stop acilinca robot yeniden dik tutulup baslatilir,
  // boylece birikmis hata ile motorlar aniden donmez.
  if (!in.motorPower && (mode_ == Mode::BALANCE || mode_ == Mode::DOCK)) {
    mode_ = Mode::STANDBY;
    modeT_ = 0;
    armT_ = 0;
    dock_.abort();
    linActive_ = rotActive_ = false;
    pendingBack_ = false;
  }

  switch (mode_) {
    case Mode::STANDBY:
      armT_ = (in.motorPower && fabsf(th) < cfg::ARM_ANGLE_DEG * DEG) ? armT_ + dt : 0;
      if (armT_ > cfg::ARM_HOLD_S) enterBalance();
      else if (charging_) { mode_ = Mode::CHARGING; modeT_ = 0; chargeLostT_ = 0; }
      break;

    case Mode::FALLEN:
      if (fabsf(th) < 20 * DEG) { mode_ = Mode::STANDBY; modeT_ = 0; armT_ = 0; }
      break;

    case Mode::CHARGING:
      chargeLostT_ = charging_ ? 0 : chargeLostT_ + dt;
      if (chargeLostT_ > 2.0f) { mode_ = Mode::STANDBY; modeT_ = 0; armT_ = 0; }
      break;

    case Mode::BALANCE:
    case Mode::DOCK: {
      float lean = 0;
      if (mode_ == Mode::DOCK) {
        DockCmd dc = dock_.step(irL_.n(), irR_.n(), charging_, dt);
        if (dock_.state() == DockState::DONE) {
          mode_ = Mode::CHARGING;
          modeT_ = 0;
          chargeLostT_ = 0;
          break;
        }
        if (dock_.state() == DockState::FAIL) {
          enterBalance();
        } else {
          vCmd_ = dc.v;
          rCmd_ = dc.yawRate;
          lean = dc.leanRad;
        }
      } else {
        if (pendingBack_ && modeT_ > 1.0f && fabsf(th) < 3 * DEG) {
          pendingBack_ = false;
          startStep(Cmd::BACK);
        }
        const bool idle = !linActive_ && !rotActive_ && fabsf(vCmd_) < 1e-3f && fabsf(rCmd_) < 1e-3f;
        const bool seen = irL_.n() >= cfg::DOCK_MIN_COUNT || irR_.n() >= cfg::DOCK_MIN_COUNT;
        // Butunlesik gorevde hedefte 5 s bekleme bozulmasin diye eldiven uzun sure bos kalmali; sarj testinde 1 s yeter
        const float idleNeed = task_ == Task::INTEGRATED ? cfg::DOCK_IDLE_S : 1.0f;
        // Sarj gorevinde robot istasyon bolgesine konur: isareti gormese de 1 s sonra aramaya baslar
        const bool look = seen || task_ == Task::CHARGING;
        undockHoldT_ = fmaxf(0.0f, undockHoldT_ - dt);
        beaconT_ = (dockAllowed() && idle && gloveIdleT_ > idleNeed && look && !pendingBack_ && undockHoldT_ <= 0)
                       ? beaconT_ + dt
                       : 0;
        if (beaconT_ > cfg::DOCK_TRIGGER_S) {
          mode_ = Mode::DOCK;
          modeT_ = 0;
          dock_.start();
        }
      }
      // --- referans uretimi ---
      if (linActive_) {
        lin_.step(dt);
        xRaw_ = xStart_ + lin_.pos();
        if (!lin_.active()) linActive_ = false;
      } else {
        vRaw_ += clampf(vCmd_ - vRaw_, -cfg::STEP_ACCEL * dt, cfg::STEP_ACCEL * dt);
        xRaw_ += vRaw_ * dt;
        xRaw_ = clampf(xRaw_, x_ - 0.15f, x_ + 0.15f);  // takilirsa referans kacmasin
      }
      {
        // referans bicimlendirme: kritik sonumlu 2. derece suzgec. Ivme referansi surekli olur,
        // egim on-beslemesi basamak yapmaz; model hatasinda durmadaki salinim azalir.
        const float w = cfg::REF_SHAPING_W;
        aRef_ = w * w * (xRaw_ - xRef_) - 2 * w * vRef_;
        vRef_ += aRef_ * dt;
        xRef_ += vRef_ * dt;
      }
      if (rotActive_) {
        rot_.step(dt);
        psiRef_ = psiStart_ + rot_.pos();
        rRef_ = rot_.vel();
        if (!rot_.active()) { rotActive_ = false; rRef_ = 0; }
      } else {
        const float dr = clampf(rCmd_ - rRef_, -cfg::TURN_ACCEL_DEG * DEG * dt, cfg::TURN_ACCEL_DEG * DEG * dt);
        rRef_ += dr;
        psiRef_ += rRef_ * dt;
      }
      out = balanceControl(in.vbat, lean);
      break;
    }
  }
  updateMotionState();
  return out;
}

int RobotLogic::telemetryJson(char* buf, int len, uint32_t seq) const {
  return snprintf(buf, len,
                  "{\"seq\":%lu,\"t\":%lu,\"bat\":%d,\"v\":%.2f,\"tilt\":%.1f,\"chg\":%d,\"mode\":\"%s\","
                  "\"mot\":\"%s\",\"dir\":\"%s\",\"task\":\"%s\",\"dock\":\"%s\",\"x\":%.3f,\"yaw\":%.0f,"
                  "\"glove\":\"%s\",\"ir\":[%d,%d]}",
                  (unsigned long)seq, (unsigned long)(t_ * 1000.0f), batteryPct(), batteryV(), thetaDeg(),
                  charging_ ? 1 : 0, modeName(mode_), motionName(motion_), dir_, taskName(task_),
                  dockName(dock_.state()), x_, psiDeg(), gloveAlive_ ? cmdName(gloveCmd_) : "yok", irL_.n(),
                  irR_.n());
}

}  // namespace cdtp
