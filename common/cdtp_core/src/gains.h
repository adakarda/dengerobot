// OTOMATIK URETILDI: tools/lqr_design.py. Elle degistirmeyin; modeli guncelleyip yeniden calistirin.
// Durum: [x (m), v (m/s), theta (rad), omega (rad/s)], cikis: her motora gerilim (V).
// u = -K (s - s_ref)
#pragma once
namespace cdtp {
namespace gains {
constexpr float K_X = -53.04604f;
constexpr float K_V = -65.55542f;
constexpr float K_TH = -108.55007f;
constexpr float K_OM = -13.48660f;
constexpr float YAW_KP = 2.73684f;
constexpr float YAW_KD = 0.61579f;
// a_ref -> egim on-besleme (rad / (m/s^2))
constexpr float TH_PER_ACC = 0.15425f;
}  // namespace gains
}  // namespace cdtp
