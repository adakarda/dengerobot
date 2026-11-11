// Robot parametreleri. "OLC" yazanlar parca gelince olculup guncellenecek.
// Bu dosya hem firmware'de hem simulasyonda ayni degerlerle kullanilir.
#pragma once

#ifndef CDTP_TILT_KALMAN
#define CDTP_TILT_KALMAN 0
#endif
// LQR girdisi. 0: enkoder farki + egim filtresi (varsayilan). 1: v, theta, omega duragan Kalman gozleyicisinden
// (state_observer.h, LQG). 2: yalniz v gozleyiciden. 1 ve 2 simulasyonda kabul testlerini bozuyor: docs/KALMAN_FILTRE.md
#ifndef CDTP_LQG
#define CDTP_LQG 0
#endif

namespace cdtp {
namespace cfg {

// ---- Mekanik (OLC) ----
constexpr float WHEEL_RADIUS_M   = 0.0325f;  // 65 mm x 28 mm kucuk arazi tekerlegi (olculdu)
constexpr float TRACK_WIDTH_M    = 0.270f;   // iki teker orta cizgisi arasi (olculdu: en distan en disa 298 mm - 28 mm)
constexpr float ENC_COUNTS_PER_REV = 836.0f; // 11 darbe x ~19 disli x 4 kenar (OLC: tekeri 10 tur cevir)
constexpr bool  ENC_LEFT_INVERT  = false;
constexpr bool  ENC_RIGHT_INVERT = true;     // sag motor ayna takili
constexpr bool  MOTOR_LEFT_INVERT  = false;
constexpr bool  MOTOR_RIGHT_INVERT = true;

// ---- Dongu ----
constexpr float LOOP_HZ = 200.0f;
constexpr float DT      = 1.0f / LOOP_HZ;

// ---- IMU filtresi ----
constexpr float COMP_ALPHA = 0.98f;           // tumleyen filtre: 0.98 jiroskop, 0.02 ivme
constexpr float PITCH_OFFSET_DEG_DEFAULT = 0.0f; // denge noktasi ofseti (NVS'ten yuklenir)
// Kalman egim filtresi (imu_filter.h TiltKalman). Derlemede -DCDTP_TILT_KALMAN=1 ile secilir; varsayilan tumleyen.
// Degerler sim/filtre_karsilastir.cpp izgara aramasiyla secildi (tools/run_filtre.sh): q_theta 1e-8..1e-7,
// r_acc 0.0016..0.025, q_bias 1e-13..1e-9 arasi duz bir plato (~0.25 deg RMS). Platonun ortasi; q_bias gercek
// robotta sicaklikla bias kaymasini izleyebilsin diye platonun ust ucunda.
constexpr float KF_Q_THETA   = 1.0e-7f;   // rad^2/s (jiro gurultusu 0.05 deg/s -> sigma^2*dt ~ 4e-9)
constexpr float KF_Q_BIAS    = 1.0e-9f;   // (rad/s)^2/s
constexpr float KF_R_ACC     = 6.4e-3f;   // rad^2 (~4.6 deg: titresim + hareket ivmesi dahil)
constexpr float KF_R_ACC_BAD = 1.0f;      // rad^2, ivme 1 g'den saparken
constexpr float KF_P0_BIAS   = 7.6e-5f;   // (0.5 deg/s)^2

// ---- Motor / guc ----
constexpr float VBAT_NOMINAL   = 11.1f;
constexpr float VBAT_EMPTY     = 9.9f;        // 3.3 V/hucre
constexpr float VBAT_FULL      = 12.6f;
constexpr float DUTY_MAX       = 0.95f;
constexpr float MOTOR_DEADBAND_V = 0.45f;     // kucuk gerilimde dislinin donmemesi (OLC)
constexpr float MOTOR_KE       = 0.216f;      // V/(rad/s), cikis milinde: 12 V / 55.5 rad/s (530 RPM)

// ---- Kontrol ----
constexpr float TRIM_RATE = 0.1f;      // rad/(m s): dururken denge acisi ogrenme hizi
constexpr float TRIM_MAX_DEG = 3.0f;   // ogrenilen aci siniri
constexpr float REF_SHAPING_W = 5.0f;  // rad/s, konum referansi suzgeci
constexpr float TH_FF_GAIN = 1.0f;   // ivme -> egim on-beslemesinin ne kadari kullanilsin (sim ile secildi)

// ---- Guvenlik ----
constexpr float FALL_ANGLE_DEG    = 40.0f;    // bunun ustunde motorlar kapanir
constexpr float FALL_HOLD_S       = 0.05f;
constexpr float ARM_ANGLE_DEG     = 3.0f;     // elle dik tutulunca bu acida dengeye girer
constexpr float ARM_HOLD_S        = 0.5f;
constexpr float GLOVE_TIMEOUT_S   = 0.30f;    // bu sure paket yoksa dur

// ---- Hareket ----
constexpr float STEP_DIST_M     = 0.50f;      // ileri/geri komutu basina yol
constexpr float STEP_VMAX       = 0.25f;      // m/s
constexpr float STEP_ACCEL      = 0.40f;      // m/s^2
constexpr float TURN_ANGLE_DEG  = 90.0f;
constexpr float TURN_RATE_DEG   = 90.0f;      // deg/s
constexpr float TURN_ACCEL_DEG  = 240.0f;     // deg/s^2
constexpr float CONT_V          = 0.20f;      // surekli modda hiz
constexpr float CONT_YAW_DEG    = 60.0f;      // surekli modda donus hizi

// ---- Yanasma ----
constexpr float DOCK_SEARCH_YAW_DEG = 30.0f;
constexpr float DOCK_ALIGN_K_DEG    = 40.0f;  // e=1 icin deg/s
constexpr float DOCK_ALIGN_TOL      = 0.25f;
constexpr float DOCK_APPROACH_V     = 0.08f;
constexpr int   DOCK_MIN_COUNT      = 6;      // bir gozun "gordu" sayilmasi icin cerceve basina darbe
constexpr float DOCK_TRIGGER_S      = 1.0f;   // gozlerden biri isareti bu kadar gorurse yanasmaya gec
constexpr float DOCK_IDLE_S         = 6.0f;   // eldiven bu kadar "dur"daysa yanasma serbest (hedefte 5 s bekleme bozulmasin)
constexpr float DOCK_LOST_S         = 1.0f;
constexpr float DOCK_TIMEOUT_S      = 60.0f;
constexpr float UNDOCK_HOLD_S       = 10.0f;  // eldivenle istasyondan ayrilinca bu sure yeniden yanasmaz
constexpr float CHARGE_DETECT_V     = 9.0f;   // plakada bu gerilim varsa sarj var
constexpr float CHARGE_CONFIRM_S    = 0.10f;
constexpr float DOCK_LEAN_DEG       = 4.0f;   // motor kesmeden once sirta dogru egilme

// ---- Eldiven jest ----
constexpr float GEST_ENTER_DEG   = 25.0f;
constexpr float GEST_EXIT_DEG    = 15.0f;
constexpr float GEST_NEUTRAL_DEG = 12.0f;
constexpr float GEST_HOLD_S      = 0.15f;     // komuta girmek icin bekleme
constexpr float GEST_NEUTRAL_S   = 0.20f;

}  // namespace cfg
}  // namespace cdtp
