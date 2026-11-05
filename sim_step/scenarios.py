"""Acceptance scenarios (ports of the C1/C2/GUV tests in sim/sim_main.cpp, same thresholds)."""
import math
import os

import numpy as np

from params import *  # noqa: F401,F403
from harness import Harness
from plant import Plant

D2R = math.pi / 180.0
R2D = 180.0 / math.pi
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def torque_summary(plant):
    """Per-motor torque demand vs pull-out in the measurement window (N.cm)."""
    st = plant.stats
    n = max(st.n, 1)
    p99 = float(np.percentile(st.tick_peaks, 99)) * 100 if st.tick_peaks else 0.0
    return dict(peak=st.peak * 100, avail_at_peak=st.avail_at_peak * 100, rms=math.sqrt(st.sumsq / n) * 100,
                p99=p99, min_margin=st.min_margin, slips=st.slips, overloads=st.overloads, max_rpm=st.max_rpm)


def merge_torque(ts):
    ts = [t for t in ts if t]
    if not ts:
        return {}
    out = dict(ts[0])
    for t in ts[1:]:
        for k in ("peak", "rms", "p99", "max_rpm"):
            out[k] = max(out[k], t[k])
        if t["peak"] >= out["peak"]:
            out["avail_at_peak"] = t["avail_at_peak"]
        out["min_margin"] = min(out["min_margin"], t["min_margin"])
        out["slips"] += t["slips"]
        out["overloads"] += t["overloads"]
    return out


def arm(h):
    h.plant.init_filter()
    h.run(1.0)


class Stats:
    def __init__(self):
        self.maxTh = 0.0
        self.maxXabs = 0.0
        self.fell = False

    def __call__(self, h):
        self.maxTh = max(self.maxTh, abs(h.plant.th))
        self.maxXabs = max(self.maxXabs, abs(h.plant.x))
        if h.ctrl.mode == h.ctrl.FALLEN or h.plant.lying:
            self.fell = True


# ---------------- ON: passive instability with motors unpowered -----------------------
def test_passive(pp):
    worst, ok = 0.0, True
    for deg in (10.0, -10.0):
        pl = Plant(pp, 3)
        pl.th = deg * D2R
        tt = 0.0
        while tt < 5 and abs(pl.th) < 40 * D2R:
            pl.run_tick(0, 0, 0, 0, False)
            tt += DT
        if tt >= 5:
            ok = False
        worst = max(worst, tt)
    return dict(id="ON", name="Unpowered +-10 deg must fall", ok=ok, detail="time to 40 deg %.2f s (rotor detent torque not modelled)" % worst)


# ---------------- C1.1 static ---------------------------------------------------------
def test_static(pp, seed, ckw=None, rep=False, dur=30.0):
    h = Harness(pp, seed, "STATIC", ckw)
    h.record = rep
    arm(h)
    h.plant.reset_stats()
    s = Stats()
    h.run(dur, s)
    ok = (not s.fell) and h.ctrl.mode == h.ctrl.BALANCE and s.maxTh < 5 * D2R and s.maxXabs < 0.15
    tq = torque_summary(h.plant)
    if rep:
        h.write_csv(os.path.join(OUT, "%s_c1_static.csv" % pp.motor))
    return dict(id="C1.1", name="%g s static balance" % dur, ok=ok, maxTh=s.maxTh * R2D, drift_cm=s.maxXabs * 100,
                torque=tq, detail="max tilt %.2f deg, max drift %.1f cm" % (s.maxTh * R2D, s.maxXabs * 100))


# ---------------- C1.2 / C1.3 1 m ----------------------------------------------------------
def test_move1m(pp, seed, ckw=None, rep=False, forward=True):
    h = Harness(pp, seed, "GUIDANCE", ckw)
    h.glove_on = True
    h.record = rep
    c = "FWD" if forward else "BACK"
    h.glove = [(0, "STOP"), (6.0, c), (6.4, "STOP"), (9.5, c), (9.9, "STOP")]
    arm(h)
    h.plant.reset_stats()
    s = Stats()
    h.run(13.0, s)
    x0 = h.plant.x
    st = dict(maxV=0.0, maxTh=0.0, maxDx=0.0)

    def hold(hh):
        st["maxV"] = max(st["maxV"], abs(hh.plant.v))
        st["maxTh"] = max(st["maxTh"], abs(hh.plant.th))
        st["maxDx"] = max(st["maxDx"], abs(hh.plant.x - x0))
    h.run(3.0, hold)
    d = abs(h.plant.x)
    ok = (not s.fell) and 0.9 < d < 1.1 and st["maxDx"] < 0.03
    dr_err = (h.ctrl.x - h.plant.x) * 1000
    tq = torque_summary(h.plant)
    if rep:
        h.write_csv(os.path.join(OUT, "%s_c1_%s.csv" % (pp.motor, "forward" if forward else "back")))
    return dict(id="C1.2" if forward else "C1.3", name="1 m %s + 3 s hold" % ("forward" if forward else "back"),
                ok=ok, dist=d, hold_dx_mm=st["maxDx"] * 1000, peak_tilt=s.maxTh * R2D, deadreck_err_mm=dr_err,
                torque=tq, v_peak_hold=st["maxV"],
                detail="travel %.3f m, hold drift %.1f mm (v peak %.3f m/s), max tilt %.1f deg, dead-reckoning error %.1f mm"
                       % (d, st["maxDx"] * 1000, st["maxV"], s.maxTh * R2D, dr_err))


# ---------------- C1.4 recovery ---------------------------------------------------------
def test_recovery(pp, seed, deg, ckw=None, rep=False):
    h = Harness(pp, seed, "STATIC", ckw)
    h.record = rep
    arm(h)
    h.plant.set_tilt(deg * D2R, 0.0)
    h.plant.reset_stats()
    t0 = h.t
    x0 = h.plant.x
    res = dict(rec=-1.0, maxDx=0.0, maxAfter=0.0)
    s = Stats()

    def each(hh):
        s(hh)
        res["maxDx"] = max(res["maxDx"], abs(hh.plant.x - x0))
        if res["rec"] < 0 and abs(hh.plant.th) < 3 * D2R and abs(hh.plant.v) < 0.1:
            res["rec"] = hh.t - t0
        if res["rec"] >= 0:
            res["maxAfter"] = max(res["maxAfter"], abs(hh.plant.th))
    h.run(10.0, each)
    if res["maxAfter"] > 5 * D2R:
        res["rec"] = -1.0
    ok = (not s.fell) and 0 <= res["rec"] < 10
    tq = torque_summary(h.plant)
    if rep:
        h.write_csv(os.path.join(OUT, "%s_c1_recovery_%s.csv" % (pp.motor, "plus" if deg > 0 else "minus")))
    return dict(id="C1.4", name="recovery from %+g deg" % deg, ok=ok, t_rec=res["rec"], travel_cm=res["maxDx"] * 100,
                torque=tq, detail="%+g deg: %.2f s (travel %.0f cm)" % (deg, res["rec"], res["maxDx"] * 100))


# ---------------- GUV.2 e-stop ---------------------------------------------------------------
def test_estop(pp, ckw=None):
    h = Harness(pp, 21, "STATIC", ckw)
    arm(h)
    h.motor_power = False
    h.run(0.02)
    off = h.ctrl.mode == h.ctrl.STANDBY and not h.enable
    h.motor_power = True
    h.run(0.3)
    stay = h.ctrl.mode != h.ctrl.BALANCE or abs(h.plant.th) < 3 * D2R
    return dict(id="GUV.2", name="E-stop: balance released, drivers off", ok=off and stay,
                detail="mode after stop %s, stays off %s" % ("STANDBY" if off else "WRONG", stay))


# ---------------- C2 glove ------------------------------------------------------------------
def test_glove(pp, ckw=None, rep=False):
    out = []
    cases = [("C2.1", "Glove: forward ~0.5 m", "FWD", True, 1), ("C2.2", "Glove: back ~0.5 m", "BACK", True, -1),
             ("C2.3", "Glove: left ~90 deg", "LEFT", False, 1), ("C2.4", "Glove: right ~90 deg", "RIGHT", False, -1)]
    for cid, name, cmd, lin, sign in cases:
        h = Harness(pp, 11, "GUIDANCE", ckw)
        h.glove_on = True
        h.glove_loss = 0.05
        h.glove = [(0, "STOP"), (1.5, cmd), (2.0, "STOP")]
        arm(h)
        h.plant.reset_stats()
        tcmd = 1.5
        res = dict(tresp=-1.0, x0=h.plant.x)
        s = Stats()

        def each(hh):
            s(hh)
            if hh.t <= tcmd:
                res["x0"] = hh.plant.x
            moving = (hh.plant.x - res["x0"]) * sign > 0.03 if lin else hh.plant.psi * sign > 5 * D2R
            if moving and res["tresp"] < 0 and hh.t > tcmd:
                res["tresp"] = hh.t - tcmd
        h.run(6.0, each)
        val = h.plant.x if lin else h.plant.psi * R2D
        ok = (not s.fell) and 0 <= res["tresp"] < 2.0 and (abs(val - 0.5 * sign) < 0.1 if lin else abs(val - 90 * sign) < 15)
        tq = torque_summary(h.plant)
        out.append(dict(id=cid, name=name, ok=ok, response_s=res["tresp"], value=val, torque=tq,
                        detail=("response %.2f s, travel %.3f m" if lin else "response %.2f s, turn %.1f deg") % (res["tresp"], val)))
    # C2.5 hold after commands
    h = Harness(pp, 12, "GUIDANCE", ckw)
    h.glove_on = True
    h.glove_loss = 0.05
    h.record = rep
    h.glove = [(0, "STOP"), (1.5, "FWD"), (1.9, "STOP"), (5.0, "BACK"), (5.4, "STOP"), (8.5, "LEFT"), (8.9, "STOP"),
               (11.0, "RIGHT"), (11.4, "STOP")]
    arm(h)
    h.plant.reset_stats()
    s = Stats()
    h.run(13.5, s)
    x0, p0 = h.plant.x, h.plant.psi
    h.run(3.0, s)
    ok = (not s.fell) and abs(h.plant.x - x0) < 0.03 and abs(h.plant.psi - p0) < 3 * D2R
    tq = torque_summary(h.plant)
    if rep:
        h.write_csv(os.path.join(OUT, "%s_c2_glove.csv" % pp.motor))
    out.append(dict(id="C2.5", name="Stop: stays in place after all commands", ok=ok, torque=tq,
                    detail="last 3 s drift %.1f mm, rotation %.2f deg; end position error (dead-reckoned vs true) %.1f mm"
                           % (abs(h.plant.x - x0) * 1000, abs(h.plant.psi - p0) * R2D, (h.ctrl.x - h.plant.x) * 1000)))
    # GUV.1 glove lost
    h = Harness(pp, 13, "GUIDANCE", ckw)
    h.glove_on = True
    h.glove = [(0, "STOP"), (1.5, "FWD"), (1.9, "STOP")]
    h.cut_from, h.cut_to = 2.5, 99.0
    arm(h)
    s = Stats()
    h.run(5.0, s)
    ok = (not s.fell) and abs(h.plant.v) < 0.1 and h.plant.x < 0.45
    out.append(dict(id="GUV.1", name="Glove lost (0.3 s): step cut, robot stops", ok=ok,
                    detail="stopped after %.3f m (full step 0.5 m)" % h.plant.x))
    return out


# ---------------- core set (used by the sensitivity sweep) -----------------------------------------
def run_core(pp, ckw=None, rep=False):
    """C1.1, C1.2, C1.3, C1.4(+-), C2.1-C2.4; returns dict id -> result."""
    r = {}
    r["C1.1"] = test_static(pp, 1, ckw, rep)
    r["C1.2"] = test_move1m(pp, 2, ckw, rep, True)
    r["C1.3"] = test_move1m(pp, 3, ckw, rep, False)
    a = test_recovery(pp, 4, 10.0, ckw, rep)
    b = test_recovery(pp, 5, -10.0, ckw, rep)
    r["C1.4"] = dict(id="C1.4", name="recovery +-10 deg", ok=a["ok"] and b["ok"], plus=a, minus=b,
                     torque=merge_torque([a["torque"], b["torque"]]),
                     detail="+10: %.2f s (travel %.0f cm), -10: %.2f s (travel %.0f cm)" % (a["t_rec"], a["travel_cm"], b["t_rec"], b["travel_cm"]))
    for g in test_glove(pp, ckw, rep):
        if g["id"] in ("C2.1", "C2.2", "C2.3", "C2.4"):
            r[g["id"]] = g
    return r


# ---------------- SAG: robustness -------------------------------------------------------------------
SAG_CASES = {
    "random":        dict(m=(0.75, 1.30), l=(0.75, 1.60)),
    "mass-25%":      dict(m=(0.75, 0.75), l=(1.0, 1.0)),
    "mass+25%":      dict(m=(1.25, 1.25), l=(1.0, 1.0)),
    "COM-25%":       dict(m=(1.0, 1.0), l=(0.75, 0.75)),
    "COM+60%":       dict(m=(1.0, 1.0), l=(1.60, 1.60)),
    "mass+25%/COM+60%": dict(m=(1.25, 1.25), l=(1.60, 1.60)),
    "mass-25%/COM-25%": dict(m=(0.75, 0.75), l=(0.75, 0.75)),
    "nominal":       dict(m=(1.0, 1.0), l=(1.0, 1.0)),
}


def sag_params(base, case, rng):
    U = rng.uniform
    c = SAG_CASES[case]
    spec = MOTORS[base.motor]
    pp = PlantParams(motor=base.motor, torque_scale=base.torque_scale * U(0.9, 1.1), damp=base.damp * U(0.7, 1.5),
                     vib_acc=base.vib_acc, J_rotor=base.J_rotor)
    pp.m_body = spec.m_body * U(*c["m"])
    pp.l_com = L_COM * U(*c["l"])
    pp.I_body = I_BODY * U(0.7, 1.4)
    pp.tau_c = base.tau_c * U(0.5, 2.0)
    pp.vbat = U(10.4, 12.6)
    pp.box_mass = U(0.03, 0.10)
    pp.imu_offset_deg = U(-1.5, 1.5)
    pp.gyro_bias_dps = U(-0.5, 0.5)
    pp.h_imu = U(0.0, 0.12)
    return pp


def sag_one(args):
    """One randomised run of one case: static 15 s + recovery +-10 + 1 m forward with 3 s hold."""
    import random
    base, case, i, ckw = args
    rng = random.Random(1000 + i * 31 + sum(map(ord, case)))
    pp = sag_params(base, case, rng)
    seed = 1000 + i
    s = test_static(pp, seed, ckw, False, 15.0)
    a = test_recovery(pp, seed, 10.0, ckw)
    b = test_recovery(pp, seed, -10.0, ckw)
    m = test_move1m(pp, seed, ckw, False, True)
    hold5 = 0.9 < m["dist"] < 1.1 and m["hold_dx_mm"] < 50
    hold3 = m["ok"]
    tq = merge_torque([s["torque"], a["torque"], b["torque"], m["torque"]])
    return dict(case=case, i=i, static=s["ok"], rec=a["ok"] and b["ok"], t_rec=max(a["t_rec"], b["t_rec"]),
                move5=hold5, move3=hold3, torque=tq, slips=tq["slips"], m_body=pp.m_body, l_com=pp.l_com,
                dr_err=m["deadreck_err_mm"])
