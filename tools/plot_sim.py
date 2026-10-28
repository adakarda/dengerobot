"""Simulasyon izlerini cizer: sim/results/*.csv -> docs/img/*.png"""
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "sim/results"
OUT = ROOT / "docs/img"
OUT.mkdir(parents=True, exist_ok=True)


def load(name):
    with open(RES / name, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {k: [float(r[k]) for r in rows] for k in rows[0]}


def style(ax):
    ax.grid(True, alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def motion(fname, title, out):
    d = load(fname)
    fig, ax = plt.subplots(3, 1, figsize=(8, 6.4), sharex=True)
    ax[0].plot(d["t"], d["x"], color="#2a6fdb")
    ax[0].set_ylabel("yol x (m)")
    ax[1].plot(d["t"], d["theta_deg"], color="#d9822b")
    ax[1].set_ylabel("egim (deg)")
    ax[2].plot(d["t"], d["dutyL"], color="#2bb3a3", lw=0.8, label="sol")
    ax[2].plot(d["t"], [-v for v in d["dutyR"]], color="#9b7cf0", lw=0.8, label="sag (ayna)")
    ax[2].set_ylabel("PWM orani")
    ax[2].set_xlabel("zaman (s)")
    ax[2].legend(frameon=False, loc="upper right")
    for a in ax:
        style(a)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(OUT / out, dpi=110)
    plt.close(fig)


def recovery():
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for fn, lab, c in (("c1_toparlanma_arti.csv", "+10 deg", "#d9822b"), ("c1_toparlanma_eksi.csv", "-10 deg", "#2a6fdb")):
        d = load(fn)
        ax.plot(d["t"], d["theta_deg"], label=lab, color=c)
    ax.axhspan(-3, 3, color="#2bb3a3", alpha=0.12, label="+-3 deg")
    ax.set_xlabel("zaman (s)")
    ax.set_ylabel("egim (deg)")
    ax.set_xlim(0.8, 6)
    ax.legend(frameon=False)
    style(ax)
    ax.set_title("C1.4: +-10 deg'den birakilinca toparlanma")
    fig.tight_layout()
    fig.savefig(OUT / "c1_toparlanma.png", dpi=110)
    plt.close(fig)


def dock():
    import math

    fig, ax = plt.subplots(figsize=(6, 5))
    for fn, c in (("c3_yanasma.csv", "#2a6fdb"), ("c5_butunlesik.csv", "#d9822b")):
        d = load(fn)
        ax.plot(d["X"], d["Y"], color=c, label="C3 yanasma" if "c3" in fn else "C5 butunlesik gorev")
        ax.plot(d["X"][0], d["Y"][0], "o", color=c)
    ax.add_patch(plt.Circle((0, 0), 0.02, color="#333"))
    th = [math.radians(a) for a in range(-45, 46)]
    ax.plot([0.3 * math.cos(a) for a in th], [0.3 * math.sin(a) for a in th], "--", color="#999", lw=0.8)
    ax.plot([0, 0.3 * math.cos(th[0])], [0, 0.3 * math.sin(th[0])], "--", color="#999", lw=0.8)
    ax.plot([0, 0.3 * math.cos(th[-1])], [0, 0.3 * math.sin(th[-1])], "--", color="#999", lw=0.8, label="30 cm / 90 deg bolge")
    ax.set_aspect("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    style(ax)
    ax.set_title("Ustten gorunus: istasyon diregi (0,0)")
    fig.tight_layout()
    fig.savefig(OUT / "yanasma_yolu.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    motion("c1_ileri.csv", "C1.2: iki 'ileri' komutu = 1 m, sonra 3 s dur", "c1_ileri.png")
    motion("c2_eldiven.csv", "C2: ileri, geri, sola, saga, dur", "c2_eldiven.png")
    recovery()
    dock()
    print("cizildi:", sorted(p.name for p in OUT.glob("*.png")))
