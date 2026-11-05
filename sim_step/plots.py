"""PNG plots from the CSV traces and result tables (matplotlib optional)."""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import scenarios as S


def load(name):
    p = os.path.join(S.OUT, name)
    return np.genfromtxt(p, delimiter=",", names=True)


def torque_panel(ax, d, label, color):
    ax.plot(d["t_s"], np.abs(d["T_L_Ncm"]), color=color, lw=1.0, label="%s |T| per motor" % label)
    ax.plot(d["t_s"], d["T_pullout_Ncm"], color=color, lw=1.0, ls="--", label="%s pull-out" % label)


def make(acc, sens, lim, SENS):
    cols = {"17HS4401": "#1f77b4", "17HS3401S": "#d95f02"}
    for fname, key, title, t0, t1 in (("recovery_plus10.png", "c1_recovery_plus", "Recovery from +10 deg", 0.95, 4.0),
                                      ("run_1m_forward.png", "c1_forward", "1 m forward (2 x 0.5 m) + 3 s hold", 5.5, 17.0)):
        fig, ax = plt.subplots(4, 1, figsize=(8, 9), sharex=True)
        for m, c in cols.items():
            d = load("%s_%s.csv" % (m, key))
            k = (d["t_s"] >= t0) & (d["t_s"] <= t1)
            d = d[k]
            ax[0].plot(d["t_s"], d["theta_deg"], color=c, label=m)
            ax[1].plot(d["t_s"], d["x_m"], color=c, label=m)
            ax[2].plot(d["t_s"], d["wheel_rate_rad_s"] * 9.5493, color=c, label=m)
            torque_panel(ax[3], d, m, c)
        ax[0].set_ylabel("pitch (deg)")
        ax[1].set_ylabel("position (m)")
        ax[2].set_ylabel("commanded wheel rpm")
        ax[3].set_ylabel("N.cm (one motor)")
        ax[3].set_xlabel("time (s)")
        ax[3].legend(fontsize=7, ncol=2)
        ax[0].set_title(title + " - dashed = available pull-out torque")
        for a in ax:
            a.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(S.OUT, fname), dpi=110)
        plt.close(fig)
    # recovery limit vs torque scale
    fig, ax = plt.subplots(figsize=(7, 4))
    w = 0.35
    scs = sorted({sc for (_, sc) in lim})
    for i, (m, c) in enumerate(cols.items()):
        v = [min(lim[(m, sc)][1][0], lim[(m, sc)][-1][0]) for sc in scs]
        ax.bar(np.arange(len(scs)) + i * w, v, w, color=c, label=m)
    ax.set_xticks(np.arange(len(scs)) + w / 2)
    ax.set_xticklabels(["torque x%.2f" % s for s in scs])
    ax.set_ylabel("largest recovered start tilt (deg)")
    ax.set_title("Recovery limit vs available pull-out torque")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(S.OUT, "recovery_limit.png"), dpi=110)
    plt.close(fig)
