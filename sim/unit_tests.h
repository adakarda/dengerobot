// Ortak cekirdek icin birim testleri (eldiven jesti, IR cerceve, paket, profil, telemetri).
#pragma once
#include <cstdio>
#include <cstring>

#include "gesture.h"
#include "ir_frame.h"
#include "protocol.h"
#include "robot_logic.h"

static int g_fail = 0;
#define EXPECT(c, msg)                                   \
  do {                                                   \
    if (!(c)) {                                          \
      std::printf("  HATA: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
      ++g_fail;                                          \
    }                                                    \
  } while (0)

static cdtp::Cmd feed(cdtp::GestureClassifier& g, float p, float r, float sec) {
  cdtp::Cmd c = cdtp::Cmd::NONE;
  for (float t = 0; t < sec; t += 0.02f) c = g.update(p, r, 0.02f);
  return c;
}

static int runUnitTests() {
  using cdtp::Cmd;
  // --- jest siniflandirici ---
  {
    cdtp::GestureClassifier g;
    EXPECT(feed(g, 0, 0, 0.5) == Cmd::STOP, "notr el = dur");
    EXPECT(feed(g, 30, 0, 0.3) == Cmd::FWD, "one 30 deg = ileri");
    EXPECT(feed(g, 18, 0, 0.5) == Cmd::FWD, "histerezis: 18 deg'de ileri surer");
    EXPECT(feed(g, 5, 0, 0.5) == Cmd::STOP, "5 deg'de dur");
    EXPECT(feed(g, -30, 0, 0.3) == Cmd::BACK, "geri");
    feed(g, 0, 0, 0.5);
    EXPECT(feed(g, 0, -30, 0.3) == Cmd::LEFT, "sol");
    feed(g, 0, 0, 0.5);
    EXPECT(feed(g, 0, 30, 0.3) == Cmd::RIGHT, "sag");
    feed(g, 0, 0, 0.5);
    EXPECT(feed(g, 28, 26, 0.5) == Cmd::STOP, "capraz el (28/26) belirsiz: komut degismez");
    EXPECT(feed(g, 30, 0, 0.06) == Cmd::STOP, "0,06 s'lik titreme komut sayilmaz");
    EXPECT(feed(g, 20, 0, 1.0) == Cmd::STOP, "20 deg giris esiginin altinda");
  }
  // --- IR cerceve sayaci ---
  {
    cdtp::IrFrameCounter c;
    int32_t cnt = 0;
    int got = -1;
    for (int ms = 0; ms < 400; ms += 1) {
      double ph = std::fmod(ms, 78.0);
      if (ph < 45 && ms % 1 == 0) cnt++;  // ~44-45 patlama
      if (ms % 5 == 0) {
        c.sample(cnt, ms / 1000.0f);
        if (c.n() > 0) got = c.n();
      }
    }
    EXPECT(got >= 40 && got <= 46, "tam gorus ~44 darbe/cerceve");
    for (int ms = 400; ms < 800; ms += 5) c.sample(cnt, ms / 1000.0f);
    EXPECT(c.n() == 0, "isaret kesilince 0,25 s icinde n=0");
  }
  // --- paket ---
  {
    cdtp::GlovePacket p{};
    p.cmd = (uint8_t)Cmd::LEFT;
    p.seq = 77;
    cdtp::sealPacket(p);
    cdtp::GlovePacket o;
    EXPECT(cdtp::checkPacket((const uint8_t*)&p, sizeof p, o) && o.cmd == (uint8_t)Cmd::LEFT, "gecerli paket");
    uint8_t bad[sizeof p];
    std::memcpy(bad, &p, sizeof p);
    bad[5] ^= 1;
    EXPECT(!cdtp::checkPacket(bad, sizeof p, o), "bozuk CRC reddedilir");
    cdtp::GlovePacket q = p;
    q.key = 0x12345678;
    q.crc = cdtp::crc8((const uint8_t*)&q, sizeof q - 1);
    EXPECT(!cdtp::checkPacket((const uint8_t*)&q, sizeof q, o), "baska takimin anahtari reddedilir");
  }
  // --- trapez profil ---
  {
    cdtp::Trapezoid tr;
    tr.start(0.5f, 0.25f, 0.4f);
    float vmax = 0;
    int n = 0;
    while (tr.active() && n < 4000) { tr.step(0.005f); vmax = std::max(vmax, tr.vel()); ++n; }
    EXPECT(std::fabs(tr.pos() - 0.5f) < 1e-3f, "profil 0,5 m'de biter");
    EXPECT(vmax <= 0.2501f, "hiz siniri");
  }
  // --- telemetri ---
  {
    cdtp::RobotLogic lg;
    char buf[320];
    int n = lg.telemetryJson(buf, sizeof buf, 5);
    EXPECT(n > 0 && n < (int)sizeof buf && buf[0] == '{' && std::strstr(buf, "\"tilt\":") && std::strstr(buf, "\"chg\":"),
           "telemetri JSON");
    std::printf("  ornek telemetri (%d bayt): %s\n", n, buf);
  }
  std::printf("  birim testleri: %s\n", g_fail ? "HATA VAR" : "hepsi gecti");
  return g_fail;
}
