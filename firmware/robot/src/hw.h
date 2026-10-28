// Robot donanim katmani: MPU6050, PCNT sayaclari, BTS7960 PWM, ADC.
#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <driver/pcnt.h>

#include "imu_filter.h"
#include "pins.h"

// ---------------- MPU6050 ----------------
class Mpu6050 {
 public:
  bool begin() {
    Wire.begin(PIN_SDA, PIN_SCL, 400000);
    uint8_t who = read8(0x75);
    // Orijinali 0x68 doner; bazi klon cipler 0x70/0x72/0x98 doner, yine de calisir
    if (who == 0x00 || who == 0xFF) return false;
    whoAmI = who;
    write8(0x6B, 0x80);  // sifirla
    delay(100);
    write8(0x6B, 0x01);  // saat: PLL (jiroskop X)
    write8(0x1A, 0x03);  // DLPF ~42 Hz
    write8(0x19, 4);     // 1 kHz / (1+4) = 200 Hz
    write8(0x1B, 0x08);  // +-500 deg/s -> 65,5 LSB/(deg/s)
    write8(0x1C, 0x08);  // +-4 g -> 8192 LSB/g
    write8(0x37, 0x10);  // INT: aktif yuksek, okuyunca temizlenir
    write8(0x38, 0x01);  // veri hazir kesmesi
    return true;
  }
  // ham olcumu robot birimlerine cevirir (m/s^2, rad/s)
  bool read(cdtp::ImuSample& s) {
    uint8_t b[14];
    Wire.beginTransmission(ADDR);
    Wire.write(0x3B);
    if (Wire.endTransmission(false) != 0) return false;
    if (Wire.requestFrom((int)ADDR, 14) != 14) return false;
    for (int i = 0; i < 14; ++i) b[i] = Wire.read();
    auto w = [&](int i) { return (int16_t)((b[i] << 8) | b[i + 1]); };
    const float ka = 9.80665f / 8192.0f, kg = (3.14159265f / 180.0f) / 65.5f;
    for (int i = 0; i < 3; ++i) {
      s.acc[i] = w(i * 2) * ka;
      s.gyro[i] = w(8 + i * 2) * kg - bias[i];
    }
    return true;
  }
  // Acilista robot hareketsizken jiroskop sapmasini olcer (yatik da olabilir)
  bool calibrateGyro(int n = 400) {
    double sum[3] = {0, 0, 0}, sq[3] = {0, 0, 0};
    for (int i = 0; i < 3; ++i) bias[i] = 0;
    cdtp::ImuSample s;
    for (int k = 0; k < n; ++k) {
      if (!read(s)) return false;
      for (int i = 0; i < 3; ++i) {
        sum[i] += s.gyro[i];
        sq[i] += s.gyro[i] * s.gyro[i];
      }
      delay(5);
    }
    for (int i = 0; i < 3; ++i) {
      double m = sum[i] / n, var = sq[i] / n - m * m;
      if (var > 0.0004) return false;  // ~1,1 deg/s std: robot kipirdadi, tekrar
      bias[i] = (float)m;
    }
    return true;
  }
  float bias[3] = {0, 0, 0};
  uint8_t whoAmI = 0;

 private:
  static constexpr uint8_t ADDR = 0x68;
  void write8(uint8_t r, uint8_t v) {
    Wire.beginTransmission(ADDR);
    Wire.write(r);
    Wire.write(v);
    Wire.endTransmission();
  }
  uint8_t read8(uint8_t r) {
    Wire.beginTransmission(ADDR);
    Wire.write(r);
    Wire.endTransmission(false);
    Wire.requestFrom((int)ADDR, 1);
    return Wire.available() ? Wire.read() : 0xFF;
  }
};

// ---------------- PCNT: enkoder (4x) ve IR darbe sayaci ----------------
// 16 bitlik donanim sayacini yazilimda 32 bite genisletir. Her 5 ms okunmasi yeterli.
class PcntCounter {
 public:
  void beginQuadrature(pcnt_unit_t u, int a, int b, uint16_t filter) {
    unit_ = u;
    pcnt_config_t c = {};
    c.unit = u;
    c.counter_h_lim = LIM;
    c.counter_l_lim = -LIM;
    // kanal 0: A kenarlari, yon B'den
    c.channel = PCNT_CHANNEL_0;
    c.pulse_gpio_num = a;
    c.ctrl_gpio_num = b;
    c.pos_mode = PCNT_COUNT_DEC;
    c.neg_mode = PCNT_COUNT_INC;
    c.lctrl_mode = PCNT_MODE_REVERSE;
    c.hctrl_mode = PCNT_MODE_KEEP;
    pcnt_unit_config(&c);
    // kanal 1: B kenarlari, yon A'dan
    c.channel = PCNT_CHANNEL_1;
    c.pulse_gpio_num = b;
    c.ctrl_gpio_num = a;
    c.pos_mode = PCNT_COUNT_INC;
    c.neg_mode = PCNT_COUNT_DEC;
    pcnt_unit_config(&c);
    gpio_pullup_en((gpio_num_t)a);
    gpio_pullup_en((gpio_num_t)b);
    finish(filter);
  }
  void beginFallingEdges(pcnt_unit_t u, int pin, uint16_t filter) {
    unit_ = u;
    pcnt_config_t c = {};
    c.unit = u;
    c.channel = PCNT_CHANNEL_0;
    c.pulse_gpio_num = pin;
    c.ctrl_gpio_num = PCNT_PIN_NOT_USED;
    c.pos_mode = PCNT_COUNT_DIS;
    c.neg_mode = PCNT_COUNT_INC;  // alici cikisi patlama sirasinda dusuk
    c.lctrl_mode = PCNT_MODE_KEEP;
    c.hctrl_mode = PCNT_MODE_KEEP;
    c.counter_h_lim = LIM;
    c.counter_l_lim = -LIM;
    pcnt_unit_config(&c);
    finish(filter);
  }
  int32_t read() {
    int16_t v = 0;
    pcnt_get_counter_value(unit_, &v);
    int32_t d = (int32_t)v - last_;
    if (d > LIM / 2) d -= LIM;  // sayac +-LIM'e ulasinca 0'a doner
    if (d < -LIM / 2) d += LIM;
    last_ = v;
    acc_ += d;
    return acc_;
  }

 private:
  static constexpr int16_t LIM = 30000;
  void finish(uint16_t filter) {
    pcnt_set_filter_value(unit_, filter);  // APB 80 MHz cevrimi; 1023 = 12,8 us
    pcnt_filter_enable(unit_);
    pcnt_counter_pause(unit_);
    pcnt_counter_clear(unit_);
    pcnt_counter_resume(unit_);
  }
  pcnt_unit_t unit_ = PCNT_UNIT_0;
  int16_t last_ = 0;
  int32_t acc_ = 0;
};

// ---------------- BTS7960 x 2 ----------------
class Motors {
 public:
  void begin() {
    pinMode(PIN_MOTOR_EN, OUTPUT);
    digitalWrite(PIN_MOTOR_EN, LOW);
    const int pins[4] = {PIN_L_RPWM, PIN_L_LPWM, PIN_R_RPWM, PIN_R_LPWM};
    for (int i = 0; i < 4; ++i) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
      ledcAttach(pins[i], FREQ, BITS);
#else
      ledcSetup(i, FREQ, BITS);
      ledcAttachPin(pins[i], i);
#endif
      write(i, 0);
    }
  }
  // duty: -1..1. enable=false: iki surucu de yuksek empedans (motor serbest)
  void set(bool enable, float dl, float dr) {
    if (!enable) {
      digitalWrite(PIN_MOTOR_EN, LOW);
      for (int i = 0; i < 4; ++i) write(i, 0);
      return;
    }
    side(0, dl);
    side(2, dr);
    digitalWrite(PIN_MOTOR_EN, HIGH);
  }

 private:
  static constexpr int FREQ = 20000, BITS = 10, MAXD = (1 << BITS) - 1;
  void side(int ch, float d) {
    int v = (int)(fabsf(d) * MAXD + 0.5f);
    if (v > MAXD) v = MAXD;
    // asla iki yari kopru ayni anda surulmez
    if (d >= 0) {
      write(ch + 1, 0);
      write(ch, v);
    } else {
      write(ch, 0);
      write(ch + 1, v);
    }
  }
  void write(int ch, int v) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    const int pins[4] = {PIN_L_RPWM, PIN_L_LPWM, PIN_R_RPWM, PIN_R_LPWM};
    ledcWrite(pins[ch], v);
#else
    ledcWrite(ch, v);
#endif
  }
};

// ---------------- ADC ----------------
inline float readVolts(int pin, float scale) { return analogReadMilliVolts(pin) * 0.001f * DIVIDER * scale; }
