// Belirsizlik testinin (SAG) rastgele robotlari: ayni dagilimlar, ayni tohum (2026).
// sim_main.cpp testRobust, filtre_karsilastir.cpp ve gozleyici_karsilastir.cpp bunlari kullanir.
#pragma once
#include <random>
#include <vector>

#include "plant.h"

inline std::vector<PlantParams> mcRobots(int n) {
  std::mt19937 g(2026);
  auto U = [&](double a, double b) { return std::uniform_real_distribution<double>(a, b)(g); };
  std::vector<PlantParams> out;
  for (int i = 0; i < n; ++i) {
    PlantParams p;
    p.m_body *= U(0.75, 1.3);
    p.l_com *= U(0.75, 1.6);  // kutle merkezi: tahminin %75'i ile %160'i arasi
    p.I_body *= U(0.7, 1.4);
    p.R *= U(0.8, 1.25);
    p.Ke *= U(0.9, 1.1);
    p.tau_c *= U(0.5, 2.0);
    p.b_visc *= U(0.5, 2.0);
    p.voc = U(10.4, 12.6);
    p.box_mass = U(0.03, 0.10);
    p.imu_offset_deg = U(-1.5, 1.5);
    p.gyro_bias_dps = U(-0.5, 0.5);
    p.h_imu = U(0.0, 0.12);
    out.push_back(p);
  }
  return out;
}

// 5 s dengede bekleme, sonra ileri-geri adimlar, toplam 31 s
inline std::vector<GloveEvent> mcGloveScript() {
  using cdtp::Cmd;
  return {{0, Cmd::STOP},    {6.0, Cmd::FWD},   {6.4, Cmd::STOP},  {9.5, Cmd::FWD},   {9.9, Cmd::STOP},
          {14.0, Cmd::BACK}, {14.4, Cmd::STOP}, {18.0, Cmd::BACK}, {18.4, Cmd::STOP}, {22.0, Cmd::FWD},
          {22.4, Cmd::STOP}};
}
