"""C++ simulasyonu ile MuJoCo dijital ikizini karsilastiran grafikler -> docs/img/ikiz_*.png"""
import csv
import math
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/img"


def load(p):
    with open(p, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {k: [float(r[k]) for r in rows] for k in rows[0]}


def style(ax):
    ax.grid(True, alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)


def compare():
    c = load(ROOT / "sim/results/c1_ileri.csv")
    t = load(ROOT / "twin/results/ikiz_ileri.csv")
    tx0, ty0 = t["x"][0], t["y"][0]
    td = [math.hypot(x - tx0, y - ty0) for x, y in zip(t["x"], t["y"])]
    fig, ax = plt.subplots(2, 1, figsize=(8, 5.4), sharex=True)
    ax[0].plot(c["t"], c["x"], color="#2a6fdb", label="C++ simülasyonu")
    ax[0].plot(t["t"], td, color="#d9822b", label="MuJoCo dijital ikiz", lw=1.2)
    ax[0].set_ylabel("yol (m)")
    ax[0].legend(frameon=False, loc="upper left")
    ax[1].plot(c["t"], c["theta_deg"], color="#2a6fdb")
    ax[1].plot(t["t"], t["theta_deg"], color="#d9822b", lw=1.2)
    ax[1].set_ylabel("eğim (°)")
    ax[1].set_xlabel("zaman (s)")
    for a in ax:
        style(a)
    fig.suptitle("Aynı firmware mantığı, iki bağımsız model: 5 s bekle, 2 × ileri, 3 s dur")
    fig.tight_layout()
    fig.savefig(OUT / "ikiz_karsilastirma.png", dpi=110)
    plt.close(fig)


def dock():
    p = ROOT / "twin/results/ikiz_yanasma.csv"
    if not p.exists():
        return
    d = load(p)
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    ax.plot(d["x"], d["y"], color="#d9822b", label="robot merkezi (ikiz)")
    ax.plot(d["x"][0], d["y"][0], "o", color="#d9822b")
    ax.add_patch(plt.Circle((0, 0), 0.02, color="#333", label="direk Ø40"))
    th = [math.radians(a) for a in range(-45, 46)]
    ax.plot([0.3 * math.cos(a) for a in th], [0.3 * math.sin(a) for a in th], "--", color="#999", lw=0.8, label="30 cm / 90° bölge")
    ax.set_aspect("equal")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.legend(frameon=False, fontsize=8)
    style(ax)
    ax.set_title("Dijital ikiz: IR ile yanaşma")
    fig.tight_layout()
    fig.savefig(OUT / "ikiz_yanasma.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    compare()
    dock()
    print("cizildi")
