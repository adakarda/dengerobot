// CDTP iki tekerlekli hasta destek robotu: robot ESP32 firmware'i.
// Cekirdek 1: 200 Hz denge dongusu (MPU6050 veri-hazir kesmesiyle tetiklenir).
// Cekirdek 0: ESP-NOW (eldiven), BLE (telefon), seri konsol.
// Tum karar mantigi common/cdtp_core/RobotLogic'tedir; PC simulasyonu ayni kodu test eder.
#include <Arduino.h>
#include <Preferences.h>

#include "hw.h"
#include "links.h"
#include "robot_logic.h"

using namespace cdtp;

// ---- Finalde true yapin: BLE/seri uzerinden ayar degisikligi kapanir (sartname: finalde parametre degismez) ----
static bool FREEZE = false;

static Mpu6050 imu;
static PcntCounter encL, encR, irL, irR;
static Motors motors;
static RobotLogic logic;
static Preferences prefs;

static SemaphoreHandle_t imuSem;
static portMUX_TYPE telemMux = portMUX_INITIALIZER_UNLOCKED;
static char telemJson[2][320];
static volatile int telemIdx = 0;
static volatile uint32_t loopMaxUs = 0, imuErrors = 0, overruns = 0;
static volatile int pendingTask = -1, pendingGlove = -1;
static volatile float pendingOffset = NAN;
static volatile int motorTestTicks = 0;  // mtest: once sol, sonra sag teker 1'er s ileri
static float vbatScale = 1.0f;

static void IRAM_ATTR onImuInt() {
  BaseType_t woke = pdFALSE;
  xSemaphoreGiveFromISR(imuSem, &woke);
  if (woke) portYIELD_FROM_ISR();
}

static void controlTask(void*) {
  RobotInputs in;
  uint32_t tick = 0, seq = 0;
  float vbat = 11.1f, vchg = 0;
  int failStreak = 0;
  const uint32_t t0 = micros();
  for (;;) {
    // veri-hazir kesmesi 5 ms'de bir gelir; 10 ms'de gelmezse yine de oku
    if (xSemaphoreTake(imuSem, pdMS_TO_TICKS(10)) != pdTRUE) overruns = overruns + 1;
    const uint32_t ts = micros();

    if (imu.read(in.imu)) {
      failStreak = 0;
    } else {
      imuErrors = imuErrors + 1;
      if (++failStreak >= 3) {  // IMU yok: guvenli taraf
        motors.set(false, 0, 0);
        continue;
      }
    }
    in.t = (ts - t0) * 1e-6f;
    in.encL = encL.read();
    in.encR = encR.read();
    in.irL = irL.read();
    in.irR = irR.read();
    if (tick % 4 == 0) {  // ADC 50 Hz
      vbat = readVolts(PIN_VBAT, vbatScale);
      vchg = readVolts(PIN_VCHG, vbatScale);
    }
    in.vbat = vbat;
    in.vcharge = vchg;
    in.motorPower = !HAS_MOTOR_SENSE || digitalRead(PIN_MOTOR_SENSE);
    in.gloveNew = gloverx::poll(in.glove);

    if (pendingTask >= 0) { logic.setTask((Task)pendingTask); pendingTask = -1; }
    if (pendingGlove >= 0) { logic.setGloveMode((GloveMode)pendingGlove); pendingGlove = -1; }
    if (!isnan(pendingOffset)) { logic.setPitchOffset(pendingOffset); pendingOffset = NAN; }

    RobotOutputs out = logic.step(in);
    if (motorTestTicks > 0) {
      // yalniz BEKLE modunda ve tekerler havadayken; %15 ileri, ters takilma bayraklari uygulanmis
      if (logic.mode() == Mode::STANDBY) {
        const float d = 0.15f;
        const bool left = motorTestTicks > 200;
        out.motorEnable = true;
        out.dutyL = left ? (cfg::MOTOR_LEFT_INVERT ? -d : d) : 0;
        out.dutyR = left ? 0 : (cfg::MOTOR_RIGHT_INVERT ? -d : d);
      }
      motorTestTicks = motorTestTicks - 1;
    }
    motors.set(out.motorEnable, out.dutyL, out.dutyR);

    // 1 Hz telemetri: JSON'u burada uret, radyo gorevi kopyalar
    if (++tick % 200 == 0) {
      int w = telemIdx ^ 1;
      logic.telemetryJson(telemJson[w], sizeof(telemJson[w]), seq++);
      portENTER_CRITICAL(&telemMux);
      telemIdx = w;
      portEXIT_CRITICAL(&telemMux);
    }
    digitalWrite(PIN_LED, logic.mode() == Mode::BALANCE || logic.mode() == Mode::DOCK ? HIGH : ((tick / 50) & 1));
    uint32_t dt = micros() - ts;
    if (dt > loopMaxUs) loopMaxUs = dt;
  }
}

// Seri ve BLE icin ortak metin komutlari
static void handleCommand(const char* c, Print& out) {
  if (!strncmp(c, "task=", 5)) {
    int t = atoi(c + 5);
    if (t >= 0 && t <= 3) {
      pendingTask = t;
      prefs.putUChar("task", t);
      out.printf("ok gorev=%s\n", taskName((Task)t));
    }
    return;
  }
  if (!strcmp(c, "mtest")) {
    motorTestTicks = 400;
    out.println("motor testi: sol 1 s, sag 1 s ileri (tekerler havada olsun)");
    return;
  }
  if (!strcmp(c, "stat")) {
    out.printf("dongu max %lu us, IMU hata %lu, gecikme %lu, eldiven paket %lu (kayip %lu, bozuk %lu), MPU=0x%02X\n",
               (unsigned long)loopMaxUs, (unsigned long)imuErrors, (unsigned long)overruns,
               (unsigned long)gloverx::count, (unsigned long)gloverx::lost, (unsigned long)gloverx::bad, imu.whoAmI);
    loopMaxUs = 0;
    return;
  }
  if (FREEZE) {
    out.println("FREEZE: ayar degisikligi kapali");
    return;
  }
  if (!strncmp(c, "glove=", 6)) {
    int m = !strcmp(c + 6, "cont") ? 1 : 0;
    pendingGlove = m;
    prefs.putUChar("glove", m);
    out.printf("ok eldiven modu=%s\n", m ? "surekli" : "adim");
  } else if (!strcmp(c, "cal")) {
    // Robotu elle denge noktasinda (en az caba ile durdugu acida) tutun, sonra "cal" yazin.
    float raw = logic.thetaDeg() + prefs.getFloat("ofs", 0);
    pendingOffset = raw * DEG;
    prefs.putFloat("ofs", raw);
    out.printf("ok egim ofseti=%.2f deg\n", raw);
  } else if (!strncmp(c, "vscale=", 7)) {
    vbatScale = atof(c + 7);
    prefs.putFloat("vscale", vbatScale);
    out.printf("ok pil olcek=%.4f\n", vbatScale);
  } else {
    out.println("komutlar: stat | mtest | task=0..3 | glove=step|cont | cal | vscale=1.000");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  if (HAS_MOTOR_SENSE) pinMode(PIN_MOTOR_SENSE, INPUT);
  motors.begin();  // once motorlari kapali konuma al
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);
  analogSetPinAttenuation(PIN_VCHG, ADC_11db);

  prefs.begin("cdtp", false);
  logic.setTask((Task)prefs.getUChar("task", (uint8_t)Task::INTEGRATED));
  logic.setGloveMode((GloveMode)prefs.getUChar("glove", 0));
  logic.setPitchOffset(prefs.getFloat("ofs", cfg::PITCH_OFFSET_DEG_DEFAULT) * DEG);
  vbatScale = prefs.getFloat("vscale", 1.0f);

  if (!imu.begin()) {
    Serial.println("HATA: MPU6050 bulunamadi (SDA=21, SCL=22, AD0=GND?)");
    for (;;) { digitalWrite(PIN_LED, !digitalRead(PIN_LED)); delay(100); }
  }
  Serial.println("Jiroskop kalibrasyonu: robotu kipirdatmayin...");
  while (!imu.calibrateGyro()) Serial.println("  hareket algilandi, tekrar");
  Serial.printf("  bias: %.4f %.4f %.4f rad/s\n", imu.bias[0], imu.bias[1], imu.bias[2]);

  encL.beginQuadrature(PCNT_UNIT_0, PIN_ENC_L_A, PIN_ENC_L_B, 100);
  encR.beginQuadrature(PCNT_UNIT_1, PIN_ENC_R_A, PIN_ENC_R_B, 100);
  irL.beginFallingEdges(PCNT_UNIT_2, PIN_IR_L, 1023);
  irR.beginFallingEdges(PCNT_UNIT_3, PIN_IR_R, 1023);

  if (!gloverx::begin()) Serial.println("HATA: ESP-NOW baslatilamadi");
  Serial.printf("Robot MAC (eldiven firmware'ine yazin): %s, kanal %d\n", WiFi.macAddress().c_str(), ESPNOW_CHANNEL);
  ble::begin("CDTP-Robot");

  snprintf(telemJson[0], sizeof telemJson[0], "{}");
  imuSem = xSemaphoreCreateBinary();
  pinMode(PIN_IMU_INT, INPUT);
  attachInterrupt(PIN_IMU_INT, onImuInt, RISING);
  xTaskCreatePinnedToCore(controlTask, "ctl", 6144, nullptr, configMAX_PRIORITIES - 1, nullptr, 1);
  Serial.println("Hazir. Robotu elle dik tutun: 0,5 s sonra dengeye girer.");
}

void loop() {
  static uint32_t lastTel = 0;
  static char line[64];
  static int n = 0;
  // 1 Hz: BLE bildirimi + seri kopya
  if (millis() - lastTel >= 1000) {
    lastTel = millis();
    char buf[320];
    portENTER_CRITICAL(&telemMux);
    memcpy(buf, telemJson[telemIdx], sizeof buf);
    portEXIT_CRITICAL(&telemMux);
    ble::publish(buf);
    Serial.println(buf);
  }
  if (ble::cmdReady) {
    handleCommand(ble::cmdBuf, Serial);
    ble::cmdReady = false;
  }
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) { line[n] = 0; handleCommand(line, Serial); n = 0; }
    } else if (n < (int)sizeof(line) - 1) {
      line[n++] = ch;
    }
  }
  delay(5);
}
