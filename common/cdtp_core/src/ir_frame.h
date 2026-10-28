// IR gozu cerceve sayaci.
// Istasyon 45 ms boyunca ~1 kHz patlama yollar, 33 ms susar. Donanim sayaci (PCNT) dusen kenarlari sayar.
// Bu sinif sayaci periyodik okur; 10 ms'den uzun sessizlik = cerceve sonu, o cercevedeki darbe sayisi n.
#pragma once
#include <stdint.h>

namespace cdtp {

class IrFrameCounter {
 public:
  // count: PCNT'nin kumulatif degeri, t: saniye
  void sample(int32_t count, float t) {
    if (count != lastCount_) {
      if (!inFrame_) {
        inFrame_ = true;
        frameStart_ = lastCount_;
      }
      lastCount_ = count;
      lastEdgeT_ = t;
    } else if (inFrame_ && t - lastEdgeT_ > GAP_S) {
      inFrame_ = false;
      n_ = count - frameStart_;
      frameT_ = t;
    }
    if (t - frameT_ > STALE_S) n_ = 0;  // isaret kayboldu
  }
  int n() const { return n_; }
  float lastFrameT() const { return frameT_; }

 private:
  static constexpr float GAP_S = 0.018f;  // isaret 33 ms susar; zayif isarette tek tuk kacan patlama cerceveyi bolmesin
  static constexpr float STALE_S = 0.25f;
  int32_t lastCount_ = 0, frameStart_ = 0;
  float lastEdgeT_ = -1, frameT_ = -1;
  bool inFrame_ = false;
  int n_ = 0;
};

}  // namespace cdtp
