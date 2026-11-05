// OTOMATIK URETILDI: tools/lqr_design.py
#pragma once
struct PlantNominal {
  static constexpr double m_body = 1.245;
  static constexpr double l_com = 0.0702;
  static constexpr double I_body = 0.00737;
  static constexpr double m_wheel = 0.07;
  static constexpr double r = 0.035;
  static constexpr double J_rotor = 5e-07;
  static constexpr double gear = 19.0;
  static constexpr double Ke = 0.216;
  static constexpr double R = 4.5;
  static constexpr double b_visc = 0.002;
  static constexpr double tau_coulomb = 0.02;
  static constexpr double track = 0.19;
  static constexpr double I_yaw = 0.012;
  static constexpr double vbat = 11.1;
};
