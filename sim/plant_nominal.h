// OTOMATIK URETILDI: tools/lqr_design.py
#pragma once
struct PlantNominal {
  static constexpr double m_body = 1.25;
  static constexpr double l_com = 0.1;
  static constexpr double I_body = 0.0065;
  static constexpr double m_wheel = 0.045;
  static constexpr double r = 0.0325;
  static constexpr double J_rotor = 5e-07;
  static constexpr double gear = 19.0;
  static constexpr double Ke = 0.216;
  static constexpr double R = 4.5;
  static constexpr double b_visc = 0.002;
  static constexpr double tau_coulomb = 0.02;
  static constexpr double track = 0.17;
  static constexpr double I_yaw = 0.012;
  static constexpr double vbat = 11.1;
};
