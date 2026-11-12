// Kablosuz baglantilar: eldivenden ESP-NOW, telefona Wi-Fi WebSocket (shared/protocol/messages.md).
#pragma once
#include <Arduino.h>
#include <WebSocketsServer.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "protocol.h"

constexpr uint8_t ESPNOW_CHANNEL = 1;  // eldivenle ayni olmali

// ---------------- ESP-NOW alici ----------------
namespace gloverx {
static portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
static cdtp::GlovePacket last;
static volatile uint32_t count = 0, bad = 0, lost = 0;
static uint32_t seenCount = 0;
static uint16_t lastSeq = 0;

static void onPacket(const uint8_t* data, int len) {
  cdtp::GlovePacket p;
  if (!cdtp::checkPacket(data, len, p)) {
    bad = bad + 1;
    return;
  }
  portENTER_CRITICAL(&mux);
  if (count > 0) lost = lost + (uint16_t)(p.seq - lastSeq - 1);
  lastSeq = p.seq;
  last = p;
  count = count + 1;
  portEXIT_CRITICAL(&mux);
}
#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void cb(const esp_now_recv_info_t*, const uint8_t* d, int n) { onPacket(d, n); }
#else
static void cb(const uint8_t*, const uint8_t* d, int n) { onPacket(d, n); }
#endif

inline bool begin() {
  // Robot kendi agini acar (AP) ve ESP-NOW ayni kanalda calisir: eldiven + telefon birlikte.
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP("CDTP-ROBOT", nullptr, ESPNOW_CHANNEL);  // IP 192.168.4.1
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(cb);
  return true;
}
// Kontrol dongusu cagirir: yeni paket varsa true
inline bool poll(cdtp::GlovePacket& out) {
  bool fresh = false;
  portENTER_CRITICAL(&mux);
  if (count != seenCount) {
    seenCount = count;
    out = last;
    fresh = true;
  }
  portEXIT_CRITICAL(&mux);
  return fresh;
}
}  // namespace gloverx

// ---------------- Wi-Fi WebSocket: telefon uygulamasi ----------------
// Sunucu port 81, yol "/", her cerceve bir JSON nesnesi. Alanlar: shared/protocol/messages.md
namespace ws {
static WebSocketsServer server(81);
static volatile uint8_t appCmd = 0;     // cdtp::Cmd, 0 = yok
static volatile bool appCmdFresh = false;
static volatile uint32_t clients = 0;

// "key":"value" icinde ilk harfi / "id": sayisini ayiklayan kucuk ayristirici (ArduinoJson gerekmez)
static bool hasType(const char* js, const char* type) {
  char pat[40];
  snprintf(pat, sizeof pat, "\"type\":\"%s\"", type);
  return strstr(js, pat) != nullptr;
}
static char cmdLetter(const char* js) {
  const char* p = strstr(js, "\"cmd\":\"");
  return p ? p[7] : 0;
}
static void onEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t len) {
  if (type == WStype_CONNECTED) clients = clients + 1;
  if (type == WStype_DISCONNECTED && clients > 0) clients = clients - 1;
  if (type != WStype_TEXT || len == 0 || len > 120) return;
  char js[128];
  memcpy(js, payload, len);
  js[len] = 0;
  if (hasType(js, "ping")) {
    const char* p = strstr(js, "\"id\":");
    char out[64];
    snprintf(out, sizeof out, "{\"type\":\"pong\",\"id\":%ld,\"t\":%lu}", p ? atol(p + 5) : 0L, (unsigned long)millis());
    server.sendTXT(num, out);
  } else if (hasType(js, "cmd")) {
    cdtp::Cmd c = cdtp::Cmd::NONE;
    switch (cmdLetter(js)) {
      case 'F': c = cdtp::Cmd::FWD; break;
      case 'B': c = cdtp::Cmd::BACK; break;
      case 'L': c = cdtp::Cmd::LEFT; break;
      case 'R': c = cdtp::Cmd::RIGHT; break;
      case 'S': c = cdtp::Cmd::STOP; break;
      default: return;
    }
    appCmd = (uint8_t)c;
    appCmdFresh = true;
  }
}
inline void begin() {
  server.begin();
  server.onEvent(onEvent);
}
inline void loop() { server.loop(); }
inline void publish(const char* json) {
  if (clients) server.broadcastTXT(json);
}
}  // namespace ws
