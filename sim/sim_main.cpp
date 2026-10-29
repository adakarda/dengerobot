// Sartnamedeki kabul testlerinin simulasyonu. Robot ESP32'sindeki ayni RobotLogic kodu kosar.
// Derle: tools/run_sim.sh   Cikti: sim/results/
#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "harness.h"
#include "unit_tests.h"

using cdtp::Cmd;
using cdtp::Mode;

static const double D2R = M_PI / 180.0, R2D = 180.0 / M_PI;
static std::string OUT = "sim/results/";

struct Result {
  std::string id, name;
  bool pass;
  std::string detail;
};
static std::vector<Result> results;
static double g_lastD = 0, g_lastDx = 0, g_lastTh = 0;

static void report(const std::string& id, const std::string& name, bool pass, const char* fmt, ...) {
  char buf[512];
  va_list ap;
  va_start(ap, fmt);
  std::vsnprintf(buf, sizeof buf, fmt, ap);
  va_end(ap);
  results.push_back({id, name, pass, buf});
  std::printf("[%s] %-6s %-44s %s\n", pass ? "GECTI" : "KALDI", id.c_str(), name.c_str(), buf);
}

// Robotu dik baslatip dengeye aldirir (elle dik tutup birakma)
static void arm(Harness& h) {
  h.plant.initFilter();
  h.run(1.0);
}

struct Stats {
  double maxTh = 0, maxX = 0, minX = 1e9, maxXabs = 0;
  bool fell = false;
  void operator()(Harness& h) {
    maxTh = std::max(maxTh, std::fabs(h.plant.th));
    maxX = std::max(maxX, h.plant.x);
    minX = std::min(minX, h.plant.x);
    maxXabs = std::max(maxXabs, std::fabs(h.plant.x));
    if (h.logic.mode() == Mode::FALLEN || h.plant.lying) fell = true;
  }
};

// ---------- C1: denge ve temel hareket ----------
static bool testStatic(const PlantParams& pp, unsigned seed, bool rep, double dur = 30) {
  Harness h(pp, seed);
  h.logic.setTask(cdtp::Task::STATIC);
  h.record = rep;
  arm(h);
  Stats s;
  h.run(dur, std::ref(s));
  bool ok = !s.fell && h.logic.mode() == Mode::BALANCE && s.maxTh < 5 * D2R && s.maxXabs < 0.15;
  if (rep) {
    h.writeCsv(OUT + "c1_statik.csv");
    report("C1.1", "30 s statik denge (kutulu)", ok, "en buyuk egim %.2f deg, en buyuk kayma %.1f cm", s.maxTh * R2D,
           s.maxXabs * 100);
  }
  return ok;
}

static bool testMove1m(const PlantParams& pp, unsigned seed, bool rep, bool forward) {
  Harness h(pp, seed);
  h.logic.setTask(cdtp::Task::GUIDANCE);
  h.gloveOn = true;
  h.record = rep;
  Cmd c = forward ? Cmd::FWD : Cmd::BACK;
  // robot once 5 s dengede bekler (denge acisini ogrenir), sonra iki adim komutu: 0,5 + 0,5 m
  h.glove = {{0, Cmd::STOP}, {6.0, c}, {6.4, Cmd::STOP}, {9.5, c}, {9.9, Cmd::STOP}};
  arm(h);
  Stats s;
  h.run(13.0, std::ref(s));
  // 3 s durma
  double x0 = h.plant.x, maxV = 0, maxTh = 0, maxDx = 0;
  h.run(3.0, [&](Harness& hh) {
    maxV = std::max(maxV, std::fabs(hh.plant.v));
    maxTh = std::max(maxTh, std::fabs(hh.plant.th));
    maxDx = std::max(maxDx, std::fabs(hh.plant.x - x0));
  });
  double d = std::fabs(h.plant.x);
  // "durdu": 3 s boyunca +-3 cm icinde (disli surtunmesi + sensor gurultusu kucuk bir titresim birakir)
  g_lastD = d;
  g_lastDx = maxDx;
  g_lastTh = s.maxTh;
  bool ok = !s.fell && d > 0.9 && d < 1.1 && maxDx < 0.03;
  if (rep) {
    h.writeCsv(OUT + (forward ? "c1_ileri.csv" : "c1_geri.csv"));
    report(forward ? "C1.2" : "C1.3", forward ? "1 m ileri + 3 s dur" : "1 m geri + 3 s dur", ok,
           "yol %.3f m, 3 s durmada en buyuk kayma %.1f mm (hiz tepe %.3f m/s), en buyuk egim %.1f deg", d,
           maxDx * 1000, maxV, s.maxTh * R2D);
  }
  return ok;
}

static bool testRecovery(const PlantParams& pp, unsigned seed, bool rep, double deg, double* tRec = nullptr,
                         double* travel = nullptr) {
  Harness h(pp, seed);
  h.logic.setTask(cdtp::Task::STATIC);
  h.record = rep;
  arm(h);
  // elle +-10 deg egilip birakildi
  h.plant.th = deg * D2R;
  h.plant.om = 0;
  double t0 = h.t, recovered = -1, maxDx = 0, maxAfter = 0;
  double x0 = h.plant.x;
  Stats s;
  // toparlanma: |theta| < 3 deg ve |v| < 0,1 m/s'ye ilk varis; sonrasinda egim 5 deg'yi hic asmamali
  h.run(10.0, [&](Harness& hh) {
    s(hh);
    maxDx = std::max(maxDx, std::fabs(hh.plant.x - x0));
    if (recovered < 0 && std::fabs(hh.plant.th) < 3 * D2R && std::fabs(hh.plant.v) < 0.1) recovered = hh.t - t0;
    if (recovered >= 0) maxAfter = std::max(maxAfter, std::fabs(hh.plant.th));
  });
  if (maxAfter > 5 * D2R) recovered = -1;
  bool ok = !s.fell && recovered >= 0 && recovered < 10;
  if (tRec) *tRec = recovered;
  if (travel) *travel = maxDx;
  if (rep) h.writeCsv(OUT + (deg > 0 ? "c1_toparlanma_arti.csv" : "c1_toparlanma_eksi.csv"));
  return ok;
}

// ---------- On test: enerjisizken pasif kararsizlik ----------
static void testPassive() {
  bool ok = true;
  double worst = 0;
  for (double deg : {10.0, -10.0}) {
    Harness h(PlantParams(), 3);
    h.plant.initFilter();
    h.plant.th = deg * D2R;
    double tFall = -1;
    // motorlar enerjisiz: mantigi hic calistirmadan yalniz fizik
    for (int i = 0; i < 5 * 2000 && !h.plant.lying; ++i) h.plant.step(0, 0, false, 0.0005);
    tFall = h.plant.lying ? 0 : -1;
    double tt = 0;
    Harness h2(PlantParams(), 3);
    h2.plant.th = deg * D2R;
    while (tt < 5 && std::fabs(h2.plant.th) < 40 * D2R) {
      h2.plant.step(0, 0, false, 0.0005);
      tt += 0.0005;
    }
    if (tt >= 5) ok = false;
    worst = std::max(worst, tt);
    (void)tFall;
  }
  report("ON", "Enerjisiz +-10 deg'den dik kalmamali", ok, "40 deg'yi gecme suresi en fazla %.2f s (sinir: 5 s icinde dusmeli)",
         worst);
}

// ---------- C2: eldiven komutlari ----------
static void testGlove() {
  struct Case { const char* id; const char* name; Cmd c; bool lin; double sign; };
  Case cs[] = {{"C2.1", "Eldiven: ileri ~0,5 m", Cmd::FWD, true, 1},
               {"C2.2", "Eldiven: geri ~0,5 m", Cmd::BACK, true, -1},
               {"C2.3", "Eldiven: sola ~90 deg", Cmd::LEFT, false, 1},
               {"C2.4", "Eldiven: saga ~90 deg", Cmd::RIGHT, false, -1}};
  for (auto& k : cs) {
    Harness h(PlantParams(), 11);
    h.logic.setTask(cdtp::Task::GUIDANCE);
    h.gloveOn = true;
    h.gloveLoss = 0.05;
    h.glove = {{0, Cmd::STOP}, {1.5, k.c}, {2.0, Cmd::STOP}};
    arm(h);
    const double tCmd = 1.5;  // eldiven jesti bu anda baslar
    double tResp = -1, x0 = h.plant.x;
    Stats s;
    h.run(6.0, [&](Harness& hh) {
      s(hh);
      if (hh.t <= tCmd) x0 = hh.plant.x;
      // tepki: komut yonunde 3 cm yol ya da 5 deg donus (denge titremesi tetiklemesin)
      bool moving = k.lin ? (hh.plant.x - x0) * k.sign > 0.03 : hh.plant.psi * k.sign > 5 * D2R;
      if (moving && tResp < 0 && hh.t > tCmd) tResp = hh.t - tCmd;
    });
    double val = k.lin ? h.plant.x : h.plant.psi * R2D;
    bool ok = !s.fell && tResp >= 0 && tResp < 2.0 &&
              (k.lin ? (std::fabs(val - 0.5 * k.sign) < 0.1) : (std::fabs(val - 90 * k.sign) < 15));
    report(k.id, k.name, ok, k.lin ? "tepki %.2f s, yol %.3f m" : "tepki %.2f s, donus %.1f deg", tResp, val);
  }
  // dur: bes komut art arda, sonra dur; robot durur ve yerinde kalir
  {
    Harness h(PlantParams(), 12);
    h.logic.setTask(cdtp::Task::GUIDANCE);
    h.gloveOn = true;
    h.gloveLoss = 0.05;
    h.record = true;
    h.glove = {{0, Cmd::STOP},  {1.5, Cmd::FWD},    {1.9, Cmd::STOP},  {5.0, Cmd::BACK}, {5.4, Cmd::STOP},
               {8.5, Cmd::LEFT}, {8.9, Cmd::STOP}, {11.0, Cmd::RIGHT}, {11.4, Cmd::STOP}};
    arm(h);
    Stats s;
    h.run(13.5, std::ref(s));
    double x0 = h.plant.x, p0 = h.plant.psi;
    h.run(3.0, std::ref(s));
    bool ok = !s.fell && std::fabs(h.plant.x - x0) < 0.03 && std::fabs(h.plant.psi - p0) < 3 * D2R;
    h.writeCsv(OUT + "c2_eldiven.csv");
    report("C2.5", "Dur: tum komutlardan sonra yerinde kalir", ok, "son 3 s kayma %.1f mm, donme %.2f deg",
           std::fabs(h.plant.x - x0) * 1000, std::fabs(h.plant.psi - p0) * R2D);
  }
  // baglanti kopmasi: adim ortasinda eldiven susarsa robot durur
  {
    Harness h(PlantParams(), 13);
    h.logic.setTask(cdtp::Task::GUIDANCE);
    h.gloveOn = true;
    h.glove = {{0, Cmd::STOP}, {1.5, Cmd::FWD}, {1.9, Cmd::STOP}};
    h.gloveCutFrom = 2.5;
    h.gloveCutTo = 99;
    arm(h);
    Stats s;
    h.run(5.0, std::ref(s));
    bool ok = !s.fell && std::fabs(h.plant.v) < 0.1 && h.plant.x < 0.45;
    report("GUV.1", "Eldiven sustu (0,3 s): adim kesilir, robot durur", ok, "durdugu yol %.3f m (tam adim 0,5 m)",
           h.plant.x);
  }
}

// ---------- C3: otonom yanasma ----------
struct DockRes { bool ok; double tDock, tCharge; bool bad; };

static DockRes runDock(double rho, double alphaDeg, double headOffDeg, unsigned seed, bool rec = false,
                       const PlantParams& pp = PlantParams()) {
  Harness h(pp, seed);
  h.logic.setTask(cdtp::Task::CHARGING);
  h.stationOn = true;
  h.record = rec;
  const double a = alphaDeg * D2R;
  h.plant.X = rho * std::cos(a);
  h.plant.Y = rho * std::sin(a);
  h.plant.psi = std::atan2(-h.plant.Y, -h.plant.X) + headOffDeg * D2R;  // istasyona bakis + sapma
  double psiW0 = h.plant.psi;
  arm(h);
  (void)psiW0;
  double tStart = h.t;
  bool fell = false;
  h.run(60.0, [&](Harness& hh) {
    if (hh.plant.lying || hh.logic.mode() == Mode::FALLEN) fell = true;
    if (hh.logic.mode() == Mode::CHARGING && hh.chargeStart > 0 && hh.t > hh.chargeStart + 0.5) hh.t = 1e9;
  });
  DockRes r;
  r.ok = !fell && h.docked && h.logic.mode() == Mode::CHARGING && !h.hitWallBad;
  r.tDock = h.dockTime > 0 ? h.dockTime - tStart : -1;
  r.tCharge = (h.chargeStart > 0 && h.dockTime > 0) ? h.chargeStart - h.dockTime : -1;
  r.bad = h.hitWallBad;
  if (rec) h.writeCsv(OUT + "c3_yanasma.csv");
  return r;
}

static void testDock() {
  int n = 0, okN = 0;
  double worstT = 0, worstCharge = 0;
  std::string fails;
  for (double rho : {0.15, 0.22, 0.30})
    for (double al : {-45.0, -30.0, -15.0, 0.0, 15.0, 30.0, 45.0})
      for (double ho : {-30.0, 0.0, 30.0}) {
        DockRes r = runDock(rho, al, ho, 100 + n);
        ++n;
        if (r.ok) {
          ++okN;
          worstT = std::max(worstT, r.tDock);
          worstCharge = std::max(worstCharge, r.tCharge);
        } else {
          char b[96];
          std::snprintf(b, sizeof b, " (%.2f m, %.0f deg, bakis %+.0f%s)", rho, al, ho, r.bad ? ", yuva disi carpma" : "");
          fails += b;
        }
      }
  report("C3.1-2", "IR ile bul, hizalan, yerles (63 baslangic, 30 cm/90 deg)", okN == n, "%d/%d basarili, en uzun %.1f s%s", okN, n,
         worstT, fails.c_str());
  report("C3.3", "Temastan sonra sarj + motor durur <= 5 s", okN > 0 && worstCharge < 5.0,
         "temas -> SARJ modu en fazla %.2f s", worstCharge);
  // arkasi istasyona donuk baslangic: ARA durumu tam tur atmali
  int backOk = 0;
  for (double ho : {90.0, -90.0, 180.0}) backOk += runDock(0.25, 10, ho, 300 + (int)ho).ok;
  report("C3.x", "Istasyon gorus disindayken arayip bulma", backOk == 3, "%d/3 basarili (90, -90, 180 deg ters bakis)",
         backOk);
  runDock(0.30, 35, 25, 7, true);
}

// ---------- C5: butunlesik gorev ----------
static void testIntegrated(int rep, bool record) {
  Harness h(PlantParams(), 500 + rep);
  h.logic.setTask(cdtp::Task::INTEGRATED);
  h.stationOn = true;
  h.gloveOn = true;
  h.gloveLoss = 0.05;
  h.record = record;
  // istasyon (0,0) +X'e bakar. Robot (0.27,-1.0)'dan +Y'ye bakarak baslar.
  h.plant.X = 0.27;
  h.plant.Y = -1.0;
  h.plant.psi = M_PI / 2;
  // 5 s denge -> 2 x ileri (1 m, hedef nokta) -> hedefte 5 s bekle -> sola don -> dur -> otonom yanasma
  h.glove = {{0, Cmd::STOP}, {5.0, Cmd::FWD}, {5.4, Cmd::STOP}, {8.6, Cmd::FWD}, {9.0, Cmd::STOP},
             {17.0, Cmd::LEFT}, {17.4, Cmd::STOP}};
  arm(h);
  bool fell = false, earlyDock = false;
  double targetWaitStart = -1;
  h.run(70.0, [&](Harness& hh) {
    if (hh.plant.lying || hh.logic.mode() == Mode::FALLEN) fell = true;
    if (hh.t < 17.0 && hh.logic.mode() == Mode::DOCK) earlyDock = true;
    if (targetWaitStart < 0 && hh.t > 9 && std::fabs(hh.plant.v) < 0.02) targetWaitStart = hh.t;
    if (hh.logic.mode() == Mode::CHARGING && hh.chargeStart > 0 && hh.t > hh.chargeStart + 0.5) hh.t = 1e9;
  });
  bool ok = !fell && !earlyDock && h.docked && h.logic.mode() == Mode::CHARGING;
  if (record) h.writeCsv(OUT + "c5_butunlesik.csv");
  char nm[64];
  std::snprintf(nm, sizeof nm, "Butunlesik gorev, tekrar %d", rep);
  report("C5." + std::to_string(rep), nm, ok, "hedefte bekleme %.1f s, erken yanasma %s, sarj %s, temas->sarj %.2f s",
         17.0 - targetWaitStart, earlyDock ? "VAR" : "yok", h.docked ? "basladi" : "YOK",
         h.chargeStart > 0 ? h.chargeStart - h.dockTime : -1.0);
}

// ---------- Saglamlik: parametre belirsizligi ----------
static void testRobust() {
  std::mt19937 g(2026);
  auto U = [&](double a, double b) { return std::uniform_real_distribution<double>(a, b)(g); };
  const int N = 40;
  int okS = 0, okR = 0, okM = 0, okM5 = 0;
  double worstRec = 0;
  std::string worst;
  for (int i = 0; i < N; ++i) {
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
    unsigned seed = 1000 + i;
    bool s = testStatic(p, seed, false, 15);
    double tr1 = 0, tr2 = 0;
    bool r = testRecovery(p, seed, false, 10, &tr1) && testRecovery(p, seed, false, -10, &tr2);
    bool m3 = testMove1m(p, seed, false, true);
    // modelden uzak robotlarda durma olcutu +-5 cm (nominal testte +-3 cm)
    bool m = g_lastD > 0.9 && g_lastD < 1.1 && g_lastDx < 0.05;
    okS += s;
    okR += r;
    okM += m3;
    okM5 += m;
    if (r) worstRec = std::max(worstRec, std::max(tr1, tr2));
    if (!(s && r && m)) {
      char b[160];
      std::snprintf(b, sizeof b, " [m=%.2f l=%.3f R=%.1f V=%.1f ofs=%.1f: %s%s%s d=%.2f dx=%.0fmm th=%.0f]", p.m_body,
                    p.l_com, p.R, p.voc, p.imu_offset_deg, s ? "" : "S", r ? "" : "T", m ? "" : "H", g_lastD,
                    g_lastDx * 1000, g_lastTh * R2D);
      worst += b;
    }
  }
  report("SAG", "Belirsizlik: kutle +-25%, KM -25/+60%, ...", okS == N && okR == N && okM5 == N,
         "statik %d/%d, toparlanma %d/%d (en uzun %.1f s), 1 m: +-5 cm durmada %d/%d, +-3 cm durmada %d/%d%s", okS, N,
         okR, N, worstRec, okM5, N, okM, N, worst.c_str());
}

int main(int argc, char** argv) {
  if (argc > 1) OUT = argv[1];
  std::printf("== Birim testleri ==\n");
  int fails = runUnitTests();
  std::printf("\n== Kabul testleri (simulasyon) ==\n");
  testPassive();
  testStatic(PlantParams(), 1, true);
  testMove1m(PlantParams(), 2, true, true);
  testMove1m(PlantParams(), 3, true, false);
  {
    double tp, tm, dp, dm;
    bool a = testRecovery(PlantParams(), 4, true, 10, &tp, &dp);
    bool b = testRecovery(PlantParams(), 5, true, -10, &tm, &dm);
    report("C1.4", "+10 ve -10 deg'den 10 s icinde toparlanma", a && b,
           "+10: %.2f s (yol %.0f cm), -10: %.2f s (yol %.0f cm)", tp, dp * 100, tm, dm * 100);
  }
  {
    Harness h(PlantParams(), 21);
    h.logic.setTask(cdtp::Task::STATIC);
    arm(h);
    h.motorPower = false;  // acil stopa basildi
    h.run(0.02);
    bool off = h.logic.mode() == Mode::STANDBY && !h.out.motorEnable;
    h.motorPower = true;   // birakildi; robot yatik -> kendiliginden donmemeli
    h.run(0.3);
    bool stay = h.logic.mode() != Mode::BALANCE || std::fabs(h.plant.th) < 3 * D2R;
    report("GUV.2", "Acil stop: denge birakilir, motorlar kapanir", off && stay, "stop sonrasi mod %s, bekleme %s",
           off ? "BEKLE" : "YANLIS", stay ? "dogru" : "yanlis");
  }
  testGlove();
  testDock();
  for (int i = 1; i <= 4; ++i) testIntegrated(i, i == 1);
  testRobust();

  int nOk = 0;
  for (auto& r : results) nOk += r.pass;
  std::printf("\nOZET: %d/%d kabul testi gecti, birim testi hatasi: %d\n", nOk, (int)results.size(), fails);

  FILE* f = std::fopen((OUT + "summary.tsv").c_str(), "w");
  if (f) {
    for (auto& r : results) std::fprintf(f, "%s\t%s\t%s\t%s\n", r.id.c_str(), r.name.c_str(), r.pass ? "GECTI" : "KALDI", r.detail.c_str());
    std::fclose(f);
  }
  return (nOk == (int)results.size() && fails == 0) ? 0 : 1;
}
