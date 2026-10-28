// Eldiven -> robot ESP-NOW paketi ve ortak tipler.
#pragma once
#include <stdint.h>
#include <string.h>

namespace cdtp {

enum class Cmd : uint8_t { NONE = 0, FWD = 1, BACK = 2, LEFT = 3, RIGHT = 4, STOP = 5 };

inline const char* cmdName(Cmd c) {
  switch (c) {
    case Cmd::FWD: return "ileri";
    case Cmd::BACK: return "geri";
    case Cmd::LEFT: return "sol";
    case Cmd::RIGHT: return "sag";
    case Cmd::STOP: return "dur";
    default: return "yok";
  }
}

// Ayni sinifta baska takimlarin eldiveni de ESP-NOW yayini yapar.
// Robot yalniz bu anahtari tasiyan paketi kabul eder. Takim icin degistirin.
constexpr uint32_t TEAM_KEY = 0xCD7B0001u;

constexpr uint8_t PROTO_VERSION = 1;

#pragma pack(push, 1)
struct GlovePacket {
  uint32_t key;       // TEAM_KEY
  uint8_t version;    // PROTO_VERSION
  uint8_t cmd;        // Cmd
  uint16_t seq;       // her pakette +1
  int8_t pitchDeg;    // hata ayiklama icin
  int8_t rollDeg;
  uint8_t batPct;     // eldiven pili
  uint8_t crc;        // onceki baytlarin CRC-8'i
};
#pragma pack(pop)
static_assert(sizeof(GlovePacket) == 12, "paket boyutu degismemeli");

inline uint8_t crc8(const uint8_t* d, size_t n) {
  uint8_t c = 0;
  for (size_t i = 0; i < n; ++i) {
    c ^= d[i];
    for (int b = 0; b < 8; ++b) c = (c & 0x80) ? (uint8_t)((c << 1) ^ 0x07) : (uint8_t)(c << 1);
  }
  return c;
}

inline void sealPacket(GlovePacket& p) {
  p.key = TEAM_KEY;
  p.version = PROTO_VERSION;
  p.crc = crc8(reinterpret_cast<const uint8_t*>(&p), sizeof(p) - 1);
}

inline bool checkPacket(const uint8_t* data, int len, GlovePacket& out) {
  if (len != (int)sizeof(GlovePacket)) return false;
  memcpy(&out, data, sizeof(out));
  if (out.key != TEAM_KEY || out.version != PROTO_VERSION) return false;
  if (out.crc != crc8(data, sizeof(out) - 1)) return false;
  return out.cmd <= (uint8_t)Cmd::STOP;
}

}  // namespace cdtp
