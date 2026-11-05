"""Run the whole stepper feasibility study.   Usage:  python sim_step/run_all.py [--quick]

Writes sim_step/results/ : summary.tsv, results.json, tables.md, CSV traces, PNG plots.
Needs numpy + scipy (+ matplotlib for the plots). Takes a few minutes on a multi-core PC.
"""
import json
import math
import os
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

from params import *  # noqa: E402,F401,F403
import scenarios as S  # noqa: E402
import controller  # noqa: E402

QUICK = "--quick" in sys.argv
N_MC = 5 if QUICK else 20
MOTOR_LIST = ["17HS4401", "17HS3401S"]


def jdefault(o):
    if hasattr(o, "item"):
        return o.item()
    return str(o)


# --------------------------------------------------------------------------------------
def acceptance(motor):
    """Full acceptance set for one motor with the nominal plant (single formal seed per test, as in sim_main.cpp)."""
    pp = PlantParams(motor=motor)
    res = [S.test_passive(pp)]
    res.append(S.test_static(pp, 1, None, True))
    res.append(S.test_move1m(pp, 2, None, True, True))
    res.append(S.test_move1m(pp, 3, None, True, False))
    a = S.test_recovery(pp, 4, 10.0, None, True)
    b = S.test_recovery(pp, 5, -10.0, None, True)
    res.append(dict(id="C1.4", name="recovery +-10 deg within 10 s", ok=bool(a["ok"] and b["ok"]), plus=a, minus=b,
                    torque=S.merge_torque([a["torque"], b["torque"]]),
                    detail="+10: %.2f s (travel %.0f cm), -10: %.2f s (travel %.0f cm)" % (a["t_rec"], a["travel_cm"], b["t_rec"], b["travel_cm"])))
    res.append(S.test_estop(pp))
    res.extend(S.test_glove(pp, None, True))
    return motor, res


SENS = [
    ("base (torque x1.0, damp 0.010)", dict()),
    ("pull-out torque x0.70", dict(torque_scale=0.70)),
    ("pull-out torque x0.50", dict(torque_scale=0.50)),
    ("pull-out torque x0.35", dict(torque_scale=0.35)),
    ("rotor damping 0.003 (very low)", dict(damp=0.003)),
    ("rotor damping 0.030 (high)", dict(damp=0.030)),
    ("vibration noise x3 (0.9 m/s2)", dict(vib_acc=0.9)),
    ("battery 9.9 V (empty pack)", dict(vbat=9.9)),
    ("torque x0.70 + damping 0.003", dict(torque_scale=0.70, damp=0.003)),
]


def sens_job(a):
    motor, label, kw = a
    pp = PlantParams(motor=motor, **kw)
    r = S.run_core(pp)
    return motor, label, r


def limit_job(a):
    """Largest initial tilt (each sign) recovered, with the torque used."""
    motor, scale = a
    pp = PlantParams(motor=motor, torque_scale=scale)
    out = {}
    for sgn in (1, -1):
        best, tq_best = 0.0, None
        for ang in (10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30):
            r = S.test_recovery(pp, 7, sgn * ang)
            if r["ok"]:
                best, tq_best = ang, r["torque"]
            else:
                break
        out[sgn] = (best, tq_best)
    return motor, scale, out


def mc_job(a):
    return S.sag_one(a)


# --------------------------------------------------------------------------------------
def fmt_tq(t):
    if not t:
        return "-"
    return "%.1f / %.1f / %.1f / %.1f" % (t["peak"], t["p99"], t["rms"], t["avail_at_peak"])


def main():
    os.makedirs(S.OUT, exist_ok=True)
    t0 = time.time()
    pool = Pool(min(os.cpu_count() or 2, 12))
    print("design:")
    for m in MOTOR_LIST:
        mdl, K, cl, ol, tpa = controller.design(MOTORS[m].m_body, MOTORS[m].J_rotor)
        print(" ", m, "K = [x, v, theta, omega] =", np.round(K, 1), "th_per_acc", round(tpa, 4))

    # 1. acceptance (both motors in parallel)
    acc = dict(pool.map(acceptance, MOTOR_LIST))
    print("acceptance done %.0fs" % (time.time() - t0))

    # 2. sensitivity
    jobs = [(m, lab, kw) for m in MOTOR_LIST for (lab, kw) in SENS]
    sens = {}
    for m, lab, r in pool.map(sens_job, jobs):
        sens[(m, lab)] = r
    print("sensitivity done %.0fs" % (time.time() - t0))

    # 3. recovery limit scan
    lim = {}
    for m, sc, o in pool.map(limit_job, [(m, s) for m in MOTOR_LIST for s in (1.0, 0.7, 0.5)]):
        lim[(m, sc)] = o
    print("limit scan done %.0fs" % (time.time() - t0))

    # 4. Monte Carlo robustness
    cases = ["nominal"] + [c for c in S.SAG_CASES if c != "nominal"]
    jobs = [(PlantParams(motor=m), c, i, None) for m in MOTOR_LIST for c in cases for i in range(N_MC)]
    mc_raw = pool.map(mc_job, jobs, chunksize=2)
    pool.close()
    mc = {}
    for (base, c, i, _), r in zip(jobs, mc_raw):
        mc.setdefault((base.motor, c), []).append(r)
    print("monte carlo done %.0fs" % (time.time() - t0))

    # ---------------- output ----------------
    json.dump(dict(acceptance=acc, sens={"%s|%s" % k: v for k, v in sens.items()},
                   limit={"%s|%s" % k: v for k, v in lim.items()},
                   mc={"%s|%s" % k: v for k, v in mc.items()}),
              open(os.path.join(S.OUT, "results.json"), "w"), default=jdefault, indent=1)

    with open(os.path.join(S.OUT, "summary.tsv"), "w") as f:
        for m in MOTOR_LIST:
            for r in acc[m]:
                tq = r.get("torque", {})
                f.write("%s\t%s\t%s\t%s\t%s\t%s\n" % (m, r["id"], r["name"], "PASS" if r["ok"] else "FAIL", r["detail"],
                                                      ("peak %.1f p99 %.1f rms %.1f avail %.1f minmargin %.2f slips %d" % (
                                                          tq["peak"], tq["p99"], tq["rms"], tq["avail_at_peak"], tq["min_margin"], tq["slips"])) if tq else ""))

    L = []
    L.append("## Acceptance results (nominal plant, formal seeds)\n")
    for m in MOTOR_LIST:
        L.append("### %s\n" % m)
        L.append("| ID | Test | Result | Key numbers | Torque per motor N.cm: peak / p99 / rms / pull-out at peak | Min margin | Lost-step events |")
        L.append("|---|---|---|---|---|---|---|")
        for r in acc[m]:
            tq = r.get("torque")
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (r["id"], r["name"], "PASS" if r["ok"] else "**FAIL**", r["detail"], fmt_tq(tq),
                                                           ("%.2f" % tq["min_margin"]) if tq else "-", tq["slips"] if tq else "-"))
        L.append("")
    L.append("## Sensitivity (core tests C1.1-C1.4, C2.1-C2.4)\n")
    for m in MOTOR_LIST:
        L.append("### %s\n" % m)
        L.append("| Case | C1.1 | C1.2 | C1.3 | C1.4 | C2.1 | C2.2 | C2.3 | C2.4 | peak T N.cm | min margin | slips |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for lab, _ in SENS:
            r = sens[(m, lab)]
            tq = S.merge_torque([r[k]["torque"] for k in r])
            cells = ["PASS" if r[k]["ok"] else "FAIL" for k in ("C1.1", "C1.2", "C1.3", "C1.4", "C2.1", "C2.2", "C2.3", "C2.4")]
            L.append("| %s | %s | %.1f | %.2f | %d |" % (lab, " | ".join(cells), tq["peak"], tq["min_margin"], tq["slips"]))
        L.append("")
    L.append("## Largest recovered initial tilt (deg, + / -) and peak torque at that tilt\n")
    L.append("| Motor | torque scale | + tilt | - tilt | peak T at + (N.cm) | pull-out there |")
    L.append("|---|---|---|---|---|---|")
    for (m, sc), o in sorted(lim.items()):
        tq = o[1][1]
        L.append("| %s | %.2f | %.1f | %.1f | %s | %s |" % (m, sc, o[1][0], o[-1][0], ("%.1f" % tq["peak"]) if tq else "-",
                                                      ("%.1f" % tq["avail_at_peak"]) if tq else "-"))
    L.append("")
    L.append("## Robustness (%d randomised runs per case: static 15 s + recovery +-10 + 1 m forward/hold)\n" % N_MC)
    for m in MOTOR_LIST:
        L.append("### %s\n" % m)
        L.append("| Case | static | recovery | 1 m hold <5 cm | 1 m hold <3 cm | worst recovery s | peak T N.cm | min margin | runs with slips | max dead-reckoning err mm |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for c in cases:
            rs = mc[(m, c)]
            n = len(rs)
            tq = S.merge_torque([r["torque"] for r in rs])
            worst = max([r["t_rec"] for r in rs if r["rec"]] or [-1])
            L.append("| %s | %d/%d | %d/%d | %d/%d | %d/%d | %.2f | %.1f | %.2f | %d | %.1f |" % (
                c, sum(r["static"] for r in rs), n, sum(r["rec"] for r in rs), n, sum(r["move5"] for r in rs), n,
                sum(r["move3"] for r in rs), n, worst, tq["peak"], tq["min_margin"], sum(1 for r in rs if r["slips"] > 0),
                max(abs(r["dr_err"]) for r in rs)))
        L.append("")
    open(os.path.join(S.OUT, "tables.md"), "w").write("\n".join(L))
    print("\n".join(L))

    try:
        import plots
        plots.make(acc, sens, lim, SENS)
    except Exception as e:  # plots are optional
        print("plots skipped:", e)
    print("total %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
