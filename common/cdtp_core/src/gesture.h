// Eldiven: el egimini bes komuta ceviren siniflandirici (histerezisli).
// Pitch: el one egik +. Roll: sag tarafa yatik +. Aci olculeri acilistaki notr durusa goredir.
#pragma once
#include "cdtp_config.h"
#include "core_math.h"
#include "protocol.h"

namespace cdtp {

class GestureClassifier {
 public:
  Cmd update(float pitchDeg, float rollDeg, float dt) {
    Cmd cand = candidate(pitchDeg, rollDeg);
    if (cand == current_) {
      pendingT_ = 0;
      pending_ = cand;
      return current_;
    }
    if (cand != pending_) {
      pending_ = cand;
      pendingT_ = 0;
    }
    pendingT_ += dt;
    float need = (cand == Cmd::STOP) ? cfg::GEST_NEUTRAL_S : cfg::GEST_HOLD_S;
    if (cand != Cmd::NONE && pendingT_ >= need) current_ = cand;
    return current_;
  }
  Cmd current() const { return current_; }

 private:
  Cmd candidate(float p, float r) const {
    float ap = fabsf(p), ar = fabsf(r);
    // Suren komut, cikis esiginin (15 deg) altina inene kadar korunur
    if (current_ == Cmd::FWD && p > cfg::GEST_EXIT_DEG && ap >= ar) return Cmd::FWD;
    if (current_ == Cmd::BACK && p < -cfg::GEST_EXIT_DEG && ap >= ar) return Cmd::BACK;
    if (current_ == Cmd::RIGHT && r > cfg::GEST_EXIT_DEG && ar >= ap) return Cmd::RIGHT;
    if (current_ == Cmd::LEFT && r < -cfg::GEST_EXIT_DEG && ar >= ap) return Cmd::LEFT;
    if (ap < cfg::GEST_NEUTRAL_DEG && ar < cfg::GEST_NEUTRAL_DEG) return Cmd::STOP;
    // Yeni komut icin giris esigi (25 deg) ve baskin eksen 1.5 kat buyuk olmali (capraz el karismasin)
    if (ap >= cfg::GEST_ENTER_DEG && ap > 1.5f * ar) return p > 0 ? Cmd::FWD : Cmd::BACK;
    if (ar >= cfg::GEST_ENTER_DEG && ar > 1.5f * ap) return r > 0 ? Cmd::RIGHT : Cmd::LEFT;
    return Cmd::NONE;  // belirsiz bolge: mevcut komut degismez
  }
  Cmd current_ = Cmd::STOP, pending_ = Cmd::STOP;
  float pendingT_ = 0;
};

}  // namespace cdtp
