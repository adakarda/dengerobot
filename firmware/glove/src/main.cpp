// CDTP eldiven firmware'i (ESP32-C3 Super Mini).
// El sirtindaki MPU6050'den egimi 50 Hz okur, bes komuta cevirir, 20 Hz ESP-NOW ile robota yollar.
// Acilista el 2 s duz tutulur: o durus "notr" kabul edilir.
#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <esp_now.h>
#include <esp_wifi.h>

#include "gesture.h"
#include "protocol.h"

using namespace cdtp;

// ---- Ayarlar ----
// Robotun MAC adresi (robot acilista seri porta yazar). Hepsi 0xFF ise yayin yapilir;
// robot yine yalniz TEAM_KEY'li paketi kabul eder.
static uint8_t ROBOT_MAC[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
constexpr uint8_t CHANNEL = 1;
constexpr int PIN_SDA = 6, PIN_SCL = 7, PIN_BAT = 3, PIN_LED = 8;  // LED aktif dusuk
// MPU6050 karti el sirtinda duz, X ekseni parmaklara dogru. Isaretler seri cikistan dogrulanir:
// eli one eg -> pitch artmali; eli saga yatir -> roll artmali. Ters ise asagidaki isareti cevirin.
constexpr float PITCH_SIGN = 1.0f, ROLL_SIGN = 1.0f;

static GestureClassifier gesture;
static float pitch = 0, roll = 0, pitch0 = 0, roll0 = 0;
static float gbx = 0, gby = 0;
static uint16_t seq = 0;
static volatile uint32_t sendFail = 0;

static void mpuWrite(uint8_t r, uint8_t v) {
  Wire.beginTransmission(0x68);
  Wire.write(r);
  Wire.write(v);
  Wire.endTransmission();
}
static bool mpuRead(float a[3], float g[3]) {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(0x68, 14) != 14) return false;
  uint8_t b[14];
  for (int i = 0; i < 14; ++i) b[i] = Wire.read();
  auto w = [&](int i) { return (int16_t)((b[i] << 8) | b[i + 1]); };
  for (int i = 0; i < 3; ++i) {
    a[i] = w(i * 2) / 8192.0f;           // g
    g[i] = w(8 + i * 2) / 65.5f;         // deg/s
  }
  return true;
}

static void updateAngles(float dt) {
  float a[3], g[3];
  if (!mpuRead(a, g)) return;
  const float ap = atan2f(-a[0], a[2]) / DEG;  // parmaklar asagi -> +
  const float ar = atan2f(a[1], a[2]) / DEG;   // sag taraf asagi -> +
  // tumleyen filtre (50 Hz): 0,96 jiroskop
  pitch = 0.96f * (pitch + (g[1] - gby) * dt) + 0.04f * ap;
  roll = 0.96f * (roll + (g[0] - gbx) * dt) + 0.04f * ar;
}

#if ESP_ARDUINO_VERSION_MAJOR >= 3
static void onSent(const wifi_tx_info_t*, esp_now_send_status_t s) {
#else
static void onSent(const uint8_t*, esp_now_send_status_t s) {
#endif
  if (s != ESP_NOW_SEND_SUCCESS) sendFail = sendFail + 1;
}

static int batteryPct() {
  float v = analogReadMilliVolts(PIN_BAT) * 0.002f;  // 100k/100k bolucu
  return (int)constrain((v - 3.4f) / (4.15f - 3.4f) * 100.0f, 0.0f, 100.0f);
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  analogSetPinAttenuation(PIN_BAT, ADC_11db);
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  mpuWrite(0x6B, 0x01);
  mpuWrite(0x1A, 0x04);  // DLPF ~20 Hz: el titremesini suzer
  mpuWrite(0x1B, 0x08);  // +-500 deg/s
  mpuWrite(0x1C, 0x08);  // +-4 g

  // notr kalibrasyon: 2 s el duz ve sabit
  Serial.println("Eli 2 s duz ve sabit tutun...");
  float sx = 0, sy = 0, a[3], g[3];
  int n = 0;
  for (uint32_t t0 = millis(); millis() - t0 < 2000; delay(10)) {
    if (!mpuRead(a, g)) continue;
    sx += g[0];
    sy += g[1];
    pitch = atan2f(-a[0], a[2]) / DEG;
    roll = atan2f(a[1], a[2]) / DEG;
    ++n;
  }
  if (n) { gbx = sx / n; gby = sy / n; }
  pitch0 = pitch;
  roll0 = roll;
  Serial.printf("notr: pitch=%.1f roll=%.1f\n", pitch0, roll0);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(CHANNEL, WIFI_SECOND_CHAN_NONE);
  esp_now_init();
  esp_now_register_send_cb(onSent);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, ROBOT_MAC, 6);
  peer.channel = CHANNEL;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
  digitalWrite(PIN_LED, HIGH);
}

void loop() {
  static uint32_t last = millis(), lastSend = 0, lastPrint = 0;
  static int tick = 0;
  const uint32_t now = millis();
  if (now - last < 20) return;  // 50 Hz
  const float dt = (now - last) * 0.001f;
  last = now;
  updateAngles(dt);
  const float p = PITCH_SIGN * (pitch - pitch0), r = ROLL_SIGN * (roll - roll0);
  const Cmd c = gesture.update(p, r, dt);

  if (now - lastSend >= 50) {  // 20 Hz
    lastSend = now;
    GlovePacket pk{};
    pk.cmd = (uint8_t)c;
    pk.seq = seq++;
    pk.pitchDeg = (int8_t)constrain(p, -127.0f, 127.0f);
    pk.rollDeg = (int8_t)constrain(r, -127.0f, 127.0f);
    static uint8_t bat = batteryPct();
    if (++tick % 20 == 0) bat = batteryPct();
    pk.batPct = bat;
    sealPacket(pk);
    esp_now_send(ROBOT_MAC, (const uint8_t*)&pk, sizeof pk);
  }
  // LED: dur'da sabit sonuk, komutta yanar
  digitalWrite(PIN_LED, c == Cmd::STOP ? HIGH : LOW);
  if (now - lastPrint >= 200) {
    lastPrint = now;
    Serial.printf("pitch=%6.1f roll=%6.1f komut=%s gonderim-hata=%lu\n", p, r, cmdName(c), (unsigned long)sendFail);
  }
}
