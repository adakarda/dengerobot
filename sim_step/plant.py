"""Wheeled inverted pendulum with stepper-motor actuators (open loop, microstepped).

Mechanics are the same wheel-pendulum equations as sim/plant.h. The actuator differs:

 * The controller commands a wheel velocity (integrated from a commanded acceleration). A DDA
   step generator (20 kHz timer, <= 1 step per timer tick) turns it into 1/16 microsteps; the
   field angle is (microstep count) * 2*pi/3200.
 * The rotor is pulled by the field through a sinusoidal torque law
        T_el = T_pullout(field speed) * sin(NP * (field - rotor))        NP = 50
   so the motor stays in sync only while |load| < T_pullout and loses poles (lost steps)
   when the load angle passes 90 electrical degrees and runs away (torque then falls, rotor
   slips whole electrical periods = 4 full steps = 64 microsteps each).
 * Electromagnetic damping acts on (field speed - rotor speed); bearing friction on rotor speed.
 * Winding current dynamics, DRV8825 decay mode, resonance of the real drive and thermal limits
   are NOT modelled (the pull-out curve lumps the current/voltage limit).
"""
import math
import random

from params import *  # noqa: F401,F403


def make_tavail(spec, scale, vbat):
    rpm = spec.curve_rpm
    ncm = spec.curve_ncm
    k = 12.0 / vbat   # curve is for 12 V: stretch the speed axis when the pack is lower
    n = len(rpm)

    def tav(rate_rad_s):
        x = abs(rate_rad_s) * 9.549296585513720 * k
        if x >= rpm[-1]:
            return ncm[-1] * scale * 0.01
        for i in range(1, n):
            if x <= rpm[i]:
                f = (x - rpm[i - 1]) / (rpm[i] - rpm[i - 1])
                return (ncm[i - 1] + f * (ncm[i] - ncm[i - 1])) * scale * 0.01
        return ncm[-1] * scale * 0.01
    return tav


class Stats:
    def __init__(self):
        self.peak = 0.0          # N m, peak |T_el| of either motor
        self.sumsq = 0.0
        self.n = 0
        self.min_margin = 1.0    # 1 - |T_el|/T_pullout, negative once past 90 el. deg
        self.tick_peaks = []     # per control tick: max over substeps and motors
        self.slips = 0           # whole electrical periods lost (each = 4 full steps)
        self.overloads = 0       # entries into |load angle| > 90 el. deg
        self.max_rpm = 0.0
        self.min_amp_at_peak = 0.0
        self.avail_at_peak = 0.0


class Plant:
    def __init__(self, p, seed=1):
        self.p = p
        self.spec = MOTORS[p.motor]
        self.rng = random.Random(seed)
        mb0 = p.m_body
        self.mb = mb0 + p.box_mass
        self.l = (mb0 * p.l_com + p.box_mass * p.box_h) / self.mb
        self.Ib = (p.I_body + mb0 * (p.l_com - self.l) ** 2 + p.box_mass * (p.box_h - self.l) ** 2)
        r = p.r
        self.Iw = 2 * 0.5 * p.m_wheel * r * r
        self.Jm = 2 * p.J_rotor
        self.a = 2 * p.m_wheel * r * r + self.Iw + self.mb * r * r + self.Jm
        self.c = self.mb * self.l * self.l + self.Ib + self.Jm
        self.Iy = p.I_yaw + (p.track ** 2 / (4 * r * r)) * (self.Iw + self.Jm)
        self.tav = make_tavail(self.spec, p.torque_scale, p.vbat)
        # state
        self.x = self.v = self.th = self.om = self.psi = self.r = 0.0
        self.xl = self.xr = 0.0
        self.relL = self.relR = 0.0
        self.cntL = self.cntR = 0      # microsteps emitted
        self.accL = self.accR = 0.0    # DDA phase
        self.lying = False
        self.accX = self.thdd = 0.0
        self.f = [0.0, 0.0, 9.81, 0.0, 0.0]
        self.kL = self.kR = 0          # electrical period index
        self.ovL = self.ovR = False
        self.stats = Stats()
        self.collect = False
        self.tel_last = (0.0, 0.0, 0.0)   # last substep T_el L, R, pull-out (N m)
        self.rate_last = 0.0
        self.total_slips_L = 0
        self.total_slips_R = 0

    # ---- measurement window -------------------------------------------------
    def reset_stats(self):
        self.stats = Stats()
        self.collect = True

    # ---- IMU (same model as sim/plant.h) ---------------------------------------
    def init_filter(self):
        self.f[0] = -9.81 * math.sin(self.th)
        self.f[2] = 9.81 * math.cos(self.th)

    def imu(self, motors_on):
        p = self.p
        g = self.rng.gauss
        th, om = self.th, self.om
        h = p.h_imu
        ax = self.accX + h * (self.thdd * math.cos(th) - om * om * math.sin(th))
        az = h * (-self.thdd * math.sin(th) - om * om * math.cos(th))
        fx, fz = ax, az + 9.81
        thm = th + p.imu_offset_deg * math.pi / 180
        fwd = fx * math.cos(thm) - fz * math.sin(thm)
        up = fx * math.sin(thm) + fz * math.cos(thm)
        vib = p.vib_acc if motors_on else 0.0
        fwd += (p.acc_noise + vib) * g(0, 1)
        up += (p.acc_noise + vib) * g(0, 1)
        side = (p.acc_noise + vib) * g(0, 1)
        gn = p.gyro_noise_dps * math.pi / 180
        gp = om + p.gyro_bias_dps * math.pi / 180 + gn * g(0, 1)
        gy = self.r + gn * g(0, 1)
        a = 1.0 - math.exp(-2 * math.pi * 42.0 / 200.0)
        f = self.f
        f[0] += a * (fwd - f[0])
        f[1] += a * (side - f[1])
        f[2] += a * (up - f[2])
        f[3] += a * (gp - f[3])
        f[4] += a * (gy - f[4])
        return (f[0], f[1], f[2], f[3], f[4])

    def set_tilt(self, th, om=0.0):
        """Hand tilt of the robot: rotor assumed to follow without losing sync (load angle kept)."""
        self.th = th
        self.om = om

    # ---- one 5 ms control tick = SUB physics substeps -------------------------------
    def run_tick(self, w0, w1, d0, d1, enable):
        p = self.p
        r_ = p.r
        hw = p.track / 2
        a, c, mb, l = self.a, self.c, self.mb, self.l
        Jm = self.Jm
        Iy = self.Iy
        tav = self.tav
        cd = p.damp
        tauc = p.tau_c
        st = self.stats
        collect = self.collect
        sin, cos, tanh, floor = math.sin, math.cos, math.tanh, math.floor
        v, om, th, rr, psi = self.v, self.om, self.th, self.r, self.psi
        x, xl, xr = self.x, self.xl, self.xr
        relL, relR = self.relL, self.relR
        cntL, cntR, accL, accR = self.cntL, self.cntR, self.accL, self.accR
        kL, kR, ovL, ovR = self.kL, self.kR, self.ovL, self.ovR
        tick_pk = 0.0
        tl_last = tr_last = amp_last = 0.0
        lying = self.lying
        twopi = 2 * math.pi
        for j in range(SUB):
            fr = (j + 0.5) / SUB
            wc = w0 + (w1 - w0) * fr
            dd = d0 + (d1 - d0) * fr
            rateL = wc - dd
            rateR = wc + dd
            # --- DDA step generator ---
            accL += rateL * DTP / MSTEP
            nL = int(accL)
            accL -= nL
            if nL > MAX_STEPS_PER_SUB:
                nL = MAX_STEPS_PER_SUB
                accL = 0.0
            elif nL < -MAX_STEPS_PER_SUB:
                nL = -MAX_STEPS_PER_SUB
                accL = 0.0
            accR += rateR * DTP / MSTEP
            nR = int(accR)
            accR -= nR
            if nR > MAX_STEPS_PER_SUB:
                nR = MAX_STEPS_PER_SUB
                accR = 0.0
            elif nR < -MAX_STEPS_PER_SUB:
                nR = -MAX_STEPS_PER_SUB
                accR = 0.0
            cntL += nL
            cntR += nR
            if lying:
                v *= 0.9
                om = 0.0
                rr = 0.0
                continue
            vl = v - rr * hw
            vr = v + rr * hw
            wl = vl / r_ - om
            wr = vr / r_ - om
            if enable:
                ampL = tav(rateL)
                ampR = tav(rateR)
                epL = NP * (cntL * MSTEP - relL)
                epR = NP * (cntR * MSTEP - relR)
                telL = ampL * sin(epL)
                telR = ampR * sin(epR)
                tl = telL + cd * (rateL - wl) - tauc * tanh(wl * 10.0)
                tr = telR + cd * (rateR - wr) - tauc * tanh(wr * 10.0)
                k = floor((epL + math.pi) / twopi)
                if k != kL:
                    self.total_slips_L += abs(k - kL)
                    if collect:
                        st.slips += abs(k - kL)
                    kL = k
                k = floor((epR + math.pi) / twopi)
                if k != kR:
                    self.total_slips_R += abs(k - kR)
                    if collect:
                        st.slips += abs(k - kR)
                    kR = k
                if collect:
                    aeL = abs(epL - twopi * kL)
                    aeR = abs(epR - twopi * kR)
                    ovl = aeL > math.pi / 2
                    ovr = aeR > math.pi / 2
                    if ovl and not ovL:
                        st.overloads += 1
                    if ovr and not ovR:
                        st.overloads += 1
                    ovL, ovR = ovl, ovr
                    # margin: 1 - |T|/Tmax inside 90 el deg, negative beyond it
                    for ae, tel, amp in ((aeL, telL, ampL), (aeR, telR, ampR)):
                        if ae <= math.pi / 2:
                            m = 1.0 - abs(tel) / amp
                        else:
                            m = -(ae - math.pi / 2)
                        if m < st.min_margin:
                            st.min_margin = m
                    at = abs(telL)
                    if abs(telR) > at:
                        at = abs(telR)
                    if at > tick_pk:
                        tick_pk = at
                    if at > st.peak:
                        st.peak = at
                        st.avail_at_peak = ampL if abs(telL) >= abs(telR) else ampR
                    st.sumsq += 0.5 * (telL * telL + telR * telR)
                    st.n += 1
                    rp = max(abs(wl), abs(wr)) * 9.549296585513720
                    if rp > st.max_rpm:
                        st.max_rpm = rp
                tl_last, tr_last, amp_last = telL, telR, ampL
            else:
                tl = -tauc * tanh(wl * 10.0)
                tr = -tauc * tanh(wr * 10.0)
                ovL = ovR = False
            tau = tl + tr
            sth = sin(th)
            cth = cos(th)
            bc = mb * r_ * l * cth - Jm
            f1 = tau + mb * r_ * l * sth * om * om
            f2 = -tau + mb * 9.81 * l * sth
            det = a * c - bc * bc
            phidd = (c * f1 - bc * f2) / det
            thdd = (a * f2 - bc * f1) / det
            rd = ((p.track / (2 * r_)) * (tr - tl) - 0.02 * rr) / Iy
            v += r_ * phidd * DTP
            om += thdd * DTP
            rr += rd * DTP
            x += v * DTP
            th += om * DTP
            psi += rr * DTP
            xl += (v - rr * hw) * DTP
            xr += (v + rr * hw) * DTP
            relL += wl * DTP
            relR += wr * DTP
            if abs(th) > 80 * math.pi / 180:
                lying = True
            self.accX = r_ * phidd
            self.thdd = thdd
        self.v, self.om, self.th, self.r, self.psi = v, om, th, rr, psi
        self.x, self.xl, self.xr = x, xl, xr
        self.relL, self.relR = relL, relR
        self.cntL, self.cntR, self.accL, self.accR = cntL, cntR, accL, accR
        self.kL, self.kR, self.ovL, self.ovR = kL, kR, ovL, ovR
        self.lying = lying
        self.tel_last = (tl_last, tr_last, amp_last)
        self.rate_last = 0.5 * (w0 + w1)
        if collect and enable:
            st.tick_peaks.append(tick_pk)
