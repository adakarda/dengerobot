// Tumleyen filtre ve Kalman (aci + jiroskop bias) karsilastirmasi.
// Kapali dongu robotun kendi filtresiyle kosar (derleme bayragina gore); iki filtre ayni IMU orneklerini
// paralel, acik dongu olarak alir. Gercek: IMU'nun egimi (plant.th + montaj hatasi).
// Belirsizlik testi (SAG) ile ayni rastgele robotlar: 0-19 ayar, 20-39 sinama.
// Derle ve kos: bash tools/run_filtre.sh
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <random>
#include <string>
#include <vector>

#include "harness.h"
#include "mc_robots.h"

using cdtp::Cmd;

static const double D2R = M_PI / 180.0, R2D = 180.0 / M_PI;

struct Sample {
  cdtp::ImuSample imu;
  double thTrue;  // rad, IMU egimi
  bool moving;
};

struct Run {
  PlantParams p;
  std::vector<Sample> s;
  bool fell;
};

// 5 s dengede bekleme, sonra ileri-geri adimlar (ivmelenme ivme olcerin acisini bozar), toplam 30 s
static Run simulate(const PlantParams& p, unsigned seed) {
  Run r{p, {}, false};
  Harness h(p, seed);
  h.logic.setTask(cdtp::Task::GUIDANCE);
  h.gloveOn = true;
  h.glove = mcGloveScript();
  h.plant.initFilter();
  h.run(31.0, [&](Harness& hh) {
    r.s.push_back({hh.lastImu, hh.plant.th + p.imu_offset_deg * D2R, std::fabs(hh.plant.v) > 0.02});
    if (hh.plant.lying) r.fell = true;
  });
  return r;
}

struct Err {
  double rms = 0, max = 0, rmsMove = 0, biasErr = 0;  // deg, deg, deg, deg/s
};

static double biasOf(const cdtp::TiltKalman& k) { return k.bias(); }
static double biasOf(const cdtp::TiltFilter&) { return 0; }

// Ilk 2 s (yerlesme) sayilmaz
template <class F>
static Err evaluate(const Run& r, F filt, bool hasBias) {
  cdtp::AxisMap m;
  const float dt = cdtp::cfg::DT;
  double se = 0, seM = 0;
  int n = 0, nM = 0;
  Err e;
  for (size_t i = 0; i < r.s.size(); ++i) {
    filt.update(r.s[i].imu, m, dt);
    if (i * dt < 2.0) continue;
    double d = (filt.thetaRaw() - r.s[i].thTrue) * R2D;
    se += d * d;
    ++n;
    e.max = std::max(e.max, std::fabs(d));
    if (r.s[i].moving) {
      seM += d * d;
      ++nM;
    }
  }
  e.rms = std::sqrt(se / std::max(n, 1));
  e.rmsMove = std::sqrt(seM / std::max(nM, 1));
  if (hasBias) e.biasErr = std::fabs(biasOf(filt) * R2D - r.p.gyro_bias_dps);
  return e;
}

struct Summary {
  double rmsMean = 0, rmsWorst = 0, maxWorst = 0, rmsMoveMean = 0, biasMean = 0, biasWorst = 0;
};

template <class Make>
static Summary summarize(const std::vector<Run>& runs, int from, int to, Make make, bool hasBias) {
  Summary s;
  int n = 0;
  for (int i = from; i < to; ++i) {
    Err e = evaluate(runs[i], make(), hasBias);
    s.rmsMean += e.rms;
    s.rmsMoveMean += e.rmsMove;
    s.biasMean += e.biasErr;
    s.rmsWorst = std::max(s.rmsWorst, e.rms);
    s.maxWorst = std::max(s.maxWorst, e.max);
    s.biasWorst = std::max(s.biasWorst, e.biasErr);
    ++n;
  }
  s.rmsMean /= n;
  s.rmsMoveMean /= n;
  s.biasMean /= n;
  return s;
}

int main(int argc, char** argv) {
  std::string out = argc > 1 ? argv[1] : "sim/results/";
  const int N = 40, NTRAIN = 20;
  std::printf("filtre: kapali dongu %s\n", CDTP_TILT_KALMAN ? "Kalman" : "tumleyen");
  auto ps = mcRobots(N);
  std::vector<Run> runs;
  int fell = 0;
  for (int i = 0; i < N; ++i) {
    runs.push_back(simulate(ps[i], 1000 + i));
    fell += runs.back().fell;
  }
  std::printf("%d robot, %d dustu\n", N, fell);

  // ayar: izgara, amac = egitim robotlarinda ortalama RMS
  const float qT[] = {1e-8f, 1e-7f, 1e-6f, 1e-5f, 1e-4f, 1e-3f};
  const float rA[] = {4e-4f, 1.6e-3f, 6.4e-3f, 2.5e-2f, 0.1f, 0.4f, 1.6f};
  const float qB[] = {1e-13f, 1e-11f, 1e-9f, 1e-7f};
  cdtp::KalmanTuning best;
  double bestRms = 1e9;
  FILE* g = std::fopen((out + "filtre_izgara.tsv").c_str(), "w");
  if (g) std::fprintf(g, "q_theta\tr_acc\tq_bias\trms_ort_deg\tbias_ort_dps\n");
  for (float a : qT)
    for (float b : rA)
      for (float c : qB) {
        cdtp::KalmanTuning t;
        t.qTheta = a;
        t.rAcc = b;
        t.qBias = c;
        Summary s = summarize(runs, 0, NTRAIN, [&] { return cdtp::TiltKalman(t); }, true);
        if (g) std::fprintf(g, "%g\t%g\t%g\t%.4f\t%.4f\n", a, b, c, s.rmsMean, s.biasMean);
        if (s.rmsMean < bestRms) {
          bestRms = s.rmsMean;
          best = t;
        }
      }
  if (g) std::fclose(g);
  std::printf("en iyi ayar (egitim 0-%d): q_theta=%g r_acc=%g q_bias=%g\n", NTRAIN - 1, best.qTheta, best.rAcc,
              best.qBias);

  // tumleyen filtreye de ayni sans: alpha izgarasi, ayni egitim robotlari
  float bestA = cdtp::cfg::COMP_ALPHA;
  double bestARms = 1e9;
  for (float a : {0.95f, 0.98f, 0.99f, 0.995f, 0.998f, 0.999f, 0.9995f, 0.9998f}) {
    Summary s = summarize(runs, 0, NTRAIN, [&] { return cdtp::TiltFilter(a); }, false);
    std::printf("  tumleyen alpha %.4f: egitim RMS ort %.3f deg\n", a, s.rmsMean);
    if (s.rmsMean < bestARms) {
      bestARms = s.rmsMean;
      bestA = a;
    }
  }
  std::printf("en iyi alpha (egitim): %.4f\n", bestA);

  cdtp::KalmanTuning def;  // cdtp_config.h degerleri
  struct Row {
    const char* name;
    Summary s;
  };
  std::vector<Row> rows = {
      {"tumleyen (alpha 0.98)", summarize(runs, NTRAIN, N, [] { return cdtp::TiltFilter(); }, false)},
      {"tumleyen, en iyi alpha", summarize(runs, NTRAIN, N, [&] { return cdtp::TiltFilter(bestA); }, false)},
      {"Kalman, config degerleri", summarize(runs, NTRAIN, N, [&] { return cdtp::TiltKalman(def); }, true)},
      {"Kalman, izgara en iyisi", summarize(runs, NTRAIN, N, [&] { return cdtp::TiltKalman(best); }, true)},
  };
  std::printf("\nSinama robotlari %d-%d (ayarda kullanilmadi), ilk 2 s haric:\n", NTRAIN, N - 1);
  std::printf("%-26s %10s %10s %10s %11s %11s %11s\n", "filtre", "RMS ort", "RMS kotu", "max kotu", "RMS hareket",
              "bias ort", "bias kotu");
  FILE* f = std::fopen((out + "filtre_karsilastirma.tsv").c_str(), "w");
  if (f) std::fprintf(f, "filtre\trms_ort_deg\trms_kotu_deg\tmax_kotu_deg\trms_hareket_deg\tbias_ort_dps\tbias_kotu_dps\n");
  for (auto& r : rows) {
    std::printf("%-26s %9.3f° %9.3f° %9.3f° %10.3f° %8.3f°/s %8.3f°/s\n", r.name, r.s.rmsMean, r.s.rmsWorst,
                r.s.maxWorst, r.s.rmsMoveMean, r.s.biasMean, r.s.biasWorst);
    if (f)
      std::fprintf(f, "%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\n", r.name, r.s.rmsMean, r.s.rmsWorst, r.s.maxWorst,
                   r.s.rmsMoveMean, r.s.biasMean, r.s.biasWorst);
  }
  if (f) std::fclose(f);
  std::printf("(tumleyen bias kestirmez; bias sutunu Kalman icin)\n");
  return 0;
}
