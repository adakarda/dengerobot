// OTOMATIK URETILDI: tools/lqr_design.py. Elle degistirmeyin; modeli guncelleyip yeniden calistirin.
// Durum: [x (m), v (m/s), theta (rad), omega (rad/s)], cikis: her motora gerilim (V).
// u = -K (s - s_ref)
#pragma once
namespace cdtp {
namespace gains {
constexpr float K_X = -54.19472f;
constexpr float K_V = -66.49182f;
constexpr float K_TH = -108.21176f;
constexpr float K_OM = -13.45884f;
constexpr float YAW_KP = 2.94737f;
constexpr float YAW_KD = 0.66316f;
// a_ref -> egim on-besleme (rad / (m/s^2))
constexpr float TH_PER_ACC = 0.16133f;
// Durum gozleyicisi (state_observer.h): s = [x, v, theta, omega, d]
// s- = AD s + BD u ; s = s- + OBS_L (z - C s-), z = [x, theta, omega]. OBS = {'sa': 4.0, 'salpha': 80.0, 'rx': 0.002, 'rth_deg': 0.1, 'rom_dps': 0.3, 'sd': 4.0}
constexpr float AD[5][5] = {{1.0f, 0.004780482f, -4.271112e-05f, 7.610983e-06f, 2.981815e-05f}, {0.0f, 0.91388f, -0.0166229f, 0.002971487f, 0.01169805f}, {0.0f, 0.001833331f, 1.001004f, 0.004937514f, -0.0002490295f}, {0.0f, 0.719321f, 0.3977034f, 0.9758276f, -0.09770854f}, {0.0f, 0.0f, 0.0f, 0.0f, 1.0f}};
constexpr float BD[1][5] = {{2.981815e-05f, 0.01169805f, -0.0002490295f, -0.09770854f, 0.0f}};
constexpr float OBS_L[5][3] = {{0.6258486f, 0.1877882f, 5.461394e-06f}, {62.53093f, 26.2356f, 0.001250655f}, {0.1430089f, 0.3138479f, 3.276997e-06f}, {3.74318e-05f, 2.949297e-05f, 0.9999991f}, {51.76157f, -127.6896f, -0.001283269f}};
}  // namespace gains
}  // namespace cdtp
