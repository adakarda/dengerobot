"""Denge robotu modeli ve LQR kazanc tasarimi.

Calistir:  python tools/lqr_design.py
Uretir:    common/cdtp_core/src/gains.h   (firmware + simulasyon kazanclari)
           sim/plant_nominal.h            (simulasyonun nominal fiziksel modeli)

Parca gelince "OLC" yazan degerleri tartip olcup bu dosyada guncelleyin, yeniden calistirin.
"""
import math
import pathlib

import numpy as np
from scipy.linalg import expm, solve_discrete_are

import mass_budget

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ---- Fiziksel model (OLC) ----
P = dict(
    # govde degerleri tools/mass_budget.py'deki parca listesinden (kutu haric; kutuyu simulasyon ekler)
    m_body=round(mass_budget.m, 3),   # kg, tekerler haric her sey (motor govdeleri dahil)
    l_com=round(mass_budget.l, 4),    # m, teker ekseninden govde kutle merkezine
    I_body=round(mass_budget.I, 5),   # kg m^2, kutle merkezi etrafinda yunuslama ataleti
    m_wheel=0.070,      # kg, tek teker (60 g) + alüminyum adaptör
    r=0.035,            # m (70 mm teker)
    J_rotor=5.0e-7,     # kg m^2, motor rotoru (disli oncesi)
    gear=19.0,          # JGB37-520 530 RPM ~ 1:19
    Ke=0.216,           # V s/rad (cikis mili) = Kt (N m/A)
    R=4.5,              # ohm, sargi + surucu
    b_visc=0.002,       # N m s/rad, disli viskoz surtunme (motor basina)
    tau_coulomb=0.02,   # N m, disli kuru surtunme (motor basina)
    track=0.19,         # m, teker merkezleri arasi (sasi cizimi; OLC)
    I_yaw=0.012,        # kg m^2
    vbat=11.1,
)

DT = 1.0 / 200.0


def linear_model(p):
    """Durum s = [x, v, theta, omega], giris u = her motora ayni gerilim (V)."""
    r, mb, l = p["r"], p["m_body"], p["l_com"]
    Iw = 2 * 0.5 * p["m_wheel"] * r**2
    Jm = 2 * p["J_rotor"] * p["gear"] ** 2
    a = 2 * p["m_wheel"] * r**2 + Iw + mb * r**2 + Jm
    b = mb * r * l - Jm
    c = mb * l**2 + p["I_body"] + Jm
    M = np.array([[a, b], [b, c]])
    Minv = np.linalg.inv(M)
    k = 2 * p["Ke"] / p["R"]                      # iki motor, tork/gerilim
    d = 2 * (p["Ke"] ** 2 / p["R"] + p["b_visc"])  # iki motor, tork/(bagil hiz)
    g = 9.81
    # q = [phi, theta]; tork tau = k u - d (phi_dot - theta_dot), tekerlege +tau, govdeye -tau
    # M qdd = [tau, -tau + mb g l theta]
    # phi = x / r
    A = np.zeros((4, 4))
    B = np.zeros((4, 1))
    # qdd = Minv @ (F_u * u + F_phid * phid + F_thd * thd + F_th * th)
    F_u = np.array([k, -k])
    F_phid = np.array([-d, d])
    F_thd = np.array([d, -d])
    F_th = np.array([0.0, mb * g * l])
    acc_u = Minv @ F_u
    acc_phid = Minv @ F_phid
    acc_thd = Minv @ F_thd
    acc_th = Minv @ F_th
    # x' = v ; v' = r phidd ; phid = v / r
    A[0, 1] = 1
    A[1, 1] = r * acc_phid[0] / r
    A[1, 2] = r * acc_th[0]
    A[1, 3] = r * acc_thd[0]
    B[1, 0] = r * acc_u[0]
    A[2, 3] = 1
    A[3, 1] = acc_phid[1] / r
    A[3, 2] = acc_th[1]
    A[3, 3] = acc_thd[1]
    B[3, 0] = acc_u[1]
    return A, B


def discretize(A, B, dt):
    n, m = A.shape[0], B.shape[1]
    big = np.zeros((n + m, n + m))
    big[:n, :n] = A
    big[:n, n:] = B
    e = expm(big * dt)
    return e[:n, :n], e[:n, n:]


def dlqr(Ad, Bd, Q, R):
    X = solve_discrete_are(Ad, Bd, Q, R)
    return np.linalg.solve(Bd.T @ X @ Bd + R, Bd.T @ X @ Ad)


# Agirliklar: izin verilen en buyuk hata (Bryson kurali, agirlik = 1/hata^2)
W = dict(x=0.06, v=0.08, th_deg=4.0, om_dps=60.0, u_volt=5.0)  # sim ile secildi (sim/sim_main.cpp SAG testi)


def design(p, w=None):
    w = w or W
    A, B = linear_model(p)
    Ad, Bd = discretize(A, B, DT)
    Q = np.diag([1 / w["x"] ** 2, 1 / w["v"] ** 2, 1 / math.radians(w["th_deg"]) ** 2, 1 / math.radians(w["om_dps"]) ** 2])
    R = np.array([[1 / w["u_volt"] ** 2]])
    K = dlqr(Ad, Bd, Q, R)
    cl = np.linalg.eigvals(Ad - Bd @ K)
    return A, B, K.flatten(), cl


def yaw_gains(p):
    # yaw: I psi_dd = (track/2r) * 2*(Ke/R) * u_d - damping ; PD ile ~6 rad/s bant
    r, tr = p["r"], p["track"]
    kyaw = (tr / (2 * r)) * 2 * p["Ke"] / p["R"]
    wn, zeta = 8.0, 0.9
    kp = p["I_yaw"] * wn**2 / kyaw
    kd = p["I_yaw"] * 2 * zeta * wn / kyaw
    return kp, kd


def main():
    import sys
    for arg in sys.argv[1:]:  # ornek: x=0.05 v=0.1
        k, v = arg.split("=")
        W[k] = float(v)
    A, B, K, cl = design(P)
    print("agirliklar:", W)
    kp_y, kd_y = yaw_gains(P)
    print("A =\n", np.round(A, 3))
    print("B =", np.round(B.flatten(), 3))
    print("acik dongu kutuplar:", np.round(np.linalg.eigvals(A), 2))
    print("K [x, v, theta, omega] =", np.round(K, 3))
    print("kapali dongu |z|:", np.round(np.abs(cl), 4))
    print(f"yaw Kp={kp_y:.3f} V/rad  Kd={kd_y:.3f} V/(rad/s)")

    gains = f"""// OTOMATIK URETILDI: tools/lqr_design.py. Elle degistirmeyin; modeli guncelleyip yeniden calistirin.
// Durum: [x (m), v (m/s), theta (rad), omega (rad/s)], cikis: her motora gerilim (V).
// u = -K (s - s_ref)
#pragma once
namespace cdtp {{
namespace gains {{
constexpr float K_X = {K[0]:.5f}f;
constexpr float K_V = {K[1]:.5f}f;
constexpr float K_TH = {K[2]:.5f}f;
constexpr float K_OM = {K[3]:.5f}f;
constexpr float YAW_KP = {kp_y:.5f}f;
constexpr float YAW_KD = {kd_y:.5f}f;
// a_ref -> egim on-besleme (rad / (m/s^2))
constexpr float TH_PER_ACC = {th_per_acc(P):.5f}f;
}}  // namespace gains
}}  // namespace cdtp
"""
    (ROOT / "common/cdtp_core/src/gains.h").write_text(gains, encoding="utf-8")

    plant = "// OTOMATIK URETILDI: tools/lqr_design.py\n#pragma once\nstruct PlantNominal {\n"
    for k, v in P.items():
        plant += f"  static constexpr double {k} = {v!r};\n"
    plant += "};\n"
    (ROOT / "sim/plant_nominal.h").write_text(plant, encoding="utf-8")
    print("yazildi: gains.h, plant_nominal.h")


def th_per_acc(p):
    # sabit ivme a icin dengedeki egim: sin(th) = a (mb l + J/r) / (mb g l)
    r, mb, l = p["r"], p["m_body"], p["l_com"]
    Iw = 2 * 0.5 * p["m_wheel"] * r**2
    J = 2 * p["m_wheel"] * r**2 + Iw + mb * r**2
    return (mb * l + J / r) / (mb * 9.81 * l)


if __name__ == "__main__":
    main()
