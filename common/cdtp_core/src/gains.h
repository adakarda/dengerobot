// OTOMATIK URETILDI: tools/lqr_design.py. Elle degistirmeyin; modeli guncelleyip yeniden calistirin.
// Durum: [x (m), v (m/s), theta (rad), omega (rad/s)], cikis: her motora gerilim (V).
// u = -K (s - s_ref)
#pragma once
namespace cdtp {
namespace gains {
constexpr float K_X = -50.52522f;
constexpr float K_V = -62.56646f;
constexpr float K_TH = -107.93807f;
constexpr float K_OM = -13.48481f;
constexpr float YAW_KP = 1.05926f;
constexpr float YAW_KD = 0.23833f;
// a_ref -> egim on-besleme (rad / (m/s^2))
constexpr float TH_PER_ACC = 0.14518f;
// Durum gozleyicisi (state_observer.h): s = [x, v, theta, omega, d]
// s- = AD s + BD u ; s = s- + OBS_L (z - C s-), z = [x, theta, omega]. OBS = {'sa': 4.0, 'salpha': 80.0, 'rx': 0.002, 'rth_deg': 0.1, 'rom_dps': 0.3, 'sd': 4.0}
constexpr float AD[5][5] = {{1.0f, 0.004709966f, -5.544826e-05f, 9.332192e-06f, 3.658259e-05f}, {0.0f, 0.8868447f, -0.02146678f, 0.0036221f, 0.0142725f}, {0.0f, 0.002204368f, 1.001076f, 0.004930162f, -0.0002780413f}, {0.0f, 0.8601216f, 0.4249614f, 0.9731219f, -0.1084888f}, {0.0f, 0.0f, 0.0f, 0.0f, 1.0f}};
constexpr float BD[1][5] = {{3.658259e-05f, 0.0142725f, -0.0002780413f, -0.1084888f, 0.0f}};
constexpr float OBS_L[5][3] = {{0.6003015f, 0.2083024f, 6.136945e-06f}, {58.16691f, 29.15027f, 0.001409996f}, {0.1586314f, 0.3479616f, 4.124033e-06f}, {4.206196e-05f, 3.71163e-05f, 0.9999991f}, {59.88981f, -121.9428f, -0.001265873f}};
}  // namespace gains
}  // namespace cdtp
