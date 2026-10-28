// Simulasyon duzenegi: fiziksel model + istasyon IR isareti + eldiven paketleri + robot mantigi.
#pragma once
#include <cstdio>
#include <functional>
#include <string>
#include <vector>

#include "plant.h"
#include "robot_logic.h"

struct GloveEvent {
  double t;
  cdtp::Cmd cmd;  // bu andan itibaren eldivenin yolladigi komut
};

struct Trace {
  double t, x, v, th, psi, X, Y, dutyL, dutyR;
  int mode, dock, nL, nR;
};

class Harness {
 public:
  Harness(const PlantParams& pp, unsigned seed = 1) : plant(pp, seed), rng_(seed * 7919u + 13) {}

  Plant plant;
  cdtp::RobotLogic logic;
  cdtp::RobotOutputs out;
  std::vector<Trace> trace;
  bool record = false;

  // istasyon: dunya orijininde, yuzu +X'e bakar
  bool stationOn = false;
  bool docked = false;       // plakalar pogo'ya degiyor
  bool hitWallBad = false;   // istasyona yanlis aciyla carpti
  double dockTime = -1, chargeStart = -1;
  double frontOffset = 0.06;  // robot merkezinden on yuze
  double eyeAxisDeg = 15;     // gozlerin disa bakis acisi (+-)
  double eyeHalfDeg = 30;     // goz tupunun kabul yari acisi

  // eldiven
  std::vector<GloveEvent> glove;
  bool gloveOn = false;
  double gloveLoss = 0.03;    // paket kaybi orani
  double gloveCutFrom = 1e9, gloveCutTo = -1;  // bu aralikta baglanti yok

  bool motorPower = true;  // acil stop sonrasi hat
  double t = 0;

  void run(double duration, const std::function<void(Harness&)>& each = nullptr) {
    const int sub = 10;  // fizik 2 kHz
    const double dtc = cdtp::cfg::DT, dtp = dtc / sub;
    const double tEnd = t + duration;
    while (t < tEnd - 1e-9) {
      // --- sensorler ---
      cdtp::RobotInputs in;
      in.t = (float)t;
      in.imu = plant.imu(out.motorEnable);
      in.encL = plant.encCount(false);
      in.encR = plant.encCount(true);
      in.vbat = (float)(plant.vbat + noise() * 0.02);
      in.vcharge = docked ? 12.4f : 0.0f;
      in.irL = irCount_[0];
      in.irR = irCount_[1];
      in.motorPower = motorPower;
      gloveInput(in);
      out = logic.step(in);
      if (logic.mode() == cdtp::Mode::CHARGING && docked && chargeStart < 0) chargeStart = t;
      // --- fizik ---
      double dl = out.dutyL * (cdtp::cfg::MOTOR_LEFT_INVERT ? -1 : 1);
      double dr = out.dutyR * (cdtp::cfg::MOTOR_RIGHT_INVERT ? -1 : 1);
      dl = std::round(dl * 1023) / 1023;  // 10 bit PWM
      dr = std::round(dr * 1023) / 1023;
      for (int i = 0; i < sub; ++i) {
        plant.step(dl, dr, out.motorEnable && motorPower, dtp);
        t += dtp;
        beacon(t);
        stationContact();
      }
      if (record) {
        trace.push_back({t, plant.x, plant.v, plant.th, plant.psi, plant.X, plant.Y, out.dutyL, out.dutyR,
                         (int)logic.mode(), (int)logic.dockState(), logic.irNL(), logic.irNR()});
      }
      if (each) each(*this);
    }
  }

  void writeCsv(const std::string& path) const {
    FILE* f = std::fopen(path.c_str(), "w");
    if (!f) return;
    std::fprintf(f, "t,x,v,theta_deg,psi_deg,X,Y,dutyL,dutyR,mode,dock,nL,nR\n");
    for (const auto& s : trace)
      std::fprintf(f, "%.4f,%.4f,%.4f,%.3f,%.2f,%.4f,%.4f,%.3f,%.3f,%d,%d,%d,%d\n", s.t, s.x, s.v,
                   s.th * 180 / M_PI, s.psi * 180 / M_PI, s.X, s.Y, s.dutyL, s.dutyR, s.mode, s.dock, s.nL, s.nR);
    std::fclose(f);
  }

 private:
  std::mt19937 rng_;
  int32_t irCount_[2] = {0, 0};
  double nextBurst_ = 0;
  uint16_t seq_ = 0;
  double nextPacket_ = 0;

  double noise() {
    std::normal_distribution<double> n(0, 1);
    return n(rng_);
  }
  double uni() {
    std::uniform_real_distribution<double> u(0, 1);
    return u(rng_);
  }

  // Istasyon isareti: 78 ms cerceve, ilk 45 ms'de ~1 kHz patlama (44 adet), sonra 33 ms sessizlik
  void beacon(double now) {
    if (!stationOn) return;
    while (nextBurst_ <= now) {
      const double phase = std::fmod(nextBurst_, 0.078);
      if (phase < 0.045) {
        for (int e = 0; e < 2; ++e)
          if (uni() < eyeGain(e)) irCount_[e]++;
      }
      nextBurst_ += 0.0010122;
      if (std::fmod(nextBurst_, 0.078) >= 0.045) nextBurst_ = (std::floor(nextBurst_ / 0.078) + 1) * 0.078;
    }
  }

  // goz kazanci: 0..1 (patlamayi algilama olasiligi)
  double eyeGain(int eye) const {
    const double fx = plant.X + frontOffset * std::cos(plant.psi), fy = plant.Y + frontOffset * std::sin(plant.psi);
    const double dist = std::hypot(fx, fy);
    if (dist > 1.2 || fx < -0.01) return 0;
    const double gamma = std::atan2(fy, fx);  // istasyon normaline gore robotun acisi
    const double emit = std::max(0.0, 1 - std::pow(gamma / (70 * M_PI / 180), 2));
    double bearing = std::atan2(-fy, -fx) - plant.psi;  // istasyonun robota gore yonu, sola +
    while (bearing > M_PI) bearing -= 2 * M_PI;
    while (bearing < -M_PI) bearing += 2 * M_PI;
    const double axis = (eye == 0 ? eyeAxisDeg : -eyeAxisDeg) * M_PI / 180;
    const double acc = std::max(0.0, 1 - std::pow((bearing - axis) / (eyeHalfDeg * M_PI / 180), 2));
    const double g = emit * acc;
    if (g < 0.12) return 0;  // alici esigi
    return std::min(1.0, g * 1.4);
  }

  // Istasyon: orijinde dikey yuvarlak direk (cap 40 mm), uzerinde iki bakir halka (ust +, alt -) ve IR isaret.
  // Robotun onunde V-yuva var; yuvanin icindeki iki yayli pim halkalara degir. Direk yuvarlak oldugu icin
  // yaklasma acisi onemsizdir; V-yuva yanal +-3 cm hatayi kendisi ortalar.
  void stationContact() {
    if (!stationOn) return;
    const double fx = plant.X + frontOffset * std::cos(plant.psi), fy = plant.Y + frontOffset * std::sin(plant.psi);
    // direk merkezinin robot eksenine gore konumu
    const double dx = -fx, dy = -fy;
    const double along = dx * std::cos(plant.psi) + dy * std::sin(plant.psi);
    const double lateral = -dx * std::sin(plant.psi) + dy * std::cos(plant.psi);
    const double postR = 0.02;
    const bool touching = along <= postR + 0.003 && along > -0.05 && std::fabs(lateral) < 0.09;
    if (touching) {
      if (std::fabs(lateral) < 0.03) {
        if (!docked) dockTime = t;
        docked = true;
      } else {
        hitWallBad = true;  // yuvanin disindan, govde kenariyla carpti
      }
      if (plant.th > 6 * M_PI / 180) {  // direge yaslanir
        plant.th = 6 * M_PI / 180;
        if (plant.om > 0) plant.om = 0;
      }
      if (plant.v > 0) plant.v = 0;  // direk ileri gitmeyi engeller
    } else if (docked && along > postR + 0.01) {
      docked = false;
    }
  }

  void gloveInput(cdtp::RobotInputs& in) {
    in.gloveNew = false;
    if (!gloveOn || t < nextPacket_) return;
    nextPacket_ = t + 0.05;  // 20 Hz
    if (t >= gloveCutFrom && t <= gloveCutTo) return;
    if (uni() < gloveLoss) return;
    cdtp::Cmd c = cdtp::Cmd::STOP;
    for (const auto& e : glove)
      if (e.t <= t) c = e.cmd;
    cdtp::GlovePacket p{};
    p.cmd = (uint8_t)c;
    p.seq = seq_++;
    cdtp::sealPacket(p);
    cdtp::GlovePacket chk;
    if (cdtp::checkPacket(reinterpret_cast<const uint8_t*>(&p), sizeof(p), chk)) {
      in.gloveNew = true;
      in.glove = chk;
    }
  }
};
