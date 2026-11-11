// Donanim test yazilimi (denge kodu YOK). Robot ESP32 pinleri firmware/robot/src/pins.h ile ayni.
// Seri monitor 115200, satir sonu "Newline". Komutlar: ? yazin.
// Motor komutlari en fazla %50 guc verir ve 1,5 s komut gelmezse otomatik durur.
#include <Arduino.h>
#include <Wire.h>

#include "hw.h"

static Mpu6050 imu;
static PcntCounter encL, encR, irL, irR;
static Motors motors;
static cdtp::ImuSample smp;
static bool imuOk = false, stream = false, enOn = false;
static float dutyL = 0, dutyR = 0;
static uint32_t lastCmdMs = 0, lastPrintMs = 0;

static void help() {
  Serial.println(F("Komutlar:"));
  Serial.println(F("  ?          bu liste"));
  Serial.println(F("  i          I2C tarama (MPU6050 0x68 gorunmeli)"));
  Serial.println(F("  m          MPU6050 bir olcum (ivme m/s2, jiroskop rad/s)"));
  Serial.println(F("  p          surekli yazdirma ac/kapa (MPU + enkoder + IR, 5 Hz)"));
  Serial.println(F("  z          enkoder ve IR sayaclarini sifirla"));
  Serial.println(F("  l 0.3      sol motor duty -0.5..0.5 (eksi = geri)"));
  Serial.println(F("  r 0.3      sag motor duty -0.5..0.5"));
  Serial.println(F("  b 0.3      iki motor birden"));
  Serial.println(F("  s          motorlari durdur (STBY dusuk)"));
}

static void i2cScan() {
  int n = 0;
  for (uint8_t a = 1; a < 127; ++a) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  I2C cihaz: 0x%02X\n", a);
      ++n;
    }
  }
  Serial.printf("  %d cihaz bulundu (beklenen: 0x68)\n", n);
}

static void printAll() {
  if (imuOk && imu.read(smp)) {
    Serial.printf("acc %6.2f %6.2f %6.2f | gyro %6.3f %6.3f %6.3f | ", smp.acc[0], smp.acc[1], smp.acc[2], smp.gyro[0], smp.gyro[1],
                  smp.gyro[2]);
  } else {
    Serial.print("IMU yok | ");
  }
  Serial.printf("encL %ld encR %ld | IR L %ld R %ld | duty %.2f %.2f EN %d\n", (long)encL.read(), (long)encR.read(), (long)irL.read(),
                (long)irR.read(), dutyL, dutyR, enOn ? 1 : 0);
}

static void applyMotors() {
  enOn = (dutyL != 0 || dutyR != 0);
  motors.set(enOn, dutyL, dutyR);
}

static float clampDuty(float v) { return v > 0.5f ? 0.5f : (v < -0.5f ? -0.5f : v); }

static void handle(String s) {
  s.trim();
  if (!s.length()) return;
  char c = s[0];
  float v = s.length() > 1 ? s.substring(1).toFloat() : 0;
  switch (c) {
    case '?': help(); break;
    case 'i': i2cScan(); break;
    case 'm':
      if (!imuOk) imuOk = imu.begin();
      if (imuOk && imu.read(smp)) {
        Serial.printf("MPU6050 WHO_AM_I=0x%02X acc %.2f %.2f %.2f m/s2 (dururken z ~ +-9.8) gyro %.3f %.3f %.3f rad/s\n", imu.whoAmI, smp.acc[0],
                      smp.acc[1], smp.acc[2], smp.gyro[0], smp.gyro[1], smp.gyro[2]);
      } else {
        Serial.println(F("MPU6050 bulunamadi: SDA=21 SCL=22 VCC=3V3 GND AD0=GND baglantilarina bak"));
      }
      break;
    case 'p': stream = !stream; Serial.println(stream ? F("akis acik") : F("akis kapali")); break;
    case 'z': encL.read(); encR.read(); Serial.println(F("sayaclar okundu (fark icin once p ile bakin)")); break;
    case 'l': dutyL = clampDuty(v); lastCmdMs = millis(); applyMotors(); Serial.printf("sol duty %.2f\n", dutyL); break;
    case 'r': dutyR = clampDuty(v); lastCmdMs = millis(); applyMotors(); Serial.printf("sag duty %.2f\n", dutyR); break;
    case 'b': dutyL = dutyR = clampDuty(v); lastCmdMs = millis(); applyMotors(); Serial.printf("iki motor duty %.2f\n", dutyL); break;
    case 's': dutyL = dutyR = 0; applyMotors(); Serial.println(F("durdu")); break;
    default: Serial.println(F("bilinmeyen komut, ? yazin"));
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  motors.begin();  // STBY dusuk, tum PWM 0
  encL.beginQuadrature(PCNT_UNIT_0, PIN_ENC_L_A, PIN_ENC_L_B, 1023);
  encR.beginQuadrature(PCNT_UNIT_1, PIN_ENC_R_A, PIN_ENC_R_B, 1023);
  irL.beginFallingEdges(PCNT_UNIT_2, PIN_IR_L, 1023);
  irR.beginFallingEdges(PCNT_UNIT_3, PIN_IR_R, 1023);
  imuOk = imu.begin();
  Serial.println();
  Serial.println(F("CDTP donanim testi hazir. ? yazin."));
  Serial.println(imuOk ? F("MPU6050 bulundu.") : F("MPU6050 BULUNAMADI (i komutu ile I2C tarayin)."));
}

void loop() {
  static String line;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      handle(line);
      line = "";
    } else if (line.length() < 40) {
      line += ch;
    }
  }
  if (enOn && millis() - lastCmdMs > 1500) {  // emniyet: komut kesilince dur
    dutyL = dutyR = 0;
    applyMotors();
    Serial.println(F("1,5 s komut yok: motorlar durdu"));
  }
  if (stream && millis() - lastPrintMs >= 200) {
    lastPrintMs = millis();
    printAll();
  }
}
