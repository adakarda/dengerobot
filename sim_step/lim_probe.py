"""Probe what limits the recovery angle (acceleration limit / speed limit / torque clamp / pull-out)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *
import scenarios as S

def maxang(pp, ckw):
    best = 0
    for ang in (10, 12.5, 15, 17.5, 20, 22.5, 25, 27.5, 30, 35, 40):
        ok = True
        for sgn in (1, -1):
            r = S.test_recovery(pp, 7, sgn * ang, ckw)
            ok = ok and r["ok"]
        if ok: best = ang
        else: break
    return best, r["torque"]

for motor in ("17HS4401", "17HS3401S"):
    pp = PlantParams(motor=motor)
    for label, ckw in (("default (a_max 150 rad/s2, 200 rpm, torque clamp 0.8)", {}),
                       ("a_max 300", dict(a_max=300.0)),
                       ("rpm_max 300", dict(rpm_max=300.0)),
                       ("a_max 300 + rpm_max 300", dict(a_max=300.0, rpm_max=300.0)),
                       ("no torque clamp", dict(torque_limit=False)),
                       ("a_max 300 + rpm 300 + no torque clamp", dict(a_max=300.0, rpm_max=300.0, torque_limit=False))):
        b, tq = maxang(pp, ckw)
        print(motor, label, "-> max start tilt %.1f deg; last fail torque peak %.1f / avail %.1f, slips %d, min margin %.2f" % (b, tq["peak"], tq["avail_at_peak"], tq["slips"], tq["min_margin"]))
