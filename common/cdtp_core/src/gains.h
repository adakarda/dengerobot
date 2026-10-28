// OTOMATIK URETILDI: tools/lqr_design.py. Elle degistirmeyin; modeli guncelleyip yeniden calistirin.
// Durum: [x (m), v (m/s), theta (rad), omega (rad/s)], cikis: her motora gerilim (V).
// u = -K (s - s_ref)
#pragma once
namespace cdtp {
namespace gains {
constexpr float K_X = -49.00149f;
constexpr float K_V = -60.66344f;
constexpr float K_TH = -108.01479f;
constexpr float K_OM = -13.37860f;
constexpr float YAW_KP = 3.05882f;
constexpr float YAW_KD = 0.68824f;
// a_ref -> egim on-besleme (rad / (m/s^2))
constexpr float TH_PER_ACC = 0.13864f;
}  // namespace gains
}  // namespace cdtp
