// Kablosuz baglantilar: eldivenden ESP-NOW, telefona BLE.
#pragma once
#include <Arduino.h>
#include <NimBLEDevice.h>
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
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
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

// ---------------- BLE: telefon uygulamasi ----------------
// Servis ve karakteristik UUID'leri uygulama ekibiyle paylasilir (docs/BLE_PROTOKOL.md).
#define CDTP_SVC_UUID "6e400001-cd7b-4e3a-9a40-2026cd7b0001"
#define CDTP_TELEM_UUID "6e400002-cd7b-4e3a-9a40-2026cd7b0001"  // notify + read, JSON, 1 Hz
#define CDTP_CMD_UUID "6e400003-cd7b-4e3a-9a40-2026cd7b0001"    // write, metin komut

namespace ble {
static NimBLECharacteristic* telem = nullptr;
static volatile bool connected = false;
static char cmdBuf[64];
static volatile bool cmdReady = false;

class ServerCb : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer*) override { connected = true; }
  void onDisconnect(NimBLEServer*) override {
    connected = false;
    NimBLEDevice::startAdvertising();
  }
};
class CmdCb : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic* c) override {
    std::string v = c->getValue();
    if (cmdReady) return;  // onceki komut islenmedi
    size_t n = v.size() < sizeof(cmdBuf) - 1 ? v.size() : sizeof(cmdBuf) - 1;
    memcpy(cmdBuf, v.data(), n);
    cmdBuf[n] = 0;
    cmdReady = true;
  }
};

inline void begin(const char* name) {
  NimBLEDevice::init(name);
  NimBLEDevice::setMTU(247);
  NimBLEDevice::setPower(ESP_PWR_LVL_P9);
  NimBLEServer* s = NimBLEDevice::createServer();
  s->setCallbacks(new ServerCb());
  NimBLEService* svc = s->createService(CDTP_SVC_UUID);
  telem = svc->createCharacteristic(CDTP_TELEM_UUID, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY);
  NimBLECharacteristic* cmd = svc->createCharacteristic(CDTP_CMD_UUID, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_NR);
  cmd->setCallbacks(new CmdCb());
  svc->start();
  NimBLEAdvertising* adv = NimBLEDevice::getAdvertising();
  adv->addServiceUUID(CDTP_SVC_UUID);
  adv->setScanResponse(true);
  adv->start();
}
inline void publish(const char* json) {
  if (!telem) return;
  telem->setValue((const uint8_t*)json, strlen(json));
  if (connected) telem->notify();
}
}  // namespace ble
