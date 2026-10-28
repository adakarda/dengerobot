// Robot ESP32 pin haritasi. Sitedeki (cdtp-robot.netlify.app > Sema > Robot pinleri) ile aynidir.
#pragma once

// IMU (MPU6050, I2C 400 kHz, adres 0x68: AD0 -> GND)
constexpr int PIN_SDA = 21;
constexpr int PIN_SCL = 22;
constexpr int PIN_IMU_INT = 19;

// BTS7960 x 2. R_EN ve L_EN iki kartta da GPIO4'e bagli; GPIO4 -> 10 kOhm -> GND
constexpr int PIN_L_RPWM = 27;  // sol motor ileri
constexpr int PIN_L_LPWM = 14;  // sol motor geri (acilista kisa darbe verir; EN kapaliyken zararsiz)
constexpr int PIN_R_RPWM = 16;  // sag motor ileri  (WROVER kartta 16/17 PSRAM'e gider: WROOM kullanin)
constexpr int PIN_R_LPWM = 17;  // sag motor geri
constexpr int PIN_MOTOR_EN = 4;

// Enkoderler (Hall, 3,3 V ile beslenir)
constexpr int PIN_ENC_L_A = 32;
constexpr int PIN_ENC_L_B = 33;
constexpr int PIN_ENC_R_A = 25;
constexpr int PIN_ENC_R_B = 26;

// IR gozleri (VS1838B; TSOP1838 4,5 V ister, 3,3 V'ta calismaz). Yalniz-giris pinleri.
// ESP32 hatasi (errata 3.11): ADC/Wi-Fi acikken GPIO36/39'da ~80 ns'lik dusuk darbeler olur.
// Kesme yerine PCNT + 12,8 us cam filtresi kullanildigi icin bu darbeler sayilmaz.
constexpr int PIN_IR_L = 36;
constexpr int PIN_IR_R = 39;

// Olcumler (ADC1; Wi-Fi/BLE acikken calisir). 100k / 27k bolucu: 12,6 V -> 2,68 V
constexpr int PIN_VBAT = 35;
constexpr int PIN_VCHG = 34;
constexpr float DIVIDER = (100.0f + 27.0f) / 27.0f;

// Acil stop sonrasi motor hatti: 100k/33k bolucu -> GPIO23 (12,6 V -> 3,1 V). Takili degilse false yapin.
constexpr bool HAS_MOTOR_SENSE = false;
constexpr int PIN_MOTOR_SENSE = 23;

constexpr int PIN_LED = 2;  // kart uzerindeki mavi LED (yalniz durum gosterir; sarj gostergesi DEGIL)
