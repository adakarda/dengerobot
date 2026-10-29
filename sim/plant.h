// Iki tekerlekli ters sarkac + DC motor + sensor modeli. Yalniz PC simulasyonu icin.
#pragma once
#include <cmath>
#include <random>

#include "cdtp_config.h"
#include "plant_nominal.h"
#include "robot_logic.h"

struct PlantParams {
  double m_body = PlantNominal::m_body, l_com = PlantNominal::l_com, I_body = PlantNominal::I_body;
  double m_wheel = PlantNominal::m_wheel, r = PlantNominal::r, J_rotor = PlantNominal::J_rotor, gear = PlantNominal::gear;
  double Ke = PlantNominal::Ke, R = PlantNominal::R, b_visc = PlantNominal::b_visc, tau_c = PlantNominal::tau_coulomb;
  double track = PlantNominal::track, I_yaw = PlantNominal::I_yaw;
  double voc = 12.0, r_int = 0.15;   // paket bos gerilim, ic direnc
  double box_mass = 0.06, box_h = 0.215;  // ilac kutusu (eksenden yukseklik)
  double h_imu = 0.05;               // IMU'nun eksenden yuksekligi
  double imu_offset_deg = 0.0;       // IMU montaj hatasi
  double gyro_bias_dps = 0.0;        // kalibrasyon sonrasi kalan bias
  double gyro_noise_dps = 0.05, acc_noise = 0.03;  // rms
  double vib_acc = 0.3;              // motor titresimi (m/s^2 rms, motor gerilimiyle olcekli)
  double backlash_deg = 0.0;         // (kullanilmiyor) disli boslugu
};

class Plant {
 public:
  explicit Plant(const PlantParams& p, unsigned seed = 1) : p_(p), rng_(seed) {
    // kutu govdeye eklenir: toplam kutle ve kutle merkezi
    mb_ = p.m_body + p.box_mass;
    l_ = (p.m_body * p.l_com + p.box_mass * p.box_h) / mb_;
    Ib_ = p.I_body + p.m_body * (p.l_com - l_) * (p.l_com - l_) + p.box_mass * (p.box_h - l_) * (p.box_h - l_);
  }

  // durum
  double x = 0, v = 0, th = 0, om = 0, psi = 0, r = 0;  // r: sapma hizi
  double X = 0, Y = 0;                                  // dunya konumu
  double xl = 0, xr = 0;                                 // teker yollari
  double iL = 0, iR = 0, vbat = 12.0;
  bool lying = false;

  // dt boyunca motor gerilimleriyle ilerle (enable=false: surucu yuksek empedans)
  void step(double dutyL, double dutyR, bool enable, double dt) {
    const double r_ = p_.r;
    const double Iw = 2 * 0.5 * p_.m_wheel * r_ * r_;
    const double Jm = 2 * p_.J_rotor * p_.gear * p_.gear;
    const double vl = v - r * p_.track / 2, vr = v + r * p_.track / 2;
    const double wl = vl / r_ - om, wr = vr / r_ - om;  // bagil mil hizi
    auto torque = [&](double duty, double w, double& cur) {
      double t;
      if (enable) {
        double V = duty * vbat;
        cur = (V - p_.Ke * w) / p_.R;
        t = p_.Ke * cur;
      } else {
        cur = 0;
        t = 0;
      }
      return t - p_.b_visc * w - p_.tau_c * std::tanh(w / 0.3);
    };
    const double tl = torque(dutyL, wl, iL), tr = torque(dutyR, wr, iR);
    vbat = p_.voc - p_.r_int * (std::fabs(iL) + std::fabs(iR));
    const double tau = tl + tr;

    if (lying) {  // yere dustu: tekerler yerinde
      v *= 0.9;
      om = 0;
      r = 0;
      return;
    }
    const double a = 2 * p_.m_wheel * r_ * r_ + Iw + mb_ * r_ * r_ + Jm;
    const double c = mb_ * l_ * l_ + Ib_ + Jm;
    const double bc = mb_ * r_ * l_ * std::cos(th) - Jm;
    const double f1 = tau + mb_ * r_ * l_ * std::sin(th) * om * om;
    const double f2 = -tau + mb_ * 9.81 * l_ * std::sin(th);
    const double det = a * c - bc * bc;
    const double phidd = (c * f1 - bc * f2) / det;
    const double thdd = (a * f2 - bc * f1) / det;
    // sapma
    const double Iy = p_.I_yaw + (p_.track * p_.track / (4 * r_ * r_)) * (Iw + Jm);
    const double rd = ((p_.track / (2 * r_)) * (tr - tl) - 0.02 * r) / Iy;

    v += r_ * phidd * dt;
    om += thdd * dt;
    r += rd * dt;
    x += v * dt;
    th += om * dt;
    psi += r * dt;
    xl += (v - r * p_.track / 2) * dt;
    xr += (v + r * p_.track / 2) * dt;
    X += v * std::cos(psi) * dt;
    Y += v * std::sin(psi) * dt;
    accX_ = r_ * phidd;
    thdd_ = thdd;
    if (std::fabs(th) > 80 * M_PI / 180) lying = true;
  }

  // IMU olcumu (ham eksen, MPU6050 X ileri / Y sol / Z yukari): acc[0]=ileri, acc[2]=yukari, gyro[1]=+yunuslama, gyro[2]=sapma
  cdtp::ImuSample imu(bool motorsOn) {
    std::normal_distribution<double> n(0, 1);
    const double h = p_.h_imu;
    // IMU noktasinin ivmesi (dunya: ileri, yukari)
    const double ax = accX_ + h * (thdd_ * std::cos(th) - om * om * std::sin(th));
    const double az = h * (-thdd_ * std::sin(th) - om * om * std::cos(th));
    const double fx = ax, fz = az + 9.81;
    const double thm = th + p_.imu_offset_deg * M_PI / 180;
    double fwd = fx * std::cos(thm) - fz * std::sin(thm);
    double up = fx * std::sin(thm) + fz * std::cos(thm);
    const double vib = motorsOn ? p_.vib_acc * (0.3 + std::fabs(iL + iR) / 2) : 0;
    fwd += (p_.acc_noise + vib) * n(rng_);
    up += (p_.acc_noise + vib) * n(rng_);
    double side = (p_.acc_noise + vib) * n(rng_);
    const double gn = p_.gyro_noise_dps * M_PI / 180;
    double gp = om + p_.gyro_bias_dps * M_PI / 180 + gn * n(rng_);
    double gy = r + gn * n(rng_);
    // MPU6050 DLPF (~42 Hz) birinci derece
    const double a = 1.0 - std::exp(-2 * M_PI * 42.0 / 200.0);
    f_[0] += a * (fwd - f_[0]);
    f_[1] += a * (side - f_[1]);
    f_[2] += a * (up - f_[2]);
    f_[3] += a * (gp - f_[3]);
    f_[4] += a * (gy - f_[4]);
    cdtp::ImuSample s;
    s.acc[0] = (float)f_[0];
    s.acc[1] = (float)f_[1];
    s.acc[2] = (float)f_[2];
    s.gyro[0] = 0;
    s.gyro[1] = (float)f_[3];
    s.gyro[2] = (float)f_[4];
    return s;
  }

  void initFilter() {
    f_[0] = -9.81 * std::sin(th);
    f_[2] = 9.81 * std::cos(th);
  }

  int32_t encCount(bool right) const {
    const double mpc = 2 * M_PI * cdtp::cfg::WHEEL_RADIUS_M / cdtp::cfg::ENC_COUNTS_PER_REV;
    // gercek enkoder teker ile govde arasindaki bagil aciyi sayar: yol - r*theta
    double c = std::floor(((right ? xr : xl) - p_.r * th) / mpc);
    bool inv = right ? cdtp::cfg::ENC_RIGHT_INVERT : cdtp::cfg::ENC_LEFT_INVERT;
    return (int32_t)(inv ? -c : c);
  }

  const PlantParams& params() const { return p_; }

 private:
  PlantParams p_;
  std::mt19937 rng_;
  double mb_, l_, Ib_;
  double accX_ = 0, thdd_ = 0;
  double f_[5] = {0, 0, 9.81, 0, 0};
};
