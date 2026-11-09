// Durum gozleyicisi (duragan Kalman, LQG) karsilastirmasi: v, theta, omega kestirimi.
// Kapali dongu robotun derlendigi yapilandirmayla kosar; gozleyici adaylari (sim/observer_grid.h) ayni
// olcum ve giris dizisini paralel, acik dongu olarak alir. Gercek: plant.v, IMU egimi, plant.om.
// Gozleyici modeli nominal; robotlar SAG'in 40 rastgele robotu (kutle +-25%, KM -25/+60%, ...): model hatasi
// gercek. 0-19 ayar, 20-39 sinama. Derle ve kos: bash tools/run_gozleyici.sh
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <string>
#include <vector>

#include "harness.h"
#include "mc_robots.h"
#include "observer_grid.h"
#include "state_observer.h"

static const double R2D = 180.0 / M_PI;

struct Sample {
  float u, x, th, om;          // gozleyicinin gordugu: giris ve olcumler
  float vDiff;                 // bugunku hiz: enkoder farki
  double vTrue, thTrue, omTrue;
  bool active;                 // denge modunda
};

static std::vector<Sample> simulate(const PlantParams& p, unsigned seed) {
  std::vector<Sample> s;
  Harness h(p, seed);
  h.logic.setTask(cdtp::Task::GUIDANCE);
  h.gloveOn = true;
  h.glove = mcGloveScript();
  h.plant.initFilter();
  h.run(31.0, [&](Harness& hh) {
    const auto& L = hh.logic;
    const bool act = L.mode() == cdtp::Mode::BALANCE;
    // egim filtresi ofsetsiz kestirir; gercek de IMU egimi (montaj hatasi dahil)
    s.push_back({L.uLast(), L.x(), L.thetaRad(), L.pitchRateRad(), L.vDiff(), hh.plant.v,
                 hh.plant.th + p.imu_offset_deg * M_PI / 180, hh.plant.om, act});
  });
  return s;
}

struct Err {
  double v = 0, th = 0, om = 0;  // RMS: m/s, deg, deg/s
};

// Gozleyicinin girdisi bir onceki adimin u'su: logic.step ayni sirayla kullanir
static Err evalObserver(const std::vector<Sample>& s, const cdtp::StateObserver::Gain& Lg) {
  cdtp::StateObserver o(Lg);
  double ev = 0, et = 0, eo = 0;
  int n = 0;
  float uPrev = 0;
  bool was = false;
  for (size_t i = 0; i < s.size(); ++i) {
    if (!s[i].active) {
      was = false;
      uPrev = 0;
      continue;
    }
    if (!was) o.reset(s[i].x, s[i].vDiff, s[i].th, s[i].om);
    else o.update(uPrev, s[i].x, s[i].th, s[i].om);
    was = true;
    uPrev = s[i].u;
    if (i * cdtp::cfg::DT < 2.0) continue;
    double dv = o.v() - s[i].vTrue, dt = (o.theta() - s[i].thTrue) * R2D, dom = (o.omega() - s[i].omTrue) * R2D;
    ev += dv * dv;
    et += dt * dt;
    eo += dom * dom;
    ++n;
  }
  n = std::max(n, 1);
  return {std::sqrt(ev / n), std::sqrt(et / n), std::sqrt(eo / n)};
}

static Err evalDirect(const std::vector<Sample>& s) {
  double ev = 0, et = 0, eo = 0;
  int n = 0;
  for (size_t i = 0; i < s.size(); ++i) {
    if (!s[i].active || i * cdtp::cfg::DT < 2.0) continue;
    double dv = s[i].vDiff - s[i].vTrue, dt = (s[i].th - s[i].thTrue) * R2D, dom = (s[i].om - s[i].omTrue) * R2D;
    ev += dv * dv;
    et += dt * dt;
    eo += dom * dom;
    ++n;
  }
  n = std::max(n, 1);
  return {std::sqrt(ev / n), std::sqrt(et / n), std::sqrt(eo / n)};
}

template <class F>
static Err mean(const std::vector<std::vector<Sample>>& runs, int a, int b, F f, Err* worst) {
  Err m;
  *worst = Err();
  for (int i = a; i < b; ++i) {
    Err e = f(runs[i]);
    m.v += e.v;
    m.th += e.th;
    m.om += e.om;
    worst->v = std::max(worst->v, e.v);
    worst->th = std::max(worst->th, e.th);
    worst->om = std::max(worst->om, e.om);
  }
  m.v /= (b - a);
  m.th /= (b - a);
  m.om /= (b - a);
  return m;
}

int main(int argc, char** argv) {
  std::string out = argc > 1 ? argv[1] : "sim/results/";
  const int N = 40, NTRAIN = 20;
  std::printf("kapali dongu: egim %s, LQR girdisi %s\n", CDTP_TILT_KALMAN ? "Kalman" : "tumleyen",
              CDTP_LQG ? "gozleyici" : "dogrudan");
  auto ps = mcRobots(N);
  // tani: NOMINAL=1 -> bütün robotlar nominal model (kutu ve sensor hatalari haric belirsizlik yok)
  if (std::getenv("NOMINAL")) {
    for (auto& p : ps) p = PlantParams();
    std::printf("NOMINAL robotlar\n");
  }
  std::vector<std::vector<Sample>> runs;
  for (int i = 0; i < N; ++i) runs.push_back(simulate(ps[i], 1000 + i));

  // ayar: hiz RMS'i (gozleyicinin asil kazanci v); theta ve omega bozulmasin diye onlar da yazilir
  int best = 0;
  double bestV = 1e9;
  FILE* g = std::fopen((out + "gozleyici_izgara.tsv").c_str(), "w");
  if (g) std::fprintf(g, "sa\tsalpha\trx\trth_deg\tv_rms\tth_rms_deg\tom_rms_dps\n");
  for (int k = 0; k < OBS_GRID_N; ++k) {
    Err w;
    Err e = mean(runs, 0, NTRAIN, [&](const std::vector<Sample>& s) { return evalObserver(s, OBS_GRID_L[k]); }, &w);
    if (g)
      std::fprintf(g, "%g\t%g\t%g\t%g\t%.5f\t%.4f\t%.4f\n", OBS_GRID_SA[k], OBS_GRID_SAL[k], OBS_GRID_RX[k],
                   OBS_GRID_RTH[k], OBS_GRID_SD[k], e.v, e.th, e.om);
    if (e.v < bestV) {
      bestV = e.v;
      best = k;
    }
  }
  if (g) std::fclose(g);
  std::printf("en iyi (egitim 0-%d): sa=%g salpha=%g rx=%g rth=%g\n", NTRAIN - 1, OBS_GRID_SA[best],
              OBS_GRID_SAL[best], OBS_GRID_RX[best], OBS_GRID_RTH[best], OBS_GRID_SD[best]);

  struct Row {
    const char* name;
    Err m, w;
  };
  std::vector<Row> rows(3);
  rows[0].name = "dogrudan (enkoder farki)";
  rows[0].m = mean(runs, NTRAIN, N, evalDirect, &rows[0].w);
  rows[1].name = "gozleyici, gains.h";
  rows[1].m = mean(runs, NTRAIN, N, [](const std::vector<Sample>& s) { return evalObserver(s, cdtp::gains::OBS_L); },
                   &rows[1].w);
  rows[2].name = "gozleyici, izgara en iyisi";
  rows[2].m = mean(runs, NTRAIN, N, [&](const std::vector<Sample>& s) { return evalObserver(s, OBS_GRID_L[best]); },
                   &rows[2].w);

  std::printf("\nSinama robotlari %d-%d, denge modunda, ilk 2 s haric (ort / en kotu robot):\n", NTRAIN, N - 1);
  std::printf("%-28s %20s %20s %22s\n", "kestirim", "v RMS (mm/s)", "theta RMS (deg)", "omega RMS (deg/s)");
  FILE* f = std::fopen((out + "gozleyici_karsilastirma.tsv").c_str(), "w");
  if (f) std::fprintf(f, "kestirim\tv_ort_mms\tv_kotu_mms\tth_ort_deg\tth_kotu_deg\tom_ort_dps\tom_kotu_dps\n");
  for (auto& r : rows) {
    std::printf("%-28s %9.2f / %8.2f %9.3f / %8.3f %10.3f / %9.3f\n", r.name, r.m.v * 1000, r.w.v * 1000, r.m.th,
                r.w.th, r.m.om, r.w.om);
    if (f)
      std::fprintf(f, "%s\t%.3f\t%.3f\t%.4f\t%.4f\t%.4f\t%.4f\n", r.name, r.m.v * 1000, r.w.v * 1000, r.m.th, r.w.th,
                   r.m.om, r.w.om);
  }
  if (f) std::fclose(f);
  return 0;
}
