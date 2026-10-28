// Otonom yanasma durum makinesi. Istasyonda yazilim yok; robot iki IR gozunun sayimiyla yon bulur.
#pragma once
#include "cdtp_config.h"
#include "core_math.h"

namespace cdtp {

enum class DockState { IDLE, SEARCH, ALIGN, APPROACH, CONTACT, DONE, FAIL };

inline const char* dockName(DockState s) {
  switch (s) {
    case DockState::SEARCH: return "ARA";
    case DockState::ALIGN: return "HIZALAN";
    case DockState::APPROACH: return "YAKLAS";
    case DockState::CONTACT: return "YERLES";
    case DockState::DONE: return "SARJ";
    case DockState::FAIL: return "BASARISIZ";
    default: return "-";
  }
}

struct DockCmd {
  float v = 0;          // m/s
  float yawRate = 0;    // rad/s, sola +
  float leanRad = 0;    // ek egim hedefi
  bool motorsOff = false;
};

class DockFsm {
 public:
  void start() {
    state_ = DockState::SEARCH;
    t_ = 0;
    stateT_ = 0;
    alignedT_ = 0;
    lostT_ = 0;
    chargeT_ = 0;
  }
  void abort() { state_ = DockState::IDLE; }
  DockState state() const { return state_; }
  bool active() const { return state_ != DockState::IDLE && state_ != DockState::DONE && state_ != DockState::FAIL; }

  DockCmd step(int nL, int nR, bool charge, float dt) {
    DockCmd c;
    t_ += dt;
    stateT_ += dt;
    const bool seeL = nL >= cfg::DOCK_MIN_COUNT, seeR = nR >= cfg::DOCK_MIN_COUNT;
    const float sum = (float)(nL + nR);
    const float e = (seeL || seeR) ? (nL - nR) / fmaxf(sum, 1.0f) : 0.0f;
    if (seeL || seeR) lastSide_ = e >= 0 ? 1.0f : -1.0f;
    chargeT_ = charge ? chargeT_ + dt : 0;
    const float kAlign = cfg::DOCK_ALIGN_K_DEG * DEG;

    if (active() && t_ > cfg::DOCK_TIMEOUT_S) go(DockState::FAIL);

    switch (state_) {
      case DockState::SEARCH:
        c.yawRate = lastSide_ * cfg::DOCK_SEARCH_YAW_DEG * DEG;
        if (seeL || seeR) go(DockState::ALIGN);
        else if (stateT_ > 15.0f) go(DockState::FAIL);  // ~1,2 tur dondu, isaret yok
        break;
      case DockState::ALIGN:
        c.yawRate = kAlign * e;
        alignedT_ = (seeL && seeR && fabsf(e) < cfg::DOCK_ALIGN_TOL) ? alignedT_ + dt : 0;
        lostT_ = (seeL || seeR) ? 0 : lostT_ + dt;
        if (alignedT_ > 0.3f) go(DockState::APPROACH);
        else if (lostT_ > cfg::DOCK_LOST_S) go(DockState::SEARCH);
        break;
      case DockState::APPROACH:
        if (seeL && seeR) {
          c.v = cfg::DOCK_APPROACH_V;
          c.yawRate = kAlign * e;
        } else if (seeL || seeR) {
          c.v = 0.4f * cfg::DOCK_APPROACH_V;  // tek goz: yavasla, don
          c.yawRate = kAlign * e;
        } else {
          c.v = 0.5f * cfg::DOCK_APPROACH_V;  // cok yakinda gozler isareti kaybedebilir: duz devam
        }
        lostT_ = (seeL || seeR) ? 0 : lostT_ + dt;
        if (chargeT_ >= cfg::CHARGE_CONFIRM_S) go(DockState::CONTACT);
        else if (lostT_ > cfg::DOCK_LOST_S) go(DockState::SEARCH);
        break;
      case DockState::CONTACT: {
        // sirta dogru yavasca egil, sonra motorlari kes
        float k = clampf(stateT_ / 0.3f, 0, 1);
        c.leanRad = k * cfg::DOCK_LEAN_DEG * DEG;
        if (!charge && stateT_ > 0.05f) go(DockState::APPROACH);
        else if (stateT_ > 0.4f) go(DockState::DONE);
        break;
      }
      case DockState::DONE:
        c.motorsOff = true;
        break;
      default:
        break;
    }
    return c;
  }

 private:
  void go(DockState s) {
    state_ = s;
    stateT_ = 0;
    alignedT_ = 0;
    lostT_ = 0;
  }
  DockState state_ = DockState::IDLE;
  float t_ = 0, stateT_ = 0, alignedT_ = 0, lostT_ = 0, chargeT_ = 0, lastSide_ = 1;
};

}  // namespace cdtp
