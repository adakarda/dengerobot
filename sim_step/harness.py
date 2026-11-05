"""Closed-loop harness: plant + controller + 20 Hz glove packets (port of sim/harness.h, no docking)."""
import csv
import random

from params import *  # noqa: F401,F403
from plant import Plant
from controller import Controller


class Harness:
    def __init__(self, pp, seed=1, task="STATIC", ctrl_kwargs=None):
        self.pp = pp
        self.plant = Plant(pp, seed)
        self.ctrl = Controller(pp.motor, task, **(ctrl_kwargs or {}))
        self.rng = random.Random(seed * 7919 + 13)
        self.k = 0
        self.glove = []              # list of (t, cmd)
        self.glove_on = False
        self.glove_loss = 0.03
        self.cut_from, self.cut_to = 1e9, -1.0
        self.next_packet = 0.0
        self.motor_power = True
        self.enable = False
        self.record = False
        self.trace = []

    @property
    def t(self):
        return self.k * DT

    def _glove_input(self, t):
        if not self.glove_on or t < self.next_packet:
            return False, "STOP"
        self.next_packet = t + 0.05
        if self.cut_from <= t <= self.cut_to:
            return False, "STOP"
        if self.rng.random() < self.glove_loss:
            return False, "STOP"
        c = "STOP"
        for (te, ce) in self.glove:
            if te <= t:
                c = ce
        return True, c

    def run(self, duration, each=None):
        n = int(round(duration / DT))
        pl, ct = self.plant, self.ctrl
        for _ in range(n):
            t = self.t
            imu = pl.imu(self.enable)
            gnew, gcmd = self._glove_input(t)
            enable, w0, w1, d0, d1 = ct.step(t, imu, pl.cntL, pl.cntR, gnew, gcmd, self.motor_power)
            self.enable = enable and self.motor_power
            pl.run_tick(w0, w1, d0, d1, self.enable)
            self.k += 1
            if self.record:
                tl, tr, amp = pl.tel_last
                self.trace.append((self.t, pl.x, pl.v, pl.th, pl.psi, tl, tr, amp, pl.rate_last,
                                   ct.x, pl.total_slips_L + pl.total_slips_R, ct.mode))
            if each is not None:
                each(self)

    def write_csv(self, path):
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_s", "x_m", "v_mps", "theta_deg", "psi_deg", "T_L_Ncm", "T_R_Ncm", "T_pullout_Ncm",
                        "wheel_rate_rad_s", "x_deadreckoned_m", "slips_total", "mode"])
            for (t, x, v, th, psi, tl, tr, amp, rate, xd, sl, mode) in self.trace:
                w.writerow(["%.4f" % t, "%.5f" % x, "%.4f" % v, "%.3f" % (th * 180 / 3.141592653589793),
                            "%.3f" % (psi * 180 / 3.141592653589793), "%.2f" % (tl * 100), "%.2f" % (tr * 100),
                            "%.2f" % (amp * 100), "%.3f" % rate, "%.5f" % xd, sl, mode])
