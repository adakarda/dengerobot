"""Balance controller for stepper wheels (open loop, dead-reckoned from commanded microsteps).

Input of the LQR is the common relative wheel ACCELERATION u (rad/s^2). The commanded wheel
velocity wc is integrated from u, turned into microsteps by the step generator (plant.py).
State [x, v, theta, omega]:
   x     = r*(mean microstep count*MSTEP) + r*theta_est          (dead reckoning, no encoder)
   v     = r*(wc + gyro pitch rate)                              (commanded velocity is exact if in sync)
   theta = complementary filter (identical to common/cdtp_core/src/imu_filter.h)
   omega = gyro pitch rate
Reference shaping, tilt trim, glove step profiles and fall/arm logic are ports of robot_logic.cpp.
Yaw: differential step rate; yaw angle/rate are dead-reckoned from the step counts too.
"""
import math

import numpy as np
from scipy.linalg import expm, solve_discrete_are

from params import *  # noqa: F401,F403
from plant import make_tavail

DEG = math.pi / 180.0
IMU_H_ASSUMED = 0.05   # m, assumed IMU height over the axle (same as the nominal in sim/plant.h)


def clamp(x, lo, hi):
    return lo if x < lo else (hi if x > hi else x)


def wrap_pi(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


class Trapezoid:
    def __init__(self):
        self.active = False
        self.pos_ = self.vel_ = self.dist = 0.0
        self.dir = 1.0
        self.vmax = self.amax = 1.0

    def start(self, dist, vmax, amax):
        self.dist = abs(dist)
        self.dir = 1.0 if dist >= 0 else -1.0
        self.vmax, self.amax = vmax, amax
        self.pos_ = self.vel_ = 0.0
        self.active = self.dist > 1e-6

    def stop_soft(self):
        if not self.active:
            return
        brake = self.vel_ * self.vel_ / (2 * self.amax)
        self.dist = self.pos_ + brake

    def step(self, dt):
        if not self.active:
            return
        remaining = self.dist - self.pos_
        v_brake = math.sqrt(max(0.0, 2 * self.amax * remaining))
        v_target = min(self.vmax, v_brake)
        if self.vel_ < v_target:
            self.vel_ = min(v_target, self.vel_ + self.amax * dt)
        else:
            self.vel_ = max(v_target, self.vel_ - self.amax * dt)
        self.pos_ += self.vel_ * dt
        if remaining <= 1e-4 or (self.vel_ <= 1e-4 and remaining < 2e-3):
            self.pos_ = self.dist
            self.vel_ = 0.0
            self.active = False

    def pos(self):
        return self.dir * self.pos_

    def vel(self):
        return self.dir * self.vel_


class TiltFilter:
    def __init__(self):
        self.theta_raw = 0.0
        self.rate = 0.0
        self.init = False

    def update(self, imu, dt, ax=0.0):
        """ax: base forward acceleration known from the commanded steps (m/s^2); removed from the accelerometer."""
        fwd, _side, up, gp, _gy = imu
        self.rate = gp
        if ax != 0.0:
            fwd -= ax * math.cos(self.theta_raw)
            up -= ax * math.sin(self.theta_raw)
        th_acc = math.atan2(-fwd, up)
        if not self.init:
            self.theta_raw = th_acc
            self.init = True
        an = math.sqrt(fwd ** 2 + imu[1] ** 2 + up ** 2)
        trust = (1.0 - COMP_ALPHA) if abs(an - 9.81) < 2.0 else 0.002
        self.theta_raw = (1 - trust) * (self.theta_raw + self.rate * dt) + trust * th_acc

    def theta(self):
        return self.theta_raw


# ------------------------------------------------------------------------------------
# model + LQR design
# ------------------------------------------------------------------------------------
def nominal_model(m_body, J_rotor):
    """Controller's belief of the plant (no box, like the DC design in tools/lqr_design.py)."""
    r, l = R_W, L_COM
    Iw = 2 * 0.5 * M_WHEEL * r * r
    Jm = 2 * J_rotor
    a = 2 * M_WHEEL * r * r + Iw + m_body * r * r + Jm
    bc = m_body * r * l - Jm
    c = m_body * l * l + I_BODY + Jm
    return dict(a=a, bc=bc, c=c, D=a + 2 * bc + c, Gc=m_body * G * l, m=m_body)


def linear_model(mdl):
    a, bc, D, Gc = mdl["a"], mdl["bc"], mdl["D"], mdl["Gc"]
    r = R_W
    A = np.zeros((4, 4))
    B = np.zeros((4, 1))
    A[0, 1] = 1
    A[1, 2] = r * Gc / D
    A[2, 3] = 1
    A[3, 2] = Gc / D
    B[1, 0] = r * (1 - (a + bc) / D)
    B[3, 0] = -(a + bc) / D
    return A, B


def discretize(A, B, dt):
    n, m = A.shape[0], B.shape[1]
    big = np.zeros((n + m, n + m))
    big[:n, :n] = A
    big[:n, n:] = B
    e = expm(big * dt)
    return e[:n, :n], e[:n, n:]


# Bryson weights (allowed error); u_acc is in rad/s^2 of the relative wheel acceleration
WEIGHTS = dict(x=0.06, v=0.10, th_deg=4.0, om_dps=40.0, u_acc=100.0)


def design(m_body, J_rotor, w=None):
    w = w or WEIGHTS
    mdl = nominal_model(m_body, J_rotor)
    A, B = linear_model(mdl)
    Ad, Bd = discretize(A, B, DT)
    Q = np.diag([1 / w["x"] ** 2, 1 / w["v"] ** 2, 1 / math.radians(w["th_deg"]) ** 2,
                 1 / math.radians(w["om_dps"]) ** 2])
    Rm = np.array([[1 / w["u_acc"] ** 2]])
    X = solve_discrete_are(Ad, Bd, Q, Rm)
    K = np.linalg.solve(Bd.T @ X @ Bd + Rm, Bd.T @ X @ Ad).flatten()
    cl = np.linalg.eigvals(Ad - Bd @ K.reshape(1, 4))
    ol = np.linalg.eigvals(A)
    # a_ref -> lean feed-forward (rad per m/s^2): sin(th)=a*(a+bc)/(r*Gc)
    th_per_acc = (mdl["a"] + mdl["bc"]) / (R_W * mdl["Gc"])
    return mdl, K, cl, ol, th_per_acc


class Controller:
    # modes
    STANDBY, BALANCE, FALLEN = 0, 1, 2

    def __init__(self, motor="17HS4401", task="STATIC", torque_frac=0.8, a_max=150.0,
                 rpm_max=200.0, weights=None, torque_limit=True, acc_comp=True, u_lpf_hz=10.0, om_lpf_hz=20.0):
        spec = MOTORS[motor]
        self.mdl, self.K, self.cl, self.ol, self.th_per_acc = design(spec.m_body, spec.J_rotor, weights)
        self.tav = make_tavail(spec, 1.0, VBAT_NOM)   # controller uses the nominal 12 V curve at 11.1 V
        self.torque_frac = torque_frac
        self.a_max = a_max
        self.w_max = rpm_max * 2 * math.pi / 60
        self.torque_limit = torque_limit
        # Aeff: torque per unit of wheel acceleration, both motors (see RAPOR)
        m = self.mdl
        self.A_eff = m["a"] - (m["a"] + m["bc"]) ** 2 / m["D"]
        self.task = task
        self.tilt = TiltFilter()
        self.mode = self.STANDBY
        self.t = 0.0
        self.arm_t = 0.0
        self.fall_t = 0.0
        self.x = self.v = self.psi = 0.0
        self.wc = 0.0    # commanded common relative wheel velocity (rad/s)
        self.dl = 0.0    # commanded differential wheel velocity (rad/s)
        self.xRaw = self.vRaw = 0.0
        self.xRef = self.vRef = self.aRef = 0.0
        self.psiRef = self.rRef = 0.0
        self.xStart = self.psiStart = 0.0
        self.trim = 0.0
        self.lin = Trapezoid()
        self.rot = Trapezoid()
        self.linActive = self.rotActive = False
        self.gloveCmd = "STOP"
        self.prevCmd = "STOP"
        self.gloveLastT = -10.0
        self.gloveAlive = False
        self.u_last = 0.0
        self.sat_ticks = 0
        self.clamp_ticks = 0
        self.enable = False
        self.acc_comp = acc_comp
        self.ax_cmd = 0.0
        self.u_alpha = 1.0 if u_lpf_hz <= 0 else 1.0 - math.exp(-2 * math.pi * u_lpf_hz * DT)
        self.om_alpha = 1.0 if om_lpf_hz <= 0 else 1.0 - math.exp(-2 * math.pi * om_lpf_hz * DT)
        self.u_f = 0.0
        self.om_f = 0.0

    # ---------------------------------------------------------------------------
    def enter_balance(self):
        self.mode = self.BALANCE
        self.xRef = self.xRaw = self.x
        self.vRef = self.aRef = self.vRaw = 0.0
        self.psiRef = self.psi
        self.rRef = 0.0
        self.linActive = self.rotActive = False

    def start_step(self, c):
        if c in ("FWD", "BACK"):
            self.xStart = self.xRaw
            self.lin.start(STEP_DIST_M if c == "FWD" else -STEP_DIST_M, STEP_VMAX, STEP_ACCEL)
            self.linActive = True
        elif c in ("LEFT", "RIGHT"):
            self.psiStart = self.psiRef
            a = TURN_ANGLE_DEG * DEG
            self.rot.start(a if c == "LEFT" else -a, TURN_RATE_DEG * DEG, TURN_ACCEL_DEG * DEG)
            self.rotActive = True

    def handle_glove(self, t, new, cmd_in):
        cmd = self.gloveCmd
        if new:
            self.gloveLastT = t
            cmd = cmd_in
        was_alive = self.gloveAlive
        self.gloveAlive = (t - self.gloveLastT) < GLOVE_TIMEOUT_S
        if not self.gloveAlive:
            cmd = "STOP"
        edge = cmd != self.prevCmd
        self.prevCmd = cmd
        self.gloveCmd = cmd
        motion = cmd in ("FWD", "BACK", "LEFT", "RIGHT")
        if self.mode != self.BALANCE or self.task == "STATIC":
            return
        if was_alive and not self.gloveAlive and (self.linActive or self.rotActive):
            self.lin.stop_soft()
            self.rot.stop_soft()
        if edge and motion:
            if self.linActive or self.rotActive:
                self.lin.stop_soft()
                self.rot.stop_soft()
            else:
                self.start_step(cmd)

    # ---------------------------------------------------------------------------
    def step(self, t, imu, nL, nR, glove_new, glove_cmd, motor_power):
        """Returns (enable, w0, w1, d0, d1): ramp of common/differential wheel velocity over this tick."""
        dt = DT
        self.t = t
        self.tilt.update(imu, dt, self.ax_cmd if self.acc_comp else 0.0)
        th = self.tilt.theta()
        om = self.tilt.rate
        r = R_W
        self.x = r * 0.5 * (nL + nR) * MSTEP + r * th
        self.v = r * (self.wc + om)
        self.psi = r * (nR - nL) * MSTEP / TRACK
        self.handle_glove(t, glove_new, glove_cmd)

        if self.mode == self.BALANCE:
            self.fall_t = self.fall_t + dt if abs(th) > FALL_ANGLE_DEG * DEG else 0.0
            if self.fall_t > FALL_HOLD_S:
                self.mode = self.FALLEN
                self.linActive = self.rotActive = False
        if not motor_power and self.mode == self.BALANCE:
            self.mode = self.STANDBY
            self.arm_t = 0.0
            self.linActive = self.rotActive = False

        if self.mode == self.STANDBY:
            self.arm_t = self.arm_t + dt if (motor_power and abs(th) < ARM_ANGLE_DEG * DEG) else 0.0
            if self.arm_t > ARM_HOLD_S:
                self.enter_balance()
        elif self.mode == self.FALLEN:
            if abs(th) < 20 * DEG:
                self.mode = self.STANDBY
                self.arm_t = 0.0

        if self.mode != self.BALANCE:
            self.enable = False
            self.wc = 0.0
            self.dl = 0.0
            return (False, 0.0, 0.0, 0.0, 0.0)

        # ---- reference generation (port) ----
        if self.linActive:
            self.lin.step(dt)
            self.xRaw = self.xStart + self.lin.pos()
            if not self.lin.active:
                self.linActive = False
        else:
            self.vRaw = 0.0
            self.xRaw = clamp(self.xRaw, self.x - 0.15, self.x + 0.15)
        w = REF_SHAPING_W
        self.aRef = w * w * (self.xRaw - self.xRef) - 2 * w * self.vRef
        self.vRef += self.aRef * dt
        self.xRef += self.vRef * dt
        if self.rotActive:
            self.rot.step(dt)
            self.psiRef = self.psiStart + self.rot.pos()
            self.rRef = self.rot.vel()
            if not self.rot.active:
                self.rotActive = False
                self.rRef = 0.0
        else:
            self.rRef = 0.0

        # ---- balance LQR with acceleration input ----
        th_ref = TH_FF_GAIN * self.th_per_acc * self.aRef
        ex = clamp(self.x - self.xRef, -0.25, 0.25)
        still = (not self.linActive) and (not self.rotActive) and abs(self.vRef) < 0.01 and abs(self.rRef) < 0.05
        if still:
            self.trim = clamp(self.trim - TRIM_RATE * ex * dt, -TRIM_MAX_DEG * DEG, TRIM_MAX_DEG * DEG)
        K = self.K
        self.om_f += self.om_alpha * (om - self.om_f)
        u = -(K[0] * ex + K[1] * (self.v - self.vRef) + K[2] * (th - th_ref - self.trim) + K[3] * self.om_f)
        self.u_f += self.u_alpha * (u - self.u_f)
        u = self.u_f
        # acceleration limit 1: absolute
        u = clamp(u, -self.a_max, self.a_max)
        # acceleration limit 2: keep the predicted per-motor torque inside the pull-out curve
        if self.torque_limit:
            m = self.mdl
            sth = math.sin(th)
            b_th = (m["a"] + m["bc"]) * m["Gc"] * sth / m["D"]
            lim = self.torque_frac * self.tav(self.wc) * 2.0       # total (both motors) allowed torque
            lo = (-lim - b_th) / self.A_eff
            hi = (lim - b_th) / self.A_eff
            if lo > hi:
                lo = hi = 0.5 * (lo + hi)
            u2 = clamp(u, lo, hi)
            if u2 != u:
                self.clamp_ticks += 1
            u = u2
        w0 = self.wc
        w1 = clamp(w0 + u * dt, -self.w_max, self.w_max)
        if w1 != w0 + u * dt:
            self.sat_ticks += 1
        self.wc = w1
        self.u_last = u
        mm = self.mdl
        thdd_est = (mm["Gc"] * math.sin(th) - (mm["a"] + mm["bc"]) * u) / mm["D"]
        # forward specific acceleration at the IMU (base acceleration + lever arm of the pitch acceleration)
        self.ax_cmd = R_W * (u + thdd_est) + IMU_H_ASSUMED * thdd_est * math.cos(th)

        # ---- yaw: differential wheel velocity ----
        r_cmd = self.rRef + 6.0 * wrap_pi(self.psiRef - self.psi)
        dl_target = r_cmd * TRACK / (2 * r)
        d0 = self.dl
        self.dl = d0 + clamp(dl_target - d0, -25.0 * dt, 25.0 * dt)
        self.enable = True
        return (True, w0, w1, d0, self.dl)
